"""Город мероприятия для «Жизни дворов».

Порядок: /city в боте → complexes в cities.yaml → справочник ЖК (config/complex_cities.json,
618 ЖК с городами из списка владельца) → слово-подсказка в названии → группа отчётов.
Названия папок на Drive пишут вразнобой («ЖК Камал-4», «Нова Сити», «Батысмұра»), поэтому сравниваем
в латинице, без «ЖК», пунктуации и слов вроде «очередь»; сначала вместе с номерами, потом без них,
потом по самому редкому слову названия.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from functools import lru_cache

import yaml

from . import db
from .settings import CONFIG_DIR

_KZ = str.maketrans({"ұ": "у", "ү": "у", "қ": "к", "ә": "а", "ө": "о", "і": "и", "ғ": "г", "ң": "н", "һ": "х", "ё": "е"})
_TR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k",
       "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h",
       "ц": "c", "ч": "ch", "ш": "sh", "щ": "sh", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}
_STOP = {"zhk", "och", "ochered", "blok", "dvor", "i", "na", "vse", "doma", "etap", "kv", "korpus"}
# русские транслитерации английских слов из названий ЖК → как в справочнике
_SYN = {"biznes": "business", "biznesss": "business", "bizness": "business", "komfort": "comfort", "siti": "city",
        "lait": "lite", "laif": "life", "tauers": "towers", "hils": "hills", "hills": "hills", "park": "park",
        "garden": "garden", "gardens": "garden", "emmoushen": "emotions", "emmotion": "emotions",
        "emotion": "emotions", "emoshen": "emotions", "kala": "kala", "kvartal": "kvartal"}


def _lat(s: str) -> str:
    s = (s or "").lower().translate(_KZ)
    s = "".join(_TR.get(c, c) for c in s)
    return s.replace("kh", "h").replace("ts", "c").replace("q", "k")


def _tokens(name: str, numbers: bool) -> list[str]:
    s = re.sub(r"[«»\"'.,;:()\-–—/+&]+", " ", _lat(name))
    out = []
    for t in s.split():
        if t in _STOP:
            continue
        if re.fullmatch(r"\d+[a-zа-я]?", t) or re.fullmatch(r"[a-z]", t):
            if numbers and re.fullmatch(r"\d+", t):
                out.append(t)
            continue
        out.append(_SYN.get(t, t))
    return out


def norm(name: str) -> str:
    """Ключ для команд /city: без «ЖК», регистра и пунктуации."""
    return " ".join(_tokens(name, numbers=True))


@lru_cache(maxsize=1)
def _index():
    path = CONFIG_DIR / "complex_cities.json"
    items = json.loads(path.read_text(encoding="utf-8"))["items"] if path.exists() else []
    full, short, words = defaultdict(set), defaultdict(set), defaultdict(set)
    for name, city in items:
        full[" ".join(_tokens(name, True))].add(city)
        b = _tokens(name, False)
        short[" ".join(b)].add(city)
        for w in b:
            if len(w) >= 4:
                words[w].add((" ".join(b), city))
    return full, short, words


def from_list(complex_name: str) -> str:
    full, short, words = _index()
    one = lambda cities: next(iter(cities)) if len(cities) == 1 else ""
    city = one(full.get(" ".join(_tokens(complex_name, True)), set()))
    if city:
        return city
    b = " ".join(_tokens(complex_name, False))
    if not b:
        return ""
    city = one(short.get(b, set()))
    if city:
        return city
    pref = set().union(*[c for k, c in short.items() if k and (k.startswith(b) or b.startswith(k))] or [set()])
    if len(pref) == 1:
        return one(pref)
    # самое редкое слово названия решает: «batysmura» встречается только в Атырау, а «biznes» — везде
    for w in sorted((w for w in b.split() if w in words), key=lambda w: len({k for k, _ in words[w]})):
        city = one({c for _, c in words[w]})
        if city:
            return city
    return ""


def _cfg() -> dict:
    return yaml.safe_load((CONFIG_DIR / "cities.yaml").read_text(encoding="utf-8")) or {}


def set_city(complex_name: str, city: str) -> None:
    db.kv_set(f"city:{norm(complex_name)}", city.strip())


def city_for(complex_name: str, group: str = "") -> str:
    saved = db.kv_get(f"city:{norm(complex_name)}")
    if saved:
        return saved
    cfg = _cfg()
    for name, city in (cfg.get("complexes") or {}).items():
        if norm(name) == norm(complex_name):
            return city
    city = from_list(complex_name)
    if city:
        return city
    low = (complex_name or "").lower()
    for word, city in (cfg.get("keywords") or {}).items():
        if word in low:
            return city
    return (cfg.get("groups") or {}).get((group or "").strip(), "")
