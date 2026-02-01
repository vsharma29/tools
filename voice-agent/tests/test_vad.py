"""Tests for Voice Activity Detection and barge-in manager."""

import asyncio
import struct

import pytest

from src.audio.vad import (
    BargeInManager,
    VADConfig,
    VADResult,
    VADState,
    VoiceActivityDetector,
)


def _make_pcm_frame(amplitude: int, n_samples: int = 320) -> bytes:
    """Generate a PCM16LE frame with constant amplitude."""
    return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))


def _silence_frame(n_samples: int = 320) -> bytes:
    return _make_pcm_frame(0, n_samples)


def _speech_frame(amplitude: int = 5000, n_samples: int = 320) -> bytes:
    return _make_pcm_frame(amplitude, n_samples)


class TestVoiceActivityDetector:
    def test_initial_state_is_silence(self):
        vad = VoiceActivityDetector(VADConfig(energy_threshold=100))
        assert vad.state == VADState.SILENCE

    def test_calibration_from_silence(self):
        config = VADConfig(energy_threshold=0, calibration_frames=5)
        vad = VoiceActivityDetector(config)

        # Feed silent frames for calibration
        for _ in range(5):
            result = vad.process_frame(_silence_frame())
        # Threshold should now be set
        assert vad._threshold > 0

    def test_detects_speech_after_calibration(self):
        config = VADConfig(
            energy_threshold=0,
            calibration_frames=5,
            speech_min_frames=2,
        )
        vad = VoiceActivityDetector(config)

        # Calibrate
        for _ in range(5):
            vad.process_frame(_silence_frame())

        # Send speech frames
        for _ in range(3):
            result = vad.process_frame(_speech_frame())

        assert result.state == VADState.SPEECH

    def test_returns_to_silence(self):
        config = VADConfig(
            energy_threshold=100,
            speech_min_frames=1,
            silence_min_frames=2,
        )
        vad = VoiceActivityDetector(config)

        # Go to speech
        vad.process_frame(_speech_frame())
        assert vad.state == VADState.SPEECH

        # Return to silence
        for _ in range(3):
            result = vad.process_frame(_silence_frame())
        assert result.state == VADState.SILENCE

    def test_no_barge_in_when_not_playing(self):
        config = VADConfig(energy_threshold=100, speech_min_frames=1)
        vad = VoiceActivityDetector(config)
        vad.is_playing = False

        result = vad.process_frame(_speech_frame())
        assert result.is_barge_in is False

    def test_barge_in_when_playing(self):
        config = VADConfig(energy_threshold=100, speech_min_frames=1)
        vad = VoiceActivityDetector(config)
        vad.is_playing = True

        result = vad.process_frame(_speech_frame())
        assert result.is_barge_in is True

    def test_barge_in_fires_only_once(self):
        config = VADConfig(energy_threshold=100, speech_min_frames=1)
        vad = VoiceActivityDetector(config)
        vad.is_playing = True

        r1 = vad.process_frame(_speech_frame())
        r2 = vad.process_frame(_speech_frame())
        assert r1.is_barge_in is True
        assert r2.is_barge_in is False  # already in SPEECH state

    def test_speech_min_frames_prevents_noise_spikes(self):
        config = VADConfig(energy_threshold=100, speech_min_frames=3)
        vad = VoiceActivityDetector(config)
        vad.is_playing = True

        # Single spike should not trigger
        r1 = vad.process_frame(_speech_frame())
        assert r1.is_barge_in is False

        # But 3 consecutive should
        r2 = vad.process_frame(_speech_frame())
        r3 = vad.process_frame(_speech_frame())
        assert r3.is_barge_in is True

    def test_reset(self):
        config = VADConfig(energy_threshold=100, speech_min_frames=1)
        vad = VoiceActivityDetector(config)
        vad.is_playing = True

        vad.process_frame(_speech_frame())
        assert vad.state == VADState.SPEECH

        vad.reset()
        assert vad.state == VADState.SILENCE


class TestBargeInManager:
    def test_cancel_event_set_on_barge_in(self):
        mgr = BargeInManager(VADConfig(energy_threshold=100, speech_min_frames=1))
        mgr.start_playback()

        result = mgr.feed_audio(_speech_frame())
        assert result.is_barge_in is True
        assert mgr.cancel_event.is_set()
        assert mgr.was_interrupted is True

    def test_audio_buffered_after_barge_in(self):
        mgr = BargeInManager(VADConfig(energy_threshold=100, speech_min_frames=1))
        mgr.start_playback()

        frame1 = _speech_frame(5000)
        frame2 = _speech_frame(6000)
        mgr.feed_audio(frame1)
        mgr.feed_audio(frame2)

        buffered = mgr.buffered_audio
        assert len(buffered) == len(frame1) + len(frame2)

    def test_handle_barge_in_returns_and_clears_buffer(self):
        mgr = BargeInManager(VADConfig(energy_threshold=100, speech_min_frames=1))
        mgr.start_playback()

        mgr.feed_audio(_speech_frame())
        mgr.feed_audio(_speech_frame())

        audio = mgr.handle_barge_in()
        assert len(audio) > 0
        assert mgr.was_interrupted is False
        assert mgr.buffered_audio == b""

    def test_no_barge_in_during_silence(self):
        mgr = BargeInManager(VADConfig(energy_threshold=100, speech_min_frames=1))
        mgr.start_playback()

        result = mgr.feed_audio(_silence_frame())
        assert result.is_barge_in is False
        assert not mgr.cancel_event.is_set()

    def test_stop_playback_clears_playing_state(self):
        mgr = BargeInManager(VADConfig(energy_threshold=100, speech_min_frames=1))
        mgr.start_playback()
        mgr.stop_playback()

        # Speech after playback stops should not trigger barge-in
        result = mgr.feed_audio(_speech_frame())
        assert result.is_barge_in is False
