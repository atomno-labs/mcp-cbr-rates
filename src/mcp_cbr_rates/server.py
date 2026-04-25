"""FastMCP entry point for ``mcp-cbr-rates``.

Run as:

    python -m mcp_cbr_rates
    # or, after `pip install .`:
    mcp-cbr-rates
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date

import httpx
from mcp.server.fastmcp import Context, FastMCP

from . import __version__
from .cache import TTLCache
from .client import DEFAULT_TIMEOUT, CbrClient
from .errors import CbrError
from .schemas import (
    CurrencyRate,
    HistoryRates,
    InflationData,
    KeyRateHistory,
    MacroSnapshot,
)
from .tools import (
    DEFAULT_DAILY_TTL,
    DEFAULT_HISTORY_TTL,
    ToolContext,
)
from .tools import (
    get_rate as _get_rate,
)
from .tools import (
    history_rates as _history_rates,
)
from .tools import (
    inflation as _inflation,
)
from .tools import (
    key_rate as _key_rate,
)
from .tools import (
    statistics as _statistics,
)

logger = logging.getLogger("mcp_cbr_rates")


def _read_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("invalid float in env var %s=%r, using %s", name, raw, default)
        return default


def build_tool_context() -> tuple[ToolContext, httpx.AsyncClient]:
    """Construct the ``ToolContext`` used by every tool, returning the owned HTTP client."""
    timeout = _read_float_env("CBR_HTTP_TIMEOUT", DEFAULT_TIMEOUT)
    daily_ttl = _read_float_env("CBR_CACHE_DAILY_TTL", DEFAULT_DAILY_TTL)
    history_ttl = _read_float_env("CBR_CACHE_HISTORY_TTL", DEFAULT_HISTORY_TTL)

    http_client = httpx.AsyncClient(
        timeout=timeout,
        headers={
            "User-Agent": f"mcp-cbr-rates/{__version__} (+https://github.com/atomno-labs/mcp-cbr-rates)",
            "Accept": "application/xml,text/xml,*/*",
        },
        transport=httpx.AsyncHTTPTransport(retries=2),
    )
    cbr = CbrClient(http_client=http_client, timeout=timeout)
    daily_cache = TTLCache(default_ttl=daily_ttl)
    history_cache = TTLCache(default_ttl=history_ttl)
    return ToolContext(client=cbr, daily_cache=daily_cache, history_cache=history_cache), http_client


@asynccontextmanager
async def _lifespan(_server: FastMCP) -> AsyncIterator[ToolContext]:
    ctx, http_client = build_tool_context()
    try:
        yield ctx
    finally:
        try:
            await ctx.client.aclose()
        finally:
            await http_client.aclose()


mcp = FastMCP(
    name="mcp-cbr-rates",
    instructions=(
        "Tools for the public Bank of Russia (CBR) data: currency quotes, key"
        " rate, inflation, and a compact macro snapshot. All data comes from"
        " cbr.ru and is cached briefly to be polite."
    ),
    lifespan=_lifespan,
)


def _ctx(ctx: Context) -> ToolContext:
    """Resolve the lifespan-provided ToolContext from the request context."""
    lifespan_ctx = ctx.request_context.lifespan_context
    if not isinstance(lifespan_ctx, ToolContext):  # pragma: no cover
        raise RuntimeError("server is not initialized: missing ToolContext")
    return lifespan_ctx


def _format_error(exc: Exception) -> str:
    name = type(exc).__name__
    return f"{name}: {exc}"


@mcp.tool(
    name="get_rate",
    description=(
        "Get the official Bank of Russia exchange rate for a single currency"
        " on a given date (or the latest published date if 'on_date' is omitted)."
        " Returns nominal, value, per-unit rate and effective quote date."
    ),
)
async def tool_get_rate(
    ctx: Context,
    char_code: str,
    on_date: date | None = None,
) -> CurrencyRate:
    try:
        return await _get_rate(_ctx(ctx), char_code=char_code, on_date=on_date)
    except CbrError as exc:
        raise RuntimeError(_format_error(exc)) from exc


@mcp.tool(
    name="history_rates",
    description=(
        "Get the official CBR exchange-rate series for a single currency between"
        " two dates inclusive. Range capped at 366 days; for longer windows call"
        " repeatedly."
    ),
)
async def tool_history_rates(
    ctx: Context,
    char_code: str,
    date_from: date,
    date_to: date,
) -> HistoryRates:
    try:
        return await _history_rates(
            _ctx(ctx), char_code=char_code, date_from=date_from, date_to=date_to
        )
    except CbrError as exc:
        raise RuntimeError(_format_error(exc)) from exc


@mcp.tool(
    name="key_rate",
    description=(
        "Get the CBR key-rate (ставка рефинансирования) time series for the"
        " requested range. Defaults to the most recent 30 days."
    ),
)
async def tool_key_rate(
    ctx: Context,
    date_from: date | None = None,
    date_to: date | None = None,
) -> KeyRateHistory:
    try:
        return await _key_rate(_ctx(ctx), date_from=date_from, date_to=date_to)
    except CbrError as exc:
        raise RuntimeError(_format_error(exc)) from exc


@mcp.tool(
    name="inflation",
    description=(
        "Get monthly year-over-year consumer price index (CPI) inflation as"
        " published by CBR for the given year range (defaults to the previous"
        " and current year)."
    ),
)
async def tool_inflation(
    ctx: Context,
    year_from: int | None = None,
    year_to: int | None = None,
) -> InflationData:
    try:
        return await _inflation(_ctx(ctx), year_from=year_from, year_to=year_to)
    except CbrError as exc:
        raise RuntimeError(_format_error(exc)) from exc


@mcp.tool(
    name="statistics",
    description=(
        "Get a compact macro snapshot: latest key rate, USD/EUR/CNY rates,"
        " latest YoY inflation, and the period the inflation refers to."
    ),
)
async def tool_statistics(ctx: Context) -> MacroSnapshot:
    try:
        return await _statistics(_ctx(ctx))
    except CbrError as exc:
        raise RuntimeError(_format_error(exc)) from exc


def main() -> None:
    """Console entry point — runs the MCP server over stdio transport."""
    logging.basicConfig(
        level=os.environ.get("CBR_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
