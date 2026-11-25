"""Сборка и доставка пакетов: выбор темы → тексты → слайды → Telegram."""
from __future__ import annotations

import html
import logging
import zipfile
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import update

from . import db, ingest, render, score, sheets, telegram, threads, writer
from .models import PostPackage
from .settings import settings

log = logging.getLogger(__name__)
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
          "сентября", "октября", "ноября", "декабря"]


def today() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()


def resolve_rubric(key: str) -> str:
    rubrics = writer.load_yaml("rubrics.yaml")["rubrics"]
    r = rubrics[key]
    if r["source"] == "drive":   # этап 2: отчёты из Google Drive ещё не подключены
        return r.get("fallback", "science")
    return key


def choose_item(rubric_key: str, exclude_ids: set[int] = frozenset()) -> dict | None:
    r = writer.load_yaml("rubrics.yaml")["rubrics"][rubric_key]
    if r["source"] == "brand":
        return None
    item = score.pick(rubric_key, prefer_kind=r.get("prefer_kind"), need_number=rubric_key == "number")
    if item is None and rubric_key == "number":   # нет материала с цифрой — берём лучшую тему для науки
        item = score.pick("science")
    if item and item["id"] in exclude_ids:
        return None
    return item


def mark_used(item: dict | None) -> None:
    if item:
        with db.engine.begin() as c:
            c.execute(update(db.items).where(db.items.c.id == item["id"]).values(used=True))


def create_post(rubric_key: str, slot_date: date, slot: int, item: dict | None) -> int:
    with db.engine.begin() as c:
        res = c.execute(db.posts.insert().values(
            item_id=item["id"] if item else None, rubric=rubric_key, slot_date=slot_date.isoformat(),
            slot=slot, status="generating", feedback=[], created_at=db.now(), updated_at=db.now()))
        return res.inserted_primary_key[0]


def generate(post_id: int, feedback: list[str] | None = None) -> None:
    """Сгенерировать (или переделать) пакет поста и отправить его в Telegram."""
    post = db.get_post(post_id)
    item = db.get_item(post["item_id"])
    previous = post["package"] if feedback else None
    pkg = writer.write(post["rubric"], item, feedback=feedback, previous=previous)
    rubric_title = writer.load_yaml("rubrics.yaml")["rubrics"][post["rubric"]]["title"]
    files = render.render(pkg, rubric_title, f"{post['slot_date']}-post{post_id}")
    db.update_post(post_id, package=pkg.model_dump(), files=[str(f) for f in files], status="generated")
    deliver(post_id)


def _zip(files: list[str], name: str):
    from pathlib import Path
    paths = [Path(f) for f in files]
    zpath = paths[0].parent / f"{name}.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        for p in paths:
            z.write(p, p.name)
    return zpath


def keyboard(post_id: int) -> list[list[dict]]:
    return [
        [{"text": "Одобрить", "callback_data": f"a:{post_id}"},
         {"text": "Переделать", "callback_data": f"r:{post_id}"}],
        [{"text": "Другая тема", "callback_data": f"n:{post_id}"},
         {"text": "Отклонить", "callback_data": f"x:{post_id}"}],
    ]


def deliver(post_id: int) -> None:
    from pathlib import Path
    post = db.get_post(post_id)
    pkg = PostPackage.model_validate(post["package"])
    item = db.get_item(post["item_id"])
    cfg = writer.load_yaml("rubrics.yaml")
    d = date.fromisoformat(post["slot_date"])
    when = f"{d.day} {MONTHS[d.month - 1]}, {cfg['slot_times'][post['slot']]}"
    e = html.escape
    chat = settings.telegram_chat_id

    telegram.send_album(chat, [Path(f) for f in post["files"]])
    telegram.send_document(chat, _zip(post["files"], f"BIGLife-{post['slot_date']}-{post_id}"),
                           caption="Слайды в исходном качестве для загрузки в Instagram")

    head = (f"<b>Пост #{post_id} · {e(when)}</b>\n"
            f"Рубрика: {e(cfg['rubrics'][post['rubric']]['title'])}\n"
            f"Тема: {e(pkg.headline)}\n"
            + (f"Источник: <a href=\"{e(item['url'])}\">{e(item['feed'])}</a>\n" if item else ""))
    caption = (f"{pkg.caption_ru}\n\nИсточник: {pkg.source_line}\n\n"
               + " ".join(f"#{h}" for h in pkg.hashtags))
    telegram.send_message(chat, head + "\n<b>Подпись (скопировать):</b>\n\n" + e(caption))

    threads = "\n\n".join(f"{i}/ {e(t)}" for i, t in enumerate(pkg.threads, 1))
    facts = "\n".join(f"• {e(f)}" for f in pkg.fact_check)
    threads_note = ("опубликуется после «Одобрить»" if threads.enabled()
                    else "Threads не подключён, опубликуйте вручную")
    details = (f"<b>Қазақша:</b> {e(pkg.summary_kz)}\n\n<b>O‘zbekcha:</b> {e(pkg.summary_uz)}\n\n"
               f"<b>Alt-текст:</b> {e(pkg.alt_text)}\n\n"
               f"<b>Threads ({threads_note}):</b>\n{threads}\n\n"
               f"<b>Проверка фактов:</b>\n{facts}")
    if post["feedback"]:
        details += "\n\n<i>Учтены комментарии:</i> " + e("; ".join(post["feedback"]))
    msg_id = telegram.send_message(chat, details, keyboard=keyboard(post_id))
    db.update_post(post_id, status="sent", tg_message_id=msg_id)
    sheets.upsert(db.get_post(post_id), item)


def run_daily(day: date | None = None) -> list[int]:
    """Собрать RSS, оценить темы и подготовить посты на день по сетке рубрик."""
    day = day or today()
    ingest.run()
    score.run()
    schedule = writer.load_yaml("rubrics.yaml")["schedule"]
    slots = schedule[day.isoweekday()][: settings.posts_per_day]
    created = []
    for slot, key in enumerate(slots):
        rubric_key = resolve_rubric(key)
        item = choose_item(rubric_key)
        if item is None and writer.load_yaml("rubrics.yaml")["rubrics"][rubric_key]["source"] == "rss":
            telegram.send_message(settings.telegram_chat_id,
                                  f"Для рубрики «{html.escape(rubric_key)}» на {day} нет подходящих материалов.")
            continue
        mark_used(item)
        post_id = create_post(rubric_key, day, slot, item)
        try:
            generate(post_id)
            created.append(post_id)
        except Exception as exc:
            log.exception("Пост %s не собран", post_id)
            db.update_post(post_id, status="failed")
            telegram.send_message(settings.telegram_chat_id,
                                  f"Пост #{post_id} не удалось собрать: {html.escape(str(exc))[:500]}")
    return created
