import time
import aiohttp


class CTFTimeClient:
    """Lightweight client for CTFtime API v1."""

    BASE_URL = "https://ctftime.org/api/v1/events/"
    DEFAULT_USER_AGENT = "CTFVigil/1.0 (Discord Bot; +https://github.com/ctfvigil)"

    def __init__(self, session: aiohttp.ClientSession | None = None, user_agent: str | None = None):
        self._session = session
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT

    async def fetch_upcoming_events(
        self, limit: int = 10, start_timestamp: int | None = None
    ) -> list[dict]:
        """Fetch upcoming events from CTFtime API with robust error handling."""
        if start_timestamp is None:
            start_timestamp = int(time.time())

        url = f"{self.BASE_URL}?limit={limit}&start={start_timestamp}"
        headers = {"User-Agent": self.user_agent}

        session_created = False
        session = self._session
        if session is None:
            session = aiohttp.ClientSession()
            session_created = True

        try:
            async with session.get(
                url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"CTFtime API error: HTTP {response.status}")
                return await response.json()
        except aiohttp.ClientError as exc:
            raise RuntimeError(f"Network error communicating with CTFtime API: {exc}") from exc
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch CTF events: {exc}") from exc
        finally:
            if session_created:
                await session.close()
