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
from pathlib import Path

import httpx

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
