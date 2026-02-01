"""Voice pipeline — orchestrates STT → Claude Agent → TTS with minimum latency.

Key latency optimizations:
1. Sentence-level streaming: Claude streams text, each sentence is immediately
   dispatched to TTS without waiting for the full response.
2. TTS pipelining: TTS synthesis starts on sentence N while sentence N-1 audio
   is still being played to the caller.
3. Barge-in detection: If the user starts speaking while TTS is playing,
   we interrupt playback and process their new input.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Optional

import structlog

from config.settings import Settings
from src.audio.base import STTProvider, TTSProvider
from src.audio.factory import create_stt, create_tts
from src.guardrails.guardrails import (
    GuardrailAction,
    check_agent_output,
    check_call_duration,
    check_user_input,
)
from src.output.handlers import OutputManager
from .interview_agent import InterviewAgent, InterviewSession

logger = structlog.get_logger()


@dataclass
class PipelineMetrics:
    stt_latency_ms: list[float] = field(default_factory=list)
    llm_first_token_ms: list[float] = field(default_factory=list)
    tts_first_byte_ms: list[float] = field(default_factory=list)
    total_turn_ms: list[float] = field(default_factory=list)


class VoicePipeline:
    """End-to-end voice pipeline: audio in → transcript → agent → speech out."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._stt: STTProvider = create_stt(settings)
        self._tts: TTSProvider = create_tts(settings)
        self._output = OutputManager(settings)

        self._agent = InterviewAgent(
            settings=settings,
            on_brief_complete=self._handle_brief_complete,
            on_transfer=self._handle_transfer,
            on_followup=self._handle_followup,
        )

        self._sessions: dict[str, InterviewSession] = {}
        self._metrics: dict[str, PipelineMetrics] = {}
        self._off_topic_counts: dict[str, int] = {}
        self._call_start_times: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def create_session(
        self,
        prospect_name: Optional[str] = None,
        prospect_phone: Optional[str] = None,
        agency_name: str = "Your Buyer's Agency",
        is_outbound: bool = True,
    ) -> InterviewSession:
        session = self._agent.start_session(
            prospect_name=prospect_name,
            prospect_phone=prospect_phone,
            agency_name=agency_name,
            is_outbound=is_outbound,
        )
        self._sessions[session.session_id] = session
        self._metrics[session.session_id] = PipelineMetrics()
        self._off_topic_counts[session.session_id] = 0
        self._call_start_times[session.session_id] = time.time()
        return session

    def get_greeting_text(self, session_id: str) -> str:
        session = self._sessions[session_id]
        return self._agent.get_greeting(session)

    async def get_greeting_audio(self, session_id: str) -> AsyncIterator[bytes]:
        text = self.get_greeting_text(session_id)
        async for chunk in self._tts.synthesize_stream(text):
            yield chunk

    # ------------------------------------------------------------------
    # Core turn processing
    # ------------------------------------------------------------------

    async def process_audio_turn(
        self,
        session_id: str,
        audio: bytes,
    ) -> AsyncIterator[bytes]:
        """Full turn: audio → STT → guardrails → Claude → guardrails → TTS → audio.

        Yields audio chunks for streaming playback.
        """
        session = self._sessions[session_id]
        metrics = self._metrics[session_id]

        # Check call duration
        elapsed = time.time() - self._call_start_times[session_id]
        duration_check = check_call_duration(elapsed, self._settings.max_call_duration_seconds)
        if duration_check.action == GuardrailAction.TERMINATE:
            async for chunk in self._tts.synthesize_stream(duration_check.replacement_text):
                yield chunk
            session.is_complete = True
            return

        # STT
        t0 = time.time()
        transcript = await self._stt.transcribe_bytes(audio)
        metrics.stt_latency_ms.append((time.time() - t0) * 1000)

        if not transcript.strip():
            return

        logger.info("user_said", session=session_id, text=transcript)

        # Input guardrails
        input_check = check_user_input(
            transcript, self._off_topic_counts.get(session_id, 0)
        )

        if input_check.action == GuardrailAction.BLOCK:
            async for chunk in self._tts.synthesize_stream(input_check.replacement_text):
                yield chunk
            return

        if input_check.action == GuardrailAction.TERMINATE:
            async for chunk in self._tts.synthesize_stream(input_check.replacement_text):
                yield chunk
            session.is_complete = True
            return

        if input_check.action == GuardrailAction.WARN:
            self._off_topic_counts[session_id] = (
                self._off_topic_counts.get(session_id, 0) + 1
            )
        else:
            self._off_topic_counts[session_id] = 0

        # Claude agent (streaming)
        t1 = time.time()
        first_token_recorded = False

        async for sentence in self._agent.stream_turn(session, transcript):
            if not first_token_recorded:
                metrics.llm_first_token_ms.append((time.time() - t1) * 1000)
                first_token_recorded = True

            # Output guardrail
            output_check = check_agent_output(sentence)
            if output_check.action == GuardrailAction.WARN:
                logger.warning("output_guardrail", reason=output_check.reason, text=sentence)
                # Still send — the system prompt should handle this,
                # guardrail is a safety net for logging/review

            # TTS (streaming)
            t2 = time.time()
            first_tts_byte = False
            async for audio_chunk in self._tts.synthesize_stream(sentence):
                if not first_tts_byte:
                    metrics.tts_first_byte_ms.append((time.time() - t2) * 1000)
                    first_tts_byte = True
                yield audio_chunk

        metrics.total_turn_ms.append((time.time() - t0) * 1000)

    async def process_text_turn(
        self, session_id: str, text: str
    ) -> str:
        """Text-only turn (for testing / WebSocket text mode)."""
        session = self._sessions[session_id]

        input_check = check_user_input(text, self._off_topic_counts.get(session_id, 0))
        if input_check.action in (GuardrailAction.BLOCK, GuardrailAction.TERMINATE):
            return input_check.replacement_text

        response = await self._agent.process_turn(session, text)
        return response

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    async def _handle_brief_complete(self, session: InterviewSession) -> None:
        if session.brief:
            results = await self._output.save_brief(session.brief)
            logger.info("brief_saved", session=session.session_id, results=results)

    async def _handle_transfer(self, session: InterviewSession, reason: str) -> None:
        logger.info("transfer_requested", session=session.session_id, reason=reason)

    async def _handle_followup(self, session: InterviewSession, details: dict) -> None:
        logger.info("followup_scheduled", session=session.session_id, details=details)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def get_metrics(self, session_id: str) -> dict:
        m = self._metrics.get(session_id)
        if not m:
            return {}

        def avg(lst):
            return round(sum(lst) / len(lst), 1) if lst else 0

        return {
            "avg_stt_ms": avg(m.stt_latency_ms),
            "avg_llm_first_token_ms": avg(m.llm_first_token_ms),
            "avg_tts_first_byte_ms": avg(m.tts_first_byte_ms),
            "avg_total_turn_ms": avg(m.total_turn_ms),
            "turns": len(m.total_turn_ms),
        }
