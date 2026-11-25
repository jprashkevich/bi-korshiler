"""Город мероприятия: по ЖК, по названию и по группе отчётов. Исключения задаются в боте командой /city."""
from __future__ import annotations

import re

import yaml

from . import db
from .settings import CONFIG_DIR


def _cfg() -> dict:
    return yaml.safe_load((CONFIG_DIR / "cities.yaml").read_text(encoding="utf-8")) or {}


def norm(name: str) -> str:
    """Ключ ЖК: без «ЖК», регистра, пунктуации и лишних пробелов («ЖК Камал-4» = «Камал 4»)."""
    s = re.sub(r"^\s*ж\s*к\s+", "", (name or "").lower())
    s = re.sub(r"[«»\"'.,;:()\-–—]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def set_city(complex_name: str, city: str) -> None:
    db.kv_set(f"city:{norm(complex_name)}", city.strip())


def city_for(complex_name: str, group: str = "") -> str:
    key = norm(complex_name)
    saved = db.kv_get(f"city:{key}")
    if saved:
        return saved
    cfg = _cfg()
    for name, city in (cfg.get("complexes") or {}).items():
        if norm(name) == key:
            return city
    low = (complex_name or "").lower()
    for word, city in (cfg.get("keywords") or {}).items():
        if word in low:
            return city
    return (cfg.get("groups") or {}).get((group or "").strip(), "")
