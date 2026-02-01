"""Core interview agent built on the Anthropic SDK.

Uses streaming for minimum latency — each assistant chunk is sent to TTS
as soon as a sentence boundary is detected (sentence-level streaming).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Callable, Optional

import anthropic
import structlog

from config.settings import Settings
from src.schemas.buyer_brief import BuyerBrief
from .prompts import SYSTEM_PROMPT, OUTBOUND_GREETING, INBOUND_GREETING, WRAP_UP_PROMPT
from .tools import ALL_TOOLS

logger = structlog.get_logger()


@dataclass
class ConversationTurn:
    role: str  # "user" | "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class InterviewSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prospect_name: Optional[str] = None
    prospect_phone: Optional[str] = None
    agency_name: str = "Your Buyer's Agency"
    is_outbound: bool = True
    history: list[ConversationTurn] = field(default_factory=list)
    brief: Optional[BuyerBrief] = None
    is_complete: bool = False
    transfer_requested: bool = False
    followup_scheduled: bool = False
    turn_count: int = 0


class InterviewAgent:
    """Drives the buyer-brief interview using Claude with streaming responses."""

    def __init__(
        self,
        settings: Settings,
        on_brief_complete: Optional[Callable] = None,
        on_transfer: Optional[Callable] = None,
        on_followup: Optional[Callable] = None,
    ):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model
        self._max_turns = settings.max_interview_turns
        self._settings = settings

        # Callbacks
        self._on_brief_complete = on_brief_complete
        self._on_transfer = on_transfer
        self._on_followup = on_followup

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_session(
        self,
        prospect_name: Optional[str] = None,
        prospect_phone: Optional[str] = None,
        agency_name: str = "Your Buyer's Agency",
        is_outbound: bool = True,
    ) -> InterviewSession:
        session = InterviewSession(
            prospect_name=prospect_name,
            prospect_phone=prospect_phone,
            agency_name=agency_name,
            is_outbound=is_outbound,
        )
        return session

    def get_greeting(self, session: InterviewSession) -> str:
        if session.is_outbound and session.prospect_name:
            return OUTBOUND_GREETING.format(
                name=session.prospect_name, agency_name=session.agency_name
            )
        return INBOUND_GREETING.format(agency_name=session.agency_name)

    async def process_turn(
        self, session: InterviewSession, user_text: str
    ) -> str:
        """Process a single user turn and return the full assistant reply.

        For lower latency in production, use `stream_turn` instead.
        """
        result_parts: list[str] = []
        async for chunk in self.stream_turn(session, user_text):
            result_parts.append(chunk)
        return "".join(result_parts)

    async def stream_turn(
        self, session: InterviewSession, user_text: str
    ) -> AsyncIterator[str]:
        """Yields sentence-sized text chunks as Claude generates them.

        Each chunk can be immediately sent to TTS for minimum latency.
        """
        session.turn_count += 1
        session.history.append(ConversationTurn(role="user", content=user_text))

        if session.turn_count > self._max_turns and not session.is_complete:
            wrap = (
                "We've covered a lot — let me save what we have so far and one of our "
                "agents can follow up on any remaining details. Thanks so much for your time!"
            )
            session.history.append(ConversationTurn(role="assistant", content=wrap))
            session.is_complete = True
            yield wrap
            return

        messages = self._build_messages(session)

        # Stream from Claude
        full_text = ""
        sentence_buffer = ""

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=ALL_TOOLS,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        sentence_buffer += event.delta.text
                        full_text += event.delta.text

                        # Yield at sentence boundaries for TTS pipelining
                        while self._has_sentence_boundary(sentence_buffer):
                            sentence, sentence_buffer = self._split_sentence(sentence_buffer)
                            yield sentence

            # Yield remaining buffer
            if sentence_buffer.strip():
                yield sentence_buffer.strip()

        # Check for tool use in the final message
        final_message = await stream.get_final_message()
        for block in final_message.content:
            if block.type == "tool_use":
                await self._handle_tool_call(session, block.name, block.input)

        session.history.append(ConversationTurn(role="assistant", content=full_text))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(self, session: InterviewSession) -> list[dict]:
        return [{"role": t.role, "content": t.content} for t in session.history]

    def _has_sentence_boundary(self, text: str) -> bool:
        for delim in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
            if delim in text:
                return True
        return False

    def _split_sentence(self, text: str) -> tuple[str, str]:
        best_idx = -1
        for delim in (". ", "! ", "? ", ".\n", "!\n", "?\n"):
            idx = text.find(delim)
            if idx != -1 and (best_idx == -1 or idx < best_idx):
                best_idx = idx
                best_delim = delim
        if best_idx == -1:
            return text, ""
        cut = best_idx + len(best_delim)
        return text[:cut].strip(), text[cut:]

    async def _handle_tool_call(
        self, session: InterviewSession, tool_name: str, tool_input: dict
    ) -> None:
        logger.info("tool_call", tool=tool_name, session=session.session_id)

        if tool_name == "save_buyer_brief":
            brief_json = tool_input.get("brief_json", "{}")
            try:
                brief_data = json.loads(brief_json)
                session.brief = BuyerBrief(**brief_data)
                session.brief.brief_id = session.session_id
                session.is_complete = True
                if self._on_brief_complete:
                    await self._on_brief_complete(session)
            except Exception:
                logger.exception("failed_to_parse_brief", session=session.session_id)

        elif tool_name == "transfer_to_human":
            session.transfer_requested = True
            if self._on_transfer:
                await self._on_transfer(session, tool_input.get("reason", ""))

        elif tool_name == "schedule_followup":
            session.followup_scheduled = True
            if self._on_followup:
                await self._on_followup(session, tool_input)
