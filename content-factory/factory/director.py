"""Режиссёр монтажа Reels: раскадровка по реальному времени слов озвучки (config/reels-motion.md).

Почему отдельный проход после озвучки: сценарист не знает, сколько длится сцена, и не может поставить
картинку на слово. Режиссёр видит каждое слово с его временем и решает, что в окне, когда меняется
метафора-якорь и где толчок. Картинки потом проверяются «по глазам» (broll.pick), числа — только из источника.
"""
from __future__ import annotations

import json
import logging

from . import llm
from .models import ReelPackage, Storyboard
from .settings import CONFIG_DIR, settings

log = logging.getLogger(__name__)
MIN_GAP = 0.8        # чаще глаз не успевает прочитать картинку
LEAD = 0.4           # картинка появляется чуть раньше слова, как у tillo (0,3–0,7 с)


def words_of(subs: list[dict]) -> list[dict]:
    """Все слова озвучки по порядку: [{i, t, w}]."""
    out = []
    for s in subs:
        for w in s.get("words", []):
            out.append({"i": len(out), "t": w["t"], "w": w["w"]})
    return out


def _catalogs() -> str:
    import yaml
    from .reels import reels_photos
    from .render import illustrations
    photos = {p["id"]: p["desc"] for p in yaml.safe_load((CONFIG_DIR / "photos.yaml").read_text(encoding="utf-8"))["photos"]}
    ills = {p["id"]: p["desc"] for p in yaml.safe_load((CONFIG_DIR / "illustrations.yaml").read_text(encoding="utf-8"))["illustrations"]}
    out = "## Наши фото для Reels (kind=photo, query=id)\n" + "\n".join(f"- {k}: {photos.get(k, '')}" for k in reels_photos())
    out += "\n\n## Наши иллюстрации (kind=illustration, query=id)\n" + "\n".join(f"- {k}: {ills.get(k, '')}" for k in illustrations())
    return out


def system(fmt: int = 5) -> str:
    from .season import today
    from .writer import MONTHS_NOM
    rules = (CONFIG_DIR / ("reels-motion-v6.md" if fmt == 6 else "reels-motion.md")).read_text(encoding="utf-8")
    return (f"{rules}\n\n## Сейчас\nМесяц: {MONTHS_NOM[today().month - 1]}. Сезон картинок — этот.\n\n"
            "## Как отвечать\nВерни раскадровку по схеме. Номера слов — из списка ниже. Не меняй текст озвучки.")


def direct(pkg: ReelPackage, subs: list[dict], hook_end: float, total: float, item: dict | None,
           fmt: int = 5) -> Storyboard:
    words = words_of(subs)
    listing = "\n".join(f"{w['i']} [{w['t']:.2f}] {w['w']}" for w in words)
    scenes = [{"type": s.type, "voice": s.voice, "highlight": s.highlight,
               "viz": s.viz.model_dump() if s.viz.kind != "none" else None} for s in pkg.scenes]
    user = (f"Длина ролика {total:.1f} с, хук заканчивается на {hook_end:.2f} с.\n\n"
            f"## Слова озвучки (номер [время, с] слово)\n{listing}\n\n"
            f"## Сцены сценария (подсказка сценариста по метафоре — viz)\n{json.dumps(scenes, ensure_ascii=False)}\n\n"
            f"## Люди из источника\n{json.dumps([p.model_dump() for p in pkg.people], ensure_ascii=False)}\n\n"
            f"## Источник\n{pkg.source_line}\n"
            + (f"{item['title']}\n{item.get('summary') or ''}\n" if item else "")
            + "\n" + _catalogs())
    if fmt == 6:
        user += ("\n\n## Формат 6: главы данных (поле chapters, anchor оставь пустым)\n"
                 "Главы — только если в тексте источника ниже есть цифры: доли, «во сколько раз», число участников, годы. "
                 "Нет цифр — chapters пустой, ролик держится на перебивках. Ничего не придумывай и не округляй сверх источника.\n"
                 "В главе: сравнение двух групп (compare) или их изменение во времени (timeline), либо масштаб "
                 "исследования (scale); одна крупная цифра (big) и её смысл. icon — предмет ТЕМЫ ролика "
                 "(зрение — eye или glasses; дом и подъезд — window, house, door; одиночество — elder; чай — cup), "
                 "silhouette — форма темы. evidence — дословная фраза источника с этими цифрами. "
                 "1–3 главы по 3–6 с (word — начало, until_word — конец), внутри глав перебивок нет. "
                 "expand_word — начало финальной главы (повтор последней в полном виде).\n\n"
                 f"## Текст источника для цифр\n{source_text(pkg, item)[:6000]}")
    sb = llm.ask(Storyboard, system=system(fmt), user=user, model=settings.writer_model, effort=settings.writer_effort)
    return normalize(sb, words, hook_end)


def normalize(sb: Storyboard, words: list[dict], hook_end: float) -> Storyboard:
    """Чинит то, что модель могла нарушить: порядок, частоту резов, одну фигуру на весь ролик."""
    n = len(words)
    clamp = lambda i: min(max(int(i), 0), n - 1)
    t = lambda i: words[clamp(i)]["t"]
    cuts, last = [], -99.0
    for c in sorted(sb.cuts, key=lambda c: c.word):
        c.word = clamp(c.word)
        if cuts and t(c.word) - last < MIN_GAP:
            continue
        cuts.append(c)
        last = t(c.word)
    if cuts:
        cuts[0].word = 0                 # первый кадр — с первого слова хука
    sb.cuts = cuts
    if sb.anchor:
        kind = sb.anchor[0].viz.kind
        states = [a for a in sorted(sb.anchor, key=lambda a: a.word) if a.viz.kind == kind]
        first_after = next((w["i"] for w in words if w["t"] >= hook_end), 0)
        for a in states:
            a.word = max(clamp(a.word), first_after)
        states[0].word = first_after
        sb.anchor = states
    sb.expand_word = clamp(sb.expand_word)
    flashes = [a for a in sb.accents if a.motion == "flash"]
    sb.accents = [a for a in sb.accents if a.motion != "flash"] + flashes[:1]   # вторая вспышка максимум
    for a in sb.accents:
        a.word = clamp(a.word)
    return sb


def word_time(words: list[dict], i: int) -> float:
    return words[min(max(i, 0), len(words) - 1)]["t"]


def source_text(pkg: ReelPackage, item: dict | None) -> str:
    """Всё, откуда главы данных могут брать цифры: заметка, статья, проверка фактов сценария."""
    parts = [pkg.source_line, *pkg.fact_check]
    if item:
        parts += [item.get("title") or "", item.get("summary") or ""]
        try:
            from .ingest import fetch_article_text
            parts.append(fetch_article_text(item["url"]) or "")
        except Exception as exc:          # без статьи — только заметка; цифр меньше, но выдумывать нельзя
            log.info("Статья для цифр не загружена: %s", exc)
    return "\n".join(p for p in parts if p)


def _nums(text: str) -> set[str]:
    import re
    text = re.sub(r"(\d)[, ](\d{3})\b", r"\1\2", text or "")        # 8,175 и 8 175 — одно число
    return {re.sub(r"[\s ]", "", m).replace(",", ".") for m in re.findall(r"\d[\d\s ]*(?:[.,]\d+)?", text)}


def valid_chapters(chapters: list, source: str) -> list:
    """Глава остаётся, только если все её цифры есть в источнике (решение владельца: нет цифр — нет главы).
    Почему проверка в коде: на #24 режиссёр нарисовал главу с процентом, которого в источнике не было."""
    have = _nums(source)
    fmt = lambda v: str(int(v)) if float(v).is_integer() else str(v)
    out = []
    for ch in chapters:
        need = _nums(ch.big) | {fmt(g.value) for g in ch.groups if g.value} | {fmt(g.start) for g in ch.groups if g.start}
        need |= {str(y) for y in ch.years}
        if not _nums(ch.big) or not need <= have:
            log.info("Глава данных снята: цифр %s нет в источнике", sorted(need - have) or ch.big)
            continue
        out.append(ch)
    return out
