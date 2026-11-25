"""Минимальный клиент Telegram Bot API."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx

from .settings import settings

log = logging.getLogger(__name__)
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096


class TelegramError(RuntimeError):
    pass


def _call(method: str, http_timeout: float = 60, files=None, **params):
    url = f"https://api.telegram.org/bot{settings.telegram_token}/{method}"
    data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
            for k, v in params.items() if v is not None}
    resp = httpx.post(url, data=data, files=files, timeout=http_timeout)
    body = resp.json()
    if not body.get("ok"):
        raise TelegramError(f"{method}: {body.get('description')}")
    return body["result"]


def send_album(chat_id: str, paths: list[Path], caption: str = "") -> list[int]:
    """Слайды карусели одним альбомом (до 10 файлов)."""
    media, files = [], {}
    for i, p in enumerate(paths[:10]):
        key = f"f{i}"
        files[key] = (p.name, p.read_bytes(), "image/png")
        item = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = caption[:CAPTION_LIMIT]
        media.append(item)
    result = _call("sendMediaGroup", http_timeout=120, files=files, chat_id=chat_id, media=media)
    return [m["message_id"] for m in result]


def send_video(chat_id: str, path: Path, cover: Path | None = None, caption: str = "") -> int:
    files = {"video": (path.name, path.read_bytes(), "video/mp4")}
    if cover:
        files["thumbnail"] = (cover.name, cover.read_bytes(), "image/png")
    result = _call("sendVideo", http_timeout=300, files=files, chat_id=chat_id, width=1080, height=1920,
                   supports_streaming="true", thumbnail="attach://thumbnail" if cover else None,
                   caption=caption[:CAPTION_LIMIT] or None)
    return result["message_id"]


def send_document(chat_id: str, path: Path, caption: str = "") -> int:
    with path.open("rb") as fh:
        result = _call("sendDocument", http_timeout=120, files={"document": (path.name, fh)},
                       chat_id=chat_id, caption=caption[:CAPTION_LIMIT] or None)
    return result["message_id"]


def send_message(chat_id: str | int, text: str, keyboard: list[list[dict]] | None = None,
                 reply_to: int | None = None, force_reply: bool = False) -> int:
    markup = None
    if keyboard:
        markup = {"inline_keyboard": keyboard}
    elif force_reply:
        markup = {"force_reply": True, "selective": True}
    result = _call("sendMessage", chat_id=chat_id, text=text[:TEXT_LIMIT], parse_mode="HTML",
                   link_preview_options={"is_disabled": True}, reply_markup=markup,
                   reply_parameters={"message_id": reply_to} if reply_to else None)
    return result["message_id"]


def edit_keyboard(chat_id: str | int, message_id: int, keyboard: list[list[dict]] | None) -> None:
    try:
        _call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id,
              reply_markup={"inline_keyboard": keyboard or []})
    except TelegramError as exc:   # сообщение могли удалить — это не критично
        log.info("Не удалось обновить кнопки: %s", exc)


def answer_callback(callback_id: str, text: str = "") -> None:
    _call("answerCallbackQuery", callback_query_id=callback_id, text=text or None)


def get_updates(offset: int | None, timeout: int = 50) -> list[dict]:
    return _call("getUpdates", http_timeout=timeout + 10, offset=offset, timeout=timeout,
                 allowed_updates=["message", "callback_query"])
