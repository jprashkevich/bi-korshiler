"""Фоновая музыка для Reels через ElevenLabs Music (инструментал под длину ролика).

Почему своя дорожка, а не музыка из библиотеки Instagram: через API библиотеку не добавить, а ролик
должен публиковаться сам. Eleven Music на платных тарифах разрешена для коммерческих соцсетей без
указания авторства (music-terms ElevenLabs). Не получилось сгенерировать — ролик выходит без музыки,
это лучше, чем не выйти совсем.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from .settings import env

log = logging.getLogger(__name__)

PROMPTS = {
    "warm": "Warm gentle acoustic background music, soft guitar and light piano, cozy neighbourly mood, "
            "steady calm rhythm, no vocals, suitable under a voiceover",
    "upbeat": "Light upbeat background music, playful plucks and soft claps, positive practical mood, "
              "medium tempo, no vocals, suitable under a voiceover",
    "mystery": "Curious minimal background music, soft pulsing synth and light percussion, intriguing but friendly, "
               "no vocals, suitable under a voiceover",
}


def compose(mood: str, seconds: float, out: Path) -> Path | None:
    if not env("ELEVENLABS_API_KEY") or env("REELS_MUSIC", "1") == "0":
        return None
    try:
        resp = httpx.post("https://api.elevenlabs.io/v1/music",
                          params={"output_format": "mp3_44100_128"},
                          headers={"xi-api-key": env("ELEVENLABS_API_KEY"), "Content-Type": "application/json"},
                          json={"prompt": PROMPTS.get(mood, PROMPTS["warm"]),
                                "music_length_ms": int(min(max(seconds, 5), 120) * 1000) + 1000,
                                "model_id": env("ELEVENLABS_MUSIC_MODEL", "music_v2"),
                                "force_instrumental": True},
                          timeout=300)
    except httpx.HTTPError as exc:
        log.warning("Музыка для Reels: сеть %s", type(exc).__name__)
        return None
    if resp.status_code >= 400 or not resp.content:
        log.warning("Музыка для Reels не сгенерирована: %s %s", resp.status_code, resp.text[:200])
        return None
    out.write_bytes(resp.content)
    return out
