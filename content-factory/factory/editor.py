"""Вычитка пакета: тон BIG Life + правила humanizer-ru, затем детерминированная проверка запретов.

Редактор получает тексты пакета и возвращает ту же структуру. Из ответа берутся только текстовые поля,
всё служебное (типы слайдов, фото, иллюстрации, люди) остаётся от исходного пакета.
"""
from __future__ import annotations

import logging
import re

from typing import Literal

from pydantic import BaseModel, Field

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
    # общие определения из редакционной политики: ничего не говорят читателю, значит, можно конкретнее
    (r"\b(уникальн|культов|знаменит|креативн|элитн|изысканн|невероятн|потрясающ)\w*", "общее определение"),
    (r"\b(хочется надеяться|как известно|пожалуй)\b", "размытая оговорка"),
    # дежурные связки Reels: модель копирует их из ролика в ролик, зритель узнаёт шаблон
    (r"\b(самое странное другое|ответ в конце|в конце (скажу|расскажу)|звучит как правда|сейчас расскажу|"
     r"учёные удивились|внимание, вопрос|знаешь ли ты|спойлер)", "дежурная связка Reels"),
    (r":\s*$", "фраза оборвана на двоеточии"),
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


LINT_CATS = ("hard", "parallel", "calque", "bureau")   # из pishi берём то, что почти всегда правка, а не вкус


def lint(pkg) -> dict:
    """Линтер pishi (factory/vendor) по текстам пакета: подсказка редактору и балл для согласующего.
    Жёстким фильтром не делаем: для коротких текстов одно попадание сильно роняет балл."""
    from .vendor.pishi_check import analyze
    res = analyze("\n".join(texts_of(pkg)))
    hits = [f"{h['hit']} («{h['context'].strip()[:60]}»)" for c in LINT_CATS for h in res["findings"].get(c, [])]
    return {"score": res["score"], "hits": hits[:12]}


def choppy(pkg) -> str:
    """Рубленая озвучка: средняя длина предложения меньше 9 слов или три коротких подряд (жалоба владельца)."""
    if not hasattr(pkg, "scenes"):
        return ""
    text = " ".join(s.voice for s in pkg.scenes)
    sents = [x for x in re.split(r"(?<=[.!?…])\s+", text) if x.strip()]
    if not sents:
        return ""
    lens = [len(x.split()) for x in sents]
    avg = sum(lens) / len(lens)
    run = max((sum(1 for _ in g) for k, g in __import__("itertools").groupby(l <= 6 for l in lens) if k), default=0)
    if avg < 9 or run >= 3:
        return (f"озвучка рубленая: в среднем {avg:.0f} слов в предложении, коротких подряд {run}. "
                "Нужен связный рассказ полными предложениями по 12–20 слов, как в образцах голоса")
    return ""


def violations(pkg) -> list[str]:
    found = [c] if (c := choppy(pkg)) else []
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
    if len(new.get(frames, [])) != len(data[frames]):
        # раньше правки сцен в этом случае молча терялись
        log.warning("Вычитка вернула %s %s вместо %s — тексты слайдов не взяты", len(new.get(frames, [])), frames, len(data[frames]))
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
    # полный скилл humanizer-ru + поправки бренда (они важнее): раньше здесь была только короткая выжимка
    skill = (CONFIG_DIR / "humanizer-ru.md").read_text(encoding="utf-8")
    rules = (CONFIG_DIR / "humanizer.md").read_text(encoding="utf-8")
    editorial = (CONFIG_DIR / "editorial.md").read_text(encoding="utf-8")
    redpol = CONFIG_DIR / "redpolitika.md"
    if redpol.exists():
        editorial += "\n\n" + redpol.read_text(encoding="utf-8")
    system = (f"{skill}\n\n{rules}\n\n## Голос бренда (tone of voice) — важнее правил скилла\n{brand}\n\n{editorial}")
    current = pkg
    for attempt in range(2):
        issues = violations(current)
        note = ("\n\nАвтоматическая проверка нашла запрещённое:\n- " + "\n- ".join(issues)) if issues else ""
        try:
            hints = lint(current)["hits"]
        except Exception:      # линтер — подсказка, его сбой не должен мешать вычитке
            hints = []
        if hints:
            note += ("\n\nЛинтер pishi подсвечивает (проверь, большинство стоит переписать):\n- " + "\n- ".join(hints))
        user = ("Вычитай тексты этого поста по правилам выше. Верни тот же JSON целиком, меняя только тексты. "
                "Структуру, типы слайдов, количество пунктов и все id не меняй." + note +
                "\n\n" + json.dumps(current.model_dump(), ensure_ascii=False))
        try:
            edited = llm.ask(type(pkg), system=system, user=user, model=settings.writer_model,
                             effort=settings.editor_effort, max_tokens=32000)
            current = _merge(current, edited)
        except Exception as exc:          # вычитка не должна ронять пост
            log.warning("Вычитка не удалась: %s", exc)
            break
        if not violations(current):
            break
    current = _fix_dashes(current)
    return current, violations(current)


# ---------- редактор сценария Reels ----------

class ReelReview(BaseModel):
    checklist_score: int = Field(ge=0, le=24, description="Сумма по чек-листу «Ремесла Reels» (12 пунктов по 0/1/2)")
    hook_score: int = Field(ge=1, le=10, description="Сила хука для незнакомого с брендом зрителя: 10 — невозможно пролистать")
    best_hook: str = Field(description="Лучший хук из hook_options или твой вариант, до 8 слов, если все слабые")
    one_story: bool = Field(description="Ролик рассказывает одну историю одного исследования, без лишних экспертов и тем")
    data_driven: bool = Field(description="Инфографика опирается на настоящие числа источника")
    problems: list[str] = Field(description="Конкретные проблемы: номер сцены и что не так (структура, хук, дежурные фразы, устная речь, ToV)")
    verdict: Literal["ok", "rewrite"] = Field(description="rewrite — если checklist_score < 18, ноль по блокирующему пункту, hook_score < 7 или нет одной истории")


REVIEW_RULES = """Ты шеф-редактор коротких видео и редактор humanizer-ru. Тебе дают сценарий Reels для пробного показа
людям, которые не знают бренд BIG Life. Оцени строго, как редактор, которому за досмотры платят.
Проверь:
1. Хук: конкретный, неожиданный, понятен без контекста, до 8 слов. Не общее утверждение, не вопрос-заглушка,
   не миф без поворота. Поставь hook_score честно: средний хук — 5.
2. Одна история: одно исследование, одна находка, одна главная цифра; нет лишних экспертов, цитат и побочных тем.
3. Ход: хук → почему это касается зрителя → как узнали → находка с цифрой → поворот → что делать → финал,
   который перекликается с хуком и не оборван.
4. Инфографика на настоящих числах источника (или честно помечена как условная).
5. Голос как в образцах tillo.journal: связный рассказ полными предложениями (12–20 слов, союзы), а не
   нарезка коротких фраз; рубленый ритм — серьёзная проблема. Плюс humanizer-ru: глаголы, нет канцелярита,
   кальки, «является», дежурных связок, длинного тире. Тон BIG Life: тёплый сосед плюс наука, без морали.
6. Факты только из источника.
Пиши problems конкретно: «сцена 3: …». Не переписывай сценарий сам."""


def review_reel(pkg, source: str = ""):
    """Оценка сценария до озвучки и рендера: дешевле переписать текст, чем перерендерить ролик."""
    import json
    skill = (CONFIG_DIR / "humanizer-ru.md").read_text(encoding="utf-8")
    brand = (CONFIG_DIR / "brand.md").read_text(encoding="utf-8")
    craft = (CONFIG_DIR / "reels-craft.md")
    redpol = (CONFIG_DIR / "redpolitika.md")
    samples = CONFIG_DIR / "reels-voice-samples.md"
    extra = "".join(f"\n\n{p.read_text(encoding='utf-8')}" for p in (craft, redpol, samples) if p.exists())
    system = f"{REVIEW_RULES}\n\nОценивай по чек-листу из «Ремесла Reels», если он ниже.{extra}\n\n## Голос бренда\n{brand}\n\n## Правила humanizer-ru\n{skill}"
    user = (("Источник:\n" + source[:6000] + "\n\n") if source else "") + \
        "Сценарий (JSON):\n" + json.dumps(pkg.model_dump(), ensure_ascii=False)
    # правил много (humanizer-ru + ремесло Reels): с лимитом 16k ответ обрезался на размышлениях
    return llm.ask(ReelReview, system=system, user=user, model=settings.writer_model, effort=settings.editor_effort,
                   max_tokens=32000)
