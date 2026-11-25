"""Контент-план в Google Sheets: одна строка на пост, статус обновляется. Работает, только если заданы ключи."""
from __future__ import annotations

import json
import logging

from .settings import settings

log = logging.getLogger(__name__)
HEADER = ["post_id", "дата", "слот", "рубрика", "тема", "источник", "статус", "threads", "обновлено"]
_ws = None


def _sheet():
    global _ws
    if _ws is None:
        import gspread
        gc = gspread.service_account_from_dict(json.loads(settings.google_sa_json))
        sh = gc.open_by_key(settings.sheet_id)
        _ws = sh.sheet1
        if _ws.row_values(1) != HEADER:
            _ws.update("A1", [HEADER])
    return _ws


def upsert(post: dict, item: dict | None) -> None:
    if not settings.sheets_enabled:
        return
    try:
        ws = _sheet()
        pkg = post.get("package") or {}
        row = [post["id"], post["slot_date"], post["slot"] + 1, post["rubric"], pkg.get("headline", ""),
               item["url"] if item else "", post["status"],
               " ".join(post.get("threads_ids") or []), str(post["updated_at"])[:16]]
        cell = ws.find(str(post["id"]), in_column=1)
        if cell:
            ws.update(f"A{cell.row}", [row])
        else:
            ws.append_row(row)
    except Exception as exc:   # таблица — вспомогательная, ошибки не должны ломать завод
        log.warning("Google Sheets: %s", exc)
