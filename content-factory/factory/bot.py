"""Воркер: Telegram-бот с кнопками согласования + ежедневный запуск завода по расписанию."""
from __future__ import annotations

import html
import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import db, pipeline, sheets, telegram, threads
from .settings import settings

log = logging.getLogger(__name__)
e = html.escape


def allowed(user_id: int) -> bool:
    return not settings.approver_ids or user_id in settings.approver_ids


def on_callback(cb: dict) -> None:
    user = cb["from"]
    if not allowed(user["id"]):
        telegram.answer_callback(cb["id"], "Согласовывать посты может только ответственный")
        return
    action, _, raw_id = cb.get("data", "").partition(":")
    post = db.get_post(int(raw_id)) if raw_id.isdigit() else None
    if not post:
        telegram.answer_callback(cb["id"], "Пост не найден")
        return
    chat, msg_id, who = cb["message"]["chat"]["id"], cb["message"]["message_id"], e(user.get("first_name", ""))
    if post["status"] in ("approved", "rejected"):
        telegram.answer_callback(cb["id"], "Решение по этому посту уже принято")
        return

    if action == "a":
        telegram.answer_callback(cb["id"], "Одобрено")
        telegram.edit_keyboard(chat, msg_id, None)
        ids = []
        if threads.enabled():
            try:
                ids = threads.publish_thread(post["package"]["threads"])
            except Exception as exc:
                log.exception("Threads")
                telegram.send_message(chat, f"Пост #{post['id']} одобрен, но тред в Threads не опубликован: "
                                            f"{e(str(exc))[:400]}", reply_to=msg_id)
        db.update_post(post["id"], status="approved", threads_ids=ids)
        done = f"Пост #{post['id']} одобрил(а) {who}."
        if ids:
            done += f" Тред в Threads опубликован ({len(ids)} сообщ.)."
        telegram.send_message(chat, done + " Можно публиковать в Instagram.", reply_to=msg_id)
    elif action == "x":
        telegram.answer_callback(cb["id"], "Отклонено")
        telegram.edit_keyboard(chat, msg_id, None)
        db.update_post(post["id"], status="rejected")
        telegram.send_message(chat, f"Пост #{post['id']} отклонил(а) {who}.", reply_to=msg_id)
    elif action == "r":
        telegram.answer_callback(cb["id"])
        prompt = telegram.send_message(
            chat, f"Что исправить в посте #{post['id']}? Ответьте на это сообщение одним комментарием.",
            reply_to=msg_id, force_reply=True)
        db.kv_set(f"redo_prompt:{chat}:{prompt}", str(post["id"]))
        db.update_post(post["id"], status="redo")
    elif action == "n":
        telegram.answer_callback(cb["id"], "Ищу другую тему")
        telegram.edit_keyboard(chat, msg_id, None)
        db.update_post(post["id"], status="rejected")
        replace_topic(post, chat)
    sheets.upsert(db.get_post(post["id"]), db.get_item(post["item_id"]))


def replace_topic(post: dict, chat) -> None:
    item = pipeline.choose_item(post["rubric"], exclude_ids={post["item_id"]} if post["item_id"] else set())
    if item is None and post["item_id"] is not None:
        telegram.send_message(chat, "Подходящих тем больше нет — дождитесь нового сбора RSS.")
        return
    pipeline.mark_used(item)
    new_id = pipeline.create_post(post["rubric"], datetime.fromisoformat(post["slot_date"]).date(),
                                  post["slot"], item)
    telegram.send_message(chat, f"Готовлю пост #{new_id} на другую тему, это займёт пару минут.")
    run_safely(new_id, chat)


def run_safely(post_id: int, chat, feedback: list[str] | None = None) -> None:
    try:
        pipeline.generate(post_id, feedback=feedback)
    except Exception as exc:
        log.exception("Генерация поста %s", post_id)
        db.update_post(post_id, status="failed")
        telegram.send_message(chat, f"Не получилось собрать пост #{post_id}: {e(str(exc))[:400]}")


def on_message(msg: dict) -> None:
    reply = msg.get("reply_to_message")
    text = (msg.get("text") or "").strip()
    chat = msg["chat"]["id"]
    if text.startswith("/id"):
        telegram.send_message(chat, f"chat_id: <code>{chat}</code>\nваш user_id: <code>{msg['from']['id']}</code>")
        return
    if text.startswith("/threads") and allowed(msg["from"]["id"]):
        try:
            url = threads.authorize_url()
        except threads.ThreadsError as exc:
            telegram.send_message(chat, e(str(exc)))
            return
        prompt = telegram.send_message(
            chat, f"1. Откройте ссылку и разрешите доступ аккаунту BIG Life:\n{e(url)}\n\n"
                  "2. Браузер перейдёт на страницу, которая не откроется, — это нормально. "
                  "Скопируйте адрес этой страницы целиком (в нём есть code=...) и пришлите ответом на это сообщение. "
                  "Код действует 1 час.", force_reply=True)
        db.kv_set(f"threads_prompt:{chat}:{prompt}", "1")
        return
    if text.startswith("/run") and allowed(msg["from"]["id"]):
        telegram.send_message(chat, "Запускаю сбор материалов и подготовку постов на сегодня.")
        pipeline.run_daily()
        return
    if not reply or not text:
        return
    if db.kv_get(f"threads_prompt:{chat}:{reply['message_id']}") == "1" and allowed(msg["from"]["id"]):
        db.kv_set(f"threads_prompt:{chat}:{reply['message_id']}", "")
        try:
            username = threads.connect(text)
            telegram.send_message(chat, f"Threads подключён: @{e(str(username))}. "
                                        "Одобренные посты будут публиковаться туда тредом.")
        except Exception as exc:
            telegram.send_message(chat, f"Не удалось подключить Threads: {e(str(exc))[:400]}. "
                                        "Отправьте /threads и попробуйте ещё раз.")
        return
    raw = db.kv_get(f"redo_prompt:{chat}:{reply['message_id']}")
    if not raw or not allowed(msg["from"]["id"]):
        return
    post = db.get_post(int(raw))
    feedback = list(post["feedback"] or []) + [text]
    db.update_post(post["id"], feedback=feedback, status="generating")
    db.kv_set(f"redo_prompt:{chat}:{reply['message_id']}", "")
    telegram.send_message(chat, f"Переделываю пост #{post['id']} с учётом комментария.", reply_to=msg["message_id"])
    run_safely(post["id"], chat, feedback=feedback)


def maybe_run_daily() -> None:
    now = datetime.now(ZoneInfo(settings.timezone))
    key = now.date().isoformat()
    if not settings.telegram_chat_id:
        return                            # группа ещё не настроена — посты некуда отправлять
    if now.hour < settings.daily_run_hour or db.kv_get("last_daily") == key:
        return
    db.kv_set("last_daily", key)          # отмечаем заранее, чтобы при сбое не запускать повторно в цикле
    log.info("Ежедневный запуск %s", key)
    try:
        threads.refresh_token_if_needed()
        pipeline.run_daily(now.date())
    except Exception as exc:
        log.exception("Ежедневный запуск")
        telegram.send_message(settings.telegram_chat_id, f"Ежедневный запуск упал: {e(str(exc))[:500]}")


def run_forever() -> None:
    db.init()
    if not settings.approver_ids:
        log.warning("TELEGRAM_APPROVER_IDS не задан: одобрять посты может любой участник группы")
    offset = int(db.kv_get("tg_offset", "0")) or None
    while True:
        try:
            maybe_run_daily()
            for upd in telegram.get_updates(offset):
                offset = upd["update_id"] + 1
                db.kv_set("tg_offset", str(offset))
                try:
                    if "callback_query" in upd:
                        on_callback(upd["callback_query"])
                    elif "message" in upd:
                        on_message(upd["message"])
                except Exception:
                    log.exception("Обработка обновления %s", upd.get("update_id"))
        except Exception:
            log.exception("Цикл бота")
            time.sleep(10)
