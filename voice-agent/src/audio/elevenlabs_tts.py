"""ElevenLabs TTS adapter."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

import httpx

from .base import TTSProvider


class ElevenLabsTTS(TTSProvider):
    BASE_URL = "https://api.elevenlabs.io/v1"

    def __init__(self, api_key: str, voice_id: str = ""):
        self._api_key = api_key
        self._voice_id = voice_id or "21m00Tcm4TlvDq8ikWAM"  # Rachel
        self._model = "eleven_turbo_v2_5"

    async def synthesize(self, text: str) -> bytes:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/text-to-speech/{self._voice_id}",
                headers={"xi-api-key": self._api_key},
                json={
                    "text": text,
                    "model_id": self._model,
                    "output_format": "pcm_24000",
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return resp.content

    async def synthesize_stream(
        self, text: str, cancel_event: Optional[asyncio.Event] = None
    ) -> AsyncIterator[bytes]:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/text-to-speech/{self._voice_id}/stream",
                headers={"xi-api-key": self._api_key},
                json={
                    "text": text,
                    "model_id": self._model,
                    "output_format": "pcm_24000",
                },
                timeout=15.0,
            ) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes(chunk_size=4096):
                    if cancel_event and cancel_event.is_set():
                        return
                    yield chunk
