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
FPS = 24          # для Reels достаточно; 30 к/с давали рендер под 35 минут на длинный ролик
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
            tail = re.search(r"\s(\S{1,3})\s*$", cur)       # отдельное короткое слово, а не конец длинного
            if tail and cur.rstrip()[-1:] not in ".!?,:" and len(cur.split()) > 2:
                cut = tail.start(1)
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


# ---------- звуковые акценты ----------
# Синтез в ffmpeg, а не генерация: бесплатно, мгновенно и одинаково в каждом ролике (узнаваемый звук бренда).
SFX = {
    "paper": "anoisesrc=c=pink:r=44100:a=0.5:d=0.28,highpass=f=1800,afade=t=in:d=0.03,afade=t=out:st=0.08:d=0.2,volume=0.35",
    "pop": "sine=f=820:r=44100:d=0.12,afade=t=out:st=0.01:d=0.11,volume=0.5",
    "whoosh": "anoisesrc=c=brown:r=44100:a=0.6:d=0.6,highpass=f=300,lowpass=f=3500,afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.3,volume=0.6",
}


def sfx_files(out_dir: Path) -> dict[str, Path]:
    out = {}
    for name, graph in SFX.items():
        path = out_dir / f"sfx-{name}.wav"
        if not path.exists():
            subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "lavfi", "-i", graph, str(path)],
                           check=True)
        out[name] = path
    return out


def sfx_events(runs: list[dict]) -> list[tuple[str, float]]:
    """Когда звучат акценты: карточка на столе — шелест, цифра — щелчок, смена кадра — «вжух»."""
    ev = []
    for k, r in enumerate(runs):
        if k:
            ev.append(("whoosh", max(r["start"] - 0.25, 0)))
        for c in r.get("cards", []):
            ev.append(("pop" if c["kind"] == "number" else "paper", c["at"]))
    return ev[:40]


# ---------- формат 4: фото → стол-коллаж → дата-арт ----------

ACCENT_HEX = {"sky": "#009fe3", "green": "#88c947", "orange": "#ff954c", "periwinkle": "#556bb8"}


def env_flag(name: str, default: str = "1") -> bool:
    from .settings import env
    return env(name, default) != "0"


def reels_photos() -> dict[str, str]:
    """Фото для пробных Reels: только помеченные reels: true (без крупных лиц и детей) и по сезону."""
    import yaml
    from .render import PHOTOS_DIR
    from .season import fits
    from .settings import CONFIG_DIR
    out = {}
    for p in yaml.safe_load((CONFIG_DIR / "photos.yaml").read_text(encoding="utf-8"))["photos"]:
        f = PHOTOS_DIR / p["file"]
        if p.get("reels") and fits(p) and f.exists():
            out[p["id"]] = f.resolve().as_uri()
    return out


def build_runs(pkg: ReelPackage, tl: list[dict], pictures: dict | None, subs: list[dict] | None = None,
               clips: list[dict] | None = None) -> list[dict]:
    """Склеивает соседние сцены с одним типом кадра в отрезки и раскладывает карточки на столе.
    Почему так: метафора не должна рваться на каждой сцене (решение владельца), поэтому кадр меняется
    только при смене типа, а внутри отрезка двигается камера и добавляются детали."""
    from .render import illustrations, picture_uris
    photos, ills, pics = reels_photos(), illustrations(), picture_uris(pictures)
    people = {p.name_en: p for p in pkg.people}
    accent = ACCENT_HEX.get(pkg.accent, "#ff954c")
    shots = []
    for s in pkg.scenes:
        shot = s.shot
        if shot == "photo" and not photos.get(s.photo_id):
            shot = "collage"
        if shot == "dataart" and s.viz.kind == "none" and not (shots and shots[-1] == "dataart"):
            shot = "collage"
        shots.append(shot)
    runs = []
    for i, (s, shot) in enumerate(zip(pkg.scenes, shots)):
        if not runs or runs[-1]["shot"] != shot:
            runs.append({"shot": shot, "idx": []})
        runs[-1]["idx"].append(i)
    out = []
    for r in runs:
        idx = r["idx"]
        run = {"shot": r["shot"], "start": tl[idx[0]]["start"], "end": tl[idx[-1]]["end"], "scenes": []}
        if r["shot"] == "photo":
            # несколько снимков на отрезок: кадр меняется на каждой фразе голоса (владелец: «медленный монтаж»)
            # только снимки, которые сценарий назвал сам: «добивка» случайными фото из каталога поставила
            # волонтёра-мужчину в историю про бабушку. Смену кадра на каждой фразе теперь дают иллюстрации фраз.
            chosen = list(dict.fromkeys(photos[pkg.scenes[i].photo_id] for i in idx if photos.get(pkg.scenes[i].photo_id)))
            run["photos"] = chosen[:3]
            if clips and not out:          # живые планы из отчётов BIG Life — в первый фото-отрезок (хук)
                run["photos"] = [Path(c["path"]).resolve().as_uri() for c in clips] + run["photos"][:1]
        if r["shot"] == "collage":
            cards, decos, y, side, focus = [], [], 300, 0, {"y": 700, "s": 1.0}
            for i in idx:
                s, at = pkg.scenes[i], tl[i]["start"]
                # карточки ложатся на стол по фразам голоса, а не все разом в начале сцены
                beats = [x["start"] for x in (subs or []) if tl[i]["start"] - 0.05 <= x["start"] < tl[i]["end"]] or [at]
                items = []
                if s.note:
                    items.append({"kind": "note", "lines": s.note[:4], "w": 620, "h": 130 + 72 * len(s.note[:4])})
                pic = None
                if s.type == "person" and pics.get(s.person, {}).get("uri"):
                    ref = people.get(s.person)
                    pic = {"uri": pics[s.person]["uri"], "person": True, "name": ref.name_ru if ref else s.person,
                           "role": ref.role_ru if ref else ""}
                elif photos.get(s.photo_id):
                    pic = {"uri": photos[s.photo_id], "person": False, "name": "", "role": ""}
                elif ills.get(s.illustration_id):
                    pic = {"uri": ills[s.illustration_id], "person": False, "name": "", "role": ""}
                if pic:
                    items.append({"kind": "photo", **pic, "w": 560, "h": 660})
                if s.viz.kind != "none":
                    items.append({"kind": "data", "viz": s.viz.model_dump(), "w": 760, "h": 560})
                if s.type == "stat" and s.title:
                    items.append({"kind": "number", "text": typograf(s.title), "caption": typograf(s.text),
                                  "size": 170 if len(s.title) < 7 else 120, "w": 400, "h": 260})
                if not items:
                    run["scenes"].append({"i": i, "start": at, "end": tl[i]["end"], "viz": None, "focus": dict(focus)})
                    continue
                row_h = max(it["h"] for it in items[:2]) + (60 if any(it["kind"] == "photo" and it["name"] for it in items) else 0)
                xs = [80, 600] if side == 0 else [600, 80]
                for k, it in enumerate(items[:2]):
                    # одиночная карточка — почти по центру, с лёгким сдвигом в сторону для живости
                    x = xs[k] if len(items) > 1 else (1080 - it["w"]) // 2 + (-40 if side == 0 else 40)
                    if it["kind"] == "data" and len(items) > 1:
                        it["w"], it["h"] = 600, 480
                        x = 50 if k == 0 else 470
                    if it["kind"] == "number" and len(items) > 1:
                        it["size"], it["w"] = min(it["size"], 150), 380
                        x = 650 if k == 1 else 60
                    it.update(x=min(x, 1080 - it["w"] - 40), y=y, at=round(beats[min(k, len(beats) - 1)] + 0.1 + (0.35 * k if k >= len(beats) else 0), 2),
                              rot=round((-2.5 if (k + side) % 2 else 2.5), 1))
                    cards.append(it)
                for it in items[2:]:              # третий предмет — под рядом
                    it.update(x=200, y=y + row_h + 20, at=round(beats[min(2, len(beats) - 1)] + 0.3, 2), rot=-1.5)
                    cards.append(it)
                    row_h += it["h"] + 40
                decos.append({"kind": ["half", "dot", "rule"][len(decos) % 3], "x": 140 + 520 * side,
                              "y": y + row_h - 10, "r": 120 if len(decos) % 3 == 0 else 60,
                              "color": "#c9b8f2" if len(decos) % 2 == 0 else accent, "at": round(at + 0.4, 2)})
                # одиночную карточку камера берёт крупнее, пару — целиком
                focus = {"y": y + row_h / 2, "s": 1.25 if len(items) == 1 else 1.0}
                run["scenes"].append({"i": i, "start": at, "end": tl[i]["end"], "viz": None, "focus": dict(focus)})
                y += row_h + 120
                side = 1 - side
            run.update(cards=cards, decos=decos, height=y + 400)
            run["zoomout"] = len(cards) >= 3
            run["zoomout_s"] = round(min(1.0, 1150 / max(y - 300, 1)), 3)
            run["zoomout_y"] = round(300 + (y - 300) / 2, 1)
            if run["scenes"] and run["scenes"][0]["focus"]["y"] == 700 and cards:
                run["scenes"][0]["focus"] = run["scenes"][1]["focus"] if len(run["scenes"]) > 1 else {"y": cards[0]["y"] + 200, "s": 1.0}
        else:
            for i in idx:
                s = pkg.scenes[i]
                run["scenes"].append({"i": i, "start": tl[i]["start"], "end": tl[i]["end"],
                                      "viz": s.viz.model_dump() if s.viz.kind != "none" else None, "focus": None})
            if r["shot"] == "dataart" and not any(x["viz"] for x in run["scenes"]):
                prev = next((pkg.scenes[j].viz.model_dump() for j in range(idx[0] - 1, -1, -1)
                             if pkg.scenes[j].viz.kind != "none"), None)
                run["scenes"][0]["viz"] = prev
        out.append(run)
    return out


MIN_SEG = 1.0      # иллюстрация фразы держится не меньше секунды, иначе глаз не успевает её прочитать


def broll_segments(pkg: ReelPackage, tl: list[dict], subs: list[dict], resolved: list[list[dict]]) -> list[dict]:
    """Раскладывает 2–3 иллюстрации каждой сцены по её времени: ~1,5 с на картинку, границы — по началу фраз
    голоса, если они рядом. В сценах с дата-артом иллюстрации идут в верхнем окне, а метафора продолжает
    расти внизу: владелец просил не резать инфографику на куски."""
    out = []
    for i, (s, row) in enumerate(zip(pkg.scenes, resolved)):
        if not row:
            continue
        a, b = tl[i]["start"], tl[i]["end"]
        if i == 0:
            a = max(a, 0.0)
        n = max(1, min(len(row), int((b - a) // MIN_SEG)))
        row = row[:n]
        beats = [x["start"] for x in subs if a + 0.3 < x["start"] < b - 0.3]
        cuts = [a]
        for k in range(1, n):
            want = a + (b - a) * k / n
            near = min(beats, key=lambda x: abs(x - want), default=None)
            cut = near if near is not None and abs(near - want) < 0.45 and near - cuts[-1] >= MIN_SEG else want
            cuts.append(round(cut, 2))
        cuts.append(b)
        split = s.viz.kind != "none"
        for k, v in enumerate(row):
            out.append({**v, "start": round(cuts[k], 2), "end": round(cuts[k + 1], 2), "scene": i,
                        "split": split, "k": len(out)})
    return out


def _launch(pw):
    return pw.chromium.launch(**({"executable_path": settings.chromium_path} if settings.chromium_path else {}))


def render_cover(pkg: ReelPackage, rubric_title: str, out: Path) -> Path:
    from .render import illustrations
    ills = illustrations()
    photos = reels_photos()
    image = (next((photos[s.photo_id] for s in pkg.scenes if photos.get(s.photo_id)), "")
             or next((ills[s.illustration_id] for s in pkg.scenes if ills.get(s.illustration_id)), ""))
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


def reel_speech(text: str, out: Path, fast: bool = False) -> tts.Speech:
    """Голос Reels: eleven_v3, естественный режим (вариант 4 из voicetest — выбор владельца 28.11).
    Тег [warmly] задаёт мягкую тёплую подачу; его символы срезаем из таймкодов, чтобы субтитры не съехали.
    REELS_VOICE_STABILITY=0 — эмоциональный вариант 5; REELS_VOICE_MODEL — вернуть v2."""
    from .settings import env
    model = env("REELS_VOICE_MODEL", "eleven_v3")
    if model == "eleven_v3":
        tag = env("REELS_VOICE_TAGS", "[warmly]").strip()
        prefix = f"{tag} " if tag else ""
        sp = tts.synthesize(prefix + text, out, model=model, stability=float(env("REELS_VOICE_STABILITY", "0.5")),
                            speed=1.2 if fast else None)
        if prefix and len(sp.starts) > len(prefix):
            sp.starts = sp.starts[len(prefix):]
        return sp
    return tts.synthesize(text, out, model=model, speed=1.2 if fast else float(env("REELS_VOICE_SPEED", "1.12")),
                          style=float(env("REELS_VOICE_STYLE", "0.55")), stability=float(env("REELS_VOICE_STABILITY", "0.3")))


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


MAX_HOLD = 2.5        # формат 6: дольше перебивка не держится (кроме глав данных)


def build_shots(cuts: list[dict], sb, words: list[dict], subs: list[dict], hook_end: float, total: float) -> tuple[list, list]:
    """Формат 6: главы данных + перебивки → один таймлайн кадров на весь экран.
    Пустоты (картинка не прошла проверку) заполняются кинетическим текстом фразы, а не удержанием
    прошлого кадра: на прогоне #24 удержание дало мёртвые 4–6 секунд."""
    from . import director
    wt = lambda i: director.word_time(words, i)
    vizs, chapters = [], []
    for a in sb.chapters:
        st = max(wt(a.word) - 0.15, hook_end + 0.3)
        en = wt(a.until_word) if a.until_word > a.word else st + 4.5
        chapters.append([st, min(max(en, st + 3.0), st + 6.0), len(vizs)])
        vizs.append(a.model_dump())
    exp = min(max(wt(sb.expand_word) - 0.2, total - 6.0), total - 2.5)
    chapters = [c for c in chapters if c[0] < exp - 1.5]
    for k in range(len(chapters) - 1):
        chapters[k][1] = min(chapters[k][1], chapters[k + 1][0])
    if chapters:
        chapters[-1][1] = min(chapters[-1][1], exp)
    if vizs:
        chapters.append([exp, total + 1, len(vizs)])
        vizs.append(vizs[-1])                   # финальная глава возвращается к метафоре в полном виде
    inside = lambda t: any(c[0] - 0.3 <= t < c[1] for c in chapters)
    shots = [dict(c) for c in cuts if not inside(c["start"])]
    shots += [{"type": "chapter", "start": round(c[0], 2), "chapter": c[2], "cend": c[1]} for c in chapters]
    shots.sort(key=lambda x: x["start"])
    if shots and shots[0]["start"] > 0:
        shots[0]["start"] = 0.0
    def sub_at(t):
        return next((x for x in subs if x["start"] - 0.05 <= t < x["end"]), None)
    out = []
    for k, sh in enumerate(shots):
        end = shots[k + 1]["start"] if k + 1 < len(shots) else total + 1
        if sh["type"] == "chapter":
            # глава закончилась, а следующего кадра ещё нет — пустоту заполняет текст, а не застывшая фигура
            sh["end"] = round(min(sh.pop("cend"), end), 2)
            out.append(sh)
            t = sh["end"]
        else:
            sh["end"] = round(end, 2)
            out.append(sh)
            t = sh["start"] + 1.8
        while end - t > 0.9 and t < total:
            if t < hook_end:                     # в хуке держит крупный текст; первый текстовый кадр — сразу после
                t = hook_end + 0.05
                continue
            if t >= hook_end:
                sub = sub_at(t)
                if sub:
                    key = sub.get("hl") or max(sub["text"].split(), key=len)
                    out[-1]["end"] = round(t, 2)
                    out.append({"type": "kinetic", "start": round(t, 2), "end": round(min(t + 1.8, end), 2),
                                "text": sub["text"], "key": key.strip(".,!?«»")})
            t += 1.8
    return out, vizs


def directed_html6(pkg: ReelPackage, subs: list[dict], tl: list[dict], total: float,
                   pictures: dict | None, clips: list[dict], item: dict | None) -> tuple[str, list]:
    """Формат 6 (config/reels-motion-v6.md): весь экран, движение в каждом кадре, метафора главами."""
    from . import director
    from .broll import resolve_storyboard
    from .render import SECOND_ACCENT
    hook_end = tl[0]["end"]
    sb = director.direct(pkg, subs, hook_end, total, item, fmt=6)
    sb.chapters = director.valid_chapters(sb.chapters, director.source_text(pkg, item))
    words = director.words_of(subs)
    cuts = resolve_storyboard(sb, words, subs, pkg, item, pictures, clips, lead=director.LEAD, world=True)
    shots, vizs = build_shots(cuts, sb, words, subs, hook_end, total)
    if not shots:
        raise RuntimeError("в раскадровке нет кадров")
    accents_js = [{"t": round(director.word_time(words, a.word), 2), "motion": a.motion} for a in sb.accents]
    final = next((x["start"] for x in shots if x["type"] == "chapter" and x["chapter"] == len(vizs) - 1), None)
    if final and not any(a["motion"] == "flash" for a in accents_js):
        accents_js.append({"t": round(final, 2), "motion": "flash"})       # вспышка перед финалом
    hook = {"title": typograf(pkg.scenes[0].title), "highlight": pkg.scenes[0].highlight}
    import zlib
    html = _env.get_template("reels6.html.j2").render(
        accent=pkg.accent, accent2=SECOND_ACCENT.get(pkg.accent, "periwinkle"), hook=hook, shots=shots,
        shots_js=[{k: x[k] for k in ("type", "start", "end", "text", "chapter") if k in x} for x in shots],
        chapters_js=vizs, accents_js=accents_js, hook_end=hook_end, total=total,
        subtitles=subs, source=sb.source or pkg.source_line[:60], seed=zlib.crc32(pkg.headline.encode()) % 100000,
        art_js=(TEMPLATES_DIR / "dataart.js").read_text(encoding="utf-8"), assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
    events = [("whoosh", max(hook_end - 0.2, 0))] + [("whoosh", max(a["t"] - 0.2, 0)) for a in accents_js if a["motion"] == "flash"]
    events += [("pop" if x["type"] == "number" else "paper", x["start"]) for x in shots
               if x["type"] not in ("full", "chapter", "kinetic")]
    events += [("whoosh", max(x["start"] - 0.15, 0)) for x in shots if x["type"] == "chapter"]
    (OUTPUT_DIR / "last_storyboard.json").write_text(sb.model_dump_json(indent=1), encoding="utf-8")
    return html, events[:40]


def directed_html(pkg: ReelPackage, rubric_title: str, subs: list[dict], tl: list[dict], total: float,
                  pictures: dict | None, clips: list[dict], item: dict | None) -> tuple[str, list]:
    """Формат 5: раскадровка режиссёра по времени слов → кадры, прошедшие проверку «по глазам» → HTML."""
    from . import director
    from .broll import resolve_storyboard
    from .render import SECOND_ACCENT
    hook_end = tl[0]["end"]
    sb = director.direct(pkg, subs, hook_end, total, item)
    words = director.words_of(subs)
    cuts = resolve_storyboard(sb, words, subs, pkg, item, pictures, clips, lead=director.LEAD)
    if not cuts or not sb.anchor:
        raise RuntimeError("в раскадровке нет кадров или метафоры")
    wt = lambda i: director.word_time(words, i)
    expand_t = min(max(wt(sb.expand_word) - 0.2, total - 6.0), total - 2.5)
    anchor_js = [{"t": round(max(wt(a.word) - 0.1, hook_end), 2), "viz": a.viz.model_dump()} for a in sb.anchor]
    accents_js = [{"t": round(wt(a.word), 2), "motion": a.motion} for a in sb.accents]
    hook = {"title": typograf(pkg.scenes[0].title), "highlight": pkg.scenes[0].highlight}
    html = _env.get_template("reels5.html.j2").render(
        accent=pkg.accent, accent2=SECOND_ACCENT.get(pkg.accent, "periwinkle"), hook=hook, cuts=cuts,
        cuts_js=[{k: c[k] for k in ("type", "start", "text") if k in c} for c in cuts],
        anchor_js=anchor_js, accents_js=accents_js, hook_end=hook_end, expand_t=round(expand_t, 2),
        total=total, subtitles=subs, source=sb.source or pkg.source_line[:60],
        viz_js=(TEMPLATES_DIR / "viz.js").read_text(encoding="utf-8"), assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
    # звук: карточка на стол — шелест, цифра — щелчок, вспышки — «вжух»
    events = [("whoosh", max(hook_end - 0.2, 0))] + [("whoosh", max(a["t"] - 0.2, 0)) for a in accents_js if a["motion"] == "flash"]
    events += [("pop" if c["type"] == "number" else "paper", c["start"]) for c in cuts if c["type"] not in ("full",)]
    (OUTPUT_DIR / "last_storyboard.json").write_text(sb.model_dump_json(indent=1), encoding="utf-8")
    return html, events[:40]


def render_video(pkg: ReelPackage, rubric_title: str, name: str, pictures: dict | None = None,
                 speech_fn=None, music_fn=None, item: dict | None = None) -> list[Path]:
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
        try:
            speech = reel_speech(full, out_dir / "voice-fast.mp3", fast=True)
        except tts.TTSError as exc:       # ускорение не поддержано моделью — оставляем обычный темп
            log.warning("Ускорить озвучку не вышло: %s", exc)
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
    clips = []
    if any(s.shot == "photo" for s in pkg.scenes) and env_flag("REELS_CLIPS"):
        try:
            from .clips import pick_clips
            clips = pick_clips(limit=2)
        except Exception as exc:          # видео — усиление, без него ролик всё равно собирается
            log.warning("Видео из отчётов не подобраны: %s", exc)
    html, events = None, None
    if not silent and env_flag("REELS_DIRECTOR"):
        try:
            from .settings import env
            if env("REELS_FORMAT", "5") == "6":
                html, events = directed_html6(pkg, subs, tl, total, pictures, clips, item)
            else:
                html, events = directed_html(pkg, rubric_title, subs, tl, total, pictures, clips, item)
        except Exception as exc:          # режиссёр — новый формат; при сбое ролик собирается прежним
            log.warning("Режиссёр не справился, собираю прежним форматом: %s", exc)
    if html is None:
        runs = build_runs(pkg, tl, pictures, subs, clips)
        broll = []
        if any(s.visuals for s in pkg.scenes):
            try:
                from .broll import resolve
                broll = broll_segments(pkg, tl, subs, resolve(pkg, item, pictures, clips))
            except Exception as exc:          # иллюстрации — усиление: без них остаётся прежний кадр сцены
                log.warning("Иллюстрации фраз не собраны: %s", exc)
        runs_js = [{k: v for k, v in r.items() if k in ("shot", "start", "end", "scenes", "zoomout", "zoomout_s", "zoomout_y")}
                   for r in runs]
        html = _env.get_template("reels.html.j2").render(
            accent2=SECOND_ACCENT.get(pkg.accent, "periwinkle"),
            scenes=scenes, hook=scenes[0], hook_end=tl[0]["end"],
            accent=pkg.accent, rubric_title=rubric_title, timeline=tl, subtitles=subs,
            runs=runs, runs_js=runs_js, broll=broll,
            broll_js=[{k: v[k] for k in ("type", "start", "end", "split", "text") if k in v} for v in broll],
            viz_js=(TEMPLATES_DIR / "viz.js").read_text(encoding="utf-8"),
            total=total, assets=(TEMPLATES_DIR / "assets").resolve().as_uri())
        events = sfx_events(runs)
    page_path = out_dir / "reel.html"
    page_path.write_text(html, encoding="utf-8")

    video = out_dir / "reel.mp4"
    frames = int(total * FPS)
    if music_fn is None:
        from .music import compose as music_fn
    music = music_fn(getattr(pkg, "music_mood", "warm"), total, out_dir / "music.mp3")
    audio_in = ["-i", str(voice_path)]
    graph, mix = ["[1:a]apad[v]"], ["[v]"]
    if music:
        # музыка тихо под голосом, плавно появляется и уходит; голос не трогаем
        audio_in += ["-i", str(music)]
        graph.append(f"[2:a]volume={0.55 if silent else 0.13},afade=t=in:d=0.6,"
                     f"afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5[m]")
        mix.append("[m]")
    # звуковые акценты: каждый звук — один вход, размножаем через asplit и сдвигаем adelay на свой момент
    sfx = sfx_files(out_dir)
    next_in = 2 + (1 if music else 0)
    for name in sorted({e[0] for e in events}):
        times = [at for nm, at in events if nm == name]
        audio_in += ["-i", str(sfx[name])]
        labels = [f"{name}{j}" for j in range(len(times))]
        graph.append(f"[{next_in}:a]asplit={len(times)}" + "".join(f"[{x}]" for x in labels) if len(times) > 1
                     else f"[{next_in}:a]anull[{labels[0]}]")
        for x, at in zip(labels, times):
            ms = int(at * 1000)
            graph.append(f"[{x}]adelay={ms}|{ms}[d{x}]")
            mix.append(f"[d{x}]")
        next_in += 1
    audio_filter = ["-filter_complex", ";".join(graph) + ";" + "".join(mix)
                    + f"amix=inputs={len(mix)}:duration=first:normalize=0[a]", "-map", "0:v", "-map", "[a]"]
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
           *audio_in, *audio_filter, "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
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
