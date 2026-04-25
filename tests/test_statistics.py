"""Tests for ``tools.statistics`` snapshot tool."""

from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
import respx

from mcp_cbr_rates.tools import statistics

from .conftest import load_fixture


@pytest.mark.asyncio
async def test_statistics_combines_all_sources(tool_ctx) -> None:
    daily = load_fixture("xml_daily_2024-04-25.xml")
    soap = load_fixture("soap_keyrate.xml")
    html = load_fixture("inflation.html")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=daily)
        )
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(200, content=soap)
        )
        router.get("/hd_base/infl/").mock(
            return_value=httpx.Response(200, content=html)
        )
        snap = await statistics(tool_ctx)
    assert snap.usd_rate == Decimal("92.5012")
    assert snap.eur_rate == Decimal("99.1331")
    assert snap.cny_rate == Decimal("12.7843")
    assert snap.key_rate_pct == Decimal("16.00")
    assert snap.inflation_yoy_pct is not None
    assert snap.inflation_period is not None


@pytest.mark.asyncio
async def test_statistics_tolerates_failed_components(tool_ctx) -> None:
    daily = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=daily)
        )
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(500, content=b"down")
        )
        router.get("/hd_base/infl/").mock(
            return_value=httpx.Response(500, content=b"down")
        )
        snap = await statistics(tool_ctx)
    assert snap.usd_rate == Decimal("92.5012")
    assert snap.key_rate_pct is None
    assert snap.inflation_yoy_pct is None


@pytest.mark.asyncio
async def test_statistics_handles_missing_currencies(tool_ctx) -> None:
    soap = load_fixture("soap_keyrate.xml")
    html = load_fixture("inflation.html")
    minimal_daily = (
        b'<?xml version="1.0" encoding="windows-1251"?>'
        b'<ValCurs Date="25.04.2024" name="Foreign Currency Market"></ValCurs>'
    )
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=minimal_daily)
        )
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(200, content=soap)
        )
        router.get("/hd_base/infl/").mock(
            return_value=httpx.Response(200, content=html)
        )
        snap = await statistics(tool_ctx)
    assert snap.usd_rate is None
    assert snap.eur_rate is None
    assert snap.key_rate_pct == Decimal("16.00")
