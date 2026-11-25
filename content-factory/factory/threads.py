"""Публикация треда в Threads через Threads API (graph.threads.net).

Каждое сообщение: создать контейнер (media_type=TEXT), затем опубликовать его.
Следующие сообщения создаются с reply_to_id предыдущего — так получается тред.
Долгоживущий токен действует 60 дней; refresh_token() продлевает его, новое значение хранится в БД.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

from . import db
from .settings import settings

log = logging.getLogger(__name__)
BASE = "https://graph.threads.net/v1.0"
LIMIT = 500


class ThreadsError(RuntimeError):
    pass


def token() -> str:
    return db.kv_get("threads_token") or settings.threads_token


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
    creation = _post(f"{settings.threads_user_id}/threads", **params)["id"]
    time.sleep(3)   # Meta рекомендует дать контейнеру обработаться перед публикацией
    return _post(f"{settings.threads_user_id}/threads_publish", creation_id=creation)["id"]


def publish_thread(messages: list[str]) -> list[str]:
    ids: list[str] = []
    for text in messages:
        ids.append(publish_text(text, reply_to=ids[-1] if ids else None))
    return ids


def refresh_token_if_needed() -> None:
    """Продлевает токен раз в 30 дней (токен живёт 60)."""
    if not settings.threads_enabled:
        return
    last = db.kv_get("threads_token_refreshed")
    if last and datetime.fromisoformat(last) > datetime.now(timezone.utc) - timedelta(days=30):
        return
    resp = httpx.get("https://graph.threads.net/refresh_access_token",
                     params={"grant_type": "th_refresh_token", "access_token": token()}, timeout=60)
    body = resp.json()
    if "access_token" not in body:
        log.error("Не удалось продлить токен Threads: %s", body)
        return
    db.kv_set("threads_token", body["access_token"])
    db.kv_set("threads_token_refreshed", datetime.now(timezone.utc).isoformat())
    log.info("Токен Threads продлён")
