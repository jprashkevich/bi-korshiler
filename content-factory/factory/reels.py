"""Сборка Reels: озвучка → таймлайн сцен и субтитров → кадры из HTML (Chromium) → MP4 (ffmpeg)."""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from . import tts
from .models import ReelPackage
from .render import typograf
from .settings import OUTPUT_DIR, TEMPLATES_DIR, settings

log = logging.getLogger(__name__)
FPS = 30
TAIL = 1.5          # пауза после последней фразы, сек
SUB_MAX = 34        # максимум символов в строке субтитров
_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html", "j2"]))


def voice_text(pkg: ReelPackage) -> tuple[str, list[int]]:
    """Полный текст озвучки и индекс первого символа каждой сцены."""
    parts, offsets, pos = [], [], 0
    for s in pkg.scenes:
        offsets.append(pos)
        chunk = s.voice.strip()
        parts.append(chunk)
        pos += len(chunk) + 1          # +1 за пробел-разделитель
    return " ".join(parts), offsets


def split_phrases(text: str, limit: int = SUB_MAX) -> list[tuple[int, str]]:
    """Делит текст на короткие фразы для субтитров; возвращает (смещение, фраза)."""
    out, start, cur = [], 0, ""
    for m in re.finditer(r"\S+\s*", text):
        word = m.group(0)
        if cur and (len(cur) + len(word.rstrip()) > limit or cur.rstrip()[-1:] in ".!?"):
            out.append((start, cur.strip()))
            start, cur = m.start(), ""
        cur += word
    if cur.strip():
        out.append((start, cur.strip()))
    return out


def timeline(pkg: ReelPackage, speech: tts.Speech) -> tuple[list[dict], list[dict], float]:
    full, offsets = voice_text(pkg)
    total = round(speech.duration + TAIL, 2)
    starts = [0.0] + [speech.time_at(o) - 0.15 for o in offsets[1:]]
    tl = [{"start": round(starts[i], 3), "end": round(starts[i + 1] if i + 1 < len(starts) else total, 3)}
          for i in range(len(starts))]
    subs = []
    for i, s in enumerate(pkg.scenes):
        phrases = split_phrases(s.voice.strip())
        for j, (off, text) in enumerate(phrases):
            st = speech.time_at(offsets[i] + off)
            en = (speech.time_at(offsets[i] + phrases[j + 1][0]) if j + 1 < len(phrases)
                  else (speech.time_at(offsets[i + 1]) if i + 1 < len(offsets) else speech.duration + 0.3))
            subs.append({"start": round(st, 3), "end": round(en, 3), "text": text})
    return tl, subs, total


def _launch(pw):
    return pw.chromium.launch(**({"executable_path": settings.chromium_path} if settings.chromium_path else {}))


def render_cover(pkg: ReelPackage, rubric_title: str, out: Path) -> Path:
    html = _env.get_template("reels_cover.html.j2").render(
        title=typograf(pkg.cover_title), accent=pkg.accent, rubric_title=rubric_title,
        assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
    page_path = out.with_suffix(".html")
    page_path.write_text(html, encoding="utf-8")
    with sync_playwright() as pw:
        b = _launch(pw)
        p = b.new_page(viewport={"width": 1080, "height": 1920})
        p.goto(page_path.resolve().as_uri(), wait_until="networkidle")
        p.evaluate("document.fonts.ready")
        p.locator("#cover").screenshot(path=str(out))
        b.close()
    return out


def render_video(pkg: ReelPackage, rubric_title: str, name: str, pictures: dict | None = None,
                 speech_fn=tts.synthesize) -> list[Path]:
    """Возвращает [mp4, обложка.png]. speech_fn подменяется в тестах."""
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    full, _ = voice_text(pkg)
    speech = speech_fn(full, out_dir / "voice.mp3")
    tl, subs, total = timeline(pkg, speech)
    scenes = []
    for s in pkg.scenes:
        d = s.model_dump()
        d["title"], d["text"], d["eyebrow"] = typograf(d["title"]), typograf(d["text"]), d["eyebrow"]
        scenes.append(d)
    from .render import illustrations, picture_uris
    html = _env.get_template("reels.html.j2").render(
        ills=illustrations(), pictures=picture_uris(pictures),
        people={p.name_en: p.model_dump() for p in pkg.people},
        scenes=scenes, accent=pkg.accent, rubric_title=rubric_title, timeline=tl, subtitles=subs,
        total=total, assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
    page_path = out_dir / "reel.html"
    page_path.write_text(html, encoding="utf-8")

    video = out_dir / "reel.mp4"
    frames = int(total * FPS)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
           "-i", str(speech.audio_path), "-af", "apad", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        with sync_playwright() as pw:
            b = _launch(pw)
            p = b.new_page(viewport={"width": 1080, "height": 1920})
            p.goto(page_path.resolve().as_uri(), wait_until="networkidle")
            p.evaluate("document.fonts.ready")
            for i in range(frames):
                p.evaluate(f"seek({i / FPS:.4f})")
                proc.stdin.write(p.screenshot(type="jpeg", quality=92))
            b.close()
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg завершился с кодом {code}")
    cover = render_cover(pkg, rubric_title, out_dir / "cover.png")
    log.info("Reels готов: %s (%.1f с, %s кадров)", video, total, frames)
    return [video, cover]
