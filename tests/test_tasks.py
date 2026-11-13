"""
tests/test_tasks.py
~~~~~~~~~~~~~~~~~~~
Unit tests for background Celery tasks in tasks/tasks.py.
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from tasks.tasks import (
    CTFD_PROBE_TTL,
    UPCOMING_EVENTS_CACHE_KEY,
    UPCOMING_EVENTS_TTL,
    check_ctfd_ctf,
    sync_ctftime_events_task,
)


@pytest.fixture
def sample_events() -> list[dict]:
    return [
        {
            "id": 101,
            "title": "Alpha CTF 2026",
            "url": "https://alpha.ctf",
            "ctftime_url": "https://ctftime.org/event/101",
            "start": "2026-11-20T10:00:00Z",
            "finish": "2026-11-22T10:00:00Z",
            "format": "Jeopardy",
            "onsite": False,
        },
        {
            "id": 102,
            "title": "Beta CTF 2026",
            "url": "https://beta.ctf",
            "ctftime_url": "https://ctftime.org/event/102",
            "start": "2026-11-25T12:00:00+00:00",
            "finish": "2026-11-26T12:00:00+00:00",
            "format": "Attack-Defense",
            "onsite": True,
        },
    ]


class TestSyncCTFTimeEventsTask:
    """Tests for sync_ctftime_events_task."""

    @patch("tasks.tasks.CTFTimeClient.fetch_upcoming_events", new_callable=AsyncMock)
    @patch("tasks.tasks.RedisCache")
    def test_sync_success_caches_data_and_returns_summary(
        self, mock_cache_cls, mock_fetch, sample_events
    ):
        mock_fetch.return_value = sample_events
        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        with patch.dict(os.environ, {}, clear=True):
            result = sync_ctftime_events_task()

        mock_fetch.assert_called_once_with(limit=10)
        mock_cache.set.assert_called_once_with(
            UPCOMING_EVENTS_CACHE_KEY, sample_events, ttl=UPCOMING_EVENTS_TTL
        )
        assert result["fetched"] == 2
        assert "cached_at" in result

    @patch("tasks.tasks.CTFTimeClient.fetch_upcoming_events", new_callable=AsyncMock)
    @patch("tasks.tasks.RedisCache")
    @patch("tasks.tasks.requests.post")
    def test_sync_dispatches_webhook_when_configured(
        self, mock_post, mock_cache_cls, mock_fetch, sample_events
    ):
        mock_fetch.return_value = sample_events
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_post.return_value = mock_resp

        webhook_url = "https://discord.com/api/webhooks/123/xyz"
        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": webhook_url}):
            result = sync_ctftime_events_task()

        mock_post.assert_called_once()
        call_url, call_kwargs = mock_post.call_args
        assert call_url[0] == webhook_url
        payload = call_kwargs["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        embed = payload["embeds"][0]
        assert "Alpha CTF 2026" in embed["fields"][0]["name"]
        assert result["fetched"] == 2

    @patch("tasks.tasks.CTFTimeClient.fetch_upcoming_events", new_callable=AsyncMock)
    @patch("tasks.tasks.RedisCache")
    @patch("tasks.tasks.requests.post")
    def test_webhook_failure_does_not_fail_task(
        self, mock_post, mock_cache_cls, mock_fetch, sample_events
    ):
        mock_fetch.return_value = sample_events
        mock_post.side_effect = requests.RequestException("Webhook timeout")

        with patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.com/webhook"}):
            result = sync_ctftime_events_task()

        assert result["fetched"] == 2
        assert "cached_at" in result

    @patch("tasks.tasks.CTFTimeClient.fetch_upcoming_events", new_callable=AsyncMock)
    def test_sync_triggers_retry_on_fetch_failure(self, mock_fetch):
        mock_fetch.side_effect = RuntimeError("CTFtime API down")

        # Mock self.retry for Celery bound task
        with patch.object(sync_ctftime_events_task, "retry", side_effect=RuntimeError("Retrying")):
            with pytest.raises(RuntimeError, match="Retrying"):
                sync_ctftime_events_task()


class TestCheckCTFdCTFTask:
    """Tests for check_ctfd_ctf."""

    @patch("tasks.tasks.CTFdClient")
    @patch("tasks.tasks.RedisCache")
    def test_check_non_ctfd_returns_early_without_caching(
        self, mock_cache_cls, mock_ctfd_cls
    ):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = False
        mock_client.base_url = "https://not-ctfd.example.com"
        mock_ctfd_cls.return_value = mock_client

        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        result = check_ctfd_ctf("https://not-ctfd.example.com")

        assert result == {"is_ctfd": False, "url": "https://not-ctfd.example.com"}
        mock_client.probe_all_endpoints.assert_not_called()
        mock_cache.set.assert_not_called()

    @patch("tasks.tasks.CTFdClient")
    @patch("tasks.tasks.RedisCache")
    def test_check_valid_ctfd_probes_and_caches(
        self, mock_cache_cls, mock_ctfd_cls
    ):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.return_value = True
        mock_client.base_url = "https://demo.ctfd.io"
        mock_client.get_ctf_title.return_value = "Demo CTF"
        mock_client.probe_all_endpoints.return_value = {
            "challenges": {"accessible": True, "count": 10},
            "scoreboard": {"accessible": True, "count": 50},
        }
        mock_ctfd_cls.return_value = mock_client

        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        result = check_ctfd_ctf("https://demo.ctfd.io")

        assert result["is_ctfd"] is True
        assert result["url"] == "https://demo.ctfd.io"
        assert result["title"] == "Demo CTF"
        assert "challenges" in result["endpoints"]
        assert "checked_at" in result

        mock_cache.set.assert_called_once()
        call_key, call_val = mock_cache.set.call_args[0][:2]
        call_ttl = mock_cache.set.call_args[1].get("ttl")
        assert call_key.startswith("ctfvigil:ctfd:")
        assert call_val == result
        assert call_ttl == CTFD_PROBE_TTL

    @patch("tasks.tasks.CTFdClient")
    def test_check_triggers_retry_on_exception(self, mock_ctfd_cls):
        mock_client = MagicMock()
        mock_client.is_ctfd_instance.side_effect = requests.RequestException("Connection error")
        mock_ctfd_cls.return_value = mock_client

        with patch.object(check_ctfd_ctf, "retry", side_effect=RuntimeError("Retrying")):
            with pytest.raises(RuntimeError, match="Retrying"):
                check_ctfd_ctf("https://error.example.com")

