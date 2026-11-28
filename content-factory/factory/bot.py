"""Воркер: Telegram-бот с кнопками согласования + ежедневный запуск завода по расписанию."""
from __future__ import annotations

import html
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import db, instagram, pipeline, sheets, telegram, threads
from .settings import chat_id, env_problem, settings

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
    if action in IG_ACTIONS:
        on_instagram_callback(action, post, cb, chat, msg_id, who)
        return
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
        after_approve(db.get_post(post["id"]), chat, msg_id, done)
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


# ---------- Instagram ----------
# p — опубликовать сейчас, q — поставить Reels в очередь на время слота, m — выложу руками
IG_ACTIONS = {"p", "q", "m"}


def ig_keyboard(post_id: int, queued: bool) -> list[list[dict]]:
    first = ({"text": "Опубликовать сейчас", "callback_data": f"p:{post_id}"} if queued
             else {"text": "Опубликовать самостоятельно", "callback_data": f"q:{post_id}"})
    return [[first, {"text": "Выложу руками", "callback_data": f"m:{post_id}"}]]


def _when(at: datetime) -> str:
    local = at.astimezone(ZoneInfo(settings.timezone))
    today = datetime.now(ZoneInfo(settings.timezone)).date()
    day = "сегодня" if local.date() == today else f"{local.day} {pipeline.MONTHS[local.month - 1]}"
    return f"{day} в {local:%H:%M}"


def _queue_at_slot(post: dict) -> datetime:
    at = max(pipeline.slot_datetime(post), datetime.now(timezone.utc))   # одобрили после слота — публикуем сразу
    instagram.queue(post["id"], at)
    return at


def after_approve(post: dict, chat, msg_id: int, done: str) -> None:
    if not instagram.enabled():
        telegram.send_message(chat, done + " Можно публиковать в Instagram.", reply_to=msg_id)
        return
    if post["package"].get("format") == "reels":
        telegram.send_message(
            chat, done + "\nReels: опубликовать самому (с озвучкой, без музыки) или выложите руками, "
                         "чтобы добавить музыку из библиотеки Instagram?",
            reply_to=msg_id, keyboard=ig_keyboard(post["id"], queued=False))
        return
    at = _queue_at_slot(post)
    telegram.send_message(chat, done + f" Опубликую в Instagram {_when(at)}.",
                          reply_to=msg_id, keyboard=ig_keyboard(post["id"], queued=True))


def on_instagram_callback(action: str, post: dict, cb: dict, chat, msg_id: int, who: str) -> None:
    st = instagram.state(post["id"])
    if post["status"] != "approved":
        telegram.answer_callback(cb["id"], "Сначала пост нужно одобрить")
        return
    if st.get("state") in ("publishing", "published"):
        telegram.answer_callback(cb["id"], "Пост уже публикуется или опубликован")
        return
    telegram.edit_keyboard(chat, msg_id, None)
    if action == "m":
        instagram.set_state(post["id"], state="manual")
        telegram.answer_callback(cb["id"], "Хорошо, без автопубликации")
        telegram.send_message(chat, f"Пост #{post['id']}: {who} выложит в Instagram руками. "
                                    "Файлы и подпись — выше.", reply_to=msg_id)
    elif action == "q":
        at = _queue_at_slot(post)
        telegram.answer_callback(cb["id"], "Поставил в очередь")
        telegram.send_message(chat, f"Пост #{post['id']}: опубликую в Instagram {_when(at)}.",
                              reply_to=msg_id, keyboard=ig_keyboard(post["id"], queued=True))
    elif action == "p":
        instagram.queue(post["id"], datetime.now(timezone.utc))
        telegram.answer_callback(cb["id"], "Публикую")
        telegram.send_message(chat, f"Пост #{post['id']}: публикую в Instagram, это займёт до пары минут.",
                              reply_to=msg_id)


def publish_due() -> None:
    for post_id in instagram.due():
        post = db.get_post(post_id)
        if not post or post["status"] != "approved":
            instagram.set_state(post_id, state="cancelled")
            continue
        if not instagram.claim(post_id):           # его уже публикует другой процесс (перекрытие при деплое)
            continue
        chat = chat_id()
        try:
            res = instagram.publish(post)
        except Exception as exc:
            log.exception("Instagram, пост %s", post_id)
            instagram.set_state(post_id, state="failed", error=str(exc)[:300])
            telegram.send_message(chat, f"Пост #{post_id} не опубликован в Instagram: {e(str(exc))[:400]}",
                                  reply_to=post["tg_message_id"],
                                  keyboard=[[{"text": "Повторить", "callback_data": f"p:{post_id}"},
                                             {"text": "Выложу руками", "callback_data": f"m:{post_id}"}]])
            continue
        instagram.set_state(post_id, state="published", **res)
        link = f' <a href="{e(res["permalink"])}">Открыть</a>' if res.get("permalink") else ""
        telegram.send_message(chat, f"Пост #{post_id} опубликован в Instagram.{link}",
                              reply_to=post["tg_message_id"])


STUCK_AFTER = timedelta(minutes=20)    # дольше публикация не идёт: ожидание обработки видео в Instagram — до 10 мин


def recover_interrupted(now: datetime | None = None) -> None:
    """Публикация прервалась перезапуском (деплой). Повторять вслепую нельзя — пост мог уже выйти.
    Только зависшие дольше STUCK_AFTER: при деплое старый процесс ещё может дописывать публикацию,
    и новый не должен объявлять её прерванной."""
    now = now or datetime.now(timezone.utc)
    for post_id, st in instagram.all_states().items():
        if st.get("state") != "publishing":
            continue
        since = st.get("claimed_at")
        if since and now - datetime.fromisoformat(since) < STUCK_AFTER:
            continue
        if instagram.transition(post_id, "publishing", state="failed", error="прервано перезапуском"):
            telegram.send_message(
                chat_id(), f"Публикация поста #{post_id} в Instagram прервалась перезапуском сервиса. "
                           "Проверьте ленту: если поста там нет, нажмите «Повторить».",
                keyboard=[[{"text": "Повторить", "callback_data": f"p:{post_id}"},
                           {"text": "Выложу руками", "callback_data": f"m:{post_id}"}]])


def publisher_loop() -> None:
    """Отдельный поток: генерация поста занимает минуты, а пост в слот должен выйти вовремя."""
    while True:
        try:
            if instagram.enabled():
                publish_due()
                recover_interrupted()
        except Exception:
            log.exception("Очередь Instagram")
        time.sleep(30)


def instagram_report() -> str:
    if not instagram.enabled():
        return "Instagram: не подключён (" + "; ".join(instagram.problems()) + ")"
    try:
        acc = instagram.account()
    except Exception as exc:
        return f"Instagram: токен не подошёл ({e(str(exc))[:200]})"
    queued = [(pid, st) for pid, st in instagram.all_states().items() if st.get("state") == "queued"]
    lines = [f"Instagram: @{e(acc.get('username', '?'))}, публикаций за сутки: {e(acc['quota'])}"]
    for pid, st in sorted(queued):
        lines.append(f"• пост #{pid} — {_when(datetime.fromisoformat(st['at']))}")
    if not queued:
        lines.append("В очереди на публикацию пусто.")
    return "\n".join(lines)


def replace_topic(post: dict, chat) -> None:
    import json
    from . import drive, writer
    if writer.load_yaml("rubrics.yaml")["rubrics"][post["rubric"]]["source"] == "drive":
        events = drive.to_dicts(drive.pick_events(drive.recent_events()))
        if len(events) < 2:
            telegram.send_message(chat, "Новых фотоотчётов за неделю не осталось.")
            return
        new_id = pipeline.create_post(post["rubric"], datetime.fromisoformat(post["slot_date"]).date(), post["slot"], None)
        db.kv_set(f"post_events:{new_id}", json.dumps(events, ensure_ascii=False))
        telegram.send_message(chat, f"Готовлю пост #{new_id} по другим мероприятиям, это займёт пару минут.")
        run_safely(new_id, chat)
        drive.mark_used(events)
        return
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
    if text.startswith("/city") and not text.startswith("/cities") and allowed(msg["from"]["id"]):
        from .cities import set_city
        body = text.split(maxsplit=1)[1] if " " in text else ""
        if "=" not in body:
            telegram.send_message(chat, "Формат: <code>/city Название ЖК = Город</code>")
            return
        cx, city = (x.strip() for x in body.split("=", 1))
        set_city(cx, city)
        telegram.send_message(chat, f"Запомнил: {e(cx)} — {e(city)}.")
        return
    if text.startswith("/cities") and allowed(msg["from"]["id"]):
        from . import drive
        try:
            evs = drive.recent_events(days=30, include_used=True)
        except Exception as exc:
            telegram.send_message(chat, f"Не удалось прочитать Drive: {e(str(exc))[:200]}")
            return
        unknown = sorted({ev.complex for ev in evs if not ev.city})
        known = sorted({(ev.city, ev.complex) for ev in evs if ev.city})
        lines = [f"<b>Без города ({len(unknown)}):</b>"] + [f"• {e(x)}" for x in unknown[:60]]
        lines += ["", f"<b>С городом:</b> {len(known)} ЖК. Задать: <code>/city ЖК = Город</code>"]
        telegram.send_message(chat, "\n".join(lines))
        return
    if text.startswith("/status") and allowed(msg["from"]["id"]):
        telegram.send_message(chat, status_report())
        return
    if text.startswith("/report") and allowed(msg["from"]["id"]):
        from . import insights
        telegram.send_message(chat, "Собираю цифры за прошлую неделю…")
        telegram.send_message(chat, insights.report(datetime.now(ZoneInfo(settings.timezone)).date()))
        return
    if text.startswith("/instagram") and allowed(msg["from"]["id"]):
        telegram.send_message(chat, instagram_report())
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
        if msg["chat"].get("type") in ("group", "supergroup") and str(chat) != chat_id():
            db.kv_set("chat_id", str(chat))   # запоминаем группу, где работает согласование
            telegram.send_message(chat, f"Запомнил эту группу для постов (id <code>{chat}</code>).")
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


def status_report() -> str:
    """Какие настройки видит сервис (только «задано / не задано», без значений)."""
    import os
    names = ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_APPROVER_IDS",
             "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
             "THREADS_APP_ID", "THREADS_APP_SECRET", "GOOGLE_SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON",
             "INSTAGRAM_ACCESS_TOKEN", "MEDIA_BASE_URL"]
    lines = []
    for n in names:
        problem = env_problem(n)
        lines.append(f"{'✅' if not problem else '❌'} {e(problem or n)}")
    commit = os.environ.get("RENDER_GIT_COMMIT", "")[:7] or "неизвестна"
    lines.append(f"\nThreads подключён: {'да' if threads.enabled() else 'нет'}")
    lines.append(instagram_report())
    from . import drive
    if drive.enabled():
        try:
            n = len(drive.recent_events())
            lines.append(f"Фотоотчёты Drive: доступ есть, новых мероприятий за неделю — {n}")
        except Exception as exc:
            lines.append(f"Фотоотчёты Drive: нет доступа ({e(str(exc))[:120]}). Откройте папку email сервисного аккаунта")
    else:
        lines.append("Фотоотчёты Drive: не настроены (нужны GOOGLE_DRIVE_FOLDER_ID и GOOGLE_SERVICE_ACCOUNT_JSON)")
    lines.append(f"Версия кода: {commit}")
    lines.append(f"Последний ежедневный запуск: {db.kv_get('last_daily') or 'ещё не было'}")
    return "<b>Состояние завода</b>\n" + "\n".join(lines)


def maybe_run_daily() -> None:
    now = datetime.now(ZoneInfo(settings.timezone))
    key = now.date().isoformat()
    if not chat_id():
        return                            # группа ещё не настроена — посты некуда отправлять
    if now.hour < settings.daily_run_hour or db.kv_get("last_daily") == key:
        return
    db.kv_set("last_daily", key)          # отмечаем заранее, чтобы при сбое не запускать повторно в цикле
    log.info("Ежедневный запуск %s", key)
    try:
        threads.refresh_token_if_needed()
        instagram.refresh_token_if_needed()
        pipeline.run_daily(now.date())
    except Exception as exc:
        log.exception("Ежедневный запуск")
        telegram.send_message(chat_id(), f"Ежедневный запуск упал: {e(str(exc))[:500]}")


def maybe_weekly_report() -> None:
    """По понедельникам после ежедневного запуска — отчёт за прошлую неделю."""
    now = datetime.now(ZoneInfo(settings.timezone))
    key = now.date().isoformat()
    if now.weekday() != 0 or now.hour < settings.daily_run_hour or not chat_id() or db.kv_get("last_weekly") == key:
        return
    db.kv_set("last_weekly", key)
    from . import insights
    try:
        telegram.send_message(chat_id(), insights.report(now.date()))
    except Exception as exc:
        log.exception("Еженедельный отчёт")
        telegram.send_message(chat_id(), f"Еженедельный отчёт не собрался: {e(str(exc))[:400]}")


def run_forever() -> None:
    db.init()
    if not settings.approver_ids:
        log.warning("TELEGRAM_APPROVER_IDS не задан: одобрять посты может любой участник группы")
    try:
        username = threads.connect_from_env()
        if username and chat_id():
            telegram.send_message(chat_id(), f"Threads подключён: @{e(str(username))}.")
    except Exception as exc:
        log.exception("Threads из переменной окружения")
        if chat_id():
            telegram.send_message(chat_id(), f"Threads не подключился: {e(str(exc))[:400]}")
    if chat_id():
        recover_interrupted()
    threading.Thread(target=publisher_loop, name="instagram", daemon=True).start()
    offset = int(db.kv_get("tg_offset", "0")) or None
    while True:
        try:
            maybe_run_daily()
            maybe_weekly_report()
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
