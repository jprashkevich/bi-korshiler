"""Лента профиля как система: фактура обложки по правилу соседства и превью сетки для согласующего.

Почему правило, а не раскладка по позициям: пробные Reels не попадают в сетку, пока Instagram не переведёт
их в ленту, а посты иногда выходят вручную или пропускаются — ряды постоянно сдвигаются. Поэтому вместо
«в этой клетке всегда фото» завод смотрит на соседей: не больше двух одинаковых фактур подряд, две тёмные
(navy) никогда не рядом ни по горизонтали, ни по вертикали, а доля фото держится около четверти.
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from pathlib import Path

import httpx

from . import db, writer

log = logging.getLogger(__name__)

# основная фактура рубрики: бумага — основа ленты, фото — живые дворы, navy — цифры и продукт
PREFERRED = {"courtyard": "photo", "number": "navy", "app": "navy"}
TEX_TILE = 3                                   # колонок в сетке профиля


def _slot_key(p: dict) -> str:
    return f"{p['slot_date']}-{p['slot']}"


def recent_textures(post: dict, limit: int = 6) -> list[str]:
    """Фактуры обложек карусели, которые выйдут перед этим постом (по времени слота), новые в конце.
    Reels не считаем: пробные ролики в сетку профиля не попадают."""
    from sqlalchemy import select
    with db.engine.begin() as c:
        rows = c.execute(select(db.posts.c.id, db.posts.c.slot_date, db.posts.c.slot, db.posts.c.status,
                                db.posts.c.package)).mappings().all()
    key = _slot_key(post)
    prior = [r for r in rows if r["id"] != post["id"] and r["status"] in ("sent", "approved", "generated")
             and _slot_key(r) < key and (r["package"] or {}).get("format") != "reels"
             and (r["package"] or {}).get("cover_texture")]
    prior.sort(key=_slot_key)
    return [r["package"]["cover_texture"] for r in prior[-limit:]]


def choose_texture(rubric: str, recent: list[str], has_photo: bool) -> str:
    """Фактура обложки по правилу соседства."""
    want = PREFERRED.get(rubric, "paper")
    if want == "photo" and not has_photo:
        want = "paper"
    candidates = [want] + [t for t in ("paper", "photo", "navy") if t != want]

    def ok(t: str) -> bool:
        if t == "photo" and not has_photo:
            return False
        if len(recent) >= 2 and recent[-1] == recent[-2] == t:          # три одинаковых подряд
            return False
        if t == "navy" and ("navy" in recent[-1:] or (len(recent) >= TEX_TILE and recent[-TEX_TILE] == "navy")):
            return False                                                 # navy рядом по горизонтали или вертикали
        return True

    # фото держим около четверти ленты: если фото давно не было, а бумага подряд — разбавляем
    if has_photo and want == "paper" and len(recent) >= 4 and "photo" not in recent[-4:]:
        candidates = ["photo"] + [c for c in candidates if c != "photo"]
    return next((t for t in candidates if ok(t)), "paper")


def cover_look(post: dict, rubric_key: str, photo_id: str = "") -> dict:
    """Всё для обложки: фактура, фото для неё, цвет рубрики."""
    from .reels import reels_photos
    rubric = writer.load_yaml("rubrics.yaml")["rubrics"][rubric_key]
    photos = reels_photos()
    photo = photos.get(photo_id) or (list(photos.values())[post["id"] % len(photos)] if photos else "")
    is_drive = rubric.get("source") == "drive"
    tex = choose_texture(rubric_key, recent_textures(post), has_photo=bool(photo) or is_drive)
    return {"cover_texture": tex, "cover_photo": photo if tex == "photo" and not is_drive else "",
            "rubric_color": rubric.get("color", "sky")}


# ---------- превью ленты ----------

def _tile(img, w: int = 360, h: int = 480):
    from PIL import Image
    img = img.convert("RGB")
    k = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * k), round(img.height * k)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def published_thumbnails(limit: int = 8) -> list:
    """Миниатюры последних постов из сетки профиля (без пробных Reels, которых в сетке нет)."""
    from PIL import Image
    from . import instagram
    if not instagram.enabled() or not instagram.user_id():
        return []
    try:
        data = instagram._request("GET", f"{instagram.user_id()}/media", limit=limit + 6,
                                  fields="media_type,media_product_type,media_url,thumbnail_url,is_shared_to_feed")["data"]
    except Exception as exc:
        log.info("Превью ленты: миниатюры не получены: %s", exc)
        return []
    out = []
    for m in data:
        if m.get("media_product_type") == "REELS" and m.get("is_shared_to_feed") is False:
            continue
        url = m.get("thumbnail_url") or m.get("media_url")
        if not url:
            continue
        try:
            out.append(Image.open(io.BytesIO(httpx.get(url, timeout=30).content)))
        except Exception:
            continue
        if len(out) >= limit:
            break
    return out


def preview(cover: Path, out: Path) -> Path | None:
    """Сетка 3×3: новая обложка в левом верхнем углу (так её покажет профиль) и 8 последних постов."""
    from PIL import Image, ImageDraw
    thumbs = published_thumbnails(8)
    tiles = [_tile(Image.open(cover))] + [_tile(t) for t in thumbs]
    if len(tiles) < 2:
        return None
    gap, w, h = 6, 360, 480
    rows = (len(tiles) + 2) // 3
    sheet = Image.new("RGB", (3 * w + 2 * gap, rows * h + (rows - 1) * gap), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 3) * (w + gap), (i // 3) * (h + gap)))
    d = ImageDraw.Draw(sheet)
    d.rectangle([2, 2, w - 3, h - 3], outline="#ff954c", width=6)          # новый пост
    sheet.save(out, "JPEG", quality=88)
    return out
