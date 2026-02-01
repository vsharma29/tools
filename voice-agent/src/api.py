"""FastAPI application — HTTP + WebSocket endpoints for the voice agent.

Designed to run:
- Locally with `uvicorn src.api:app`
- On AWS Lambda via Mangum adapter (see handler.py)
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from config.settings import get_settings
from src.agent.voice_pipeline import VoicePipeline
from src.telephony.factory import create_telephony

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

pipeline: Optional[VoicePipeline] = None
telephony = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline, telephony
    settings = get_settings()
    pipeline = VoicePipeline(settings)
    try:
        telephony = create_telephony(settings)
    except Exception:
        logger.warning("telephony_not_configured", msg="Telephony disabled — set provider keys")
    yield


app = FastAPI(
    title="Buyer Voice Agent",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    prospect_name: Optional[str] = None
    prospect_phone: Optional[str] = None
    agency_name: str = "Your Buyer's Agency"
    is_outbound: bool = True


class TextTurnRequest(BaseModel):
    session_id: str
    text: str


class OutboundCallRequest(BaseModel):
    to_number: str
    prospect_name: Optional[str] = None
    agency_name: str = "Your Buyer's Agency"


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/sessions")
async def create_session(req: StartSessionRequest):
    session = pipeline.create_session(
        prospect_name=req.prospect_name,
        prospect_phone=req.prospect_phone,
        agency_name=req.agency_name,
        is_outbound=req.is_outbound,
    )
    greeting = pipeline.get_greeting_text(session.session_id)
    return {
        "session_id": session.session_id,
        "greeting": greeting,
    }


@app.post("/api/turns/text")
async def text_turn(req: TextTurnRequest):
    response = await pipeline.process_text_turn(req.session_id, req.text)
    session = pipeline._sessions.get(req.session_id)
    return {
        "response": response,
        "is_complete": session.is_complete if session else False,
        "brief": (
            json.loads(session.brief.model_dump_json(exclude_none=True))
            if session and session.brief
            else None
        ),
    }


@app.get("/api/sessions/{session_id}/metrics")
async def get_metrics(session_id: str):
    return pipeline.get_metrics(session_id)


@app.post("/api/calls/outbound")
async def initiate_outbound_call(req: OutboundCallRequest):
    if not telephony:
        return JSONResponse(status_code=503, content={"error": "Telephony not configured"})
    settings = get_settings()
    webhook_base = f"https://{settings.environment}.example.com"  # Set via env in production
    call_session = await telephony.initiate_call(req.to_number, webhook_base)
    return {"call_sid": call_session.call_sid, "status": call_session.status}


# ---------------------------------------------------------------------------
# Twilio webhook endpoints
# ---------------------------------------------------------------------------

@app.post("/api/telephony/twilio/incoming")
async def twilio_incoming(request: Request):
    """Handle incoming Twilio call — return TwiML to start media stream."""
    if not telephony:
        return PlainTextResponse("<Response><Say>Service unavailable</Say></Response>")
    form = await request.form()
    settings = get_settings()
    webhook_base = str(request.base_url).rstrip("/")
    twiml = telephony.generate_incoming_twiml(webhook_base)
    return PlainTextResponse(twiml, media_type="text/xml")


@app.post("/api/telephony/twilio/status")
async def twilio_status(request: Request):
    form = await request.form()
    logger.info("twilio_status", data=dict(form))
    return {"ok": True}


# ---------------------------------------------------------------------------
# WebSocket: text mode (for testing / web clients)
# ---------------------------------------------------------------------------

@app.websocket("/ws/text/{session_id}")
async def ws_text(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await pipeline.process_text_turn(session_id, data)
            session = pipeline._sessions.get(session_id)
            await websocket.send_json({
                "response": response,
                "is_complete": session.is_complete if session else False,
            })
            if session and session.is_complete:
                break
    except WebSocketDisconnect:
        logger.info("ws_text_disconnected", session=session_id)


# ---------------------------------------------------------------------------
# WebSocket: Twilio Media Stream (bidirectional audio)
# ---------------------------------------------------------------------------

@app.websocket("/api/telephony/twilio/media-stream")
async def twilio_media_stream(websocket: WebSocket):
    """Handle Twilio Media Stream WebSocket for real-time voice.

    Protocol:
    - Twilio sends JSON messages with base64-encoded mulaw audio
    - We decode, run through pipeline, and send back audio
    """
    await websocket.accept()
    stream_sid = None
    session_id = None
    audio_buffer = bytearray()
    BUFFER_THRESHOLD = 16_000  # ~1 second of 8kHz mulaw

    try:
        while True:
            message = await websocket.receive_text()
            data = json.loads(message)
            event = data.get("event")

            if event == "connected":
                logger.info("twilio_stream_connected")

            elif event == "start":
                stream_sid = data["start"]["streamSid"]
                # Create a new interview session for this call
                session = pipeline.create_session(is_outbound=False)
                session_id = session.session_id
                logger.info("twilio_stream_started", stream_sid=stream_sid, session=session_id)

                # Send greeting audio
                greeting_text = pipeline.get_greeting_text(session_id)
                greeting_audio = await pipeline._tts.synthesize(greeting_text)
                from src.telephony.twilio_provider import TwilioProvider
                msg = TwilioProvider.encode_media_message(greeting_audio, stream_sid)
                await websocket.send_text(msg)

            elif event == "media" and session_id:
                from src.telephony.twilio_provider import TwilioProvider
                payload = data["media"]["payload"]
                audio_bytes = TwilioProvider.decode_media_payload(payload)
                audio_buffer.extend(audio_bytes)

                if len(audio_buffer) >= BUFFER_THRESHOLD:
                    chunk = bytes(audio_buffer)
                    audio_buffer.clear()

                    # Process through pipeline
                    async for response_audio in pipeline.process_audio_turn(
                        session_id, chunk
                    ):
                        msg = TwilioProvider.encode_media_message(response_audio, stream_sid)
                        await websocket.send_text(msg)

            elif event == "stop":
                logger.info("twilio_stream_stopped", stream_sid=stream_sid)
                break

    except WebSocketDisconnect:
        logger.info("twilio_stream_disconnected", stream_sid=stream_sid)
