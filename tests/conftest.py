"""Shared pytest fixtures for ``mcp-cbr-rates``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

from mcp_cbr_rates.cache import TTLCache
from mcp_cbr_rates.client import CbrClient
from mcp_cbr_rates.tools import ToolContext

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    """A real ``httpx.AsyncClient`` whose transport will be intercepted by respx."""
    async with httpx.AsyncClient(
        base_url="https://www.cbr.ru",
        timeout=5.0,
        headers={"User-Agent": "mcp-cbr-rates/test"},
    ) as client:
        yield client


@pytest_asyncio.fixture
async def cbr_client(http_client: httpx.AsyncClient) -> AsyncIterator[CbrClient]:
    client = CbrClient(http_client=http_client)
    try:
        yield client
    finally:
        await client.aclose()


@pytest_asyncio.fixture
async def tool_ctx(cbr_client: CbrClient) -> AsyncIterator[ToolContext]:
    yield ToolContext(
        client=cbr_client,
        daily_cache=TTLCache(default_ttl=60.0),
        history_cache=TTLCache(default_ttl=120.0),
    )
