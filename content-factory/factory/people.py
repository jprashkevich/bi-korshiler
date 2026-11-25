"""Фото людей и организаций для коллажей: Википедия / Wikidata → только свободные файлы Wikimedia Commons.

Берём фото, только если:
- страница Википедии (или элемент Wikidata) описывает человека подходящего рода занятий (или организацию);
- файл лежит на Wikimedia Commons (локальные файлы en.wikipedia часто несвободные — их не берём);
- лицензия свободная (CC BY, CC BY-SA, CC0, Public domain). Автор и лицензия идут в подпись на слайде.
Если что-то не сходится — фото нет, слайд рисуется без него. Согласующий в Telegram проверяет, тот ли человек.
"""
from __future__ import annotations

import hashlib
import html
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, unquote

import httpx

from .settings import OUTPUT_DIR

log = logging.getLogger(__name__)
UA = {"User-Agent": "BIGLifeContentFactory/1.0 (social media content tool)"}
CACHE = OUTPUT_DIR / "_people"
PERSON_WORDS = ("psycholog", "scien", "research", "professor", "physician", "sociolog", "economist",
                "epidemiolog", "neuro", "author", "writer", "journalist", "gerontolog", "psychiatr",
                "urban", "architect", "academic", "doctor", "biolog", "anthropolog", "explorer", "philosoph")
ORG_WORDS = ("university", "institute", "college", "school", "hospital", "academy", "foundation",
             "organization", "organisation", "centre", "center", "laboratory", "agency", "journal")
FREE_LICENSES = ("cc by", "cc-by", "cc0", "public domain", "pd", "attribution")


@dataclass
class Picture:
    path: Path
    credit: str          # «Фото: автор / лицензия, Wikimedia Commons»
    title: str           # заголовок страницы, для проверки человеком
    description: str
    page_url: str


def _get(url: str, **params) -> dict:
    """GET с повтором при 429: Википедия ограничивает частоту запросов."""
    import time
    for attempt in range(4):
        r = httpx.get(url, params=params or None, headers=UA, timeout=30, follow_redirects=True)
        if r.status_code == 429 and attempt < 3:
            time.sleep(float(r.headers.get("retry-after", 0) or 2 * (attempt + 1)))
            continue
        r.raise_for_status()
        return r.json()
    return {}


def _commons_file_from_url(url: str) -> str | None:
    m = re.search(r"/wikipedia/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/?#]+)", url or "")
    return unquote(m.group(1)) if m else None


def _commons_info(filename: str) -> tuple[str, str, str] | None:
    """(url уменьшенной копии, автор, лицензия) или None, если лицензия несвободная."""
    data = _get("https://commons.wikimedia.org/w/api.php", action="query", format="json",
                titles=f"File:{filename}", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth="900")
    page = next(iter(data.get("query", {}).get("pages", {}).values()), {})
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    license_name = (meta.get("LicenseShortName", {}).get("value") or "").strip()
    if meta.get("NonFree", {}).get("value") == "true" or not any(x in license_name.lower() for x in FREE_LICENSES):
        log.info("Фото %s пропущено: лицензия «%s»", filename, license_name)
        return None
    artist = re.sub(r"<[^>]+>", "", html.unescape(meta.get("Artist", {}).get("value") or "")).strip()
    return info.get("thumburl") or info.get("url"), artist[:60] or "автор не указан", license_name


def _download(url: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha1(url.encode()).hexdigest()[:16] + Path(url.split("?")[0]).suffix.lower())
    if not path.exists():
        r = httpx.get(url, headers=UA, timeout=60, follow_redirects=True)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path


def _fits(description: str, kind: str) -> bool:
    words = PERSON_WORDS if kind == "person" else ORG_WORDS
    return any(w in (description or "").lower() for w in words)


def find(name_en: str, kind: str = "person") -> Picture | None:
    """Найти свободное фото человека (kind='person') или организации (kind='org')."""
    name_en = (name_en or "").strip()
    if not name_en:
        return None
    try:
        candidates: list[tuple[str, str, str, str]] = []   # (файл Commons, заголовок, описание, ссылка)
        s = {}
        try:
            s = _get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(name_en.replace(' ', '_'))}")
        except httpx.HTTPError:
            pass
        if s.get("type") == "standard":
            src = (s.get("originalimage") or s.get("thumbnail") or {}).get("source", "")
            f = _commons_file_from_url(src)
            if f:
                candidates.append((f, s.get("title", name_en), s.get("description", ""),
                                   s.get("content_urls", {}).get("desktop", {}).get("page", "")))
        if not candidates:   # запасной путь: Wikidata, свойство «изображение» (P18)
            found = _get("https://www.wikidata.org/w/api.php", action="wbsearchentities", search=name_en,
                         language="en", format="json", limit=1).get("search", [])
            if found:
                qid, desc = found[0]["id"], found[0].get("description", "")
                ent = _get(f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json")["entities"][qid]
                p18 = ent.get("claims", {}).get("P18", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                if p18:
                    candidates.append((p18, found[0].get("label", name_en), desc,
                                       f"https://www.wikidata.org/wiki/{qid}"))
        for filename, title, desc, url in candidates:
            if kind == "org" and not filename.lower().endswith((".jpg", ".jpeg")):
                continue   # у организаций PNG/SVG — обычно герб или логотип, для коллажа нужна фотография
            if not _fits(desc, kind):
                log.info("%s: описание «%s» не подходит", name_en, desc)
                continue
            info = _commons_info(filename)
            if not info:
                continue
            thumb, artist, license_name = info
            return Picture(_download(thumb), f"Фото: {artist} / {license_name}, Wikimedia Commons",
                           title, desc, url)
    except Exception as exc:   # фото — украшение, его отсутствие не должно ломать пост
        log.warning("Поиск фото «%s»: %s", name_en, exc)
    return None
