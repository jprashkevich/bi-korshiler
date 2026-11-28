"""Сборка Reels: озвучка → таймлайн сцен и субтитров → кадры из HTML (Chromium) → MP4 (ffmpeg)."""
from __future__ import annotations

import json
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
TAIL = 1.0          # пауза после последней фразы, сек (короче — ролик зациклен)
MAX_VOICE_SECONDS = {"short": 30, "mid": 42, "long": 62}   # A/B длины: короткий, средний, длинный
SUB_MAX = 44        # максимум символов во фразе-плашке (две строки)
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
            # не оставляем в конце плашки предлог или союз («…не знал по» / «имени»)
            tail = re.search(r"(\S{1,3})\s*$", cur)
            if tail and cur.rstrip()[-1:] not in ".!?,:" and len(cur.split()) > 2:
                cut = tail.start()
                out.append((start, cur[:cut].strip()))
                start, cur = start + cut, cur[cut:]
            else:
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
            words = [{"t": round(speech.time_at(offsets[i] + off + m.start()), 3), "w": m.group(0)}
                     for m in re.finditer(r"\S+", text)]
            subs.append({"start": round(st, 3), "end": round(en, 3), "text": typograf(text), "words": words,
                         "hl": s.highlight})
    return tl, subs, total


# Ритм фонов как у каруселей: края navy, выводы и цифры — цветные (два акцента по очереди),
# цветная сцена никогда не идёт сразу за цветной, остальное — светлый фон.
COLORED = {"stat", "insight", "truth", "rehook", "payoff"}


def scene_backgrounds(scenes) -> list[str]:
    out, prev_colored, flip = [], False, False
    for i, sc in enumerate(scenes):
        if sc.type in ("hook", "cta") or i == 0:
            out.append("navy"); prev_colored = False
        elif sc.type in COLORED and not prev_colored:
            out.append("accent2" if flip else "accent"); flip = not flip; prev_colored = True
        else:
            out.append("light"); prev_colored = False
    return out


def meta_states(pkg: ReelPackage) -> tuple[list, list[int]]:
    """Состояние метафоры на каждую сцену: сцена без viz продолжает предыдущую фигуру, а не обрывает её
    (владелец: «не резать инфографика — текст — инфографика»). runs[i] — первая сцена непрерывного
    отрезка с тем же состоянием: внутри отрезка анимация не перезапускается."""
    states, runs, cur = [], [], None
    first = next((s.viz.model_dump() for s in pkg.scenes if s.viz.kind != "none"), None)
    for i, s in enumerate(pkg.scenes):
        if s.viz.kind != "none":
            cur = s.viz.model_dump()
        states.append(cur or first)
        runs.append(runs[-1] if i and states[i] == states[i - 1] else i)
    return states, runs


def scene_cards(pkg: ReelPackage, pictures: dict | None) -> list:
    """Карточка поверх метафоры: фото исследователя (person) или иллюстрация сцены."""
    from .render import illustrations, picture_uris
    ills, pics = illustrations(), picture_uris(pictures)
    people = {p.name_en: p for p in pkg.people}
    out = []
    for s in pkg.scenes:
        if s.type == "person" and pics.get(s.person, {}).get("uri"):
            ref = people.get(s.person)
            out.append({"uri": pics[s.person]["uri"], "person": True, "name": ref.name_ru if ref else s.person,
                        "role": ref.role_ru if ref else "", "credit": pics[s.person].get("credit", "")})
        elif s.illustration_id and ills.get(s.illustration_id):
            out.append({"uri": ills[s.illustration_id], "person": False, "name": "", "role": "", "credit": ""})
        else:
            out.append(None)
    return out


def silent_subs(pkg: ReelPackage, tl: list[dict]) -> list[dict]:
    """Без голоса субтитры — единственный текст: фразы озвучки равномерно по длительности сцены."""
    subs = []
    for s, seg in zip(pkg.scenes, tl):
        phrases = [p for _, p in split_phrases(s.voice.strip())] or [s.title]
        dur = (seg["end"] - seg["start"]) / len(phrases)
        for j, p in enumerate(phrases):
            subs.append({"start": round(seg["start"] + j * dur, 3), "end": round(seg["start"] + (j + 1) * dur, 3),
                         "text": typograf(p), "hl": s.highlight})
    return subs


def _launch(pw):
    return pw.chromium.launch(**({"executable_path": settings.chromium_path} if settings.chromium_path else {}))


def render_cover(pkg: ReelPackage, rubric_title: str, out: Path) -> Path:
    from .render import illustrations
    ills = illustrations()
    image = next((ills[s.illustration_id] for s in pkg.scenes if ills.get(s.illustration_id)), "")
    html = _env.get_template("reels_cover.html.j2").render(
        title=typograf(pkg.cover_title), accent=pkg.accent, rubric_title=rubric_title, image=image,
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


def reel_speech(text: str, out: Path) -> tts.Speech:
    """Голос для Reels живее и быстрее, чем для длинных текстов: темп 1.18, больше эмоций
    (style выше, stability ниже — интонация свободнее). Владелец просил «скорости и эмоций»."""
    from .settings import env
    # 1.18 вместе с рублеными фразами звучало как скороговорка; связному рассказу нужен естественный темп
    return tts.synthesize(text, out, speed=float(env("REELS_VOICE_SPEED", "1.08")),
                          style=float(env("REELS_VOICE_STYLE", "0.55")),
                          stability=float(env("REELS_VOICE_STABILITY", "0.3")))


def silent_timeline(pkg: ReelPackage, out: Path) -> tuple[list[dict], list[dict], float, Path]:
    """Ролик без голоса (A/B-вариант «только музыка и текст»): длительность сцены — по объёму текста
    на экране, сцены с инфографикой дольше, чтобы фигура успела собраться."""
    import imageio_ffmpeg
    tl, t = [], 0.0
    for s in pkg.scenes:
        words = len((s.title + " " + s.text).split())
        dur = min(max(1.4 + 0.3 * words, 2.0), 4.2)
        if s.viz.kind != "none":
            dur += 1.6
        tl.append({"start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
    total = round(t + TAIL, 2)
    silence = out / "silence.m4a"
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=mono", "-t", f"{total:.2f}", "-c:a", "aac", str(silence)], check=True)
    return tl, [], total, silence


def render_video(pkg: ReelPackage, rubric_title: str, name: str, pictures: dict | None = None,
                 speech_fn=None, music_fn=None) -> list[Path]:
    """Возвращает [mp4, обложка.png]. speech_fn подменяется в тестах."""
    out_dir = OUTPUT_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    full, _ = voice_text(pkg)
    silent = getattr(pkg, "voice_mode", "voice") == "music"
    if silent:
        tl, subs, total, voice_path = silent_timeline(pkg, out_dir)
    else:
        speech = (speech_fn or reel_speech)(full, out_dir / "voice.mp3")
    if not silent and speech_fn is None and speech.duration > MAX_VOICE_SECONDS.get(pkg.length, 36):
        # длинный ролик досматривают хуже: перезаписываем на предельной скорости голоса
        log.info("Озвучка %.1f с длиннее %s с — перезаписываю быстрее", speech.duration, MAX_VOICE_SECONDS)
        speech = tts.synthesize(full, out_dir / "voice.mp3", speed=1.2, style=0.55, stability=0.3)
    if not silent:
        tl, subs, total = timeline(pkg, speech)
        voice_path = speech.audio_path
    scenes = []
    for s in pkg.scenes:
        d = s.model_dump()
        d["title"], d["text"], d["eyebrow"] = typograf(d["title"]), typograf(d["text"]), d["eyebrow"]
        d.setdefault("highlight", "")
        scenes.append(d)
    from .render import SECOND_ACCENT
    if silent:
        subs = silent_subs(pkg, tl)
    states, runs = meta_states(pkg)
    html = _env.get_template("reels.html.j2").render(
        accent2=SECOND_ACCENT.get(pkg.accent, "periwinkle"),
        scenes=scenes, cards=scene_cards(pkg, pictures), hook=scenes[0], hook_end=tl[0]["end"],
        accent=pkg.accent, rubric_title=rubric_title, timeline=tl, subtitles=subs,
        vizs=states, runs=runs,
        viz_js=(TEMPLATES_DIR / "viz.js").read_text(encoding="utf-8"),
        total=total, assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
    page_path = out_dir / "reel.html"
    page_path.write_text(html, encoding="utf-8")

    video = out_dir / "reel.mp4"
    frames = int(total * FPS)
    if music_fn is None:
        from .music import compose as music_fn
    music = music_fn(getattr(pkg, "music_mood", "warm"), total, out_dir / "music.mp3")
    audio_in = ["-i", str(voice_path)]
    if music:
        # музыка тихо под голосом, плавно появляется и уходит; голос не трогаем
        audio_in += ["-i", str(music)]
        audio_filter = ["-filter_complex",
                        f"[1:a]apad[v];[2:a]volume={0.55 if silent else 0.13},afade=t=in:d=0.6,afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5[m];"
                        "[v][m]amix=inputs=2:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]"]
    else:
        audio_filter = ["-af", "apad"]
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
           *audio_in, *audio_filter, "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(video)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        with sync_playwright() as pw:
            b = _launch(pw)
            p = b.new_page(viewport={"width": 1080, "height": 1920})
            p.goto(page_path.resolve().as_uri(), wait_until="networkidle")
            p.evaluate("document.fonts.ready")
            p.wait_for_function("document.body.dataset.fitted === '1'", timeout=15000)
            issues = p.evaluate("window.layoutIssues || []")
            target = {"short": 30, "mid": 43, "long": 63}.get(getattr(pkg, "length", "mid"), 45)
            if total > target:
                issues.append(f"ролик {total:.0f} с при цели до {target} с ({getattr(pkg, 'length', 'mid')}): "
                              "можно нажать «Переделать» с просьбой сократить")
            (out_dir / "layout_issues.json").write_text(json.dumps(issues, ensure_ascii=False), encoding="utf-8")
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
