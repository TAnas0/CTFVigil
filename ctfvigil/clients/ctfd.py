# Utilities and functions to communicate with a CTFd instance
# Demo instance at: https://demo.ctfd.io/
# API docs: https://docs.ctfd.io/docs/api/redoc/

from urllib.parse import urlparse

import requests


class CTFdClient:
    """HTTP client to manage and communicate with a CTFd instance."""

    def __init__(
        self, base_url: str, token: str = None, session_cookie: str = None, csrf_token: str = None
    ):
        cleaned_url = base_url.strip()
        if not cleaned_url.startswith(("http://", "https://")):
            cleaned_url = f"https://{cleaned_url}"
        self.base_url = cleaned_url.rstrip("/")

        self.token = token
        self.session_cookie = session_cookie
        self.csrf_token = csrf_token

        self.session = requests.Session()
        if self.token:
            self.session.headers.update({"Authorization": f"Token {self.token}"})
        if self.session_cookie:
            self.session.cookies.set("session", self.session_cookie)
        if self.csrf_token:
            self.session.headers.update({"CSRF-Token": self.csrf_token})

        self.session.headers.update(
            {
                "User-Agent": "CTFVigil/1.0 (Discord Bot; +https://github.com/ctfvigil)",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def is_ctfd_instance(self) -> bool:
        """Fingerprints a target URL to verify if it's running CTFd by checking API structure."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/users", timeout=5)
            data = response.json()
            if isinstance(data, dict) and "success" in data:
                return True
        except (requests.RequestException, ValueError):
            pass
        return False

    def probe_endpoint(self, endpoint: str) -> dict:
        """Probes a specific CTFd API endpoint and returns status code, payload, count, and access state."""
        url = f"{self.base_url}/api/v1/{endpoint.strip('/')}"
        try:
            response = self.session.get(url, timeout=5)
            status_code = response.status_code
            try:
                data = response.json()
            except ValueError:
                data = None

            if status_code == 200 and isinstance(data, dict) and data.get("success"):
                items = data.get("data", [])
                count = len(items) if isinstance(items, list) else None
                return {
                    "status_code": status_code,
                    "accessible": True,
                    "count": count,
                    "data": items,
                }
            elif status_code in (401, 403):
                return {
                    "status_code": status_code,
                    "accessible": False,
                    "reason": "Protected / Authentication Required",
                }
            elif status_code == 404:
                return {
                    "status_code": status_code,
                    "accessible": False,
                    "reason": "Endpoint Not Found / Disabled",
                }
            else:
                return {
                    "status_code": status_code,
                    "accessible": False,
                    "reason": f"HTTP {status_code}",
                }
        except requests.RequestException as exc:
            return {"status_code": 0, "accessible": False, "reason": f"Connection Error ({exc})"}

    def get_ctf_title(self) -> str:
        """Attempts to fetch the CTF event title from public settings or falls back to hostname."""
        try:
            # Try fetching CTFd's public configs endpoint
            res = self.session.get(f"{self.base_url}/api/v1/config", timeout=5)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict) and data.get("success"):
                    configs = data.get("data", {})
                    if isinstance(configs, dict) and "ctf_name" in configs:
                        return str(configs["ctf_name"])
        except (requests.RequestException, ValueError):
            pass

        parsed = urlparse(self.base_url)
        return parsed.netloc or self.base_url

    def probe_all_endpoints(self) -> dict:
        """Runs diagnostics across standard CTFd public endpoints."""
        endpoints = ["users", "teams", "challenges", "scoreboard"]
        results = {}
        for ep in endpoints:
            results[ep] = self.probe_endpoint(ep)
        return results

    def register_bot_user(self, username: str, email: str, password: str) -> dict:
        """Programmatically registers a bot user via CTFd's administrative API."""
        url = f"{self.base_url}/api/v1/users"
        payload = {
            "name": username,
            "email": email,
            "password": password,
            "type": "user",
            "verified": True,
            "hidden": False,
            "banned": False,
            "fields": [],
        }

        response = self.session.post(url, json=payload)
        try:
            data = response.json()
        except ValueError:
            data = {"message": response.text}

        return {"status_code": response.status_code, "data": data}

    def get_ctfd_users(self) -> list:
        return self.probe_endpoint("users").get("data", [])

    def get_ctfd_teams(self) -> list:
        return self.probe_endpoint("teams").get("data", [])

    def get_ctfd_challenges(self) -> list:
        return self.probe_endpoint("challenges").get("data", [])

    def get_ctfd_scoreboard(self) -> list:
        return self.probe_endpoint("scoreboard").get("data", [])

    def get_ctfd_scoreboard_details(self, limit: int = 10) -> dict:
        """Fetches live scoreboard standings with rank, team/user name, and score details."""
        probe = self.probe_endpoint("scoreboard")
        if not probe.get("accessible"):
            return {
                "accessible": False,
                "status_code": probe.get("status_code", 0),
                "reason": probe.get("reason", "Forbidden or Unavailable"),
                "standings": [],
            }

        raw_data = probe.get("data", [])
        standings = []
        for idx, entry in enumerate(raw_data[:limit], start=1):
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("account_name") or f"Entry #{idx}"
                score = entry.get("score", 0)
                pos = entry.get("pos") or idx
                standings.append({"pos": pos, "name": name, "score": score})

        return {"accessible": True, "status_code": 200, "reason": "OK", "standings": standings}
