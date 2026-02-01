"""Factory to build telephony providers from config."""

from __future__ import annotations

from config.settings import Settings
from .base import TelephonyProvider


def create_telephony(settings: Settings) -> TelephonyProvider:
    provider = settings.telephony_provider.lower()
    if provider == "twilio":
        from .twilio_provider import TwilioProvider
        return TwilioProvider(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            phone_number=settings.twilio_phone_number,
        )
    else:
        raise ValueError(
            f"Unknown telephony provider: {provider}. "
            f"Supported: twilio. Vonage/Telnyx adapters can be added following the same pattern."
        )
