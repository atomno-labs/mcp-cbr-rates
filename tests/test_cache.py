"""Unit tests for the TTL cache."""

from __future__ import annotations

import asyncio

import pytest

from mcp_cbr_rates.cache import TTLCache


@pytest.mark.asyncio
async def test_cache_set_and_get_returns_same_value() -> None:
    cache = TTLCache(default_ttl=10.0)
    await cache.set("k", {"v": 42})
    assert await cache.get("k") == {"v": 42}


@pytest.mark.asyncio
async def test_cache_returns_none_for_missing_key() -> None:
    cache = TTLCache(default_ttl=10.0)
    assert await cache.get("absent") is None


@pytest.mark.asyncio
async def test_cache_expires_after_ttl() -> None:
    cache = TTLCache(default_ttl=0.05)
    await cache.set("k", "v")
    await asyncio.sleep(0.1)
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_cache_clear_drops_everything() -> None:
    cache = TTLCache(default_ttl=10.0)
    await cache.set("a", 1)
    await cache.set("b", 2)
    await cache.clear()
    assert await cache.get("a") is None
    assert await cache.get("b") is None


@pytest.mark.asyncio
async def test_cache_prune_removes_only_expired_entries() -> None:
    cache = TTLCache(default_ttl=10.0)
    await cache.set("fresh", 1, ttl=10.0)
    await cache.set("stale", 2, ttl=0.01)
    await asyncio.sleep(0.05)
    removed = await cache.prune()
    assert removed == 1
    assert await cache.get("fresh") == 1
    assert await cache.get("stale") is None


@pytest.mark.asyncio
async def test_cache_set_overrides_previous_value() -> None:
    cache = TTLCache(default_ttl=10.0)
    await cache.set("k", "first")
    await cache.set("k", "second")
    assert await cache.get("k") == "second"
