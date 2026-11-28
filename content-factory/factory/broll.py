"""Иллюстрации под каждую фразу Reels: 2–3 картинки по ~1,5 с (требование владельца 28.11).

Источники: сток Pixabay (фото и видео, ключ PIXABAY_API_KEY на Render) с запасным Openverse CC0,
карты стран Natural Earth (общественное достояние) рисуются кодом, фото исследователей — Википедия
(people.py), обложка журнала — наша типографская карточка плюс снимок страницы статьи, наши фото,
иллюстрации и видео из отчётов. Не нашлась картинка — иллюстрация выпадает, а не заменяется случайной:
случайное фото уже подставило волонтёра-мужчину в историю про бабушку.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import subprocess
from pathlib import Path

import httpx
from urllib.parse import unquote, urlparse

from .settings import OUTPUT_DIR, TEMPLATES_DIR, env

log = logging.getLogger(__name__)
CACHE = OUTPUT_DIR / "broll"


# ---------- сток ----------
# Pexels закрыл выдачу новых ключей (28.11), поэтому основной сток — Pixabay: фото и видео,
# лицензия без обязательного указания авторства, ключ бесплатный (PIXABAY_API_KEY на Render).
# Запасной — Openverse без ключа, но только CC0 и общественное достояние: картинки под CC BY
# потребовали бы подписи автора в кадре, а её в Reels некуда поставить.

def _get(url: str, **kw) -> dict:
    try:
        r = httpx.get(url, timeout=30, headers={"User-Agent": "biglife-content-factory/1.0"}, **kw)
        return r.json() if r.status_code == 200 else {}
    except (httpx.HTTPError, ValueError) as exc:
        log.info("Сток %s: %s", url.split("/")[2], type(exc).__name__)
        return {}


def _download(url: str, suffix: str) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:20] + suffix)
    if path.exists():
        return path
    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True,
                          headers={"User-Agent": "biglife-content-factory/1.0"}) as r:
            r.raise_for_status()
            with path.open("wb") as fh:
                for chunk in r.iter_bytes():
                    fh.write(chunk)
    except httpx.HTTPError as exc:
        log.info("Скачать %s не вышло: %s", url[:60], type(exc).__name__)
        path.unlink(missing_ok=True)
        return None
    return path


def _pixabay_photos(query: str) -> list[tuple[str, str]]:
    key = env("PIXABAY_API_KEY")
    if not key:
        return []
    data = _get("https://pixabay.com/api/", params={"key": key, "q": query[:100], "image_type": "photo",
                                                    "orientation": "vertical", "safesearch": "true", "per_page": 10})
    return [(f"pb{h['id']}", h["largeImageURL"]) for h in data.get("hits", []) if h.get("largeImageURL")]


def _openverse_photos(query: str) -> list[tuple[str, str]]:
    data = _get("https://api.openverse.org/v1/images/", params={"q": query[:200], "license": "cc0,pdm",
                                                               "aspect_ratio": "tall", "page_size": 10, "mature": "false"})
    return [(f"ov{h['id']}", h["url"]) for h in data.get("results", []) if h.get("url")]


def stock_photo(query: str, used: set[str]) -> Path | None:
    for provider in (_pixabay_photos, _openverse_photos):
        for pid, url in provider(query):
            if pid in used:
                continue
            used.add(pid)
            path = _download(url, ".jpg")
            if path:
                return path
    return None


def stock_video(query: str, used: set[str]) -> Path | None:
    key = env("PIXABAY_API_KEY")
    if not key:
        return None
    from .clips import prepare
    data = _get("https://pixabay.com/api/videos/", params={"key": key, "q": query[:100], "safesearch": "true", "per_page": 8})
    for h in data.get("hits", []):
        pid = f"pbv{h['id']}"
        if pid in used:
            continue
        files = [f for f in (h.get("videos") or {}).values() if f.get("url") and f.get("height", 0) >= 720]
        if not files:
            continue
        used.add(pid)
        f = min(files, key=lambda f: f["height"])          # самое лёгкое из годных: всё равно режем до 1080×1920
        src = _download(f["url"], ".mp4")
        return prepare(src, 0.5, pid) if src else None
    return None


def stock_status() -> str:
    """Строка для бота и отчёта: откуда сейчас берётся сток."""
    return "Pixabay (фото и видео)" if env("PIXABAY_API_KEY") else "только Openverse (CC0), без видео: нет PIXABAY_API_KEY"


# ---------- карты ----------

_COUNTRIES = None


def _countries() -> list[dict]:
    global _COUNTRIES
    if _COUNTRIES is None:
        _COUNTRIES = json.loads((TEMPLATES_DIR / "assets" / "countries.json").read_text(encoding="utf-8"))
    return _COUNTRIES


def map_svg(country: str, accent: str = "#ff954c") -> str | None:
    """Силуэт страны (выделен) на фоне соседей, в рамке 900×700. Название — по-английски или по-русски."""
    q = country.strip().lower()
    target = next((c for c in _countries() if q in (c["name"].lower(), c["ru"].lower(), (c["iso"] or "").lower())), None)
    if not target:
        target = next((c for c in _countries() if q and (q in c["name"].lower() or q in c["ru"].lower())), None)
    if not target:
        return None

    def rings(c):
        return c["coords"] if c["type"] == "Polygon" else [r for poly in c["coords"] for r in poly]
    pts = [p for r in rings(target) for p in r]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    if lon1 - lon0 > 180:                                   # Россия, США с Аляской: берём основную часть
        lon0 = max(lon0, -170)
    pad = max(lon1 - lon0, lat1 - lat0) * 0.35 + 2
    lon0, lon1, lat0, lat1 = lon0 - pad, lon1 + pad, lat0 - pad, lat1 + pad
    k = math.cos(math.radians((lat0 + lat1) / 2))
    W, H = 900, 700
    sx, sy = W / ((lon1 - lon0) * k), H / (lat1 - lat0)
    s = min(sx, sy)
    ox, oy = (W - (lon1 - lon0) * k * s) / 2, (H - (lat1 - lat0) * s) / 2

    def path(c):
        out = []
        for r in rings(c):
            out.append("M" + "L".join(f"{ox + (x - lon0) * k * s:.1f},{oy + (lat1 - y) * s:.1f}" for x, y in r) + "Z")
        return "".join(out)
    neigh = []
    for c in _countries():
        if c is target:
            continue
        cp = [p for r in rings(c) for p in r]
        if any(lon0 <= x <= lon1 and lat0 <= y <= lat1 for x, y in cp[::5]):
            neigh.append(f'<path d="{path(c)}" fill="#e4dccd" stroke="#f6efe4" stroke-width="2"/>')
    # соседи растворяются к краям: обрезанные рамкой материки выглядели вырезанным прямоугольником
    mid = hashlib.sha1(country.encode()).hexdigest()[:6]
    fade = (f'<defs><radialGradient id="g{mid}"><stop offset="55%" stop-color="#fff"/><stop offset="100%" stop-color="#000"/>'
            f'</radialGradient><mask id="m{mid}"><rect width="{W}" height="{H}" fill="url(#g{mid})"/></mask></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">' + fade
            + f'<g mask="url(#m{mid})">' + "".join(neigh) + "</g>"
            + f'<path class="hit" d="{path(target)}" fill="{accent}" stroke="#28348a" stroke-width="3"/></svg>')


# ---------- снимок статьи ----------

def article_shot(url: str) -> Path | None:
    """Шапка статьи на сайте источника — как «доказательство», что исследование настоящее."""
    from playwright.sync_api import sync_playwright
    from .settings import settings
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:20] + "-article.png")
    if out.exists():
        return out
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(**({"executable_path": settings.chromium_path} if settings.chromium_path else {}))
            pg = b.new_page(viewport={"width": 820, "height": 1100}, device_scale_factor=1.3)
            resp = pg.goto(url, wait_until="domcontentloaded", timeout=30000)
            pg.wait_for_timeout(2500)
            title = (pg.title() or "").lower()
            if not resp or resp.status >= 400 or any(w in title for w in ("just a moment", "access denied", "attention required", "403")):
                b.close()
                return None
            pg.screenshot(path=str(out))
            b.close()
        return out
    except Exception as exc:
        log.info("Снимок статьи %s не вышел: %s", url[:60], exc)
        return None


# ---------- сборка ----------

def resolve(pkg, item: dict | None, pictures: dict | None, clips: list[dict] | None = None) -> list[list[dict]]:
    """Для каждой сцены — список готовых к показу иллюстраций [{type, uri|svg|text, caption, detail}]."""
    from .reels import reels_photos, ACCENT_HEX
    from .render import illustrations, picture_uris
    photos, ills, pics = reels_photos(), illustrations(), picture_uris(pictures)
    people = {p.name_en: p for p in pkg.people}
    accent = ACCENT_HEX.get(pkg.accent, "#ff954c")
    used: set[str] = set()
    clip_pool = list(clips or [])
    article = None
    out = []
    for s in pkg.scenes:
        row = []
        for v in s.visuals[:3]:
            got = None
            try:
                if v.kind == "stock":
                    p = stock_photo(v.query, used)
                    got = p and {"type": "full", "uri": p.resolve().as_uri()}
                elif v.kind == "stock_video":
                    p = stock_video(v.query, used) or stock_photo(v.query, used)
                    got = p and {"type": "full", "uri": Path(p).resolve().as_uri()}
                elif v.kind == "our_video" and clip_pool:
                    got = {"type": "full", "uri": Path(clip_pool.pop(0)["path"]).resolve().as_uri()}
                elif v.kind == "photo" and photos.get(v.query):
                    got = {"type": "full", "uri": photos[v.query]}
                elif v.kind == "illustration" and ills.get(v.query):
                    got = {"type": "card", "uri": ills[v.query]}
                elif v.kind == "map":
                    svg = map_svg(v.query, accent)
                    got = svg and {"type": "map", "svg": svg}
                elif v.kind == "person":
                    pic = pics.get(v.query)
                    ref = people.get(v.query)
                    if pic and pic.get("uri"):
                        got = {"type": "person", "uri": pic["uri"], "name": ref.name_ru if ref else v.query,
                               "role": v.detail or (ref.role_ru if ref else "")}
                    elif ref:
                        got = {"type": "namecard", "name": ref.name_ru, "role": v.detail or ref.role_ru}
                elif v.kind == "journal":
                    got = {"type": "journal", "name": v.query}
                    if item and article is None:
                        article = article_shot(item["url"]) or False
                    if article:
                        row.append({"type": "article", "uri": article.resolve().as_uri(), "caption": v.query, "detail": ""})
                elif v.kind == "number":
                    got = {"type": "number", "text": v.query}
                elif v.kind == "quote":
                    got = {"type": "quote", "text": v.query}
            except Exception as exc:
                log.info("Иллюстрация %s/%s не собрана: %s", v.kind, v.query[:40], exc)
            if got:
                got.setdefault("caption", v.caption)
                got.setdefault("detail", v.detail)
                row.append(got)
        out.append(row[:3])
    return out


# ---------- раскадровка режиссёра: кандидаты и проверка «по глазам» ----------
# Решение владельца 28.11: каждую картинку перед рендером смотрит модель — совпадают ли пол, возраст,
# сезон и предмет с фразой. Поиск в стоке по словам этого не гарантирует: на «пожилая женщина»
# фотобанк спокойно отдаёт мужчину.

PICK_CANDIDATES = 5


def _photo_cands(query: str) -> list[dict]:
    out = []
    key = env("PIXABAY_API_KEY")
    if key:
        data = _get("https://pixabay.com/api/", params={"key": key, "q": query[:100], "image_type": "photo",
                                                        "orientation": "vertical", "safesearch": "true", "per_page": 12})
        out += [{"id": f"pb{h['id']}", "thumb": h["webformatURL"], "full": h["largeImageURL"], "video": False}
                for h in data.get("hits", []) if h.get("largeImageURL")]
    if len(out) < PICK_CANDIDATES:
        data = _get("https://api.openverse.org/v1/images/", params={"q": query[:200], "license": "cc0,pdm",
                                                                   "aspect_ratio": "tall", "page_size": 10, "mature": "false"})
        out += [{"id": f"ov{h['id']}", "thumb": h.get("thumbnail") or h["url"], "full": h["url"], "video": False}
                for h in data.get("results", []) if h.get("url")]
    return out


def _video_cands(query: str) -> list[dict]:
    key = env("PIXABAY_API_KEY")
    if not key:
        return []
    data = _get("https://pixabay.com/api/videos/", params={"key": key, "q": query[:100], "safesearch": "true", "per_page": 10})
    out = []
    for h in data.get("hits", []):
        files = [f for f in (h.get("videos") or {}).values() if f.get("url") and f.get("height", 0) >= 720]
        thumbs = [f.get("thumbnail") for f in (h.get("videos") or {}).values() if f.get("thumbnail")]
        if files and thumbs:
            out.append({"id": f"pbv{h['id']}", "thumb": thumbs[0], "full": min(files, key=lambda f: f["height"])["url"],
                        "video": True})
    return out


def _jpeg_small(path: Path) -> bytes:
    from .clips import FF
    return subprocess.run([FF, "-loglevel", "error", "-i", str(path), "-frames:v", "1", "-vf", "scale=512:-2",
                           "-f", "image2", "-c:v", "mjpeg", "-"], capture_output=True).stdout


def pick(cands: list[dict], must_show: str, phrase: str) -> int:
    """Номер подходящего кандидата или -1. Кандидат — {"thumb": url} или {"path": локальный файл}."""
    return pick_verdict(cands, must_show, phrase)[0]


def pick_verdict(cands: list[dict], must_show: str, phrase: str) -> tuple[int, str]:
    """(номер или -1, запрос получше). Второй запрос нужен потому, что режиссёр пишет длинные точные запросы
    («elderly woman drinking tea by window, autumn, back view»), а фотобанк по ним находит мало: на первом
    живом прогоне #24 отбраковано три четверти перебивок."""
    import base64
    from . import llm
    from .models import PickVerdict
    from .settings import settings
    content = [{"type": "text", "text": (
        f"Фраза ролика: «{phrase}».\nВ кадре обязательно: {must_show or 'то, о чём фраза'}.\n"
        "Ниже кандидаты. Выбери тот, что буквально показывает нужное: пол, возраст, время года, предмет совпадают. "
        "Не подходит: крупное лицо (больше ~1/8 кадра), дети крупным планом, логотипы и крупный текст, "
        "лето и зелень, если нужна зима, постановочная «стоковая» улыбка в камеру. При сомнении — -1.")}]
    shown = []
    for k, c in enumerate(cands[:PICK_CANDIDATES]):
        try:
            if c.get("path"):
                jpg = _jpeg_small(Path(c["path"]))
            else:
                r = httpx.get(c["thumb"], timeout=30, follow_redirects=True, headers={"User-Agent": "biglife-content-factory/1.0"})
                jpg = r.content if r.status_code == 200 else b""
        except (httpx.HTTPError, OSError):
            jpg = b""
        if not jpg:
            continue
        shown.append(k)
        content.append({"type": "text", "text": f"Кандидат {len(shown) - 1}"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(jpg).decode()}})
    if not shown:
        return -1, ""
    v = llm.ask(PickVerdict, system="Ты фоторедактор научно-популярного издания. Картинка должна буквально совпадать с фразой.",
                user=content, model=settings.scorer_model, effort="low")
    log.info("Проверка «по глазам» (%s): %s — %s", must_show[:40], v.best, v.reason[:120])
    return (shown[v.best], "") if 0 <= v.best < len(shown) else (-1, v.better_query)


def _phrase_at(subs: list[dict], t: float) -> str:
    s = next((s for s in subs if s["start"] - 0.05 <= t < s["end"]), None)
    return s["text"] if s else ""


def _resolve_cut(c, t: float, phrase: str, ctx: dict) -> list[dict]:
    """Одна перебивка → 0, 1 или 2 кадра (журнал даёт обложку и снимок статьи)."""
    from .clips import prepare
    base = {"start": t, "caption": c.caption, "detail": c.detail}
    if c.kind in ("stock", "stock_video"):
        tries = [("video", c.query)] if c.kind == "stock_video" else []
        tries.append(("photo", c.query))
        retried = False
        while tries:
            what, q = tries.pop(0)
            cands = [x for x in (_video_cands(q) if what == "video" else _photo_cands(q)) if x["id"] not in ctx["used"]]
            k, better = pick_verdict(cands, c.must_show, phrase) if cands else (-1, "")
            if k < 0:
                if better and not retried:            # одна повторная попытка с запросом от фоторедактора
                    retried = True
                    tries = [(what, better)] + ([("photo", better)] if what == "video" else [])
                continue
            x = cands[k]
            ctx["used"].add(x["id"])
            src = _download(x["full"], ".mp4" if x["video"] else ".jpg")
            if not src:
                continue
            path = prepare(src, 0.3, x["id"]) if x["video"] else src
            return [{**base, "type": "full", "uri": Path(path).resolve().as_uri()}]
        return []
    if c.kind == "photo":
        uri = ctx["photos"].get(c.query)
        if uri and pick([{"path": unquote(urlparse(uri).path)}], c.must_show, phrase) == 0:
            return [{**base, "type": "full", "uri": uri}]
        return []
    if c.kind == "our_video":
        for clip in list(ctx["clips"]):
            if pick([{"path": clip["path"]}], c.must_show, phrase) == 0:
                ctx["clips"].remove(clip)
                return [{**base, "type": "full", "uri": Path(clip["path"]).resolve().as_uri()}]
        return []
    if c.kind == "illustration" and ctx["ills"].get(c.query):
        return [{**base, "type": "card", "uri": ctx["ills"][c.query]}]
    if c.kind == "map":
        if ctx.get("world"):                     # формат 6: влёт с карты мира в страну
            ws = world_svg(c.query, ctx["accent"])
            return [{**base, "type": "world", "svg": ws[0], "box": ws[1]}] if ws else []
        svg = map_svg(c.query, ctx["accent"])
        return [{**base, "type": "map", "svg": svg}] if svg else []
    if c.kind == "person":
        ref = ctx["people"].get(c.query)
        pic = ctx["pics"].get(c.query)
        if not (pic and pic.get("uri")) and ref:      # режиссёр назвал учёного, которого не было в сценах
            from . import people as people_mod
            found = people_mod.find(ref.name_en, ref.kind)
            pic = {"uri": Path(found.path).resolve().as_uri()} if found else None
        name, role = (ref.name_ru if ref else c.query), (c.detail or (ref.role_ru if ref else ""))
        if pic and pic.get("uri"):
            return [{**base, "type": "person", "uri": pic["uri"], "name": name, "role": role}]
        return [{**base, "type": "namecard", "name": name, "role": role}] if ref else []
    if c.kind == "journal":
        out = [{**base, "type": "journal", "name": c.query}]
        shot = article_shot(ctx["item"]["url"]) if ctx.get("item") else None
        if shot:
            out.append({**base, "start": t + 1.3, "type": "article", "uri": shot.resolve().as_uri()})
        return out
    if c.kind == "number":
        return [{**base, "type": "number", "text": c.query}]
    if c.kind == "quote":
        return [{**base, "type": "quote", "text": c.query}]
    return []


def resolve_storyboard(sb, words: list[dict], subs: list[dict], pkg, item: dict | None, pictures: dict | None,
                       clips: list[dict] | None = None, lead: float = 0.4, world: bool = False) -> list[dict]:
    """Перебивки раскадровки → готовые кадры [{type, start, …}] по времени. Не прошедшие проверку выпадают:
    предыдущий кадр держится дольше, а не заменяется случайным."""
    from concurrent.futures import ThreadPoolExecutor
    from .reels import reels_photos, ACCENT_HEX
    from .render import illustrations, picture_uris
    ctx = {"photos": reels_photos(), "ills": illustrations(), "pics": picture_uris(pictures),
           "people": {p.name_en: p for p in pkg.people}, "accent": ACCENT_HEX.get(pkg.accent, "#ff954c"),
           "used": set(), "clips": list(clips or []), "item": item, "world": world}
    jobs = []
    for c in sb.cuts:
        t = max(0.0, words[c.word]["t"] - lead) if words else 0.0
        if c.word == 0:
            t = 0.0
        jobs.append((c, round(t, 2), _phrase_at(subs, words[c.word]["t"]) if words else ""))

    def run(j):
        try:
            return _resolve_cut(*j, ctx)
        except Exception as exc:          # одна картинка не должна ронять ролик
            log.info("Перебивка %s/%s не собрана: %s", j[0].kind, j[0].query[:40], exc)
            return []
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, jobs))
    out = sorted((x for row in rows for x in row), key=lambda x: x["start"])
    # статья не должна наезжать на следующую перебивку
    clean = []
    for k, x in enumerate(out):
        nxt = out[k + 1]["start"] if k + 1 < len(out) else 1e9
        if x["type"] == "article" and nxt - x["start"] < 0.9:
            continue
        clean.append(x)
    return clean


def world_svg(country: str, accent: str = "#ff954c") -> tuple[str, list[float]] | None:
    """Карта мира для «влёта в страну» (формат 6): весь мир одной SVG, страна выделена; рамка страны
    возвращается отдельно — по ней камера в шаблоне летит с глобуса в страну."""
    q = country.strip().lower()
    target = next((c for c in _countries() if q in (c["name"].lower(), c["ru"].lower(), (c["iso"] or "").lower())), None)
    if not target:
        target = next((c for c in _countries() if q and (q in c["name"].lower() or q in c["ru"].lower())), None)
    if not target:
        return None
    W, H = 2000, 1000

    def rings(c):
        return c["coords"] if c["type"] == "Polygon" else [r for poly in c["coords"] for r in poly]

    def xy(lon, lat):
        return (lon + 180) / 360 * W, (90 - lat) / 180 * H

    def path(c):
        out = []
        for r in rings(c):
            pts = [xy(x, y) for x, y in r[::2] or r]
            if len(pts) > 2:
                out.append("M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in pts) + "Z")
        return "".join(out)
    others = "".join(f'<path d="{path(c)}"/>' for c in _countries() if c is not target)
    # рамка по самому большому кольцу: у Франции, США и других — далёкие острова, камере нужен материк
    main = max(rings(target), key=len)
    xs, ys = zip(*(xy(x, y) for x, y in main))
    box = [min(xs), min(ys), max(xs), max(ys)]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" overflow="visible">'
           f'<g class="others" fill="#e4dccd" stroke="#f6efe4" stroke-width="1.5">{others}</g>'
           f'<path class="hit" d="{path(target)}" fill="{accent}" stroke="#28348a" stroke-width="2"/></svg>')
    return svg, [round(v, 1) for v in box]
