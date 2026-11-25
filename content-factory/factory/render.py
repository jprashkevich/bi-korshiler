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


_SHORT = re.compile(r"(?<![\w-])([А-Яа-яЁёA-Za-z]{1,2})\s+", re.U)


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


def illustrations() -> dict[str, str]:
    """id → file:// URI для иллюстраций из config/illustrations.yaml."""
    path = CONFIG_DIR / "illustrations.yaml"
    if not path.exists():
        return {}
    out = {}
    for it in yaml.safe_load(path.read_text(encoding="utf-8")).get("illustrations", []):
        f = TEMPLATES_DIR / "assets" / "illustrations" / it["file"]
        if f.exists():
            out[it["id"]] = f.resolve().as_uri()
    return out


def picture_uris(pictures: dict | None) -> dict[str, dict]:
    out = {}
    for name, pic in (pictures or {}).items():
        if pic and Path(pic["path"]).exists():
            out[name] = {"uri": Path(pic["path"]).resolve().as_uri(), "credit": pic.get("credit", "")}
    return out


COLORED = {"statement", "stat", "steps"}          # типы, которые просят цветной фон
SECOND_ACCENT = {"sky": "green", "green": "sky", "orange": "periwinkle", "periwinkle": "orange"}


def backgrounds(slides) -> list[str]:
    """Ритм фонов: обложка и финал — navy; внутри цветной слайд никогда не идёт сразу за цветным,
    а цветные чередуют два акцента поста. Цветной тип после цветного рисуется светлым вариантом."""
    out, prev_colored, flip = [], False, False
    for sl in slides:
        if sl.type in ("cover", "cta"):
            out.append("navy"); prev_colored = False
        elif sl.type in COLORED and not prev_colored:
            out.append("accent2" if flip else "accent"); flip = not flip; prev_colored = True
        else:
            out.append("light"); prev_colored = False
    return out


def render_html(pkg: PostPackage, rubric_title: str, pictures: dict | None = None,
                drive_photos: dict | None = None, photo_city: dict | None = None,
                cities: list | None = None) -> str:
    return _env.get_template("carousel.html.j2").render(
        bgs=backgrounds(pkg.slides), accent2=SECOND_ACCENT.get(pkg.accent, "periwinkle"),
        photo_city=photo_city or {}, cities=cities or [],
        dphotos={k: Path(v).resolve().as_uri() for k, v in (drive_photos or {}).items()},
        ills=illustrations(),
        pictures=picture_uris(pictures),
        people={p.name_en: p.model_dump() for p in pkg.people},
        slides=[_prepare(s.model_dump()) for s in pkg.slides],
        accent=pkg.accent,
        photo=photo_path(pkg.photo_id),
        source_line=pkg.source_line,
        rubric_title=rubric_title,
        assets=(TEMPLATES_DIR / "assets").resolve().as_uri(),
    )


def render(pkg: PostPackage, rubric_title: str, name: str, pictures: dict | None = None,
           drive_photos: dict | None = None, photo_city: dict | None = None,
           cities: list | None = None) -> list[Path]:
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / "carousel.html"
    html_path.write_text(render_html(pkg, rubric_title, pictures, drive_photos, photo_city, cities), encoding="utf-8")
    files = []
    launch = {"executable_path": settings.chromium_path} if settings.chromium_path else {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.evaluate("document.fonts.ready")
        page.wait_for_function("document.body.dataset.fitted === '1'", timeout=15000)
        issues = page.evaluate("window.layoutIssues || []")
        (out_dir / "layout_issues.json").write_text(__import__("json").dumps(issues, ensure_ascii=False), encoding="utf-8")
        for i in range(1, len(pkg.slides) + 1):
            path = out_dir / f"slide-{i:02d}.png"
            page.locator(f"#s{i}").screenshot(path=str(path))
            files.append(path)
        browser.close()
    log.info("Отрендерено %s слайдов в %s", len(files), out_dir)
    return files
