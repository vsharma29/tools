#!/usr/bin/env python3
"""Interactive local test script — text-mode interview via the API.

Requires only ANTHROPIC_API_KEY to run. No audio or telephony keys needed.

Usage:
    # Terminal 1: start the server
    cd voice-agent
    ANTHROPIC_API_KEY=sk-ant-... uvicorn src.api:app --port 8000

    # Terminal 2: run this script
    python scripts/test_text_interview.py

    # Or run against a remote server:
    python scripts/test_text_interview.py --url https://your-deployment.com
"""

from __future__ import annotations

import argparse
import json
import sys

import httpx


def main():
    parser = argparse.ArgumentParser(description="Test the buyer voice agent in text mode")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--name", default="Jane Smith", help="Prospect name")
    parser.add_argument("--agency", default="Sydney Buyers Co", help="Agency name")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    client = httpx.Client(timeout=60.0)

    # Health check
    try:
        r = client.get(f"{base}/health")
        r.raise_for_status()
    except Exception as e:
        print(f"Cannot reach server at {base}: {e}")
        sys.exit(1)

    # Create session
    r = client.post(f"{base}/api/sessions", json={
        "prospect_name": args.name,
        "agency_name": args.agency,
        "is_outbound": True,
    })
    r.raise_for_status()
    data = r.json()
    session_id = data["session_id"]
    print(f"\n{'='*60}")
    print(f"Session: {session_id}")
    print(f"{'='*60}")
    print(f"\nAva: {data['greeting']}\n")

    # Conversation loop
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nEnding conversation.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "bye"):
            print("\nEnding conversation.")
            break

        r = client.post(f"{base}/api/turns/text", json={
            "session_id": session_id,
            "text": user_input,
        })
        r.raise_for_status()
        data = r.json()

        print(f"\nAva: {data['response']}\n")

        if data.get("is_complete"):
            print(f"\n{'='*60}")
            print("INTERVIEW COMPLETE")
            print(f"{'='*60}")
            if data.get("brief"):
                print("\nBuyer Brief (JSON):")
                print(json.dumps(data["brief"], indent=2))
            break

    # Print metrics
    r = client.get(f"{base}/api/sessions/{session_id}/metrics")
    if r.status_code == 200:
        metrics = r.json()
        if metrics:
            print(f"\n{'='*60}")
            print("Session Metrics:")
            print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
