"""Живые планы для Reels из видео отчётов BIG Life (решение владельца: только общие планы без лиц).

Почему так: у tillo.journal ролик держится на движении людей в кадре, у нас были только фото.
Видео из отчётов снимают Драйверы дома на телефон — там бывают крупные лица и дети, а Reels пробные
и уходят незнакомым людям. Поэтому каждый ролик перед использованием смотрит модель по нескольким кадрам:
общий план, нет крупных лиц, нет детей крупным планом, не запись экрана. Решение кешируется.
"""
from __future__ import annotations

import base64
import json
import logging
import subprocess
from pathlib import Path

import imageio_ffmpeg
from pydantic import BaseModel, Field

from . import db, drive, llm
from .settings import OUTPUT_DIR, settings

log = logging.getLogger(__name__)
FF = imageio_ffmpeg.get_ffmpeg_exe()
CLIP_SECONDS = 5.0


class ClipVerdict(BaseModel):
    ok: bool = Field(description="Подходит: общий или средний план, нет крупных лиц (лицо меньше ~1/10 кадра), нет детей крупным планом, не запись экрана, не тёмный и не смазанный кадр")
    start_frame: int = Field(description="Номер кадра (0–3), с которого лучше начать фрагмент")
    reason: str = Field(description="Коротко: почему подходит или нет")


def _duration(path: Path) -> float:
    import re
    err = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def _frames(path: Path, dur: float) -> list[tuple[float, bytes]]:
    out = []
    for k in range(4):
        t = max(0.0, (dur - CLIP_SECONDS) * k / 3) if dur > CLIP_SECONDS else 0.0
        jpg = subprocess.run([FF, "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                              "-vf", "scale=512:-2", "-f", "image2", "-c:v", "mjpeg", "-"], capture_output=True).stdout
        if jpg:
            out.append((t, jpg))
    return out


def check(path: Path) -> tuple[bool, float]:
    dur = _duration(path)
    if dur < 2.5:
        return False, 0.0
    frames = _frames(path, dur)
    if not frames:
        return False, 0.0
    content = [{"type": "text", "text": "Четыре кадра из одного видео с соседского мероприятия. Можно ли показать этот "
                                        "фрагмент в публичном ролике для незнакомых людей?"}]
    for k, (_, jpg) in enumerate(frames):
        content.append({"type": "text", "text": f"Кадр {k}"})
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(jpg).decode()}})
    v = llm.ask(ClipVerdict, system="Ты фоторедактор. Строго соблюдай приватность: при сомнении — не подходит.",
                user=content, model=settings.vision_model, effort="low")
    k = min(max(v.start_frame, 0), len(frames) - 1)
    return v.ok, frames[k][0]


def pick_clips(limit: int = 2, days: int = 30) -> list[dict]:
    """До `limit` проверенных фрагментов из свежих отчётов: [{"path": webm, "start": сек}]."""
    if not drive.enabled():
        return []
    try:
        events = drive.recent_events(days=days, include_used=True)
    except Exception as exc:
        log.info("Видео из отчётов: Drive недоступен: %s", exc)
        return []
    out = []
    for ev in events:
        for vf in ev.video_files:
            if len(out) >= limit:
                return out
            key = f"clip:{vf['id']}"
            cached = db.kv_get(key)
            if cached and not json.loads(cached).get("ok"):
                continue
            if vf.get("size") and vf["size"] > 120 * 1024 * 1024:
                continue
            try:
                src = drive.download_video(vf["id"])
                if not src:
                    continue
                if cached:
                    ok, start = True, json.loads(cached)["start"]
                else:
                    ok, start = check(src)
                    db.kv_set(key, json.dumps({"ok": ok, "start": start}))
                if ok:
                    out.append({"path": str(prepare(src, start, vf["id"])), "start": start})
            except Exception as exc:
                log.info("Видео %s пропущено: %s", vf["name"], exc)
    return out


def prepare(src: Path, start: float, key: str) -> Path:
    """Фрагмент в вертикаль 1080×1920 без звука, VP8/WebM — встроенный Chromium его точно играет."""
    out_dir = OUTPUT_DIR / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{key}.webm"
    if not out.exists():
        subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(src), "-t", f"{CLIP_SECONDS:.1f}",
                        "-an", "-vf", "scale=-2:1920,crop=1080:1920,fps=24", "-c:v", "libvpx", "-b:v", "5M",
                        "-auto-alt-ref", "0", str(out)], check=True)
    return out
