"""Еженедельный отчёт и самообучение: цифры постов из Instagram → отчёт в группу → уроки для тем и хуков.

Почему так:
- Цифры берём из Instagram API сами, без ручного ввода SMM-щиком: ручной ввод забывают, и отчёт пустеет.
- Посты, выложенные руками («Выложу руками»), находим в ленте по началу подписи: подпись делает завод.
- Сравниваем не лайки, а вовлечённость на охват: сохранения и репосты весят больше, это сигнал «полезно,
  отправлю соседу». Охват сам по себе зависит от дня и алгоритма, а не от темы.
- Итоги недели превращаются в короткие «уроки» (kv learnings): их видят скоринг тем и автор,
  поэтому следующая неделя тянется к тому, что сработало. Сетку рубрик код сам не меняет — это решение
  редакции, отчёт только подсказывает.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

from sqlalchemy import select

from . import db, instagram

log = logging.getLogger(__name__)
METRICS = ["reach", "saved", "shares", "likes", "comments"]


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", (text or "").lower()).strip()[:80]


def fetch_metrics(media_id: str) -> dict:
    try:
        data = instagram._request("GET", f"{media_id}/insights", metric=",".join(METRICS))["data"]
        return {m["name"]: (m.get("values") or [{}])[0].get("value", m.get("total_value", {}).get("value", 0))
                for m in data}
    except instagram.InstagramError:
        out = {}
        for name in METRICS:      # одна метрика не поддержана для типа медиа — берём остальные по одной
            try:
                m = instagram._request("GET", f"{media_id}/insights", metric=name)["data"][0]
                out[name] = (m.get("values") or [{}])[0].get("value", 0)
            except (instagram.InstagramError, IndexError, KeyError):
                pass
        return out


def score(m: dict) -> float:
    """Вовлечённость на 100 охвата: сохранения и репосты ×3, комментарии ×2, лайки ×1."""
    reach = m.get("reach") or 0
    if not reach:
        return 0.0
    eng = 3 * m.get("saved", 0) + 3 * m.get("shares", 0) + 2 * m.get("comments", 0) + m.get("likes", 0)
    return round(100 * eng / reach, 2)


def week_posts(start: date, end: date) -> list[dict]:
    with db.engine.begin() as c:
        rows = c.execute(select(db.posts).where(db.posts.c.slot_date >= start.isoformat(),
                                                db.posts.c.slot_date <= end.isoformat(),
                                                db.posts.c.status == "approved")).mappings().all()
    return [dict(r) for r in rows]


def match_media(posts: list[dict]) -> dict[int, str]:
    """post_id → media_id: из очереди публикации или по началу подписи в ленте."""
    found = {}
    for p in posts:
        st = instagram.state(p["id"])
        if st.get("media_id"):
            found[p["id"]] = st["media_id"]
    rest = {_norm(p["package"].get("caption_ru", "")): p["id"] for p in posts if p["id"] not in found}
    rest.pop("", None)
    if rest:
        feed = instagram._request("GET", f"{instagram.user_id()}/media", fields="id,caption", limit=60).get("data", [])
        for m in feed:
            key = _norm(m.get("caption", ""))
            for cap, pid in rest.items():
                if key and (key.startswith(cap[:60]) or cap.startswith(key[:60])):
                    found.setdefault(pid, m["id"])
    return found


def collect(start: date, end: date) -> list[dict]:
    posts = week_posts(start, end)
    media = match_media(posts)
    out = []
    for p in posts:
        row = {"id": p["id"], "rubric": p["rubric"], "headline": p["package"].get("headline", ""),
               "format": p["package"].get("format", "carousel"), "metrics": {}, "score": None,
               # A/B Reels: голос или музыка, длина, шаблон — чтобы выбрать победителя по цифрам
               "voice_mode": p["package"].get("voice_mode"), "length": p["package"].get("length"),
               "reel_format": p["package"].get("reel_format")}
        if p["id"] in media:
            row["metrics"] = fetch_metrics(media[p["id"]])
            row["score"] = score(row["metrics"])
            db.kv_set(f"ig_metrics:{p['id']}", json.dumps(row["metrics"]))
        out.append(row)
    return out


def rubric_stats(rows: list[dict]) -> list[tuple[str, float, int]]:
    by: dict[str, list[float]] = {}
    for r in rows:
        if r["score"] is not None:
            by.setdefault(r["rubric"], []).append(r["score"])
    return sorted(((k, round(sum(v) / len(v), 2), len(v)) for k, v in by.items()), key=lambda x: -x[1])


def reel_experiments(rows: list[dict]) -> list[str]:
    """Сравнение вариантов Reels. Сигнал слабый, пока роликов мало: показываем число роликов рядом."""
    reels = [r for r in rows if r["format"] == "reels" and r["score"] is not None]
    if len(reels) < 2:
        return []
    names = {"voice": "с голосом", "music": "без голоса", "short": "короткие", "mid": "средние", "long": "длинные"}
    out = ["\n<b>Эксперимент Reels</b> (вовлечённость на 100 охвата):"]
    for key in ("voice_mode", "length", "reel_format"):
        by: dict[str, list[float]] = {}
        for r in reels:
            if r.get(key):
                by.setdefault(r[key], []).append(r["score"])
        if len(by) > 1:
            out.append("• " + " · ".join(f"{names.get(k, k)}: {round(sum(v) / len(v), 2)} ({len(v)})"
                                         for k, v in sorted(by.items(), key=lambda x: -sum(x[1]) / len(x[1]))))
    if len(out) > 1:
        out.append("Выводы надёжны, когда в каждом варианте хотя бы 4–5 роликов.")
    return out if len(out) > 1 else []


def learnings(rows: list[dict], titles: dict[str, str]) -> str:
    scored = sorted([r for r in rows if r["score"] is not None], key=lambda r: -r["score"])
    if len(scored) < 3:
        return ""
    top, low = scored[:3], scored[-2:]
    lines = ["Что сработало у аудитории на прошлой неделе (больше сохранений и репостов на охват):"]
    lines += [f"- «{r['headline']}» ({titles.get(r['rubric'], r['rubric'])})" for r in top]
    lines.append("Что зашло слабее:")
    lines += [f"- «{r['headline']}» ({titles.get(r['rubric'], r['rubric'])})" for r in low]
    lines.append("Тяни темы и подачу к сильным примерам, но не копируй их дословно.")
    return "\n".join(lines)


def report(today: date) -> str:
    """Отчёт за прошлую неделю (пн–вс). Сохраняет уроки для скоринга и автора."""
    from html import escape as e
    from .writer import load_yaml
    titles = {k: v["title"] for k, v in load_yaml("rubrics.yaml")["rubrics"].items()}
    start = today - timedelta(days=today.weekday() + 7)
    end = start + timedelta(days=6)
    period = f"{start:%d.%m}–{end:%d.%m}"
    if not instagram.enabled():
        return (f"<b>Неделя {period}</b>\nОтчёт не собран: Instagram не подключён "
                f"({e('; '.join(instagram.problems()))}).")
    rows = collect(start, end)
    scored = sorted([r for r in rows if r["score"] is not None], key=lambda r: -r["score"])
    lines = [f"<b>Неделя {period}: что сработало</b>",
             f"Одобрено постов: {len(rows)}, найдено в Instagram: {len(scored)}."]
    if not scored:
        lines.append("Цифр пока нет: посты не найдены в ленте. Сигнала нет — это не значит, что всё плохо.")
        return "\n".join(lines)

    def fmt(r):
        m = r["metrics"]
        return (f"«{e(r['headline'])}» — охват {m.get('reach', 0)}, сохранения {m.get('saved', 0)}, "
                f"репосты {m.get('shares', 0)}, комментарии {m.get('comments', 0)}")
    lines.append("\n<b>Лучшие:</b>")
    lines += [f"{i}. {fmt(r)}" for i, r in enumerate(scored[:3], 1)]
    if len(scored) > 3:
        lines.append("\n<b>Слабее всего:</b>")
        lines += [f"• {fmt(r)}" for r in scored[-2:]]
    stats = rubric_stats(rows)
    if stats:
        lines.append("\n<b>Рубрики</b> (вовлечённость на 100 охвата):")
        lines += [f"• {e(titles.get(k, k))}: {v} ({n} пост.)" for k, v, n in stats]
        if len(stats) > 1:
            lines.append(f"\nУсилить: «{e(titles.get(stats[0][0], stats[0][0]))}». "
                         f"Пересмотреть подачу: «{e(titles.get(stats[-1][0], stats[-1][0]))}».")
    lines += reel_experiments(rows)
    text = learnings(rows, titles)
    if text:
        db.kv_set("learnings", text)
        lines.append("\nЗавод учтёт это при выборе тем и хуков на этой неделе.")
    return "\n".join(lines)
