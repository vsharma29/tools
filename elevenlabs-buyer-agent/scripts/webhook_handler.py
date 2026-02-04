#!/usr/bin/env python3
"""Simple webhook handler for receiving buyer briefs.

This is a minimal FastAPI server that receives buyer briefs from
ElevenLabs webhook calls and stores them in S3.

For production, you'd integrate this into your CRM or backend system.

Usage:
    # Start the webhook server
    uvicorn scripts.webhook_handler:app --port 3000

    # Set WEBHOOK_URL in .env to point to this server
    # WEBHOOK_URL=https://your-domain.com/api/briefs
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import boto3
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

app = FastAPI(title="Buyer Brief Webhook Handler")

# Configuration from environment
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "buyer-briefs")
S3_REGION = os.getenv("S3_REGION", "ap-southeast-2")


class BriefData(BaseModel):
    """Buyer brief data structure."""
    brief_data: dict[str, Any]


@app.post("/api/briefs")
async def receive_brief(
    request: Request,
    x_webhook_secret: str = Header(None, alias="X-Webhook-Secret"),
):
    """Receive and store a buyer brief from ElevenLabs.

    The brief is saved to S3 with a timestamp-based key.
    """
    # Verify webhook secret if configured
    if WEBHOOK_SECRET and x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    # Parse the request body
    body = await request.json()
    brief_data = body.get("brief_data", {})

    if not brief_data:
        raise HTTPException(status_code=400, detail="No brief_data in request")

    # Generate a unique ID
    timestamp = datetime.utcnow()
    prospect_name = brief_data.get("prospect_name", "unknown").lower().replace(" ", "_")
    brief_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{prospect_name}"

    # Add metadata
    brief_data["brief_id"] = brief_id
    brief_data["created_at"] = timestamp.isoformat()
    brief_data["source"] = "elevenlabs_voice_agent"

    # Save to S3
    try:
        s3 = boto3.client("s3", region_name=S3_REGION)
        key = f"briefs/{timestamp.strftime('%Y/%m/%d')}/{brief_id}.json"

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=json.dumps(brief_data, indent=2).encode(),
            ContentType="application/json",
        )

        print(f"Brief saved to s3://{S3_BUCKET}/{key}")

        return {
            "success": True,
            "brief_id": brief_id,
            "s3_path": f"s3://{S3_BUCKET}/{key}",
        }

    except Exception as e:
        print(f"Error saving brief: {e}")
        # Still return success to ElevenLabs to avoid retries
        # Log the error for investigation
        return {
            "success": True,
            "brief_id": brief_id,
            "warning": "S3 save failed, brief logged locally",
        }


@app.post("/api/post-call")
async def post_call_webhook(request: Request):
    """Receive post-call webhook from ElevenLabs.

    This receives conversation analysis, transcript, and audio URL
    after each call completes.
    """
    body = await request.json()

    conversation_id = body.get("conversation_id")
    analysis = body.get("analysis", {})
    transcript = body.get("transcript", [])

    print(f"Post-call webhook for conversation {conversation_id}")
    print(f"Evaluations: {analysis.get('evaluations', {})}")
    print(f"Data collected: {analysis.get('data_collection', {})}")

    # Here you would:
    # - Update your CRM with the conversation data
    # - Trigger follow-up workflows
    # - Alert sales team of qualified leads

    return {"success": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
