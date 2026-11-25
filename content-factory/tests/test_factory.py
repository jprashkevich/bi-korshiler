"""Офлайн-тесты: без Claude, Telegram и Threads."""
import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).parent
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


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
    assert typograf("Барьер — в ожидании") == "Барьер — в ожидании"


def test_render_html_contains_all_slides():
    from factory.render import render_html
    html = render_html(sample(), "Наука о соседстве")
    for i in range(1, 7):
        assert f'id="s{i}"' in html
    assert "gal-14.jpg" in html and "Источник:" in html


def test_feeds_and_rubrics_config():
    from factory.ingest import load_feeds
    from factory.writer import load_yaml
    assert len(load_feeds()) >= 20
    cfg = load_yaml("rubrics.yaml")
    assert sum(len(v) for v in cfg["schedule"].values()) == 14
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
