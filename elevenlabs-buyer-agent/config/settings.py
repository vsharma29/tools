"""Centralised configuration from environment variables."""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configuration loaded from environment / .env file."""

    # --- ElevenLabs API ---
    elevenlabs_api_key: str = ""

    # --- Voice Configuration ---
    elevenlabs_voice_id: str = ""  # Empty = use default voice
    elevenlabs_tts_model: str = "eleven_turbo_v2"  # Must use v2 (not v2_5) for English agents
    elevenlabs_voice_stability: float = Field(0.5, ge=0, le=1)
    elevenlabs_similarity_boost: float = Field(0.75, ge=0, le=1)
    elevenlabs_speech_speed: float = Field(1.0, ge=0.7, le=1.3)

    # --- LLM Configuration ---
    elevenlabs_llm_model: str = "gpt-4o-mini"  # Fast and cost-effective for conversational AI
    elevenlabs_llm_temperature: float = Field(0.3, ge=0, le=1)

    # --- Twilio Integration ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # --- Webhook Configuration ---
    webhook_url: str = ""
    webhook_secret: str = ""

    # --- S3 Storage ---
    s3_bucket_name: str = "buyer-briefs"
    s3_region: str = "ap-southeast-2"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # --- Buyer Brief Agent Settings ---
    agency_name: str = "Your Buyer's Agency"
    max_conversation_duration: int = 900
    enable_recording: bool = True
    retention_days: int = 90

    # --- Inbound Call Triggers ---
    # Comma-separated list of phone numbers that can trigger the buyer brief agent
    # Format: +61412345678,+61498765432 (E.164 format)
    allowed_inbound_numbers: str = ""
    # If True, any inbound call triggers the agent. If False, only allowed numbers.
    allow_all_inbound: bool = True

    # --- Sales Associate Agent Settings ---
    sales_agent_id: str = ""  # ElevenLabs agent ID for sales associate
    sales_voice_id: str = ""  # Different voice for sales associate
    sales_llm_model: str = "claude-3-5-sonnet"

    # --- CRM Integration ---
    crm_api_url: str = ""
    crm_api_key: str = ""
    crm_type: str = ""  # salesforce, hubspot, zoho, custom

    # --- Lead Source Configuration ---
    leads_csv_path: str = ""  # Path to CSV file with leads
    leads_webhook_url: str = ""  # Webhook to receive new leads

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def has_twilio(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token)

    @property
    def has_webhook(self) -> bool:
        return bool(self.webhook_url)

    @property
    def has_s3(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key)

    @property
    def allowed_inbound_list(self) -> list[str]:
        """Parse allowed inbound numbers into a list."""
        if not self.allowed_inbound_numbers:
            return []
        return [n.strip() for n in self.allowed_inbound_numbers.split(",") if n.strip()]

    def is_inbound_allowed(self, phone_number: str) -> bool:
        """Check if an inbound phone number is allowed to trigger the agent."""
        if self.allow_all_inbound:
            return True
        return phone_number in self.allowed_inbound_list


@lru_cache
def get_settings() -> Settings:
    return Settings()
