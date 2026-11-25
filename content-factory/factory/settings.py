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


def env(name: str, default: str = "") -> str:
    """Значение переменной окружения в момент вызова, без лишних пробелов по краям."""
    return (os.environ.get(name) or default).strip()


def env_problem(name: str) -> str:
    """Почему переменная не видна процессу: опечатка или пробелы в имени, пустое значение."""
    if os.environ.get(name, "").strip():
        return ""
    lookalikes = [k for k in os.environ
                  if k != name and k.strip().upper().replace("-", "_").replace(" ", "_") == name]
    if lookalikes:
        return f"{name}: найдена переменная с похожим именем {lookalikes[0]!r} — уберите пробелы или исправьте регистр"
    if name in os.environ:
        return f"{name}: переменная есть, но значение пустое"
    return f"{name}: переменная не видна сервису"


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
    threads_app_id: str = os.getenv("THREADS_APP_ID", "")
    threads_app_secret: str = os.getenv("THREADS_APP_SECRET", "")
    threads_redirect_uri: str = os.getenv("THREADS_REDIRECT_URI", "https://localhost/")

    # Google Sheets (необязательно)
    google_sa_json: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    sheet_id: str = os.getenv("GOOGLE_SHEET_ID", "")

    # Рендер
    chromium_path: str = os.getenv("CHROMIUM_EXECUTABLE", "")

    @property
    def sheets_enabled(self) -> bool:
        return bool(self.google_sa_json and self.sheet_id)


settings = Settings()
