"""
ctfvigil/cache.py
~~~~~~~~~~~~~~~~~
Thin Redis cache wrapper for CTFVigil.

Provides a ``RedisCache`` class with a JSON-serialised get/set/delete
interface, and a ``get_client()`` factory that reads ``REDIS_URL`` from
the environment.

Usage::

    from ctfvigil.cache import RedisCache, get_client

    cache = RedisCache(get_client())
    cache.set("ctfvigil:events:upcoming", events, ttl=3600)
    events = cache.get("ctfvigil:events:upcoming")
    cache.delete("ctfvigil:events:upcoming")
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import redis

logger = logging.getLogger(__name__)

# Default TTL (seconds) used when the caller does not supply one — 1 hour.
DEFAULT_TTL = 3600

# Environment variable name consumed by get_client().
_REDIS_URL_ENV = "REDIS_URL"
_REDIS_URL_FALLBACK = "redis://localhost:6379/0"


def get_client() -> redis.Redis:
    """Create and return a Redis client from the ``REDIS_URL`` environment variable.

    Falls back to ``redis://localhost:6379/0`` when the variable is absent,
    matching the docker-compose default for local development.

    The client is configured with:
    - ``decode_responses=True`` so all values come back as ``str``, not ``bytes``.
    - A 5-second socket connect/read timeout to avoid hanging indefinitely.
    """
    url = os.getenv(_REDIS_URL_ENV, _REDIS_URL_FALLBACK)
    return redis.Redis.from_url(
        url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


class RedisCache:
    """JSON-serialising cache backed by Redis.

    All values are serialised to JSON before storage and deserialised on
    retrieval, so callers work with native Python objects (dicts, lists,
    strings, numbers) rather than raw byte strings.

    Args:
        client: A ``redis.Redis`` instance. Pass a mock in tests.
    """

    def __init__(self, client: redis.Redis) -> None:
        self._r = client

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Any | None:
        """Return the cached value for *key*, or ``None`` if absent / expired.

        Args:
            key: Redis key string.

        Returns:
            The deserialised Python object, or ``None`` when the key does
            not exist or has expired.
        """
        try:
            raw = self._r.get(key)
        except redis.RedisError as exc:
            logger.error("RedisCache.get(%r) failed: %s", key, exc)
            return None

        if raw is None:
            return None

        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            logger.warning("RedisCache.get(%r) — JSON decode failed: %s", key, exc)
            return None

    def set(self, key: str, value: Any, ttl: int | None = DEFAULT_TTL) -> bool:
        """Serialise *value* to JSON and store it under *key*.

        Args:
            key:   Redis key string.
            value: Any JSON-serialisable Python object.
            ttl:   Time-to-live in seconds. ``None`` stores without expiry
                   (use sparingly — prefer always setting a TTL).

        Returns:
            ``True`` on success, ``False`` if the write failed.
        """
        try:
            payload = json.dumps(value, default=str)
        except (TypeError, ValueError) as exc:
            logger.error("RedisCache.set(%r) — JSON encode failed: %s", key, exc)
            return False

        try:
            if ttl is not None:
                self._r.setex(key, ttl, payload)
            else:
                self._r.set(key, payload)
            return True
        except redis.RedisError as exc:
            logger.error("RedisCache.set(%r) failed: %s", key, exc)
            return False

    def delete(self, key: str) -> bool:
        """Delete *key* from the cache.

        Args:
            key: Redis key string.

        Returns:
            ``True`` if the key existed and was deleted, ``False`` otherwise.
        """
        try:
            deleted = self._r.delete(key)
            return deleted > 0
        except redis.RedisError as exc:
            logger.error("RedisCache.delete(%r) failed: %s", key, exc)
            return False

    def exists(self, key: str) -> bool:
        """Return ``True`` if *key* exists in the cache (not expired).

        Args:
            key: Redis key string.
        """
        try:
            return bool(self._r.exists(key))
        except redis.RedisError as exc:
            logger.error("RedisCache.exists(%r) failed: %s", key, exc)
            return False

    def ttl(self, key: str) -> int:
        """Return the remaining TTL (seconds) for *key*.

        Returns:
            Remaining seconds, ``-1`` if the key has no expiry, or ``-2``
            if the key does not exist. Mirrors the raw Redis ``TTL`` semantics.
        """
        try:
            return self._r.ttl(key)
        except redis.RedisError as exc:
            logger.error("RedisCache.ttl(%r) failed: %s", key, exc)
            return -2
