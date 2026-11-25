"""Публикация треда в Threads через Threads API (graph.threads.com).

Подключение: команда /threads в Telegram-боте даёт ссылку авторизации, пользователь присылает
адрес, на который его перенаправило, бот обменивает код на долгоживущий токен (60 дней) и сохраняет его в БД.
Токен продлевается автоматически раз в 30 дней. Можно задать и вручную через THREADS_USER_ID / THREADS_ACCESS_TOKEN.

Публикация: для каждого сообщения создаётся контейнер (media_type=TEXT) и публикуется;
следующие сообщения создаются с reply_to_id предыдущего — так получается тред.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from . import db
from .settings import env, env_problem, settings

log = logging.getLogger(__name__)
GRAPH = "https://graph.threads.com"
BASE = f"{GRAPH}/v1.0"
LIMIT = 500
SCOPES = "threads_basic,threads_content_publish,threads_manage_replies"


class ThreadsError(RuntimeError):
    pass


def token() -> str:
    return db.kv_get("threads_token") or settings.threads_token


def user_id() -> str:
    return db.kv_get("threads_user_id") or settings.threads_user_id


def enabled() -> bool:
    return bool(token() and user_id())


# ---------- подключение ----------

def app_id() -> str:
    return env("THREADS_APP_ID")


def app_secret() -> str:
    return env("THREADS_APP_SECRET")


def redirect_uri() -> str:
    return env("THREADS_REDIRECT_URI", "https://localhost/")


def authorize_url() -> str:
    problems = [p for p in (env_problem("THREADS_APP_ID"), env_problem("THREADS_APP_SECRET")) if p]
    if problems:
        raise ThreadsError("Threads не настроен:\n" + "\n".join(problems))
    return "https://threads.com/oauth/authorize?" + urlencode({
        "client_id": app_id(), "redirect_uri": redirect_uri(),
        "scope": SCOPES, "response_type": "code"})


def extract_code(text: str) -> str:
    m = re.search(r"code=([^&#\s]+)", text)
    return (m.group(1) if m else text.strip()).removesuffix("#_")


def connect(code_or_url: str) -> str:
    """Обменять код авторизации на долгоживущий токен, сохранить его. Возвращает @username."""
    code = extract_code(code_or_url)
    r = httpx.post(f"{GRAPH}/oauth/access_token", timeout=60, data={
        "client_id": app_id(), "client_secret": app_secret(),
        "grant_type": "authorization_code", "redirect_uri": redirect_uri(), "code": code})
    short = r.json()
    if "access_token" not in short:
        raise ThreadsError(f"Код не принят: {short.get('error', short)}")
    r = httpx.get(f"{GRAPH}/access_token", timeout=60, params={
        "grant_type": "th_exchange_token", "client_secret": app_secret(),
        "access_token": short["access_token"]})
    long = r.json()
    if "access_token" not in long:
        raise ThreadsError(f"Не удалось получить долгоживущий токен: {long.get('error', long)}")
    me = httpx.get(f"{BASE}/me", timeout=60,
                   params={"fields": "id,username", "access_token": long["access_token"]}).json()
    if "id" not in me:
        raise ThreadsError(f"Не удалось получить профиль: {me.get('error', me)}")
    db.kv_set("threads_token", long["access_token"])
    db.kv_set("threads_user_id", str(me["id"]))
    db.kv_set("threads_token_refreshed", datetime.now(timezone.utc).isoformat())
    return me.get("username", me["id"])


# ---------- публикация ----------

def _post(path: str, **params) -> dict:
    resp = httpx.post(f"{BASE}/{path}", params={**params, "access_token": token()}, timeout=60)
    body = resp.json()
    if resp.status_code >= 400 or "error" in body:
        raise ThreadsError(f"{path}: {body.get('error', body)}")
    return body


def publish_text(text: str, reply_to: str | None = None) -> str:
    params = {"media_type": "TEXT", "text": text[:LIMIT]}
    if reply_to:
        params["reply_to_id"] = reply_to
    creation = _post(f"{user_id()}/threads", **params)["id"]
    time.sleep(3)   # даём контейнеру обработаться перед публикацией
    return _post(f"{user_id()}/threads_publish", creation_id=creation)["id"]


def publish_thread(messages: list[str]) -> list[str]:
    ids: list[str] = []
    for text in messages:
        ids.append(publish_text(text, reply_to=ids[-1] if ids else None))
    return ids


def refresh_token_if_needed() -> None:
    """Продлевает токен раз в 30 дней (токен живёт 60)."""
    if not enabled():
        return
    last = db.kv_get("threads_token_refreshed")
    if last and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(days=30):
        return
    body = httpx.get(f"{GRAPH}/refresh_access_token", timeout=60,
                     params={"grant_type": "th_refresh_token", "access_token": token()}).json()
    if "access_token" not in body:
        log.error("Не удалось продлить токен Threads: %s", body)
        return
    db.kv_set("threads_token", body["access_token"])
    db.kv_set("threads_token_refreshed", datetime.now(timezone.utc).isoformat())
    log.info("Токен Threads продлён")
