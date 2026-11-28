"""Сезонность картинок: в ноябре во дворах Астаны снег, а не цветущая лаванда.

У каждой иллюстрации и фото в каталоге есть тег season:
  any    — в помещении или без примет сезона, подходит всегда;
  warm   — зелень, цветы, люди без курток: апрель–октябрь;
  summer — именно лето (пикник, пенная вечеринка, кино под открытым небом): июнь–август;
  cold   — поздняя осень и зима без обязательного снега (куртки, голые деревья): ноябрь–март;
  winter — снег, Новый год: декабрь–февраль.
Тега нет — считаем warm: старые записи каталога сделаны летом, лучше не показать, чем показать не к месту.
"""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo


def tags_for(day: date) -> set[str]:
    m = day.month
    out = {"any"}
    if 4 <= m <= 10:
        out.add("warm")
    if 6 <= m <= 8:
        out.add("summer")
    if m >= 11 or m <= 3:
        out.add("cold")
    if m == 12 or m <= 2:
        out.add("winter")
    return out


def today() -> date:
    from .settings import settings
    return datetime.now(ZoneInfo(settings.timezone)).date()


def fits(entry: dict, day: date | None = None) -> bool:
    tags = entry.get("season", "warm")
    tags = {tags} if isinstance(tags, str) else set(tags)
    return bool(tags & tags_for(day or today()))
