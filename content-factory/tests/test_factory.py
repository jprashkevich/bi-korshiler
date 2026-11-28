"""Офлайн-тесты: без Claude, Telegram и Threads."""
import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).parent
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture(autouse=True)
def _summer(monkeypatch):
    """Тесты не должны зависеть от месяца запуска: по умолчанию «сейчас» — июль, все тестовые картинки видны."""
    from datetime import date
    from factory import season
    monkeypatch.setattr(season, "today", lambda: date(2026, 7, 15))


def sample():
    from factory.models import PostPackage
    return PostPackage.model_validate(json.loads((HERE / "fixtures/sample_package.json").read_text()))


def test_strict_schema_has_no_refs_and_is_closed():
    from factory.llm import strict_schema
    from factory.models import PostPackage, ScoreBatch
    for model in (PostPackage, ScoreBatch):
        text = json.dumps(strict_schema(model))
        assert "$ref" not in text and "maxLength" not in text
        schema = strict_schema(model)
        assert schema["additionalProperties"] is False
        assert set(schema["required"]) == set(schema["properties"])


def test_normalize_fixes_first_last_and_photo():
    from factory.writer import normalize
    pkg = sample()
    pkg.slides[0].type = "insight"
    pkg.slides[-1].type = "steps"
    pkg.photo_id = "no-such-photo"
    pkg.hashtags = ["#соседи", "BIG Life"]
    pkg = normalize(pkg)
    assert pkg.slides[0].type == "cover" and pkg.slides[-1].type == "cta"
    assert pkg.photo_id == ""
    assert pkg.hashtags == ["соседи", "BIGLife"]


def test_typograf():
    from factory.render import typograf
    # тире прилипает к предыдущему слову, но после тире строку можно перенести
    assert typograf("Барьер — в ожидании") == "Барьер\u00a0— в\u00a0ожидании"


def test_render_html_contains_all_slides():
    from factory.render import render_html
    html = render_html(sample(), "Наука о соседстве")
    for i in range(1, 7):
        assert f'id="s{i}"' in html
    assert "gal-14.jpg" in html
    assert "Источник:" not in html            # источник только в подписи, не на слайдах


def test_feeds_and_rubrics_config():
    from factory.ingest import load_feeds
    from factory.writer import load_yaml
    assert len(load_feeds()) >= 20
    cfg = load_yaml("rubrics.yaml")
    assert sum(len(v) for v in cfg["schedule"].values()) == 17      # 2 карусели в день + Reels пн, ср, пт
    assert len(cfg["slot_times"]) == 3
    for slots in cfg["schedule"].values():
        for key in slots:
            assert key in cfg["rubrics"]


def test_pick_prefers_rubric_and_skips_used(monkeypatch):
    from factory import db, score
    db.init()
    now = db.now()
    with db.engine.begin() as c:
        c.execute(db.items.delete())
        for i, (rub, sc, used) in enumerate([("science", 7.0, False), ("practice", 7.5, False), ("science", 9.0, True)]):
            c.execute(db.items.insert().values(
                feed="F", kind="popular", title=f"t{i}", url=f"u{i}", summary="", fetched_at=now,
                score=sc, used=used, score_data={"best_rubric": rub, "relevance": 8, "has_number": False}))
    assert score.pick("science")["title"] == "t0"     # 7 + бонус рубрики > 7.5; использованный пропущен
    assert score.pick("number", need_number=True) is None


def test_threads_extract_code():
    from factory.threads import extract_code
    assert extract_code("https://localhost/?code=AQBx12#_") == "AQBx12"
    assert extract_code("https://localhost/?code=AQBx12&state=1") == "AQBx12"
    assert extract_code("  AQBx12#_ ") == "AQBx12"


@pytest.mark.parametrize("fixture,fmt,n_files", [("sample_package.json", "carousel", 6), ("sample_reel.json", "reels", 2)])
def test_deliver_sends_package_with_buttons(tmp_path, monkeypatch, fixture, fmt, n_files):
    """Отправка в Telegram без сети: альбом/видео, ZIP, подпись, блок с кнопками."""
    from factory import db, pipeline, telegram
    db.init()
    files = []
    for i in range(n_files):
        f = tmp_path / (f"f{i}.png" if fmt == "carousel" or i else "reel.mp4")
        f.write_bytes(b"x")
        files.append(str(f))
    pkg = json.loads((HERE / "fixtures" / fixture).read_text())
    pkg["format"] = fmt
    with db.engine.begin() as c:
        pid = c.execute(db.posts.insert().values(
            rubric="number" if fmt == "reels" else "science", slot_date="2026-11-30", slot=0, status="generated",
            package=pkg, files=files, feedback=[], created_at=db.now(), updated_at=db.now())).inserted_primary_key[0]
    sent = []
    monkeypatch.setattr(telegram, "send_album", lambda *a, **k: sent.append("album") or [1])
    monkeypatch.setattr(telegram, "send_video", lambda *a, **k: sent.append("video") or 1)
    monkeypatch.setattr(telegram, "send_document", lambda *a, **k: sent.append("doc") or 2)
    monkeypatch.setattr(telegram, "send_message",
                        lambda chat, text, keyboard=None, **k: sent.append("buttons" if keyboard else "msg") or 3)
    pipeline.deliver(pid)
    assert sent == [("video" if fmt == "reels" else "album"), "doc", "msg", "buttons"]
    assert db.get_post(pid)["status"] == "sent"


def test_reel_timeline_and_subtitles():
    from factory import reels, tts
    from factory.models import ReelPackage
    pkg = ReelPackage.model_validate(json.loads((HERE / "fixtures/sample_reel.json").read_text()))
    full, offsets = reels.voice_text(pkg)
    speech = tts.Speech(Path("x.mp3"), [i / 14 for i in range(len(full))], len(full) / 14)
    tl, subs, total = reels.timeline(pkg, speech)
    assert len(tl) == len(pkg.scenes) and tl[0]["start"] == 0 and tl[-1]["end"] == total
    assert all(a["end"] <= b["start"] + 0.01 for a, b in zip(tl, tl[1:]))
    assert all(len(s["text"]) <= reels.SUB_MAX + 15 for s in subs)
    assert subs[0]["start"] == 0


def test_illustrations_catalog_matches_files():
    from factory.render import illustrations
    from factory.writer import load_yaml
    ills = illustrations(all_seasons=True)
    assert len(ills) >= 6
    ids = {i["id"] for i in load_yaml("illustrations.yaml")["illustrations"]}
    assert set(ills) <= ids


def test_carousel_html_has_illustration_and_person_collage(tmp_path):
    from factory.render import render_html
    photo = tmp_path / "p.jpg"
    photo.write_bytes(b"x")
    html = render_html(sample(), "Наука о соседстве",
                       {"Dan Buettner": {"path": str(photo), "credit": "Фото: X / CC BY-SA 2.0, Wikimedia Commons"}})
    assert "ill-elevator.jpg" in html and "cv-card" in html
    assert 'class="collage"' in html and "Дэн Бюттнер" in html and "CC BY-SA 2.0" in html


def test_cover_pill_hidden_when_equal_to_rubric():
    from factory.render import render_html
    pkg = sample()
    pkg.slides[0].eyebrow = "Наука о соседстве"
    assert 'class="pill">Наука' not in render_html(pkg, "Наука о соседстве")
    pkg.slides[0].eyebrow = "Исследование"
    assert 'class="cv-rub"' in render_html(pkg, "Наука о соседстве")      # рубрика — меткой, eyebrow на обложке не дублируем


def test_person_slide_without_photo_is_a_namecard():
    from factory.render import render_html
    html = render_html(sample(), "Наука о соседстве", {})
    assert 'class="namecard"' in html and 'class="collage"' not in html and 'class="mono"' not in html


def test_commons_filename_parsing():
    from factory.people import _commons_file_from_url
    url = "https://upload.wikimedia.org/wikipedia/commons/a/ab/DanBuettnerOct10.jpg?utm_source=x"
    assert _commons_file_from_url(url) == "DanBuettnerOct10.jpg"
    assert _commons_file_from_url("https://upload.wikimedia.org/wikipedia/en/a/ab/X.jpg") is None


def test_drive_recent_events_parses_structure(monkeypatch):
    from datetime import date
    from factory import db, drive
    db.init()
    db.kv_set("drive_used_events", '["used-ev"]')
    tree = {
        "root": [{"id": "m11", "name": "2026-11", "mimeType": drive.FOLDER}, {"id": "m07", "name": "2026-07", "mimeType": drive.FOLDER}],
        "m11": [{"id": "zk1", "name": "Urban Hills", "mimeType": drive.FOLDER}],
        "zk1": [{"id": "ev1", "name": "24.11 · Точки Опоры · vTSZ", "mimeType": drive.FOLDER},
                {"id": "ev2", "name": "01.11 · Старое · abcd", "mimeType": drive.FOLDER},
                {"id": "used-ev", "name": "23.11 · Уже было · zzzz", "mimeType": drive.FOLDER},
                {"id": "ev3", "name": "без даты", "mimeType": drive.FOLDER}],
        "ev1": [{"id": "p1", "name": "b.jpg", "mimeType": "image/jpeg"}, {"id": "p0", "name": "a.jpg", "mimeType": "image/jpeg"},
                {"id": "v1", "name": "c.mp4", "mimeType": "video/mp4"}],
    }
    monkeypatch.setattr(drive, "root_id", lambda: "root")
    monkeypatch.setattr(drive, "_children", lambda fid, folders_only=False: [
        f for f in tree.get(fid, []) if not folders_only or f["mimeType"] == drive.FOLDER])
    events = drive.recent_events(today=date(2026, 11, 25))
    assert [e.folder_id for e in events] == ["ev1"]
    ev = events[0]
    assert ev.complex == "Urban Hills" and ev.activity == "Точки Опоры" and ev.day == "2026-11-24"
    assert [p["id"] for p in ev.photos] == ["p0", "p1"] and ev.videos == 1
    assert ev.city == "Шымкент" and ev.label == "24.11 · Шымкент, Urban Hills · Точки Опоры"


def test_pick_events_prefers_variety():
    from factory.drive import Event, pick_events
    evs = [Event("1", "A", "Йога", "2026-11-25", city="Астана"), Event("2", "A", "Йога", "2026-11-24", city="Астана"),
           Event("3", "B", "Танцы", "2026-11-24", city="Астана"), Event("4", "C", "Йога", "2026-11-23", city="Шымкент")]
    assert [e.folder_id for e in pick_events(evs, limit=3)] == ["1", "4", "3"]   # сначала разные города


def test_strict_schema_keeps_fields_named_title():
    """Регрессия: поле «title» слайда не должно пропадать вместе с ключевым словом JSON Schema title."""
    from factory.llm import strict_schema
    from factory.models import PostPackage, ReelPackage
    slide = strict_schema(PostPackage)["properties"]["slides"]["items"]
    assert "title" in slide["properties"] and "title" in slide["required"]
    scene = strict_schema(ReelPackage)["properties"]["scenes"]["items"]
    assert "title" in scene["properties"]
    assert "title" not in slide["properties"]["title"]   # а служебный title внутри описания поля убран



def test_editor_violations_and_dash_fix():
    from factory import editor
    pkg = sample()
    pkg.caption_ru = "Стоит отметить, что соседство является не просто привычкой, а навыком — и это важно."
    found = " ".join(editor.violations(pkg))
    for name in ("длинное тире", "стоит отметить", "является", "не просто"):
        assert name in found
    fixed = editor._fix_dashes(pkg)
    assert "—" not in fixed.caption_ru and fixed.slides[0].illustration_id == pkg.slides[0].illustration_id


def test_editor_merge_keeps_structure():
    from factory import editor
    orig = sample()
    edited = sample()
    edited.slides[1].title = "Новый заголовок"
    edited.slides[1].type = "stat"            # смену типа слайда редактором игнорируем
    edited.slides[1].photo_ref = "hack"
    edited.slides[3].items = ["только один"]  # другое число пунктов — не берём
    merged = editor._merge(orig, edited)
    assert merged.slides[1].title == "Новый заголовок"
    assert merged.slides[1].type == orig.slides[1].type and merged.slides[1].photo_ref == ""
    assert merged.slides[3].items == orig.slides[3].items


def test_editor_runs_with_mocked_llm(monkeypatch):
    from factory import editor, llm
    pkg = sample()
    pkg.caption_ru = "Данный пост является важным."
    def fake_ask(cls, **kw):
        out = pkg.model_copy(deep=True)
        out.caption_ru = "Этот пост про соседей."
        return out
    monkeypatch.setattr(llm, "ask", fake_ask)
    res, issues = editor.edit(pkg)
    assert res.caption_ru == "Этот пост про соседей." and not issues


def test_drive_uses_report_json(monkeypatch):
    from datetime import date
    from factory import db, drive
    db.init()
    db.kv_set("drive_used_events", "[]")
    tree = {
        "root": [{"id": "m11", "name": "2026-11", "mimeType": drive.FOLDER}],
        "m11": [{"id": "zk1", "name": "Urban Hills", "mimeType": drive.FOLDER}],
        "zk1": [{"id": "ev1", "name": "24.11 · Точки Опоры · vTSZ", "mimeType": drive.FOLDER}],
        "ev1": [{"id": "p1", "name": "a.jpg", "mimeType": "image/jpeg"}, {"id": "p2", "name": "b.jpg", "mimeType": "image/jpeg"},
                {"id": "p3", "name": "c.jpg", "mimeType": "image/jpeg"},
                {"id": "rj", "name": "report.json", "mimeType": "application/json"}],
    }
    monkeypatch.setattr(drive, "root_id", lambda: "root")
    monkeypatch.setattr(drive, "_children", lambda fid, folders_only=False: [
        f for f in tree.get(fid, []) if not folders_only or f["mimeType"] == drive.FOLDER])
    monkeypatch.setattr(drive, "read_json", lambda fid: {"description": "Зарядка во дворе", "participants": "12",
                                                         "photos_best": ["b.jpg", "a.jpg"], "photos_not_event": ["c.jpg"]})
    ev = drive.recent_events(today=date(2026, 11, 25))[0]
    assert [p["name"] for p in ev.photos] == ["b.jpg", "a.jpg"]       # лучшие первыми, афиша убрана
    assert ev.report["participants"] == "12"



def test_city_resolution_order():
    from factory import cities, db
    db.init()
    assert cities.city_for("Nova City 14", "Community 2 Управление") == "Астана"
    assert cities.city_for("4YOU Shymkent", "Community 1 Управление") == "Шымкент"   # слово в названии важнее группы
    assert cities.city_for("ЖК Батысмұра Бизнес", "Community Запад") == "Атырау"     # справочник ЖК, казахские буквы
    assert cities.city_for("Клубный дом 39") == "Шымкент"                            # номер различает ЖК
    assert cities.city_for("Клубный дом 56") == "Астана"
    assert cities.city_for("ЖК Санат") == ""                                         # нет в справочнике
    cities.set_city("ЖК Санат", "Алматы")
    assert cities.city_for("Санат") == "Алматы"                                      # «ЖК» и регистр не важны


def test_album_is_split_by_ten(monkeypatch, tmp_path):
    from factory import telegram
    calls = []
    monkeypatch.setattr(telegram, "_call", lambda method, **kw: calls.append((method, len(kw.get("files") or {})))
                        or ([{"message_id": 1}] * len(kw.get("files") or {}) if method == "sendMediaGroup" else {"message_id": 1}))
    paths = []
    for i in range(12):
        p = tmp_path / f"s{i}.png"; p.write_bytes(b"x"); paths.append(p)
    telegram.send_album("-1", paths)
    assert calls == [("sendMediaGroup", 10), ("sendMediaGroup", 2)]
    calls.clear()
    telegram.send_album("-1", paths[:11])
    assert calls == [("sendMediaGroup", 10), ("sendPhoto", 1)]


def test_event_slide_shows_city_and_cover_lists_cities(tmp_path):
    from factory.models import PostPackage
    from factory.render import render_html
    photo = tmp_path / "e.jpg"; photo.write_bytes(b"x")
    E = lambda **k: {"type": "event", "eyebrow": "", "title": "T", "text": "", "items": [], "item_labels": [],
                     "illustration_id": "", "person": "", "photo_ref": "", **k}
    pkg = PostPackage(headline="x", accent="orange", photo_id="", people=[], slides=[
        E(type="cover", photo_ref="p1"), E(photo_ref="p1"), E(type="cta")],
        caption_ru="x", hashtags=[], summary_kz="x", summary_uz="x", alt_text="x", source_line="x",
        threads=["x"], fact_check=[])
    html = render_html(pkg, "Жизнь дворов", drive_photos={"p1": str(photo)}, photo_city={"p1": "Астана"},
                       cities=["Астана", "Шымкент"])
    assert 'class="citytag"' in html and "Астана · Шымкент" in html


def test_background_rhythm():
    from types import SimpleNamespace as N
    from factory.render import backgrounds
    kinds = ["cover", "insight", "statement", "stat", "steps", "list", "stat", "cta"]
    assert backgrounds([N(type=k) for k in kinds]) == \
        ["navy", "light", "accent", "light", "accent2", "light", "accent", "navy"]


def test_weekend_ideas_prompt(monkeypatch):
    from datetime import date
    from factory import llm, writer, drive, score
    seen = {}
    def fake_ask(cls, *, system, user, model, effort, max_tokens=16000):
        seen["system"], seen["user"] = system, user
        return sample()
    monkeypatch.setattr(llm, "ask", fake_ask)
    monkeypatch.setattr(drive, "enabled", lambda: False)
    monkeypatch.setattr(score, "pick", lambda *a, **k: None)
    pkg = writer.write_ideas(date(2026, 12, 11))          # пятница перед Днём Независимости
    assert "Выходные: 12 декабря–13 декабря" in seen["user"]
    assert "16 декабря: День Независимости (KZ)" in seen["user"]
    assert "Идеи на выходные" in seen["system"] and pkg.people == []


def _ig_post(tmp_path, fmt="carousel", n=3, slot_date="2026-11-30"):
    from PIL import Image
    from factory import db
    db.init()
    files = []
    for i in range(n):
        if fmt == "reels" and i == 0:
            f = tmp_path / "reel.mp4"
            f.write_bytes(b"mp4")
        else:
            f = tmp_path / f"s{i}.png"
            Image.new("RGBA", (40, 50), (10, 20, 30, 255)).save(f)
        files.append(str(f))
    pkg = json.loads((HERE / "fixtures" / ("sample_reel.json" if fmt == "reels" else "sample_package.json")).read_text())
    pkg["format"] = fmt
    with db.engine.begin() as c:
        pid = c.execute(db.posts.insert().values(
            rubric="science", slot_date=slot_date, slot=1, status="approved", package=pkg, files=files,
            feedback=[], tg_message_id=5, created_at=db.now(), updated_at=db.now())).inserted_primary_key[0]
    return pid, files


def test_instagram_media_stored_as_jpeg_with_random_tokens(tmp_path):
    from factory import db, instagram
    pid, files = _ig_post(tmp_path, "reels", 2)
    items = instagram.store_media(pid, files, is_reel=True)
    assert [m["kind"] for m in items] == ["video", "cover"]
    assert items[0]["token"].endswith(".mp4") and items[1]["token"].endswith(".jpg")
    assert len(items[1]["token"]) > 40
    with db.engine.begin() as c:
        mime = c.execute(db.select(db.media.c.mime).where(db.media.c.token == items[1]["token"])).scalar()
        data = b"".join(r[0] for r in c.execute(db.select(db.media_parts.c.data)
                                                .where(db.media_parts.c.token == items[1]["token"])
                                                .order_by(db.media_parts.c.idx)))
    assert mime == "image/jpeg" and data[:2] == b"\xff\xd8"      # файл хранится частями в media_parts
    assert instagram.media_for(pid) == items


def test_instagram_caption_limits():
    from factory.instagram import caption
    text = caption({"caption_ru": "а" * 3000, "source_line": "Nature, 2026", "hashtags": [f"t{i}" for i in range(40)]})
    assert len(text) <= 2200 and text.endswith("#t29") and "#t30" not in text


def test_instagram_publish_carousel(tmp_path, monkeypatch):
    from factory import instagram
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "EAAtest")
    monkeypatch.setenv("INSTAGRAM_USER_ID", "42")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://media.example/")
    pid, files = _ig_post(tmp_path, "carousel", 3)
    instagram.store_media(pid, files, is_reel=False)
    calls = []

    def fake(method, path, **params):
        calls.append((method, path, params))
        if path == "42/media":
            return {"id": f"c{len(calls)}"}
        if path == "42/media_publish":
            return {"id": "m1"}
        if params.get("fields") == "permalink":
            return {"permalink": "https://instagram.com/p/x"}
        return {"status_code": "FINISHED"}
    monkeypatch.setattr(instagram, "_request", fake)
    monkeypatch.setattr(instagram, "wake_media_server", lambda: None)
    from factory import db
    res = instagram.publish(db.get_post(pid))
    assert res == {"media_id": "m1", "permalink": "https://instagram.com/p/x"}
    creates = [p for m, path, p in calls if path == "42/media"]
    assert len(creates) == 4 and all(p["image_url"].startswith("https://media.example/m/") for p in creates[:3])
    assert creates[3]["media_type"] == "CAROUSEL" and len(creates[3]["children"].split(",")) == 3
    assert instagram.graph() == "https://graph.facebook.com/v21.0"


def test_instagram_queue_waits_for_slot(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from factory import bot, instagram, telegram
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "EAAtest")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://media.example")
    pid, _ = _ig_post(tmp_path, "carousel", 2, slot_date="2099-01-01")
    sent = []
    monkeypatch.setattr(telegram, "send_message", lambda chat, text, keyboard=None, **k: sent.append((text, keyboard)) or 7)
    from factory import db
    bot.after_approve(db.get_post(pid), 1, 5, "Одобрено.")
    assert instagram.state(pid)["state"] == "queued"
    assert pid not in instagram.due() and "19:30" in sent[-1][0]
    assert sent[-1][1][0][0]["callback_data"] == f"p:{pid}"
    assert pid in instagram.due(datetime(2099, 1, 2, tzinfo=timezone.utc))
    # Reels сначала спрашивают, публиковать ли самому
    rid, _ = _ig_post(tmp_path, "reels", 2)
    bot.after_approve(db.get_post(rid), 1, 5, "Одобрено.")
    assert instagram.state(rid) == {} and sent[-1][1][0][0]["callback_data"] == f"q:{rid}"


def test_reel_backgrounds_and_word_limit():
    from factory import reels, writer
    from factory.models import ReelPackage
    pkg = ReelPackage.model_validate(json.loads((HERE / "fixtures/sample_reel.json").read_text()))
    bgs = reels.scene_backgrounds(pkg.scenes)
    assert bgs[0] == "navy" and bgs[-1] == "navy"
    assert all(not (a.startswith("accent") and b.startswith("accent")) for a, b in zip(bgs, bgs[1:]))
    assert writer.voice_words(pkg) <= writer.MAX_REEL_WORDS["long"]


def test_season_filter_hides_summer_pictures_in_november():
    from datetime import date
    from factory.season import fits, tags_for
    nov, jul = date(2026, 11, 28), date(2026, 7, 1)
    assert tags_for(nov) == {"any", "cold"}
    assert not fits({"season": "summer"}, nov) and not fits({}, nov) and fits({"season": "any"}, nov)
    assert fits({"season": ["cold", "winter"]}, nov) and fits({"season": "summer"}, jul)
    assert not fits({"season": "winter"}, date(2026, 3, 10)) and fits({"season": "cold"}, date(2026, 3, 10))
    from factory import render, season
    season.today = lambda: nov    # фикстура вернёт июль после теста
    assert set(render.illustrations()) <= {"ill-common-room", "ill-elevator", "ill-kids-workshop", "ill-grandparents",
                                           "ill-cleanup", "ill-loneliness", "ill-chat", "ill-winter", "ill-science",
                                           "ill-newyear", "ill-indoor-cinema"}


def test_weekly_report_scores_and_learnings(tmp_path, monkeypatch):
    from datetime import date
    from factory import db, insights, instagram
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "EAAtest")
    monkeypatch.setenv("INSTAGRAM_USER_ID", "42")
    monkeypatch.setenv("MEDIA_BASE_URL", "https://media.example")
    db.init()
    pkg = json.loads((HERE / "fixtures/sample_package.json").read_text())
    ids = []
    with db.engine.begin() as c:
        for i, rub in enumerate(["science", "practice", "science", "question"]):
            p = dict(pkg, headline=f"Тема {i}", caption_ru=f"Подпись номер {i} про соседей и двор")
            ids.append(c.execute(db.posts.insert().values(
                rubric=rub, slot_date=f"2030-01-0{i + 1}", slot=0, status="approved", package=p, files=[],
                feedback=[], created_at=db.now(), updated_at=db.now())).inserted_primary_key[0])
    instagram.set_state(ids[0], state="published", media_id="m0")
    reach = {"m0": 1000, "m1": 1000, "m2": 1000, "m3": 1000}
    saved = {"m0": 50, "m1": 5, "m2": 20, "m3": 1}

    def fake(method, path, **params):
        if path == "42/media":    # три поста выложены руками — находим по подписи
            return {"data": [{"id": f"m{i}", "caption": f"Подпись номер {i} про соседей и двор\n\n#tag"} for i in (1, 2, 3)]}
        mid = path.split("/")[0]
        return {"data": [{"name": "reach", "values": [{"value": reach[mid]}]},
                         {"name": "saved", "values": [{"value": saved[mid]}]}]}
    monkeypatch.setattr(instagram, "_request", fake)
    text = insights.report(date(2030, 1, 7))       # понедельник → неделя 31.12–06.01
    assert "найдено в Instagram: 4" in text and text.index("Тема 0") < text.index("Тема 2")
    assert "Тема 0" in db.kv_get("learnings") and insights.score({"reach": 100, "saved": 1}) == 3.0


def test_lead_slide_and_editorial_policy_in_prompt(monkeypatch):
    from factory import render, writer, editor
    from factory.models import PostPackage
    pkg = json.loads((HERE / "fixtures/sample_package.json").read_text())
    pkg["slides"].insert(1, dict(pkg["slides"][1], type="lead", text="Лид " * 60, illustration_id="", photo_ref=""))
    pkg["alt_headlines"] = ["Вариант 1", "Вариант 2"]
    p = PostPackage.model_validate(pkg)
    html = render.render_html(p, "Наука о соседстве")
    assert 'class="lead"' in html and render.backgrounds(p.slides)[1] == "light"
    monkeypatch.setattr(writer, "lessons_block", lambda: "")
    prompt = writer.system_prompt()
    assert "Лид" in prompt and "до 280 символов" in prompt and "лучше короче" not in prompt
    assert any("общее определение" in v for v in editor.violations(p.model_copy(update={"caption_ru": "Уникальный двор"})))


def test_reel_plan_rotates_experiment_and_viz_in_templates():
    from datetime import date, timedelta
    from factory import insights, render, writer
    from factory.models import PostPackage
    days = [date(2026, 11, 30) + timedelta(days=i) for i in range(21)]
    plans = [writer.reel_plan(d, {"score_data": {"has_number": True}}) for d in days if d.isoweekday() in (1, 3, 5)]
    assert {p["voice_mode"] for p in plans} == {"voice", "music"}
    assert {p["length"] for p in plans} == {"short", "mid", "long"}
    assert {p["viz"] for p in plans} == set(writer.VIZ_KINDS)
    pkg = json.loads((HERE / "fixtures/sample_package.json").read_text())
    pkg["slides"].insert(2, dict(pkg["slides"][1], type="stat", title="20%", illustration_id="", photo_ref="",
                                 viz={"kind": "dots", "mode": "build", "total": 3000, "unit": "1 точка = 12 человек",
                                      "groups": [{"label": "одиноки", "value": 20, "color": "accent"}],
                                      "callouts": [], "conditional": False}))
    html = render.render_html(PostPackage.model_validate(pkg), "Наука о соседстве")
    assert 'class="viz"' in html and "window.drawViz" in html
    rows = [{"format": "reels", "score": s, "voice_mode": v, "length": "mid", "reel_format": "myth"}
            for s, v in ((5, "voice"), (3, "music"), (7, "voice"))]
    out = insights.reel_experiments(rows)
    assert any("с голосом: 6.0 (2)" in x for x in out)


def test_reel_template_phrases_and_full_humanizer_in_editor(monkeypatch):
    from factory import editor
    from factory.models import ReelPackage
    pkg = ReelPackage.model_validate(json.loads((HERE / "fixtures/sample_reel.json").read_text()))
    pkg.scenes[1].voice = "Ответ в конце, не переключайся."
    pkg.scenes[-1].voice = "Отправь соседу. Ведь все уверены:"
    found = " ".join(editor.violations(pkg))
    assert "дежурная связка Reels" in found and "оборвана на двоеточии" in found
    seen = {}
    monkeypatch.setattr(editor.llm, "ask", lambda cls, system, user, **k: seen.setdefault("system", system) and (_ for _ in ()).throw(RuntimeError("stop")))
    editor.edit(pkg)
    assert "Humanizer-RU" in seen["system"] and "Поправки BIG Life" in seen["system"]


def test_choppy_voice_is_flagged():
    from factory import editor
    from factory.models import ReelPackage
    pkg = ReelPackage.model_validate(json.loads((HERE / "fixtures/sample_reel.json").read_text()))
    for s in pkg.scenes:
        s.voice = "Соседи молчат. Это важно. Учёные знают."
    assert "рубленая" in editor.choppy(pkg)
    for s in pkg.scenes:
        s.voice = ("Учёные двадцать лет опрашивали жителей одного района и заметили, что одиноких выдаёт "
                   "не возраст, а то, знают ли они по имени хотя бы одного соседа.")
    assert editor.choppy(pkg) == ""


def test_broll_map_and_segments():
    """Карта страны рисуется из Natural Earth; иллюстрации делят время сцены, а сцены с дата-артом идут окном сверху."""
    from factory import broll, reels
    from factory.models import ReelPackage
    svg = broll.map_svg("Japan")
    assert svg and 'class="hit"' in svg and broll.map_svg("Нарния") is None
    base = {"eyebrow": "", "title": "", "text": "", "illustration_id": "", "person": "", "voice": "фраза"}
    pkg = ReelPackage.model_validate({
        "headline": "t", "accent": "orange", "cover_title": "t", "people": [], "caption_ru": "c", "hashtags": ["a"],
        "summary_kz": "k", "summary_uz": "u", "source_line": "s", "threads": ["x"], "fact_check": ["f"],
        "scenes": [{**base, "type": "hook"}, {**base, "type": "stat", "viz": {"kind": "dots", "total": 10, "highlight": 3}}]})
    tl = [{"start": 0.0, "end": 4.5}, {"start": 4.5, "end": 6.0}]
    subs = [{"start": 1.6}, {"start": 3.1}]
    rows = [[{"type": "map"}, {"type": "number"}, {"type": "quote"}], [{"type": "full"}, {"type": "card"}]]
    segs = reels.broll_segments(pkg, tl, subs, rows)
    first = [g for g in segs if g["scene"] == 0]
    assert len(first) == 3 and first[1]["start"] == 1.6 and first[2]["start"] == 3.1   # границы — по фразам голоса
    assert all(g["split"] for g in segs if g["scene"] == 1)
    assert all(g["end"] - g["start"] >= 1.0 for g in segs)


def test_instagram_claim_is_exclusive(monkeypatch):
    """При деплое старый и новый процесс минуту работают вместе: взять пост из очереди может только один,
    а свежую публикацию соседа новый процесс не объявляет прерванной."""
    from datetime import datetime, timedelta, timezone
    from factory import bot, db, instagram
    db.init()
    instagram.queue(9001, datetime.now(timezone.utc))
    assert instagram.claim(9001) is True
    assert instagram.claim(9001) is False
    sent = []
    monkeypatch.setattr(bot.telegram, "send_message", lambda *a, **k: sent.append(a))
    monkeypatch.setattr(bot, "chat_id", lambda: 1)
    bot.recover_interrupted()
    assert instagram.state(9001)["state"] == "publishing" and not sent
    bot.recover_interrupted(now=datetime.now(timezone.utc) + timedelta(minutes=30))
    assert instagram.state(9001)["state"] == "failed" and len(sent) == 1
    bot.recover_interrupted(now=datetime.now(timezone.utc) + timedelta(minutes=30))
    assert len(sent) == 1


def test_director_normalize_keeps_rhythm_and_one_metaphor():
    """Режиссёр мог нарушить правила монтажа: резы чаще 0,8 с, вторая фигура, лишние вспышки — чиним кодом."""
    from factory import director
    from factory.models import Storyboard
    words = [{"i": i, "t": i * 0.3, "w": f"w{i}"} for i in range(40)]
    sb = Storyboard.model_validate({
        "metaphor": "m", "expand_word": 99,
        "anchor": [{"word": 2, "viz": {"kind": "dots"}}, {"word": 20, "viz": {"kind": "house"}}, {"word": 25, "viz": {"kind": "dots", "mode": "highlight"}}],
        "cuts": [{"word": 3, "kind": "number", "query": "5%"}, {"word": 4, "kind": "quote", "query": "q"},
                 {"word": 10, "kind": "map", "query": "Japan"}],
        "accents": [{"word": 5, "motion": "flash"}, {"word": 30, "motion": "flash"}, {"word": 7, "motion": "punch"}]})
    out = director.normalize(sb, words, hook_end=3.0)
    assert [c.word for c in out.cuts] == [0, 10]                  # 3 и 4 ближе 0,8 с; первый кадр — с первого слова
    assert [a.viz.kind for a in out.anchor] == ["dots", "dots"] and out.anchor[0].word == 10   # после хука
    assert out.expand_word == 39 and sum(a.motion == "flash" for a in out.accents) == 1


def test_format6_shots_fill_gaps_and_keep_chapters():
    """Формат 6: перебивки внутри глав данных выпадают, пустоты дольше 2,5 с заполняются текстом фразы,
    финальная глава возвращает метафору."""
    from factory import reels
    from factory.models import Storyboard
    words = [{"i": i, "t": i * 0.4, "w": f"w{i}"} for i in range(60)]
    subs = [{"start": k * 2.0, "end": k * 2.0 + 2.0, "text": f"фраза номер {k}", "hl": ""} for k in range(13)]
    sb = Storyboard.model_validate({"metaphor": "m", "expand_word": 55,
        "chapters": [{"word": 20, "until_word": 30, "chart": "compare", "icon": "eye", "big": "37%", "big_caption": "c",
                      "groups": [{"label": "a", "value": 37}, {"label": "b", "value": 23}], "evidence": "37% 23%"}],
        "cuts": [{"word": 0, "kind": "number", "query": "1"}, {"word": 22, "kind": "number", "query": "2"}]})
    cuts = [{"type": "full", "start": 0.0, "uri": "a"}, {"type": "number", "start": 8.4, "text": "2"}]
    shots, vizs = reels.build_shots(cuts, sb, words, subs, hook_end=2.0, total=24.0)
    kinds = [s["type"] for s in shots]
    assert "number" not in kinds                                  # перебивка внутри главы выпала
    assert kinds.count("chapter") == 2 and len(vizs) == 2         # глава + финал
    assert "kinetic" in kinds                                     # пустота после первого кадра заполнена
    gaps = [b["start"] - a["start"] for a, b in zip(shots, shots[1:]) if a["type"] != "chapter"]
    assert max(gaps) <= 2.6


def test_chapters_need_numbers_from_source():
    """Решение владельца 28.11: нет цифр в источнике — нет главы данных; 8,175 и 8 175 — одно число."""
    from factory import director
    from factory.models import DataChapter
    mk = lambda big, vals, years=(): DataChapter(word=1, until_word=5, chart="compare", icon="eye", big=big, big_caption="c",
                                                 groups=[{"label": "a", "value": v} for v in vals], years=list(years), evidence="e")
    src = "Among 8,175 adults, 37% of those with vision loss reported depression vs 23%, 2010 to 2018."
    kept = director.valid_chapters([mk("37%", [37, 23]), mk("в 2 раза", [50, 25]), mk("8 175", [37]),
                                    mk("37%", [37], [2010, 2018]), mk("41%", [41])], src)
    assert [c.big for c in kept] == ["37%", "8 175", "37%"]
    assert director.valid_chapters([mk("37%", [37])], "Зрение и настроение связаны.") == []


def test_usage_is_recorded_and_summed():
    """Учёт расхода API: каждый запрос пишет токены и стоимость, недельная сводка складывает по постам."""
    from datetime import date
    from types import SimpleNamespace
    from factory import db, insights, llm
    db.init()
    u = SimpleNamespace(input_tokens=1000, output_tokens=2000, cache_creation_input_tokens=0, cache_read_input_tokens=30000)
    assert abs(llm.cost("claude-opus-5-5", u) - (1000 * 4 + 30000 * 0.2 + 2000 * 20) / 1e6) < 1e-9
    llm.CURRENT_POST = None
    llm._record("claude-opus-5-5", "ScoreBatch", u)
    text = insights.spend(date.today(), date.today())
    assert "Расход API за неделю: $0.05" in text and "отбор тем" in text
