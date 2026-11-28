"""Точка входа: python -m factory <команда>."""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from . import db


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # httpx пишет полный URL запроса, а в URL Telegram Bot API есть токен бота — такие строки в логи не пускаем
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    p = argparse.ArgumentParser(prog="factory", description="Контент-завод BIG Life")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("worker", help="Telegram-бот + ежедневный запуск (основной процесс на сервере)")
    sub.add_parser("ingest", help="Собрать RSS")
    sub.add_parser("score", help="Оценить новые материалы")
    sub.add_parser("daily", help="Подготовить и отправить посты на сегодня")
    one = sub.add_parser("post", help="Собрать и отправить в Telegram один пост рубрики на сегодня")
    one.add_argument("rubric")
    one.add_argument("--slot", type=int, default=0)
    one.add_argument("--format", choices=["5", "6"], help="Формат монтажа Reels для этого поста (сравнение вариантов)")
    redo = sub.add_parser("redo", help="Пересобрать пост по id с комментарием и отправить в Telegram")
    redo.add_argument("post_id", type=int)
    redo.add_argument("comment", nargs="*")
    rv = sub.add_parser("revisual", help="Новый визуальный ряд для готового текста Reels и отправка в Telegram")
    rv.add_argument("post_id", type=int)
    rv.add_argument("--format", choices=["5", "6"], help="Формат монтажа Reels для этой пересборки (сравнение вариантов)")
    vt = sub.add_parser("voicetest", help="5 вариантов озвучки фрагмента поста в Telegram")
    vt.add_argument("post_id", type=int)
    sp = sub.add_parser("spend", help="Расход API за последние N дней (по умолчанию сегодня), по постам")
    sp.add_argument("days", type=int, nargs="?", default=1)
    show = sub.add_parser("show", help="Напечатать пакет поста (тексты) в лог")
    show.add_argument("post_id", type=int)
    top = sub.add_parser("top", help="Показать лучшие темы после скоринга")
    top.add_argument("-n", type=int, default=15)
    r = sub.add_parser("render", help="Отрендерить карусель из JSON-пакета (без вызова Claude)")
    r.add_argument("package", type=Path)
    r.add_argument("--rubric", default="Наука о соседстве")
    args = p.parse_args()

    db.init()
    if args.cmd == "worker":
        from .bot import run_forever
        run_forever()
    elif args.cmd == "ingest":
        from .ingest import run
        print(run())
    elif args.cmd == "score":
        from .score import run
        print(run())
    elif args.cmd == "daily":
        from .pipeline import run_daily
        print(run_daily())
    elif args.cmd == "post":
        import os
        from . import pipeline
        if getattr(args, "format", None):
            os.environ["REELS_FORMAT"] = args.format
        item = pipeline.choose_item(args.rubric)
        pipeline.mark_used(item)
        pid = pipeline.create_post(args.rubric, pipeline.today(), args.slot, item)
        pipeline.generate(pid)
        print("post", pid)
    elif args.cmd == "redo":
        from . import pipeline
        post = db.get_post(args.post_id)
        feedback = list(post["feedback"] or []) + ([" ".join(args.comment)] if args.comment else [])
        db.update_post(args.post_id, feedback=feedback, status="generating")
        pipeline.generate(args.post_id, feedback=feedback)
        print("redone", args.post_id)
    elif args.cmd == "revisual":
        import os
        from . import pipeline
        if args.format:
            os.environ["REELS_FORMAT"] = args.format
        pipeline.revisualize(args.post_id)
        print("revisual", args.post_id)
    elif args.cmd == "spend":
        from datetime import date, timedelta
        from sqlalchemy import func, select
        from . import insights
        end = date.today()
        print(insights.spend(end - timedelta(days=args.days - 1), end))
        with db.engine.begin() as c:
            for row in c.execute(select(db.usage.c.post_id, db.usage.c.purpose, func.count(), func.sum(db.usage.c.usd),
                                        func.sum(db.usage.c.cache_read), func.sum(db.usage.c.input_tokens))
                                 .where(db.usage.c.at >= db.now() - timedelta(days=args.days))
                                 .group_by(db.usage.c.post_id, db.usage.c.purpose).order_by(db.usage.c.post_id)):
                print(f"пост {row[0]} {row[1]}: запросов {row[2]}, ${row[3]:.3f}, из кэша {row[4]} / без кэша {row[5]} ток.")
        from . import telegram, tts
        from .settings import OUTPUT_DIR, chat_id
        pkg = db.get_post(args.post_id)["package"]
        text = " ".join(s["voice"] for s in pkg["scenes"][:4])
        out_dir = OUTPUT_DIR / f"voicetest-{args.post_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        telegram.send_message(chat_id(), f"Варианты озвучки: один и тот же фрагмент ролика #{args.post_id}. "
                                         "Напишите номер, который нравится больше всего.")
        for key, title, path in tts.voicetest(text, out_dir):
            if path:
                telegram.send_document(chat_id(), path, caption=f"Вариант {key}. {title}")
            else:
                telegram.send_message(chat_id(), f"Вариант {key}. {title}")
        print("voicetest", args.post_id)
    elif args.cmd == "show":
        post = db.get_post(args.post_id)
        pkg = post["package"] or {}
        for k in ("headline", "reel_format", "voice_mode", "length", "cover_title"):
            print(k, ":", pkg.get(k))
        for i, sc in enumerate(pkg.get("scenes") or pkg.get("slides") or []):
            print(f"[{i}] {sc.get('type')} | {sc.get('title')} | {sc.get('text')} | voice: {sc.get('voice', '')} | viz: {(sc.get('viz') or {}).get('kind')}")
        print("caption:", (pkg.get("caption_ru") or "").replace("\n", " / ")[:1500])
        print("edit_issues:", pkg.get("edit_issues"))
        print("review:", pkg.get("review"))
        print("hook_options:", pkg.get("hook_options"))
    elif args.cmd == "top":
        from sqlalchemy import select
        with db.engine.begin() as c:
            rows = c.execute(select(db.items).where(db.items.c.score.is_not(None))
                             .order_by(db.items.c.score.desc()).limit(args.n)).mappings().all()
        for row in rows:
            sd = row["score_data"] or {}
            print(f"{row['score']:>5} [{sd.get('best_rubric')}] {row['title'][:90]}\n      {sd.get('hook')}")
    elif args.cmd == "render":
        from .models import PostPackage
        from .render import render
        pkg = PostPackage.model_validate(json.loads(args.package.read_text(encoding="utf-8")))
        for f in render(pkg, args.rubric, args.package.stem):
            print(f)


if __name__ == "__main__":
    main()
