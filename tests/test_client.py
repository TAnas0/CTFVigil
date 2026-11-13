import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import pytest

from ctfvigil.client import CTFTimeClient


def async_test(coro):
    """Helper runner to avoid needing pytest-asyncio plugin dependency."""

    def wrapper(*args, **kwargs):
        return asyncio.run(coro(*args, **kwargs))

    return wrapper


class TestCTFTimeClient:
    """Tests for CTFTimeClient."""

    def test_init_defaults_and_custom_agent(self):
        client_default = CTFTimeClient()
        assert client_default.user_agent == CTFTimeClient.DEFAULT_USER_AGENT
        assert client_default._session is None

        custom_agent = "CustomBot/2.0"
        client_custom = CTFTimeClient(user_agent=custom_agent)
        assert client_custom.user_agent == custom_agent

    @async_test
    async def test_fetch_upcoming_events_success_with_provided_session(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = [{"title": "Test CTF", "id": 1}]

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        client = CTFTimeClient(session=mock_session)
        events = await client.fetch_upcoming_events(limit=5, start_timestamp=1700000000)

        assert events == [{"title": "Test CTF", "id": 1}]
        expected_url = f"{CTFTimeClient.BASE_URL}?limit=5&start=1700000000"
        mock_session.get.assert_called_once_with(
            expected_url,
            headers={"User-Agent": CTFTimeClient.DEFAULT_USER_AGENT},
            timeout=aiohttp.ClientTimeout(total=10),
        )

    @async_test
    async def test_fetch_upcoming_events_creates_and_closes_session(self):
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = []

        mock_session_inst = MagicMock()
        mock_session_inst.get.return_value.__aenter__.return_value = mock_response
        mock_session_inst.close = AsyncMock()

        with patch("aiohttp.ClientSession", return_value=mock_session_inst):
            client = CTFTimeClient()
            events = await client.fetch_upcoming_events(limit=10)
            assert events == []
            mock_session_inst.close.assert_awaited_once()

    @async_test
    async def test_fetch_upcoming_events_http_error(self):
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response

        client = CTFTimeClient(session=mock_session)
        with pytest.raises(RuntimeError, match="CTFtime API error: HTTP 500"):
            await client.fetch_upcoming_events()

    @async_test
    async def test_fetch_upcoming_events_client_error(self):
        mock_session = MagicMock()
        mock_session.get.side_effect = aiohttp.ClientError("Connection reset")

        client = CTFTimeClient(session=mock_session)
        with pytest.raises(
            RuntimeError, match="Network error communicating with CTFtime API: Connection reset"
        ):
            await client.fetch_upcoming_events()
