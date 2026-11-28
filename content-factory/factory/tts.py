"""Озвучка через ElevenLabs с посимвольными таймкодами (для синхронизации сцен и субтитров)."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

import httpx

from .settings import env


class TTSError(RuntimeError):
    pass


def enabled() -> bool:
    return bool(env("ELEVENLABS_API_KEY") and env("ELEVENLABS_VOICE_ID"))


@dataclass
class Speech:
    audio_path: Path
    starts: list[float]        # время начала каждого символа исходного текста, сек
    duration: float            # конец последнего символа, сек

    def time_at(self, char_index: int) -> float:
        if not self.starts:
            return 0.0
        return self.starts[min(max(char_index, 0), len(self.starts) - 1)]


def synthesize(text: str, out_path: Path, *, speed: float | None = None, style: float | None = None,
               stability: float | None = None, model: str | None = None,
               similarity: float | None = None) -> Speech:
    voice = env("ELEVENLABS_VOICE_ID")
    resp = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": model or env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            "voice_settings": {
                "stability": stability if stability is not None else float(env("ELEVENLABS_STABILITY", "0.5")),
                "similarity_boost": similarity if similarity is not None else float(env("ELEVENLABS_SIMILARITY", "0.75")),
                "style": style if style is not None else float(env("ELEVENLABS_STYLE", "0.0")),
                "speed": speed if speed is not None else float(env("ELEVENLABS_SPEED", "1.0")),
                "use_speaker_boost": True,
            },
        },
        timeout=180,
    )
    if resp.status_code >= 400:
        raise TTSError(f"ElevenLabs {resp.status_code}: {resp.text[:300]}")
    body = resp.json()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(body["audio_base64"]))
    al = body.get("alignment") or body.get("normalized_alignment") or {}
    starts = list(al.get("character_start_times_seconds") or [])
    ends = list(al.get("character_end_times_seconds") or [])
    if len(starts) != len(text) and starts:
        # длина выравнивания не совпала с текстом — растягиваем пропорционально
        n = len(starts)
        starts = [starts[min(int(i * n / len(text)), n - 1)] for i in range(len(text))]
    duration = max(ends) if ends else 0.0
    if not duration:
        raise TTSError("ElevenLabs не вернул таймкоды")
    return Speech(out_path, starts, duration)


# Варианты голоса для выбора владельцем (команда voicetest): темп, мягкость, эмоциональность.
VOICE_VARIANTS = [
    ("1", "Сейчас в роликах: v2, темп 1.08, эмоции средние", dict(model="eleven_multilingual_v2", speed=1.08, style=0.55, stability=0.3)),
    ("2", "v2 быстрее и теплее: темп 1.15, больше выразительности", dict(model="eleven_multilingual_v2", speed=1.15, style=0.75, stability=0.35, similarity=0.8)),
    ("3", "v2 мягко и живо: темп 1.12, ровнее, мягче подача", dict(model="eleven_multilingual_v2", speed=1.12, style=0.4, stability=0.5, similarity=0.85)),
    ("4", "v3 естественный: новая модель, живые интонации", dict(model="eleven_v3", stability=0.5, tags="[warmly] ")),
    ("5", "v3 эмоциональный: новая модель, максимум эмоций", dict(model="eleven_v3", stability=0.0, tags="[warmly] [excited] ")),
]


def voicetest(text: str, out_dir: Path) -> list[tuple[str, str, Path]]:
    """Пять вариантов одного фрагмента. Ошибка одного варианта (например, модель недоступна) не мешает остальным."""
    out = []
    for key, title, opts in VOICE_VARIANTS:
        opts = dict(opts)
        tags = opts.pop("tags", "")
        path = out_dir / f"voice-{key}.mp3"
        try:
            synthesize(tags + text, path, **opts)
            out.append((key, title, path))
        except Exception as exc:
            out.append((key, f"{title} — не получилось: {str(exc)[:150]}", None))
    return out
