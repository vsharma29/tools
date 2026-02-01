#!/usr/bin/env python3
"""WebSocket-based text interview test.

Tests the WebSocket endpoint which is closer to the real-time flow
(persistent connection, message-by-message).

Usage:
    # Terminal 1: start the server
    ANTHROPIC_API_KEY=sk-ant-... uvicorn src.api:app --port 8000

    # Terminal 2: run this script
    python scripts/test_websocket.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx
import websockets


async def main():
    parser = argparse.ArgumentParser(description="WebSocket text interview test")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--name", default="Jane Smith", help="Prospect name")
    parser.add_argument("--agency", default="Sydney Buyers Co", help="Agency name")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")

    # Create session via REST
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(f"{base}/api/sessions", json={
            "prospect_name": args.name,
            "agency_name": args.agency,
        })
        r.raise_for_status()
        data = r.json()
        session_id = data["session_id"]
        print(f"\nSession: {session_id}")
        print(f"\nAva: {data['greeting']}\n")

    # Connect WebSocket
    ws_url = f"{ws_base}/ws/text/{session_id}"
    async with websockets.connect(ws_url) as ws:
        while True:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("You: ").strip()
                )
            except (KeyboardInterrupt, EOFError):
                print("\nEnding conversation.")
                break

            if not user_input or user_input.lower() in ("quit", "exit", "bye"):
                break

            await ws.send(user_input)
            response = await ws.recv()
            data = json.loads(response)

            print(f"\nAva: {data['response']}\n")

            if data.get("is_complete"):
                print("INTERVIEW COMPLETE")
                break


if __name__ == "__main__":
    asyncio.run(main())
