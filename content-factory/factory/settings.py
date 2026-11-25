"""Настройки из переменных окружения. Секреты задаются только через env (на Render — Environment)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # content-factory/
CONFIG_DIR = ROOT / "config"
TEMPLATES_DIR = ROOT / "templates"
PHOTOS_DIR = Path(os.getenv("PHOTOS_DIR", ROOT.parent / "images"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", ROOT / "output"))


def _list(name: str) -> list[int]:
    return [int(x) for x in os.getenv(name, "").replace(" ", "").split(",") if x]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'factory.db'}")
    timezone: str = os.getenv("FACTORY_TZ", "Asia/Almaty")
    daily_run_hour: int = int(os.getenv("DAILY_RUN_HOUR", "6"))       # во сколько готовить пакеты на день
    posts_per_day: int = int(os.getenv("POSTS_PER_DAY", "2"))
    freshness_days: int = int(os.getenv("FRESHNESS_DAYS", "21"))      # насколько старые материалы допускаются

    # Claude
    writer_model: str = os.getenv("WRITER_MODEL", "claude-opus-5-5")
    scorer_model: str = os.getenv("SCORER_MODEL", "claude-opus-5-5")
    writer_effort: str = os.getenv("WRITER_EFFORT", "high")
    scorer_effort: str = os.getenv("SCORER_EFFORT", "low")

    # Telegram
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")          # id группы SMM + согласующий
    approver_ids: list[int] = field(default_factory=lambda: _list("TELEGRAM_APPROVER_IDS"))

    # Threads
    threads_user_id: str = os.getenv("THREADS_USER_ID", "")
    threads_token: str = os.getenv("THREADS_ACCESS_TOKEN", "")

    # Google Sheets (необязательно)
    google_sa_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")

    # Рендер
    chromium_path: str = os.getenv("CHROMIUM_EXECUTABLE", "")

    @property
    def threads_enabled(self) -> bool:
        return bool(self.threads_user_id and self.threads_token)

    @property
    def sheets_enabled(self) -> bool:
        return bool(self.google_sa_json and self.sheet_id)


settings = Settings()
