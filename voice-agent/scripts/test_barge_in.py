#!/usr/bin/env python3
"""Standalone barge-in simulation test.

No API keys needed — tests VAD + BargeInManager with synthetic audio.

Usage:
    python scripts/test_barge_in.py
"""

from __future__ import annotations

import asyncio
import struct
import time

from src.audio.vad import BargeInManager, VADConfig, VADState


def make_pcm_frame(amplitude: int, n_samples: int = 320) -> bytes:
    return struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))


def run_simulation():
    print("=" * 60)
    print("Barge-In Simulation Test")
    print("=" * 60)

    config = VADConfig(
        energy_threshold=0,       # auto-calibrate
        calibration_frames=5,
        speech_min_frames=3,
        silence_min_frames=5,
        calibration_multiplier=2.5,
    )
    mgr = BargeInManager(config)

    # Phase 1: Calibrate with silence
    print("\n[Phase 1] Calibrating with silence...")
    for i in range(5):
        result = mgr.feed_audio(make_pcm_frame(10))
        print(f"  Frame {i}: state={result.state} rms={result.rms_energy:.1f} threshold={result.threshold:.1f}")

    # Phase 2: Simulate agent talking (playback active) + caller silent
    print("\n[Phase 2] Agent speaking, caller silent...")
    mgr.start_playback()
    for i in range(5):
        result = mgr.feed_audio(make_pcm_frame(10))
        print(f"  Frame {i}: state={result.state} barge_in={result.is_barge_in}")
    assert not mgr.cancel_event.is_set(), "Should not barge-in during silence"
    print("  ✓ No false barge-in during silence")

    # Phase 3: Caller starts speaking → barge-in
    print("\n[Phase 3] Caller interrupts (speech during playback)...")
    barge_in_frame = None
    for i in range(5):
        result = mgr.feed_audio(make_pcm_frame(5000))
        print(f"  Frame {i}: state={result.state} rms={result.rms_energy:.1f} barge_in={result.is_barge_in}")
        if result.is_barge_in:
            barge_in_frame = i

    assert mgr.cancel_event.is_set(), "Cancel event should be set"
    assert mgr.was_interrupted, "Should be marked as interrupted"
    print(f"  ✓ Barge-in detected at frame {barge_in_frame}")

    # Phase 4: Collect buffered audio
    print("\n[Phase 4] Handling barge-in...")
    buffered = mgr.handle_barge_in()
    print(f"  Buffered audio: {len(buffered)} bytes")
    assert len(buffered) > 0, "Should have buffered audio"
    assert not mgr.was_interrupted, "Should be cleared after handle"
    print("  ✓ Buffered audio collected and state reset")

    # Phase 5: Next turn — no barge-in during silence
    print("\n[Phase 5] New turn, agent responds, caller silent...")
    mgr.start_playback()
    for i in range(5):
        result = mgr.feed_audio(make_pcm_frame(10))
    mgr.stop_playback()
    assert not mgr.cancel_event.is_set()
    print("  ✓ Clean turn with no interruption")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_simulation()
