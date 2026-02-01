"""Deepgram STT adapter — optimised for real-time streaming transcription."""

from __future__ import annotations

from typing import AsyncIterator

import structlog
from deepgram import DeepgramClient, LiveOptions, PrerecordedOptions

from .base import STTProvider

logger = structlog.get_logger()


class DeepgramSTT(STTProvider):
    def __init__(self, api_key: str):
        self._client = DeepgramClient(api_key)

    async def transcribe_stream(self, audio_chunks: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Open a live WebSocket connection for streaming STT.

        Yields interim + final transcript strings as they arrive.
        """
        connection = self._client.listen.asyncwebsocket.v("1")

        options = LiveOptions(
            model="nova-2",
            language="en-AU",
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1200,
            vad_events=True,
            endpointing=300,
            encoding="linear16",
            sample_rate=16000,
            channels=1,
        )

        transcript_buffer: list[str] = []

        async def on_transcript(_, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if sentence.strip():
                transcript_buffer.append(sentence)

        connection.on("Results", on_transcript)

        await connection.start(options)

        async for chunk in audio_chunks:
            await connection.send(chunk)
            while transcript_buffer:
                yield transcript_buffer.pop(0)

        await connection.finish()

        # Flush remaining
        while transcript_buffer:
            yield transcript_buffer.pop(0)

    async def transcribe_bytes(self, audio: bytes, mime_type: str = "audio/wav") -> str:
        options = PrerecordedOptions(
            model="nova-2",
            language="en-AU",
            smart_format=True,
        )
        source = {"buffer": audio, "mimetype": mime_type}
        response = await self._client.listen.asyncrest.v("1").transcribe_file(source, options)
        return response.results.channels[0].alternatives[0].transcript
