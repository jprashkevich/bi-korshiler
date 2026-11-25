"""Сбор RSS: скачивает ленты, сохраняет новые материалы. Повторы отсекаются по URL."""
from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import feedparser
import httpx
import yaml
from sqlalchemy import select

from . import db
from .settings import CONFIG_DIR

log = logging.getLogger(__name__)
UA = "Mozilla/5.0 (compatible; BIGLifeContentFactory/1.0; RSS reader)"


def load_feeds() -> list[dict]:
    data = yaml.safe_load((CONFIG_DIR / "feeds.yaml").read_text(encoding="utf-8"))
    return [f for f in data["feeds"] if f.get("enabled", True)]


def clean_text(raw: str, limit: int = 1500) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:limit]


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_feed(client: httpx.Client, feed: dict) -> list[dict]:
    resp = client.get(feed["url"])
    resp.raise_for_status()
    parsed = feedparser.parse(resp.content)
    out = []
    for e in parsed.entries:
        url = (e.get("link") or "").strip()
        title = clean_text(e.get("title", ""), 500)
        if not url or not title:
            continue
        summary = e.get("summary") or ""
        if not summary and e.get("content"):
            summary = e["content"][0].get("value", "")
        out.append({
            "feed": feed["name"], "kind": feed.get("kind", "journal"), "title": title,
            "url": url, "summary": clean_text(summary), "published": _published(e),
        })
    return out


def run() -> int:
    """Скачать все ленты. Возвращает число новых материалов."""
    db.init()
    new = 0
    with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as client, \
            db.engine.begin() as conn:
        known = {r[0] for r in conn.execute(select(db.items.c.url))}
        for feed in load_feeds():
            try:
                entries = fetch_feed(client, feed)
            except Exception as exc:  # одна сломанная лента не должна останавливать сбор
                log.warning("Лента %s недоступна: %s", feed["name"], exc)
                continue
            for e in entries:
                if e["url"] in known:
                    continue
                known.add(e["url"])
                conn.execute(db.items.insert().values(**e, fetched_at=db.now(), used=False))
                new += 1
    log.info("Новых материалов: %s", new)
    return new


class _TextExtractor(HTMLParser):
    """Достаёт текст абзацев статьи, пропуская скрипты, меню и подвал."""
    SKIP = {"script", "style", "nav", "footer", "header", "aside", "form", "noscript"}

    def __init__(self):
        super().__init__()
        self.depth_skip = 0
        self.in_p = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.depth_skip += 1
        elif tag in ("p", "li", "h2", "h3"):
            self.in_p = True
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.depth_skip:
            self.depth_skip -= 1
        elif tag in ("p", "li", "h2", "h3"):
            self.in_p = False

    def handle_data(self, data):
        if self.in_p and not self.depth_skip:
            self.parts.append(data)


def fetch_article_text(url: str, limit: int = 12000) -> str:
    """Полный текст статьи для генерации. Если страница закрыта, вернёт пустую строку."""
    try:
        with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except Exception as exc:
        log.info("Не удалось скачать статью %s: %s", url, exc)
        return ""
    p = _TextExtractor()
    p.feed(resp.text)
    text = re.sub(r"[ \t]+", " ", "".join(p.parts))
    text = re.sub(r"\n\s*\n+", "\n", text).strip()
    return text[:limit]
