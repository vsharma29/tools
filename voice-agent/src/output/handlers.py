"""Output handlers — save the completed buyer brief to S3 and/or webhook."""

from __future__ import annotations

import json
from datetime import datetime

import boto3
import httpx
import structlog

from config.settings import Settings
from src.schemas.buyer_brief import BuyerBrief

logger = structlog.get_logger()


class S3Handler:
    def __init__(self, settings: Settings):
        self._bucket = settings.s3_bucket_name
        self._s3 = boto3.client("s3", region_name=settings.s3_region)

    async def save(self, brief: BuyerBrief) -> str:
        key = (
            f"briefs/{datetime.utcnow().strftime('%Y/%m/%d')}/"
            f"{brief.brief_id or 'unknown'}.json"
        )
        body = brief.model_dump_json(indent=2, exclude_none=True)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body.encode(),
            ContentType="application/json",
        )
        logger.info("brief_saved_s3", bucket=self._bucket, key=key)
        return f"s3://{self._bucket}/{key}"


class WebhookHandler:
    def __init__(self, settings: Settings):
        self._url = settings.webhook_url

    async def send(self, brief: BuyerBrief) -> int:
        payload = json.loads(brief.model_dump_json(exclude_none=True))
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self._url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            logger.info("brief_sent_webhook", status=resp.status_code, url=self._url)
            return resp.status_code


class OutputManager:
    """Routes completed briefs to configured outputs."""

    def __init__(self, settings: Settings):
        self._mode = settings.output_mode.lower()
        self._s3 = S3Handler(settings) if self._mode in ("s3", "both") else None
        self._webhook = WebhookHandler(settings) if self._mode in ("webhook", "both") else None

    async def save_brief(self, brief: BuyerBrief) -> dict:
        results: dict = {}
        if self._s3:
            results["s3_path"] = await self._s3.save(brief)
        if self._webhook:
            results["webhook_status"] = await self._webhook.send(brief)
        logger.info("brief_output_complete", results=results)
        return results
