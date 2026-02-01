"""Factory to build STT/TTS providers from config."""

from __future__ import annotations

from config.settings import Settings
from .base import STTProvider, TTSProvider


def create_stt(settings: Settings) -> STTProvider:
    provider = settings.audio_stt_provider.lower()
    if provider == "deepgram":
        from .deepgram_stt import DeepgramSTT
        return DeepgramSTT(api_key=settings.deepgram_api_key)
    elif provider == "whisper":
        from .whisper_stt import WhisperSTT
        return WhisperSTT(api_key=settings.openai_api_key)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")


def create_tts(settings: Settings) -> TTSProvider:
    provider = settings.audio_tts_provider.lower()
    if provider == "cartesia":
        from .cartesia_tts import CartesiaTTS
        return CartesiaTTS(api_key=settings.cartesia_api_key, voice_id=settings.tts_voice_id)
    elif provider == "openai":
        from .openai_tts import OpenAITTS
        return OpenAITTS(api_key=settings.openai_api_key, voice=settings.tts_voice_id or "nova")
    elif provider == "elevenlabs":
        from .elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS(api_key=settings.elevenlabs_api_key, voice_id=settings.tts_voice_id)
    else:
        raise ValueError(f"Unknown TTS provider: {provider}")
