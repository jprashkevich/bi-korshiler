"""Хранилище: материалы из RSS, посты и служебные значения. Postgres на Render, SQLite локально."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, Column, DateTime, Float, Integer, LargeBinary, MetaData, String, Table, Text,
    create_engine, select, update,
)

from .settings import settings

metadata = MetaData()

items = Table(
    "items", metadata,
    Column("id", Integer, primary_key=True),
    Column("feed", String(200), nullable=False),
    Column("kind", String(20), nullable=False, default="journal"),
    Column("title", Text, nullable=False),
    Column("url", String(1000), nullable=False, unique=True),
    Column("summary", Text, default=""),
    Column("published", DateTime(timezone=True)),
    Column("fetched_at", DateTime(timezone=True), nullable=False),
    Column("score", Float),                 # итоговый балл скоринга 0..10
    Column("score_data", JSON),             # оценки по критериям, идея хука, лучшая рубрика
    Column("used", Boolean, nullable=False, default=False),
)

posts = Table(
    "posts", metadata,
    Column("id", Integer, primary_key=True),
    Column("item_id", Integer),             # пусто для рубрик без внешнего источника
    Column("rubric", String(40), nullable=False),
    Column("slot_date", String(10), nullable=False),   # YYYY-MM-DD
    Column("slot", Integer, nullable=False),            # 0 — утро, 1 — вечер
    # generated -> sent -> approved | rejected; redo — ждёт комментарий для переделки
    Column("status", String(20), nullable=False, default="generated"),
    Column("package", JSON),                # сгенерированный пакет (тексты, слайды)
    Column("files", JSON),                  # пути к PNG
    Column("feedback", JSON, default=list),  # комментарии на переделку
    Column("tg_message_id", Integer),       # сообщение с кнопками
    Column("threads_ids", JSON),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# Файлы для публикации в Instagram: их отдаёт по случайному адресу media_server.py (см. instagram.py)
media = Table(
    "media", metadata,
    Column("token", String(80), primary_key=True),
    Column("post_id", Integer, nullable=False, index=True),
    Column("mime", String(40), nullable=False),
    Column("data", LargeBinary, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

kv = Table(
    "kv", metadata,
    Column("key", String(100), primary_key=True),
    Column("value", Text),
)

engine = create_engine(settings.database_url.replace("postgres://", "postgresql+psycopg://", 1)
                       .replace("postgresql://", "postgresql+psycopg://", 1), future=True)


def now() -> datetime:
    return datetime.now(timezone.utc)


def init() -> None:
    metadata.create_all(engine)


def kv_get(key: str, default: str | None = None) -> str | None:
    with engine.begin() as c:
        row = c.execute(select(kv.c.value).where(kv.c.key == key)).first()
    return row[0] if row else default


def kv_set(key: str, value: str) -> None:
    with engine.begin() as c:
        if c.execute(select(kv.c.key).where(kv.c.key == key)).first():
            c.execute(update(kv).where(kv.c.key == key).values(value=value))
        else:
            c.execute(kv.insert().values(key=key, value=value))


def get_post(post_id: int) -> dict | None:
    with engine.begin() as c:
        row = c.execute(select(posts).where(posts.c.id == post_id)).mappings().first()
    return dict(row) if row else None


def update_post(post_id: int, **values) -> None:
    values["updated_at"] = now()
    with engine.begin() as c:
        c.execute(update(posts).where(posts.c.id == post_id).values(**values))


def get_item(item_id: int | None) -> dict | None:
    if item_id is None:
        return None
    with engine.begin() as c:
        row = c.execute(select(items).where(items.c.id == item_id)).mappings().first()
    return dict(row) if row else None


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)
