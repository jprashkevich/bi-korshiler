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
