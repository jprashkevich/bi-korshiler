"""Вычитка пакета: тон BIG Life + правила humanizer-ru, затем детерминированная проверка запретов.

Редактор получает тексты пакета и возвращает ту же структуру. Из ответа берутся только текстовые поля,
всё служебное (типы слайдов, фото, иллюстрации, люди) остаётся от исходного пакета.
"""
from __future__ import annotations

import logging
import re

from . import llm
from .models import PostPackage, ReelPackage
from .settings import CONFIG_DIR, settings

log = logging.getLogger(__name__)

# Детерминированные запреты: то, что после вычитки не должно остаться ни в одном тексте
BANNED = [
    (r"—", "длинное тире"),
    (r"\bне просто\b[^.!?]{0,60}\bа\b", "«не просто…, а…»"),
    (r"\bне только\b[^.!?]{0,60}\bно и\b", "«не только…, но и…»"),
    (r"\bв современном мире\b", "«в современном мире»"),
    (r"\bстоит отметить\b", "«стоит отметить»"),
    (r"\bважно (понимать|помнить|отметить)\b", "«важно понимать»"),
    (r"\bданн(ый|ая|ое|ые|ого|ой|ому|ым|ых)\b", "«данный»"),
    (r"\bявля(ется|ются)\b", "«является»"),
    (r"\bиграет (важную|ключевую|огромную) роль\b", "«играет роль»"),
    (r"\bраскры(ть|вает) потенциал\b", "«раскрыть потенциал»"),
    (r"\bна новый уровень\b", "«на новый уровень»"),
    (r"\bкомплексн(ый|ое) (подход|решение)\b", "«комплексный подход»"),
    (r"\bподводя итог\b", "«подводя итог»"),
    (r"(^|[.!?]\s+)Таким образом,", "«Таким образом,» в начале"),
    (r"\bдавайте разбер[её]мся\b", "«давайте разберёмся»"),
    (r"\bпогрузимся\b", "«погрузимся»"),
    (r"\bоткрыва(ет|ют) новые (горизонты|перспективы)\b", "«новые горизонты»"),
    (r"\bв связи с этим\b", "«в связи с этим»"),
]


def texts_of(pkg) -> list[str]:
    out = [pkg.caption_ru, pkg.summary_kz, pkg.summary_uz, *pkg.threads]
    frames = pkg.slides if isinstance(pkg, PostPackage) else pkg.scenes
    for f in frames:
        out += [f.eyebrow, f.title, f.text]
        out += getattr(f, "items", []) or []
        if isinstance(pkg, ReelPackage):
            out.append(f.voice)
    if isinstance(pkg, ReelPackage):
        out.append(pkg.cover_title)
    else:
        out.append(pkg.alt_text)
    return [t for t in out if t]


def violations(pkg) -> list[str]:
    found = []
    for t in texts_of(pkg):
        for rx, name in BANNED:
            if re.search(rx, t, flags=re.IGNORECASE | re.MULTILINE):
                found.append(f"{name}: «{t[:70]}»")
    return found


def _merge(orig, edited):
    """Берём из вычитанной версии только тексты; структура и ссылки на медиа — от исходной."""
    data = orig.model_dump()
    new = edited.model_dump()
    for key in ("headline", "caption_ru", "summary_kz", "summary_uz", "threads", "hashtags", "source_line"):
        if new.get(key):
            data[key] = new[key]
    if "alt_text" in data and new.get("alt_text"):
        data["alt_text"] = new["alt_text"]
    if "cover_title" in data and new.get("cover_title"):
        data["cover_title"] = new["cover_title"]
    frames = "slides" if "slides" in data else "scenes"
    if len(new.get(frames, [])) == len(data[frames]):
        for o, n in zip(data[frames], new[frames]):
            for k in ("eyebrow", "title", "text", "items", "voice"):
                if k in o and n.get(k) not in (None, "") and not (k == "items" and len(n[k]) != len(o[k])):
                    o[k] = n[k]
    return type(orig).model_validate(data)


def _fix_dashes(pkg):
    """Последняя страховка: длинное тире, которое пропустил редактор, заменяем на двоеточие/запятую."""
    def fix(s: str) -> str:
        s = re.sub(r"\s+—\s+это\b", " это", s)          # «X — это Y» → «X это Y»
        return re.sub(r"\s*—\s*", ", ", s)
    data = pkg.model_dump()

    def walk(v):
        if isinstance(v, str):
            return fix(v)
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: (walk(x) if k not in ("photo_id", "illustration_id", "person", "photo_ref", "name_en",
                                              "accent", "type") else x) for k, x in v.items()}
        return v
    return type(pkg).model_validate(walk(data))


def edit(pkg):
    """Вычитать пакет. Возвращает (пакет, список оставшихся замечаний)."""
    import json
    brand = (CONFIG_DIR / "brand.md").read_text(encoding="utf-8")
    rules = (CONFIG_DIR / "humanizer.md").read_text(encoding="utf-8")
    system = f"{rules}\n\n## Голос бренда (tone of voice)\n{brand}"
    current = pkg
    for attempt in range(2):
        issues = violations(current)
        note = ("\n\nАвтоматическая проверка нашла запрещённое:\n- " + "\n- ".join(issues)) if issues else ""
        user = ("Вычитай тексты этого поста по правилам выше. Верни тот же JSON целиком, меняя только тексты. "
                "Структуру, типы слайдов, количество пунктов и все id не меняй." + note +
                "\n\n" + json.dumps(current.model_dump(), ensure_ascii=False))
        try:
            edited = llm.ask(type(pkg), system=system, user=user, model=settings.writer_model,
                             effort=settings.editor_effort)
            current = _merge(current, edited)
        except Exception as exc:          # вычитка не должна ронять пост
            log.warning("Вычитка не удалась: %s", exc)
            break
        if not violations(current):
            break
    current = _fix_dashes(current)
    return current, violations(current)
