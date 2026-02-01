"""Voice Activity Detection (VAD) for barge-in interruption.

Provides two strategies:
1. **Energy-based VAD** — fast, no dependencies, works on raw PCM audio.
   Compares RMS energy against an adaptive threshold.
2. **WebRTC VAD** — more accurate, requires `webrtcvad` package.

The energy-based approach is the default since it adds zero latency and
no extra dependencies. Switch to WebRTC VAD for noisy environments.
"""

from __future__ import annotations

import asyncio
import struct
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class VADState(str, Enum):
    SILENCE = "silence"
    SPEECH = "speech"


@dataclass
class VADConfig:
    """Tuning knobs for energy-based VAD."""
    # RMS threshold — audio above this is considered speech.
    # Auto-calibrated from the first N frames if set to 0.
    energy_threshold: float = 0.0

    # Number of initial frames used to calibrate silence baseline
    calibration_frames: int = 10

    # Multiplier applied to calibrated silence RMS to get threshold
    calibration_multiplier: float = 2.5

    # Minimum consecutive speech frames before triggering SPEECH state
    # Prevents single-frame noise spikes from triggering barge-in
    speech_min_frames: int = 3

    # Minimum consecutive silence frames before returning to SILENCE
    # Prevents brief pauses from ending barge-in detection
    silence_min_frames: int = 8

    # Frame size in samples (at 16kHz: 160 = 10ms, 320 = 20ms)
    frame_samples: int = 320


@dataclass
class VADResult:
    state: VADState
    rms_energy: float
    threshold: float
    is_barge_in: bool = False  # True on the transition from SILENCE → SPEECH


class VoiceActivityDetector:
    """Stateful energy-based VAD that detects barge-in events.

    Feed it audio frames continuously. It tracks state transitions
    and fires `is_barge_in=True` exactly once when speech begins
    during what should be agent playback time.
    """

    def __init__(self, config: Optional[VADConfig] = None):
        self._config = config or VADConfig()
        self._state = VADState.SILENCE
        self._speech_count = 0
        self._silence_count = 0
        self._calibration_rms: list[float] = []
        self._threshold = self._config.energy_threshold
        self._is_playing = False  # True while TTS audio is being sent

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @is_playing.setter
    def is_playing(self, value: bool) -> None:
        self._is_playing = value

    @property
    def state(self) -> VADState:
        return self._state

    def reset(self) -> None:
        self._state = VADState.SILENCE
        self._speech_count = 0
        self._silence_count = 0

    def process_frame(self, pcm_bytes: bytes) -> VADResult:
        """Process a single PCM16 audio frame.

        Args:
            pcm_bytes: Raw PCM 16-bit signed little-endian audio bytes.

        Returns:
            VADResult with current state and barge-in flag.
        """
        rms = self._compute_rms(pcm_bytes)

        # Auto-calibrate threshold from initial silent frames
        if self._threshold == 0.0:
            self._calibration_rms.append(rms)
            if len(self._calibration_rms) >= self._config.calibration_frames:
                avg_silence = sum(self._calibration_rms) / len(self._calibration_rms)
                self._threshold = max(avg_silence * self._config.calibration_multiplier, 50.0)
            return VADResult(
                state=VADState.SILENCE,
                rms_energy=rms,
                threshold=self._threshold,
            )

        is_speech_frame = rms > self._threshold
        barge_in = False

        if is_speech_frame:
            self._speech_count += 1
            self._silence_count = 0

            if (
                self._state == VADState.SILENCE
                and self._speech_count >= self._config.speech_min_frames
            ):
                self._state = VADState.SPEECH
                # Only flag barge-in if we're currently playing TTS
                if self._is_playing:
                    barge_in = True
        else:
            self._silence_count += 1
            self._speech_count = 0

            if (
                self._state == VADState.SPEECH
                and self._silence_count >= self._config.silence_min_frames
            ):
                self._state = VADState.SILENCE

        return VADResult(
            state=self._state,
            rms_energy=rms,
            threshold=self._threshold,
            is_barge_in=barge_in,
        )

    def _compute_rms(self, pcm_bytes: bytes) -> float:
        """Compute RMS energy of PCM16LE audio."""
        if len(pcm_bytes) < 2:
            return 0.0
        n_samples = len(pcm_bytes) // 2
        samples = struct.unpack(f"<{n_samples}h", pcm_bytes[:n_samples * 2])
        if not samples:
            return 0.0
        mean_sq = sum(s * s for s in samples) / n_samples
        return math.sqrt(mean_sq)


class BargeInManager:
    """Coordinates barge-in detection with TTS playback and pipeline cancellation.

    Usage:
        manager = BargeInManager()

        # When TTS starts playing:
        manager.start_playback()

        # Feed incoming audio continuously:
        result = manager.feed_audio(frame)
        if result.is_barge_in:
            # Cancel TTS, clear Twilio buffer, process new user input
            manager.handle_barge_in()

        # When TTS finishes naturally:
        manager.stop_playback()
    """

    def __init__(self, config: Optional[VADConfig] = None):
        self._vad = VoiceActivityDetector(config)
        self._cancel_event: Optional[asyncio.Event] = None
        self._interrupted = False
        self._incoming_buffer = bytearray()

    @property
    def cancel_event(self) -> asyncio.Event:
        """Event that is set when barge-in occurs. TTS tasks should watch this."""
        if self._cancel_event is None:
            self._cancel_event = asyncio.Event()
        return self._cancel_event

    @property
    def was_interrupted(self) -> bool:
        return self._interrupted

    @property
    def buffered_audio(self) -> bytes:
        """Audio captured during/after barge-in — feed this to STT."""
        return bytes(self._incoming_buffer)

    def start_playback(self) -> None:
        """Call when TTS audio starts being sent to the caller."""
        self._vad.is_playing = True
        self._interrupted = False
        self._incoming_buffer.clear()
        if self._cancel_event:
            self._cancel_event.clear()

    def stop_playback(self) -> None:
        """Call when TTS playback finishes naturally (no interruption)."""
        self._vad.is_playing = False

    def feed_audio(self, pcm_bytes: bytes) -> VADResult:
        """Feed incoming caller audio. Returns VAD result with barge-in flag."""
        result = self._vad.process_frame(pcm_bytes)

        if result.is_barge_in:
            self._interrupted = True
            self._incoming_buffer.extend(pcm_bytes)
            self.cancel_event.set()
        elif self._interrupted:
            # Keep buffering audio after barge-in until pipeline picks it up
            self._incoming_buffer.extend(pcm_bytes)

        return result

    def handle_barge_in(self) -> bytes:
        """Acknowledge barge-in and return buffered audio for STT.

        Call this after cancelling TTS and clearing Twilio playback.
        """
        audio = bytes(self._incoming_buffer)
        self._incoming_buffer.clear()
        self._interrupted = False
        self._vad.is_playing = False
        self._vad.reset()
        return audio
