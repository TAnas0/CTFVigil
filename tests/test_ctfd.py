from unittest.mock import MagicMock, patch

import requests

from ctfvigil.clients.ctfd import CTFdClient


class TestCTFdClientProbing:
    """Unit tests for CTFdClient endpoint probing and title resolution."""

    def test_url_formatting(self):
        client1 = CTFdClient("demo.ctfd.io")
        assert client1.base_url == "https://demo.ctfd.io"

        client2 = CTFdClient("http://localhost:8000/")
        assert client2.base_url == "http://localhost:8000"

    def test_is_ctfd_instance_success(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True, "data": []}

        with patch.object(client.session, "get", return_value=mock_response):
            assert client.is_ctfd_instance() is True

    def test_is_ctfd_instance_failure(self):
        client = CTFdClient("https://example.com")
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Not Found"}

        with patch.object(client.session, "get", return_value=mock_response):
            assert client.is_ctfd_instance() is False

    def test_probe_endpoint_200_accessible(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": [{"id": 1}, {"id": 2}]}

        with patch.object(client.session, "get", return_value=mock_response):
            res = client.probe_endpoint("challenges")
            assert res["accessible"] is True
            assert res["status_code"] == 200
            assert res["count"] == 2

    def test_probe_endpoint_403_protected(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch.object(client.session, "get", return_value=mock_response):
            res = client.probe_endpoint("challenges")
            assert res["accessible"] is False
            assert res["status_code"] == 403
            assert "Protected" in res["reason"]

    def test_get_ctf_title_from_config(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"ctf_name": "CyberGames 2026"}}

        with patch.object(client.session, "get", return_value=mock_response):
            assert client.get_ctf_title() == "CyberGames 2026"

    def test_get_ctf_title_fallback_to_host(self):
        client = CTFdClient("https://demo.ctfd.io")
        with patch.object(client.session, "get", side_effect=requests.RequestException()):
            assert client.get_ctf_title() == "demo.ctfd.io"

    def test_get_ctfd_scoreboard_details_accessible(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": [
                {"account_name": "Team Alpha", "score": 1500, "pos": 1},
                {"name": "Team Beta", "score": 1200, "pos": 2},
            ],
        }

        with patch.object(client.session, "get", return_value=mock_response):
            details = client.get_ctfd_scoreboard_details(limit=5)
            assert details["accessible"] is True
            assert len(details["standings"]) == 2
            assert details["standings"][0]["name"] == "Team Alpha"
            assert details["standings"][0]["score"] == 1500

    def test_get_ctfd_scoreboard_details_protected(self):
        client = CTFdClient("https://demo.ctfd.io")
        mock_response = MagicMock()
        mock_response.status_code = 403

        with patch.object(client.session, "get", return_value=mock_response):
            details = client.get_ctfd_scoreboard_details(limit=5)
            assert details["accessible"] is False
            assert details["status_code"] == 403
            assert details["standings"] == []
