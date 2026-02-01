"""OpenAI Whisper STT adapter — batch transcription fallback."""

from __future__ import annotations

import io
from typing import AsyncIterator

from openai import AsyncOpenAI

from .base import STTProvider


class WhisperSTT(STTProvider):
    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Whisper doesn't support true streaming — buffer and transcribe in chunks."""
        buffer = bytearray()
        CHUNK_THRESHOLD = 32_000  # ~1 second of 16kHz 16-bit mono

        async for chunk in audio_chunks:
            buffer.extend(chunk)
            if len(buffer) >= CHUNK_THRESHOLD:
                text = await self.transcribe_bytes(bytes(buffer))
                buffer.clear()
                if text.strip():
                    yield text

        if buffer:
            text = await self.transcribe_bytes(bytes(buffer))
            if text.strip():
                yield text

    async def transcribe_bytes(self, audio: bytes, mime_type: str = "audio/wav") -> str:
        audio_file = io.BytesIO(audio)
        audio_file.name = "audio.wav"
        response = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en",
        )
        return response.text
