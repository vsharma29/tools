"""Cartesia TTS adapter — ultra-low-latency streaming synthesis."""

from __future__ import annotations

from typing import AsyncIterator

import cartesia

from .base import TTSProvider


class CartesiaTTS(TTSProvider):
    def __init__(self, api_key: str, voice_id: str = ""):
        self._client = cartesia.AsyncCartesia(api_key=api_key)
        # Default to a warm professional Australian-sounding voice
        self._voice_id = voice_id or "a0e99841-438c-4a64-b679-ae501e7d6091"
        self._model_id = "sonic-english"
        self._output_format = {
            "container": "raw",
            "encoding": "pcm_s16le",
            "sample_rate": 24000,
        }

    async def synthesize(self, text: str) -> bytes:
        chunks: list[bytes] = []
        async for chunk in self.synthesize_stream(text):
            chunks.append(chunk)
        return b"".join(chunks)

    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        async for output in self._client.tts.sse(
            model_id=self._model_id,
            transcript=text,
            voice_id=self._voice_id,
            output_format=self._output_format,
            stream=True,
        ):
            if hasattr(output, "audio") and output.audio:
                yield output.audio
