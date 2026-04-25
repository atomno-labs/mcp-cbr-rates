"""Tests for ``tools.get_rate``."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from mcp_cbr_rates.errors import (
    CbrApiError,
    CbrNotFoundError,
    CbrTimeoutError,
)
from mcp_cbr_rates.tools import get_rate

from .conftest import load_fixture


@pytest.mark.asyncio
async def test_get_rate_happy_path_latest(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        rate = await get_rate(tool_ctx, "USD")
    assert rate.char_code == "USD"
    assert rate.num_code == "840"
    assert rate.nominal == 1
    assert rate.value == Decimal("92.5012")
    assert rate.vunit_rate == Decimal("92.5012")
    assert rate.date == date(2024, 4, 25)
    assert rate.name == "Доллар США"


@pytest.mark.asyncio
async def test_get_rate_normalizes_lowercase_input(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        rate = await get_rate(tool_ctx, "usd")
    assert rate.char_code == "USD"


@pytest.mark.asyncio
async def test_get_rate_with_explicit_date_passes_param(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        route = router.get("/scripts/XML_daily.asp", params={"date_req": "25/04/2024"}).mock(
            return_value=httpx.Response(200, content=payload)
        )
        rate = await get_rate(tool_ctx, "EUR", on_date=date(2024, 4, 25))
    assert route.called
    assert rate.char_code == "EUR"


@pytest.mark.asyncio
async def test_get_rate_currency_not_in_response_raises_not_found(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        with pytest.raises(CbrNotFoundError):
            await get_rate(tool_ctx, "ZZZ")


@pytest.mark.asyncio
async def test_get_rate_invalid_input_raises_value_error(tool_ctx) -> None:
    with pytest.raises(ValueError):
        await get_rate(tool_ctx, "")


@pytest.mark.asyncio
async def test_get_rate_5xx_raises_api_error(tool_ctx) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(503, content=b"<html>oops</html>")
        )
        with pytest.raises(CbrApiError):
            await get_rate(tool_ctx, "USD")


@pytest.mark.asyncio
async def test_get_rate_timeout_raises_typed_error(tool_ctx) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(side_effect=httpx.ReadTimeout("slow"))
        with pytest.raises(CbrTimeoutError):
            await get_rate(tool_ctx, "USD")


@pytest.mark.asyncio
async def test_get_rate_uses_cache_on_second_call(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        route = router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        first = await get_rate(tool_ctx, "USD")
        second = await get_rate(tool_ctx, "USD")
    assert route.call_count == 1
    assert first == second


@pytest.mark.asyncio
async def test_get_rate_jpy_converts_per_unit_correctly(tool_ctx) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        rate = await get_rate(tool_ctx, "JPY")
    assert rate.nominal == 100
    assert rate.value == Decimal("59.9412")
    assert rate.vunit_rate == Decimal("0.599412")
