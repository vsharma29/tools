"""Abstract base classes for STT and TTS providers."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class STTProvider(ABC):
    """Speech-to-Text provider interface."""

    @abstractmethod
    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Yield partial transcripts as audio streams in."""
        ...

    @abstractmethod
    async def transcribe_bytes(self, audio: bytes, mime_type: str = "audio/wav") -> str:
        """Transcribe a complete audio buffer."""
        ...


class TTSProvider(ABC):
    """Text-to-Speech provider interface.

    All streaming methods accept an optional `cancel_event` — an asyncio.Event
    that, when set, causes the generator to stop yielding audio immediately.
    This is the mechanism used for barge-in interruption.
    """

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return complete audio bytes for the given text."""
        ...

    @abstractmethod
    async def synthesize_stream(
        self, text: str, cancel_event: Optional[asyncio.Event] = None
    ) -> AsyncIterator[bytes]:
        """Yield audio chunks as they are generated.

        If cancel_event is set during generation, stop yielding immediately.
        """
        ...
