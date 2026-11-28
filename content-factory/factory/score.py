"""ИИ-скоринг свежих материалов: релевантность, вирусность, польза, лучшая рубрика."""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import and_, or_, select, update

from . import db, llm
from .models import ScoreBatch
from .settings import settings

log = logging.getLogger(__name__)
BATCH = 40

SYSTEM = """Ты — редактор Instagram-паблика BIG Life о добрососедстве, социальном здоровье и активном долголетии
(жилые сообщества в Казахстане и Узбекистане, аудитория — жители ЖК и молодые семьи).
Оцени материалы из RSS как темы для вирусных каруселей. Будь строгим: высокие баллы только у материалов,
которые прямо касаются отношений между людьми, соседства, сообществ, одиночества, социальной поддержки,
семьи, долголетия, здоровых привычек, которые легче делать вместе, или городской среды.
Узкоспециальные нейро- и клинические работы без понятного вывода для обычного человека — низкая релевантность.
Не выдумывай цифры: has_number = true, только если цифра есть в тексте материала."""


def total(s) -> float:
    return round(0.45 * s.relevance + 0.35 * s.virality + 0.2 * s.usefulness, 2)


def run(limit: int = 200) -> int:
    db.init()
    since = db.now() - timedelta(days=settings.freshness_days)
    with db.engine.begin() as c:
        rows = c.execute(
            select(db.items.c.id, db.items.c.feed, db.items.c.title, db.items.c.summary)
            .where(and_(db.items.c.score.is_(None), db.items.c.used.is_(False),
                        or_(db.items.c.published >= since,
                            and_(db.items.c.published.is_(None), db.items.c.fetched_at >= since))))
            .order_by(db.items.c.id.desc()).limit(limit)
        ).all()
    done = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        listing = "\n\n".join(
            f"id={r.id} | {r.feed}\n{r.title}\n{(r.summary or '')[:600]}" for r in chunk)
        lessons = db.kv_get("learnings") or ""   # итоги прошлой недели из insights.report
        result = llm.ask(ScoreBatch, system=SYSTEM + (f"\n\n{lessons}\nУчитывай это в оценке virality." if lessons else ""),
                         user=f"Оцени каждый материал (верни оценку для каждого id):\n\n{listing}",
                         model=settings.scorer_model, effort=settings.scorer_effort)
        ids = {r.id for r in chunk}
        with db.engine.begin() as c:
            for s in result.scores:
                if s.id not in ids:
                    continue
                c.execute(update(db.items).where(db.items.c.id == s.id)
                          .values(score=total(s), score_data=s.model_dump()))
                done += 1
    log.info("Оценено материалов: %s", done)
    return done


def pick(rubric: str, prefer_kind: str | None = None, need_number: bool = False) -> dict | None:
    """Лучший неиспользованный материал для рубрики."""
    since = db.now() - timedelta(days=settings.freshness_days)
    with db.engine.begin() as c:
        rows = c.execute(
            select(db.items).where(and_(db.items.c.score.is_not(None), db.items.c.used.is_(False),
                                        db.items.c.fetched_at >= since))
            .order_by(db.items.c.score.desc()).limit(60)
        ).mappings().all()

    def rank(r):
        sd = r["score_data"] or {}
        bonus = 1.0 if sd.get("best_rubric") == rubric else 0.0
        bonus += 0.5 if prefer_kind and r["kind"] == prefer_kind else 0.0
        return r["score"] + bonus

    candidates = [dict(r) for r in rows
                  if not need_number or (r["score_data"] or {}).get("has_number")]
    candidates = [r for r in candidates if (r["score_data"] or {}).get("relevance", 0) >= 5]
    return max(candidates, key=rank) if candidates else None
