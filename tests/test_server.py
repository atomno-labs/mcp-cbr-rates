"""Smoke tests for the FastMCP-based server module.

These do not start an actual MCP transport — they verify the server object is
constructed correctly, the lifespan factory builds a usable ``ToolContext``,
and the expected tools are registered.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from mcp_cbr_rates import server as server_module
from mcp_cbr_rates.tools import ToolContext


def test_server_exposes_expected_tools() -> None:
    expected = {"get_rate", "history_rates", "key_rate", "inflation", "statistics"}
    registered = {tool.name for tool in server_module.mcp._tool_manager.list_tools()}
    assert expected.issubset(registered)


def test_server_module_main_callable() -> None:
    assert callable(server_module.main)


@pytest.mark.asyncio
async def test_build_tool_context_returns_initialized_dependencies() -> None:
    ctx, http_client = server_module.build_tool_context()
    try:
        assert isinstance(ctx, ToolContext)
        assert ctx.client is not None
        assert ctx.daily_cache is not None
        assert ctx.history_cache is not None
        assert http_client is not None
    finally:
        await ctx.client.aclose()
        await http_client.aclose()


def test_build_tool_context_respects_env_overrides() -> None:
    with patch.dict(
        os.environ,
        {
            "CBR_HTTP_TIMEOUT": "5",
            "CBR_CACHE_DAILY_TTL": "60",
            "CBR_CACHE_HISTORY_TTL": "120",
        },
        clear=False,
    ):
        ctx, http_client = server_module.build_tool_context()
    assert ctx.daily_cache._default_ttl == 60.0
    assert ctx.history_cache._default_ttl == 120.0


def test_build_tool_context_falls_back_on_invalid_env(caplog) -> None:
    with patch.dict(os.environ, {"CBR_HTTP_TIMEOUT": "not-a-number"}, clear=False):
        ctx, http_client = server_module.build_tool_context()
    assert ctx is not None
    assert http_client is not None


def test_format_error_renders_type_and_message() -> None:
    from mcp_cbr_rates.errors import CbrApiError

    msg = server_module._format_error(CbrApiError("boom"))
    assert "CbrApiError" in msg
    assert "boom" in msg
