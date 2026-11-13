"""
tests/test_cache.py
~~~~~~~~~~~~~~~~~~~
Unit tests for ctfvigil/cache.py.

All Redis interactions are mocked — no live Redis instance required.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch, call

import pytest
import redis

from ctfvigil.cache import DEFAULT_TTL, RedisCache, get_client


# ======================================================================= #
# Helpers                                                                  #
# ======================================================================= #

def make_cache(mock_redis: MagicMock | None = None) -> tuple[RedisCache, MagicMock]:
    """Return a (RedisCache, mock_redis_client) pair."""
    if mock_redis is None:
        mock_redis = MagicMock(spec=redis.Redis)
    return RedisCache(mock_redis), mock_redis


# ======================================================================= #
# get_client()                                                             #
# ======================================================================= #

class TestGetClient:
    """Tests for the get_client() factory."""

    def test_uses_redis_url_env_var(self):
        custom_url = "redis://myredis:6380/1"
        with patch.dict(os.environ, {"REDIS_URL": custom_url}):
            with patch("ctfvigil.cache.redis.Redis.from_url") as mock_from_url:
                mock_from_url.return_value = MagicMock()
                get_client()
                mock_from_url.assert_called_once()
                assert mock_from_url.call_args[0][0] == custom_url

    def test_falls_back_to_localhost_when_env_absent(self):
        env = {k: v for k, v in os.environ.items() if k != "REDIS_URL"}
        with patch.dict(os.environ, env, clear=True):
            with patch("ctfvigil.cache.redis.Redis.from_url") as mock_from_url:
                mock_from_url.return_value = MagicMock()
                get_client()
                called_url = mock_from_url.call_args[0][0]
                assert called_url == "redis://localhost:6379/0"

    def test_returns_redis_instance(self):
        with patch("ctfvigil.cache.redis.Redis.from_url") as mock_from_url:
            fake_client = MagicMock(spec=redis.Redis)
            mock_from_url.return_value = fake_client
            result = get_client()
            assert result is fake_client

    def test_decode_responses_enabled(self):
        with patch("ctfvigil.cache.redis.Redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            get_client()
            kwargs = mock_from_url.call_args[1]
            assert kwargs.get("decode_responses") is True

    def test_socket_timeouts_set(self):
        with patch("ctfvigil.cache.redis.Redis.from_url") as mock_from_url:
            mock_from_url.return_value = MagicMock()
            get_client()
            kwargs = mock_from_url.call_args[1]
            assert "socket_connect_timeout" in kwargs
            assert "socket_timeout" in kwargs


# ======================================================================= #
# RedisCache.get                                                           #
# ======================================================================= #

class TestRedisCacheGet:
    """Tests for RedisCache.get()."""

    def test_returns_none_for_missing_key(self):
        cache, mock_r = make_cache()
        mock_r.get.return_value = None
        assert cache.get("missing:key") is None
        mock_r.get.assert_called_once_with("missing:key")

    def test_returns_deserialized_dict(self):
        cache, mock_r = make_cache()
        payload = {"title": "PicoCTF", "url": "https://picoctf.org"}
        mock_r.get.return_value = json.dumps(payload)
        assert cache.get("ctfvigil:events:upcoming") == payload

    def test_returns_deserialized_list(self):
        cache, mock_r = make_cache()
        payload = [{"id": 1}, {"id": 2}]
        mock_r.get.return_value = json.dumps(payload)
        assert cache.get("ctfvigil:events:upcoming") == payload

    def test_returns_deserialized_string(self):
        cache, mock_r = make_cache()
        mock_r.get.return_value = json.dumps("hello")
        assert cache.get("some:key") == "hello"

    def test_returns_deserialized_integer(self):
        cache, mock_r = make_cache()
        mock_r.get.return_value = json.dumps(42)
        assert cache.get("some:key") == 42

    def test_returns_none_on_redis_error(self):
        cache, mock_r = make_cache()
        mock_r.get.side_effect = redis.RedisError("connection refused")
        assert cache.get("any:key") is None

    def test_returns_none_on_corrupt_json(self):
        cache, mock_r = make_cache()
        mock_r.get.return_value = "not-valid-json{{{"
        assert cache.get("any:key") is None


# ======================================================================= #
# RedisCache.set                                                           #
# ======================================================================= #

class TestRedisCacheSet:
    """Tests for RedisCache.set()."""

    def test_set_with_default_ttl_calls_setex(self):
        cache, mock_r = make_cache()
        value = {"events": []}
        result = cache.set("ctfvigil:events:upcoming", value)
        mock_r.setex.assert_called_once_with(
            "ctfvigil:events:upcoming",
            DEFAULT_TTL,
            json.dumps(value, default=str),
        )
        assert result is True

    def test_set_with_explicit_ttl(self):
        cache, mock_r = make_cache()
        value = [1, 2, 3]
        cache.set("some:key", value, ttl=120)
        mock_r.setex.assert_called_once_with("some:key", 120, json.dumps(value, default=str))

    def test_set_without_ttl_calls_plain_set(self):
        cache, mock_r = make_cache()
        value = {"permanent": True}
        cache.set("some:key", value, ttl=None)
        mock_r.set.assert_called_once_with("some:key", json.dumps(value, default=str))
        mock_r.setex.assert_not_called()

    def test_returns_false_on_redis_error(self):
        cache, mock_r = make_cache()
        mock_r.setex.side_effect = redis.RedisError("write failed")
        assert cache.set("key", {"data": 1}) is False

    def test_returns_false_on_non_serializable_value(self):
        cache, mock_r = make_cache()

        class Unserializable:
            pass

        # json.dumps with default=str will actually stringify it,
        # but a set with an object containing a bytes value should still fail.
        # We test a genuinely un-dumpable structure by patching json.dumps.
        with patch("ctfvigil.cache.json.dumps", side_effect=TypeError("not serializable")):
            assert cache.set("key", object()) is False
        mock_r.setex.assert_not_called()

    def test_set_list_value(self):
        cache, mock_r = make_cache()
        events = [{"id": 1, "title": "CTF A"}, {"id": 2, "title": "CTF B"}]
        result = cache.set("events", events, ttl=600)
        assert result is True
        stored = json.loads(mock_r.setex.call_args[0][2])
        assert stored == events


# ======================================================================= #
# RedisCache.delete                                                        #
# ======================================================================= #

class TestRedisCacheDelete:
    """Tests for RedisCache.delete()."""

    def test_delete_existing_key_returns_true(self):
        cache, mock_r = make_cache()
        mock_r.delete.return_value = 1
        assert cache.delete("ctfvigil:events:upcoming") is True
        mock_r.delete.assert_called_once_with("ctfvigil:events:upcoming")

    def test_delete_missing_key_returns_false(self):
        cache, mock_r = make_cache()
        mock_r.delete.return_value = 0
        assert cache.delete("nonexistent:key") is False

    def test_delete_returns_false_on_redis_error(self):
        cache, mock_r = make_cache()
        mock_r.delete.side_effect = redis.RedisError("delete failed")
        assert cache.delete("any:key") is False


# ======================================================================= #
# RedisCache.exists                                                        #
# ======================================================================= #

class TestRedisCacheExists:
    """Tests for RedisCache.exists()."""

    def test_returns_true_when_key_exists(self):
        cache, mock_r = make_cache()
        mock_r.exists.return_value = 1
        assert cache.exists("some:key") is True

    def test_returns_false_when_key_absent(self):
        cache, mock_r = make_cache()
        mock_r.exists.return_value = 0
        assert cache.exists("some:key") is False

    def test_returns_false_on_redis_error(self):
        cache, mock_r = make_cache()
        mock_r.exists.side_effect = redis.RedisError("oops")
        assert cache.exists("some:key") is False


# ======================================================================= #
# RedisCache.ttl                                                           #
# ======================================================================= #

class TestRedisCacheTTL:
    """Tests for RedisCache.ttl()."""

    def test_returns_remaining_seconds(self):
        cache, mock_r = make_cache()
        mock_r.ttl.return_value = 1800
        assert cache.ttl("some:key") == 1800

    def test_returns_minus_one_for_no_expiry(self):
        cache, mock_r = make_cache()
        mock_r.ttl.return_value = -1
        assert cache.ttl("some:key") == -1

    def test_returns_minus_two_for_missing_key(self):
        cache, mock_r = make_cache()
        mock_r.ttl.return_value = -2
        assert cache.ttl("some:key") == -2

    def test_returns_minus_two_on_redis_error(self):
        cache, mock_r = make_cache()
        mock_r.ttl.side_effect = redis.RedisError("oops")
        assert cache.ttl("some:key") == -2


# ======================================================================= #
# Key naming conventions (documentation via test)                          #
# ======================================================================= #

class TestCacheKeyConventions:
    """Smoke tests that document the agreed key namespaces used by CTFVigil.

    These are not behavioural tests — they assert nothing about Redis.
    They serve as living documentation of the key schema.
    """

    KNOWN_KEY_PREFIXES = [
        "ctfvigil:events:upcoming",   # Periodic CTFtime feed cache
        "ctfvigil:ctfd:",             # Per-CTFd instance probe results (suffix = url hash)
    ]

    def test_key_prefixes_are_documented(self):
        """Ensure the key schema constants are non-empty strings."""
        for prefix in self.KNOWN_KEY_PREFIXES:
            assert isinstance(prefix, str)
            assert prefix.startswith("ctfvigil:")

