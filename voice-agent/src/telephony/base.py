"""Abstract telephony provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional


@dataclass
class CallSession:
    call_sid: str
    from_number: str
    to_number: str
    direction: str  # "inbound" | "outbound"
    status: str = "initiated"


class TelephonyProvider(ABC):
    """Interface for telephony providers (Twilio, Vonage, Telnyx, etc.)."""

    @abstractmethod
    async def initiate_call(
        self,
        to_number: str,
        webhook_base_url: str,
    ) -> CallSession:
        """Place an outbound call. Returns call session info."""
        ...

    @abstractmethod
    async def handle_incoming_webhook(self, request_data: dict) -> CallSession:
        """Parse an incoming call webhook and return session info."""
        ...

    @abstractmethod
    async def stream_audio_to_call(
        self, call_sid: str, audio_chunks: AsyncIterator[bytes]
    ) -> None:
        """Send audio chunks to an active call."""
        ...

    @abstractmethod
    async def get_audio_stream(self, call_sid: str) -> AsyncIterator[bytes]:
        """Receive audio chunks from an active call."""
        ...

    @abstractmethod
    async def end_call(self, call_sid: str) -> None:
        """Hang up a call."""
        ...

    @abstractmethod
    async def transfer_call(self, call_sid: str, to_number: str) -> None:
        """Transfer a call to a human agent."""
        ...
