"""Рендер карусели: HTML-шаблон на токенах дизайн-системы → PNG 1080×1350 через Chromium."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from .models import PostPackage
from .settings import CONFIG_DIR, OUTPUT_DIR, PHOTOS_DIR, TEMPLATES_DIR, settings

log = logging.getLogger(__name__)
_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html", "j2"]))


def photo_path(photo_id: str) -> str:
    if not photo_id:
        return ""
    for p in yaml.safe_load((CONFIG_DIR / "photos.yaml").read_text(encoding="utf-8"))["photos"]:
        if p["id"] == photo_id and (PHOTOS_DIR / p["file"]).exists():
            return (PHOTOS_DIR / p["file"]).resolve().as_uri()
    return ""


_SHORT = re.compile(r"(?<![\w-])([А-Яа-яЁёA-Za-z]{1,2}|—)\s+", re.U)


def typograf(text: str) -> str:
    """Неразрывный пробел после коротких слов и тире, чтобы предлоги не висели в конце строки."""
    text = text.replace(" \u2014", "\u00a0\u2014")
    return _SHORT.sub(lambda m: m.group(1) + "\u00a0", text)


def _prepare(slide: dict) -> dict:
    out = dict(slide)
    for k in ("title", "text", "eyebrow"):
        out[k] = typograf(out[k])
    out["items"] = [typograf(x) for x in out["items"]]
    return out


def render_html(pkg: PostPackage, rubric_title: str) -> str:
    return _env.get_template("carousel.html.j2").render(
        slides=[_prepare(s.model_dump()) for s in pkg.slides],
        accent=pkg.accent,
        photo=photo_path(pkg.photo_id),
        source_line=pkg.source_line,
        rubric_title=rubric_title,
        assets=(TEMPLATES_DIR / "assets").resolve().as_uri(),
    )


def render(pkg: PostPackage, rubric_title: str, name: str) -> list[Path]:
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "carousel.html"
    html_path.write_text(render_html(pkg, rubric_title), encoding="utf-8")
    files = []
    launch = {"executable_path": settings.chromium_path} if settings.chromium_path else {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        for i in range(1, len(pkg.slides) + 1):
            path = out_dir / f"slide-{i:02d}.png"
            page.locator(f"#s{i}").screenshot(path=str(path))
            files.append(path)
        browser.close()
    log.info("Отрендерено %s слайдов в %s", len(files), out_dir)
    return files
