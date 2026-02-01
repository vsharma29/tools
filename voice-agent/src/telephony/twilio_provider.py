"""Twilio telephony adapter.

Uses Twilio Media Streams (WebSocket) for real-time bidirectional audio,
which is the lowest-latency approach for voice agents.

## How to add Twilio to your deployment
1. Create a Twilio account and buy an Australian phone number (+61...).
2. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env.
3. Configure the Twilio number's Voice webhook to:
   POST https://<your-domain>/api/telephony/twilio/incoming
4. Configure a TwiML Bin or the /api/telephony/twilio/connect endpoint to
   return the <Connect><Stream> TwiML that opens a Media Stream WebSocket.
5. The WebSocket endpoint is: wss://<your-domain>/api/telephony/twilio/media-stream

See README.md for full setup instructions.
"""

from __future__ import annotations

import base64
import json
from typing import AsyncIterator

import structlog
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import Connect, VoiceResponse

from .base import CallSession, TelephonyProvider

logger = structlog.get_logger()


class TwilioProvider(TelephonyProvider):
    def __init__(self, account_sid: str, auth_token: str, phone_number: str):
        self._client = TwilioClient(account_sid, auth_token)
        self._phone_number = phone_number

    async def initiate_call(
        self, to_number: str, webhook_base_url: str
    ) -> CallSession:
        """Place an outbound call that connects to our media stream."""
        twiml = self._build_stream_twiml(webhook_base_url)

        call = self._client.calls.create(
            to=to_number,
            from_=self._phone_number,
            twiml=str(twiml),
            status_callback=f"{webhook_base_url}/api/telephony/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed"],
        )

        logger.info("outbound_call_initiated", call_sid=call.sid, to=to_number)
        return CallSession(
            call_sid=call.sid,
            from_number=self._phone_number,
            to_number=to_number,
            direction="outbound",
            status="initiated",
        )

    async def handle_incoming_webhook(self, request_data: dict) -> CallSession:
        return CallSession(
            call_sid=request_data.get("CallSid", ""),
            from_number=request_data.get("From", ""),
            to_number=request_data.get("To", ""),
            direction="inbound",
            status="ringing",
        )

    def generate_incoming_twiml(self, webhook_base_url: str) -> str:
        """Generate TwiML response for incoming calls."""
        twiml = self._build_stream_twiml(webhook_base_url)
        return str(twiml)

    async def stream_audio_to_call(
        self, call_sid: str, audio_chunks: AsyncIterator[bytes]
    ) -> None:
        # Audio is sent via the WebSocket Media Stream — see media_stream_handler
        raise NotImplementedError("Use WebSocket media stream handler directly")

    async def get_audio_stream(self, call_sid: str) -> AsyncIterator[bytes]:
        raise NotImplementedError("Use WebSocket media stream handler directly")

    async def end_call(self, call_sid: str) -> None:
        self._client.calls(call_sid).update(status="completed")
        logger.info("call_ended", call_sid=call_sid)

    async def transfer_call(self, call_sid: str, to_number: str) -> None:
        twiml = VoiceResponse()
        twiml.say("Please hold while I transfer you to one of our agents.")
        twiml.dial(to_number)
        self._client.calls(call_sid).update(twiml=str(twiml))
        logger.info("call_transferred", call_sid=call_sid, to=to_number)

    def _build_stream_twiml(self, webhook_base_url: str) -> VoiceResponse:
        ws_url = webhook_base_url.replace("https://", "wss://").replace("http://", "ws://")
        response = VoiceResponse()
        connect = Connect()
        connect.stream(url=f"{ws_url}/api/telephony/twilio/media-stream")
        response.append(connect)
        return response

    # ------------------------------------------------------------------
    # WebSocket media stream helpers
    # ------------------------------------------------------------------

    @staticmethod
    def decode_media_payload(payload: str) -> bytes:
        """Decode base64 mulaw audio from Twilio Media Stream."""
        return base64.b64decode(payload)

    @staticmethod
    def encode_media_message(audio_bytes: bytes, stream_sid: str) -> str:
        """Encode audio bytes into a Twilio Media Stream JSON message."""
        return json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": base64.b64encode(audio_bytes).decode("ascii"),
            },
        })

    @staticmethod
    def clear_audio_message(stream_sid: str) -> str:
        """Send a clear message to interrupt current audio playback."""
        return json.dumps({"event": "clear", "streamSid": stream_sid})
