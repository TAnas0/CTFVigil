from __future__ import annotations

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

import requests

from ctfvigil.cache import RedisCache, get_client
from ctfvigil.client import CTFTimeClient
from ctfvigil.utils import iso_to_timestamp
from tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

UPCOMING_EVENTS_CACHE_KEY = "ctfvigil:events:upcoming"
UPCOMING_EVENTS_TTL = 6 * 3600  # 6 hours in seconds


@celery_app.task(bind=True, max_retries=3)
def sync_ctftime_events_task(self) -> dict[str, Any]:
    """Fetch upcoming CTF events from CTFtime, cache in Redis, and optionally send a webhook digest."""
    logger.info("Starting CTFtime upcoming events sync task...")
    try:

        async def _fetch() -> list[dict]:
            client = CTFTimeClient()
            return await client.fetch_upcoming_events(limit=10)

        events = asyncio.run(_fetch())
        logger.info("Fetched %d events from CTFtime API", len(events))

        cache = RedisCache(get_client())
        cache.set(UPCOMING_EVENTS_CACHE_KEY, events, ttl=UPCOMING_EVENTS_TTL)
        logger.info(
            "Cached %d events under '%s' with %d seconds TTL",
            len(events),
            UPCOMING_EVENTS_CACHE_KEY,
            UPCOMING_EVENTS_TTL,
        )

        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if webhook_url:
            fields = []
            for ev in events[:3]:
                title = ev.get("title", "Unnamed CTF")
                start_str = ev.get("start", "")
                start_ts = iso_to_timestamp(start_str)
                time_display = (
                    f"<t:{start_ts}:F> (<t:{start_ts}:R>)" if start_ts else (start_str or "Unknown")
                )
                fields.append(
                    {
                        "name": title,
                        "value": f"⏰ Starts: {time_display}",
                        "inline": False,
                    }
                )

            embed = {
                "title": "🦉 CTFVigil Upcoming CTF Digest",
                "description": f"Found **{len(events)}** upcoming events on CTFtime.",
                "color": 0x5865F2,
                "fields": fields,
                "footer": {"text": "CTFVigil Periodic Digest • Next sync in 6 hours"},
            }

            try:
                resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=10)
                resp.raise_for_status()
                logger.info(
                    "Successfully dispatched CTF digest to Discord webhook (HTTP %d)",
                    resp.status_code,
                )
            except Exception as hook_exc:
                logger.warning("Failed to dispatch CTF digest to Discord webhook: %s", hook_exc)

        cached_at = datetime.now(UTC).isoformat()
        return {
            "fetched": len(events),
            "cached_at": cached_at,
        }
    except Exception as exc:
        logger.error("Failed to sync CTFtime events: %s", exc)
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(bind=True, max_retries=3)
def check_ctfd_ctf(self, ctf_url: str):
    """Given"""
    try:
        print(f"Checking CTF platform at {ctf_url} for CTFd infrastructure...")
        # TODO ensure the URL points to a CTFd instance
    except Exception as exc:
        # Automatic exponential backoff retry on failure
        raise self.retry(exc=exc, countdown=60) from exc
