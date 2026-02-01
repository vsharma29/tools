"""Centralised configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All config lives here — reads from env / .env automatically."""

    # --- Anthropic / Claude ---
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # --- Audio STT ---
    audio_stt_provider: str = Field("deepgram", description="deepgram | whisper")
    deepgram_api_key: str = ""
    openai_api_key: str = ""

    # --- Audio TTS ---
    audio_tts_provider: str = Field("cartesia", description="cartesia | openai | elevenlabs")
    cartesia_api_key: str = ""
    elevenlabs_api_key: str = ""
    tts_voice_id: str = ""  # provider-specific voice identifier

    # --- Telephony ---
    telephony_provider: str = Field("twilio", description="twilio | vonage | telnyx")
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # --- Output ---
    output_mode: str = Field("both", description="s3 | webhook | both")
    s3_bucket_name: str = "buyer-briefs"
    s3_region: str = "ap-southeast-2"
    webhook_url: str = ""

    # --- General ---
    log_level: str = "INFO"
    environment: str = "development"
    max_interview_turns: int = 40
    max_call_duration_seconds: int = 900  # 15 min safety cap

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
