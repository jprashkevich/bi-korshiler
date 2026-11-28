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
               stability: float | None = None) -> Speech:
    voice = env("ELEVENLABS_VOICE_ID")
    resp = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            "voice_settings": {
                "stability": stability if stability is not None else float(env("ELEVENLABS_STABILITY", "0.5")),
                "similarity_boost": float(env("ELEVENLABS_SIMILARITY", "0.75")),
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
