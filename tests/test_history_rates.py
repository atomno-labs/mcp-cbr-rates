"""Tests for ``tools.history_rates``."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from mcp_cbr_rates.errors import CbrNotFoundError, CbrValidationError
from mcp_cbr_rates.tools import history_rates

from .conftest import load_fixture


@pytest.mark.asyncio
async def test_history_rates_happy_path_returns_sorted_points(tool_ctx) -> None:
    dyn = load_fixture("xml_dynamic_usd.xml")
    daily = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_dynamic.asp").mock(
            return_value=httpx.Response(200, content=dyn)
        )
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=daily)
        )
        result = await history_rates(
            tool_ctx, "USD", date(2024, 4, 1), date(2024, 4, 5)
        )
    assert result.char_code == "USD"
    assert len(result.points) == 4
    assert result.points[0].date == date(2024, 4, 2)
    assert result.points[-1].date == date(2024, 4, 5)
    assert result.points[0].value == Decimal("92.7549")
    assert result.name in {"Доллар США", "USD"}


@pytest.mark.asyncio
async def test_history_rates_rejects_inverted_range(tool_ctx) -> None:
    with pytest.raises(CbrValidationError):
        await history_rates(tool_ctx, "USD", date(2024, 4, 5), date(2024, 4, 1))


@pytest.mark.asyncio
async def test_history_rates_rejects_too_long_range(tool_ctx) -> None:
    with pytest.raises(CbrValidationError):
        await history_rates(tool_ctx, "USD", date(2020, 1, 1), date(2024, 1, 1))


@pytest.mark.asyncio
async def test_history_rates_empty_response_raises_not_found(tool_ctx) -> None:
    empty = (
        b'<?xml version="1.0" encoding="windows-1251"?>'
        b'<ValCurs ID="R01235" DateRange1="01.04.2024" DateRange2="05.04.2024" name="Foreign Currency Market Dynamic"></ValCurs>'
    )
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_dynamic.asp").mock(
            return_value=httpx.Response(200, content=empty)
        )
        with pytest.raises(CbrNotFoundError):
            await history_rates(
                tool_ctx, "USD", date(2024, 4, 1), date(2024, 4, 5)
            )


@pytest.mark.asyncio
async def test_history_rates_unknown_currency_raises_not_found(tool_ctx) -> None:
    valfull = load_fixture("xml_valfull.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_valFull.asp").mock(
            return_value=httpx.Response(200, content=valfull)
        )
        with pytest.raises(CbrNotFoundError):
            await history_rates(
                tool_ctx, "AAA", date(2024, 4, 1), date(2024, 4, 5)
            )


@pytest.mark.asyncio
async def test_history_rates_uses_lookup_for_unknown_code(tool_ctx) -> None:
    dyn = load_fixture("xml_dynamic_usd.xml")
    valfull = load_fixture("xml_valfull.xml")
    daily = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_valFull.asp").mock(
            return_value=httpx.Response(200, content=valfull)
        )
        router.get("/scripts/XML_dynamic.asp").mock(
            return_value=httpx.Response(200, content=dyn)
        )
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=daily)
        )
        result = await history_rates(
            tool_ctx, "XPH", date(2024, 4, 1), date(2024, 4, 5)
        )
    assert result.char_code == "XPH"
    assert len(result.points) == 4


@pytest.mark.asyncio
async def test_history_rates_caches_repeated_queries(tool_ctx) -> None:
    dyn = load_fixture("xml_dynamic_usd.xml")
    daily = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        dynamic_route = router.get("/scripts/XML_dynamic.asp").mock(
            return_value=httpx.Response(200, content=dyn)
        )
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=daily)
        )
        await history_rates(tool_ctx, "USD", date(2024, 4, 1), date(2024, 4, 5))
        await history_rates(tool_ctx, "USD", date(2024, 4, 1), date(2024, 4, 5))
    assert dynamic_route.call_count == 1
