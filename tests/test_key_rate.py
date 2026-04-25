"""Tests for ``tools.key_rate``."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest
import respx

from mcp_cbr_rates.errors import CbrApiError, CbrTimeoutError, CbrValidationError
from mcp_cbr_rates.tools import key_rate

from .conftest import load_fixture


@pytest.mark.asyncio
async def test_key_rate_happy_path_returns_sorted_points(tool_ctx) -> None:
    soap = load_fixture("soap_keyrate.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(200, content=soap)
        )
        result = await key_rate(tool_ctx, date(2024, 4, 24), date(2024, 4, 26))
    assert len(result.points) == 3
    assert result.points[0].date == date(2024, 4, 24)
    assert result.points[-1].date == date(2024, 4, 26)
    assert result.points[0].rate == Decimal("16.00")


@pytest.mark.asyncio
async def test_key_rate_default_range_uses_last_30_days(tool_ctx) -> None:
    soap = load_fixture("soap_keyrate.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        route = router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(200, content=soap)
        )
        result = await key_rate(tool_ctx)
    assert route.called
    assert result.points  # non-empty


@pytest.mark.asyncio
async def test_key_rate_inverted_range_raises_validation_error(tool_ctx) -> None:
    with pytest.raises(CbrValidationError):
        await key_rate(tool_ctx, date(2024, 5, 1), date(2024, 4, 1))


@pytest.mark.asyncio
async def test_key_rate_5xx_raises_api_error(tool_ctx) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(503, content=b"down")
        )
        with pytest.raises(CbrApiError):
            await key_rate(tool_ctx, date(2024, 4, 1), date(2024, 4, 5))


@pytest.mark.asyncio
async def test_key_rate_timeout_raises_timeout_error(tool_ctx) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            side_effect=httpx.ConnectTimeout("slow")
        )
        with pytest.raises(CbrTimeoutError):
            await key_rate(tool_ctx, date(2024, 4, 1), date(2024, 4, 5))


@pytest.mark.asyncio
async def test_key_rate_caches_results(tool_ctx) -> None:
    soap = load_fixture("soap_keyrate.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        route = router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(200, content=soap)
        )
        await key_rate(tool_ctx, date(2024, 4, 24), date(2024, 4, 26))
        await key_rate(tool_ctx, date(2024, 4, 24), date(2024, 4, 26))
    assert route.call_count == 1
