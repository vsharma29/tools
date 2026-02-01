"""Abstract base classes for STT and TTS providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator


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
    """Text-to-Speech provider interface."""

    @abstractmethod
    async def synthesize(self, text: str) -> bytes:
        """Return complete audio bytes for the given text."""
        ...

    @abstractmethod
    async def synthesize_stream(self, text: str) -> AsyncIterator[bytes]:
        """Yield audio chunks as they are generated — for real-time playback."""
        ...
