"""OpenAI TTS adapter."""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from .base import TTSProvider


class OpenAITTS(TTSProvider):
    def __init__(self, api_key: str, voice: str = "nova"):
        self._client = AsyncOpenAI(api_key=api_key)
        self._voice = voice

    async def synthesize(self, text: str) -> bytes:
        response = await self._client.audio.speech.create(
            model="tts-1",  # tts-1 for low latency, tts-1-hd for quality
            voice=self._voice,
            input=text,
            response_format="pcm",
            speed=1.0,
        )
        return response.content

    async def synthesize_stream(
        self, text: str, cancel_event: Optional[asyncio.Event] = None
    ) -> AsyncIterator[bytes]:
        async with self._client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=self._voice,
            input=text,
            response_format="pcm",
            speed=1.0,
        ) as response:
            async for chunk in response.iter_bytes(chunk_size=4096):
                if cancel_event and cancel_event.is_set():
                    return
                yield chunk
