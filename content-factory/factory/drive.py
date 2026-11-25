"""Фотоотчёты о соседских активностях из Google Drive для рубрики «Жизнь дворов».

Структура папки: <корень>/<ГГГГ-ММ>/<ЖК>/<«ДД.ММ · Активность · код»>/фото и видео.
Берём мероприятия за последние дни, которые ещё не попадали в посты, и до 4 фото из каждого.
Доступ — сервисный аккаунт Google (GOOGLE_SERVICE_ACCOUNT_JSON) с правом «Читатель» на корневую папку.
"""
from __future__ import annotations

import io
import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from . import db
from .settings import OUTPUT_DIR, env

log = logging.getLogger(__name__)
API = "https://www.googleapis.com/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
EVENT_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\s*·\s*(.+?)\s*·\s*\S+\s*$")
CACHE = OUTPUT_DIR / "_drive"
_token: dict = {}


@dataclass
class Event:
    folder_id: str
    complex: str           # ЖК
    activity: str          # название активности/клуба
    day: str               # ISO-дата
    photos: list[dict] = field(default_factory=list)   # [{"id", "name"}]
    videos: int = 0
    report: dict = field(default_factory=dict)         # report.json от tunely: описание, участники, лучшие кадры

    @property
    def label(self) -> str:
        d = date.fromisoformat(self.day)
        return f"{d.day:02d}.{d.month:02d} · {self.complex} · {self.activity}"


def root_id() -> str:
    return env("GOOGLE_DRIVE_FOLDER_ID")


def enabled() -> bool:
    return bool(root_id() and env("GOOGLE_SERVICE_ACCOUNT_JSON"))


def _access_token() -> str:
    from google.auth.transport.requests import Request
    from google.oauth2 import service_account
    creds = _token.get("creds")
    if creds is None:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(env("GOOGLE_SERVICE_ACCOUNT_JSON")),
            scopes=["https://www.googleapis.com/auth/drive.readonly"])
        _token["creds"] = creds
    if not creds.valid:
        creds.refresh(Request())
    return creds.token


def _list(query: str, fields: str = "files(id,name,mimeType,createdTime)") -> list[dict]:
    out, page = [], None
    while True:
        params = {"q": query, "fields": f"nextPageToken,{fields}", "pageSize": 1000,
                  "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if page:
            params["pageToken"] = page
        r = httpx.get(API, params=params, headers={"Authorization": f"Bearer {_access_token()}"}, timeout=60)
        r.raise_for_status()
        body = r.json()
        out += body.get("files", [])
        page = body.get("nextPageToken")
        if not page:
            return out


def _children(folder_id: str, folders_only: bool = False) -> list[dict]:
    q = f"'{folder_id}' in parents and trashed = false"
    if folders_only:
        q += f" and mimeType = '{FOLDER}'"
    return _list(q)


def recent_events(days: int = 8, today: date | None = None) -> list[Event]:
    """Мероприятия за последние `days` дней, ещё не использованные в постах, с хотя бы одним фото."""
    today = today or date.today()
    since = today - timedelta(days=days)
    used = set(json.loads(db.kv_get("drive_used_events", "[]")))
    months = {f"{d.year}-{d.month:02d}" for d in (today, since)}
    events: list[Event] = []
    for month in _children(root_id(), folders_only=True):
        if month["name"].strip() not in months:
            continue
        year = int(month["name"][:4])
        for complex_ in _children(month["id"], folders_only=True):
            for ev in _children(complex_["id"], folders_only=True):
                m = EVENT_RE.match(ev["name"])
                if not m or ev["id"] in used:
                    continue
                try:
                    d = date(year, int(m.group(2)), int(m.group(1)))
                except ValueError:
                    continue
                if not since <= d <= today:
                    continue
                files = _children(ev["id"])
                report = {}
                rj = next((f for f in files if f["name"] == "report.json"), None)
                if rj:
                    try:
                        report = read_json(rj["id"])
                    except Exception as exc:
                        log.info("report.json %s не прочитан: %s", ev["name"], exc)
                photos = [{"id": f["id"], "name": f["name"]} for f in files if f["mimeType"].startswith("image/")]
                bad = set(report.get("photos_not_event") or [])
                photos = [p for p in photos if p["name"] not in bad]          # афиши и скриншоты не берём
                rank = {n: i for i, n in enumerate(report.get("photos_best") or [])}
                photos.sort(key=lambda p: (rank.get(p["name"], 99), p["name"]))  # лучшие по оценке ИИ — первыми
                if photos:
                    events.append(Event(ev["id"], complex_["name"].strip(), m.group(3).strip(), d.isoformat(),
                                        photos[:4], sum(f["mimeType"].startswith("video/") for f in files),
                                        report))
    events.sort(key=lambda e: e.day, reverse=True)
    return events


def read_json(file_id: str) -> dict:
    r = httpx.get(f"{API}/{file_id}", params={"alt": "media", "supportsAllDrives": "true"},
                  headers={"Authorization": f"Bearer {_access_token()}"}, timeout=60)
    r.raise_for_status()
    return r.json()


def pick_events(events: list[Event], limit: int = 5) -> list[Event]:
    """Разнообразие: сначала разные ЖК и разные активности, потом остальные."""
    chosen, seen_c, seen_a = [], set(), set()
    # мероприятия с описанием из отчёта — в приоритете: по ним текст получается точнее
    events = sorted(events, key=lambda e: (not (e.report or {}).get("description"),))
    for e in events:
        if e.complex not in seen_c and e.activity not in seen_a:
            chosen.append(e); seen_c.add(e.complex); seen_a.add(e.activity)
    for e in events:
        if len(chosen) >= limit:
            break
        if e not in chosen:
            chosen.append(e)
    return chosen[:limit]


def download(file_id: str, max_side: int = 1600) -> Path:
    """Скачать фото (с кешем) и уменьшить до max_side по длинной стороне."""
    from PIL import Image, ImageOps
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{file_id}.jpg"
    if not path.exists():
        r = httpx.get(f"{API}/{file_id}", params={"alt": "media", "supportsAllDrives": "true"},
                      headers={"Authorization": f"Bearer {_access_token()}"}, timeout=120, follow_redirects=True)
        r.raise_for_status()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(r.content))).convert("RGB")
        im.thumbnail((max_side, max_side))
        im.save(path, quality=88)
    return path


def mark_used(events: list[dict]) -> None:
    used = set(json.loads(db.kv_get("drive_used_events", "[]")))
    used.update(e["folder_id"] for e in events)
    db.kv_set("drive_used_events", json.dumps(sorted(used)))


def to_dicts(events: list[Event]) -> list[dict]:
    return [asdict(e) | {"label": e.label} for e in events]
