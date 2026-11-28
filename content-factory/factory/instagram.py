"""Публикация в Instagram через Content Publishing API.

Почему так устроено:
- Instagram не принимает файлы напрямую: он сам скачивает их по публичному адресу. Воркер на Render
  не виден из интернета, поэтому файлы кладутся в таблицу media (Postgres), а отдаёт их маленький
  веб-сервис media_server.py по адресу MEDIA_BASE_URL/m/<случайный токен>.jpg. Токен из 32 случайных
  байт: угадать адрес нельзя, а сами файлы — это то, что и так уходит в публичную ленту.
- Файлы сохраняются в БД ещё при отправке пакета в Telegram: диск воркера стирается при каждом деплое,
  а между отправкой и публикацией проходят часы.
- Поддерживаются оба вида токенов: токен системного пользователя Meta Business (EAA…, graph.facebook.com,
  не истекает) и токен «Instagram API с входом через Instagram» (IG…, graph.instagram.com, живёт 60 дней,
  продлевается автоматически). Эндпоинты публикации у них одинаковые.
- Instagram принимает только JPEG, поэтому PNG слайдов перекодируются.
"""
from __future__ import annotations

import io
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import delete, select

from . import db
from .settings import env

log = logging.getLogger(__name__)
VERSION = "v21.0"
CAPTION_LIMIT = 2200
HASHTAG_LIMIT = 30


class InstagramError(RuntimeError):
    pass


# ---------- подключение ----------

def _env_token() -> str:
    return env("INSTAGRAM_ACCESS_TOKEN")


def token() -> str:
    """Продлённый токен из БД, если он получен из текущего значения переменной; иначе сама переменная.
    Так новый токен, заданный в Render, сразу вытесняет старый продлённый."""
    raw = _env_token()
    if raw and db.kv_get("ig_token_env") == raw[-12:] and db.kv_get("ig_token"):
        return db.kv_get("ig_token") or raw
    return raw


def graph() -> str:
    host = "graph.instagram.com" if token().startswith("IG") else "graph.facebook.com"
    return f"https://{host}/{VERSION}"


def user_id() -> str:
    return env("INSTAGRAM_USER_ID") or db.kv_get("ig_user_id") or ""


def media_base() -> str:
    return env("MEDIA_BASE_URL").rstrip("/")


def problems() -> list[str]:
    out = []
    if not _env_token():
        out.append("не задан INSTAGRAM_ACCESS_TOKEN")
    if not media_base():
        out.append("не задан MEDIA_BASE_URL (адрес сервиса biglife-media)")
    return out


def enabled() -> bool:
    return not problems()


def _scrub(text: str) -> str:
    tok = token()
    return text.replace(tok, "***") if tok else text


def _request(method: str, path: str, **params) -> dict:
    url = path if path.startswith("http") else f"{graph()}/{path}"
    try:
        resp = httpx.request(method, url, params={**params, "access_token": token()}, timeout=120)
    except httpx.HTTPError as exc:   # в тексте ошибки httpx есть URL с токеном
        raise InstagramError(f"{path}: сетевая ошибка {type(exc).__name__}") from None
    try:
        body = resp.json()
    except ValueError:
        raise InstagramError(f"{path}: ответ {resp.status_code} не JSON") from None
    if resp.status_code >= 400 or "error" in body:
        err = body.get("error", body)
        msg = err.get("error_user_msg") or err.get("message") if isinstance(err, dict) else str(err)
        raise InstagramError(_scrub(f"{path}: {msg}"))
    return body


def account() -> dict:
    """@username и квота публикаций — для /status и /instagram."""
    uid = user_id()
    if not uid:
        if not token().startswith("IG"):
            raise InstagramError("для токена Meta Business нужен INSTAGRAM_USER_ID")
        me = _request("GET", "me", fields="user_id,username")
        uid = str(me.get("user_id") or me["id"])
        db.kv_set("ig_user_id", uid)
    info = _request("GET", uid, fields="username")
    try:
        quota = _request("GET", f"{uid}/content_publishing_limit", fields="quota_usage,config")["data"][0]
        info["quota"] = f"{quota['quota_usage']} из {quota['config']['quota_total']} за сутки"
    except (InstagramError, KeyError, IndexError):
        info["quota"] = "неизвестно"
    return info


def refresh_token_if_needed() -> None:
    """Токен с входом через Instagram живёт 60 дней — продлеваем раз в 30. Токен Meta Business не истекает."""
    raw = _env_token()
    if not raw.startswith("IG"):
        return
    last = db.kv_get("ig_token_refreshed") if db.kv_get("ig_token_env") == raw[-12:] else None
    if last and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(days=30):
        return
    try:
        body = _request("GET", "https://graph.instagram.com/refresh_access_token", grant_type="ig_refresh_token")
    except InstagramError as exc:
        log.error("Не удалось продлить токен Instagram: %s", exc)
        return
    db.kv_set("ig_token", body["access_token"])
    db.kv_set("ig_token_env", raw[-12:])
    db.kv_set("ig_token_refreshed", datetime.now(timezone.utc).isoformat())


# ---------- файлы для Instagram ----------

def to_jpeg(path: Path) -> bytes:
    from PIL import Image
    with Image.open(path) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=92, optimize=True)
        return buf.getvalue()


def store_media(post_id: int, files: list[str], is_reel: bool) -> list[dict]:
    """Кладёт файлы поста в БД и возвращает [{token, kind}] в порядке публикации.
    Для Reels: видео, затем обложка. Старые файлы (старше 14 дней) удаляются."""
    out = []
    with db.engine.begin() as c:
        c.execute(delete(db.media).where(db.media.c.created_at < db.now() - timedelta(days=14)))
        c.execute(delete(db.media).where(db.media.c.post_id == post_id))
        for f in files:
            p = Path(f)
            if p.suffix.lower() == ".mp4":
                data, mime, ext, kind = p.read_bytes(), "video/mp4", "mp4", "video"
            else:
                data, mime, ext, kind = to_jpeg(p), "image/jpeg", "jpg", "cover" if is_reel else "image"
            tok = f"{secrets.token_urlsafe(32)}.{ext}"
            c.execute(db.media.insert().values(token=tok, post_id=post_id, mime=mime, data=data,
                                               created_at=db.now()))
            out.append({"token": tok, "kind": kind})
    db.kv_set(f"ig_media:{post_id}", json.dumps(out))
    return out


def media_for(post_id: int) -> list[dict]:
    raw = db.kv_get(f"ig_media:{post_id}")
    items = json.loads(raw) if raw else []
    with db.engine.begin() as c:
        have = {r[0] for r in c.execute(select(db.media.c.token).where(db.media.c.post_id == post_id))}
    return [m for m in items if m["token"] in have]


def url(tok: str) -> str:
    return f"{media_base()}/m/{tok}"


def wake_media_server(timeout: float = 150) -> None:
    """Бесплатный веб-сервис Render засыпает без запросов; будим его до того, как Instagram придёт за файлом."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            if httpx.get(f"{media_base()}/health", timeout=30).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        if time.monotonic() > deadline:
            raise InstagramError(f"сервис файлов {media_base()} не отвечает")
        time.sleep(5)


# ---------- публикация ----------

def caption(pkg: dict) -> str:
    tags = [f"#{h.lstrip('#')}" for h in pkg.get("hashtags", [])][:HASHTAG_LIMIT]
    body = pkg.get("caption_ru", "")
    if pkg.get("source_line"):
        body += f"\n\nИсточник: {pkg['source_line']}"
    tail = ("\n\n" + " ".join(tags)) if tags else ""
    return body[: CAPTION_LIMIT - len(tail)] + tail


def _wait(container: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while True:
        st = _request("GET", container, fields="status_code,status")
        code = st.get("status_code")
        if code in ("FINISHED", "PUBLISHED"):
            return
        if code in ("ERROR", "EXPIRED"):
            raise InstagramError(f"Instagram не принял файл: {st.get('status', code)}")
        if time.monotonic() > deadline:
            raise InstagramError("Instagram слишком долго обрабатывает файл")
        time.sleep(5)


def _create(**params) -> str:
    return _request("POST", f"{user_id()}/media", **params)["id"]


def _image_child(tok: str, alt: str) -> str:
    try:
        return _create(image_url=url(tok), is_carousel_item="true", alt_text=alt)
    except InstagramError as exc:
        if "alt_text" not in str(exc):
            raise
        return _create(image_url=url(tok), is_carousel_item="true")   # alt-текст не поддержан — без него


def publish(post: dict) -> dict:
    """Публикует пост и возвращает {media_id, permalink}."""
    if not user_id():
        account()                       # для токена с входом через Instagram id определяется сам
    pkg = post["package"]
    items = media_for(post["id"])
    if not items:
        raise InstagramError("файлы поста не найдены, нажмите «Переделать», чтобы собрать их заново")
    wake_media_server()
    text = caption(pkg)
    if pkg.get("format") == "reels":
        video = next(m for m in items if m["kind"] == "video")
        cover = next((m for m in items if m["kind"] == "cover"), None)
        params = dict(media_type="REELS", video_url=url(video["token"]), caption=text, share_to_feed="true")
        if cover:
            params["cover_url"] = url(cover["token"])
        if env("INSTAGRAM_TRIAL_REELS", "1") != "0":
            # пробный Reels: сначала неподписанным, в ленту подписчиков — сам, если хорошо зайдёт
            params["trial_params"] = json.dumps({"graduation_strategy": env("INSTAGRAM_TRIAL_STRATEGY", "SS_PERFORMANCE")})
        try:
            container = _create(**params)
        except InstagramError as exc:
            if "trial" not in str(exc).lower():
                raise
            log.warning("Пробные Reels недоступны, публикую обычным: %s", exc)
            params.pop("trial_params")
            container = _create(**params)
        _wait(container, timeout=600)
    else:
        images = [m for m in items if m["kind"] == "image"][:20]
        alt = pkg.get("alt_text", "")
        if len(images) == 1:
            container = _create(image_url=url(images[0]["token"]), caption=text, alt_text=alt)
        else:
            children = [_image_child(m["token"], alt) for m in images]
            for ch in children:
                _wait(ch, timeout=120)
            container = _create(media_type="CAROUSEL", children=",".join(children), caption=text)
        _wait(container, timeout=180)
    media_id = _request("POST", f"{user_id()}/media_publish", creation_id=container)["id"]
    try:
        permalink = _request("GET", media_id, fields="permalink").get("permalink", "")
    except InstagramError:
        permalink = ""
    return {"media_id": media_id, "permalink": permalink}


# ---------- очередь ----------

def state(post_id: int) -> dict:
    raw = db.kv_get(f"ig:{post_id}")
    return json.loads(raw) if raw else {}


def set_state(post_id: int, **values) -> dict:
    st = {**state(post_id), **values}
    db.kv_set(f"ig:{post_id}", json.dumps(st, ensure_ascii=False))
    return st


def queue(post_id: int, at: datetime) -> None:
    set_state(post_id, state="queued", at=at.astimezone(timezone.utc).isoformat(), error="")


def all_states() -> dict[int, dict]:
    with db.engine.begin() as c:
        rows = c.execute(select(db.kv.c.key, db.kv.c.value).where(db.kv.c.key.like("ig:%"))).all()
    out = {}
    for key, value in rows:
        tail = key.split(":", 1)[1]
        if tail.isdigit() and value:
            out[int(tail)] = json.loads(value)
    return out


def due(now: datetime | None = None) -> list[int]:
    now = now or datetime.now(timezone.utc)
    return sorted(pid for pid, st in all_states().items()
                  if st.get("state") == "queued" and datetime.fromisoformat(st["at"]) <= now)
