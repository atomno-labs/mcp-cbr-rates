"""Lower-level tests against ``CbrClient`` directly."""

from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from mcp_cbr_rates.client import CbrClient
from mcp_cbr_rates.errors import (
    CbrApiError,
    CbrNotFoundError,
    CbrParseError,
    CbrTimeoutError,
)

from .conftest import load_fixture


@pytest.mark.asyncio
async def test_client_fetch_daily_rates_parses_all_currencies(cbr_client: CbrClient) -> None:
    payload = load_fixture("xml_daily_2024-04-25.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        rates = await cbr_client.fetch_daily_rates()
    assert set(rates.keys()) == {"USD", "EUR", "CNY", "JPY"}
    assert rates["USD"]["value"] == "92,5012"
    assert rates["JPY"]["nominal"] == "100"


@pytest.mark.asyncio
async def test_client_fetch_daily_rates_404_raises_not_found(cbr_client: CbrClient) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(404, content=b"not here")
        )
        with pytest.raises(CbrNotFoundError):
            await cbr_client.fetch_daily_rates()


@pytest.mark.asyncio
async def test_client_fetch_daily_rates_invalid_xml_raises_parse_error(
    cbr_client: CbrClient,
) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=b"<not-xml")
        )
        with pytest.raises(CbrParseError):
            await cbr_client.fetch_daily_rates()


@pytest.mark.asyncio
async def test_client_lookup_cbr_id_resolves_iso_code(cbr_client: CbrClient) -> None:
    payload = load_fixture("xml_valfull.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_valFull.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        cbr_id = await cbr_client._lookup_cbr_id("XPH")
    assert cbr_id == "R01999"


@pytest.mark.asyncio
async def test_client_lookup_cbr_id_returns_none_for_unknown(cbr_client: CbrClient) -> None:
    payload = load_fixture("xml_valfull.xml")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_valFull.asp").mock(
            return_value=httpx.Response(200, content=payload)
        )
        cbr_id = await cbr_client._lookup_cbr_id("ABC")
    assert cbr_id is None


@pytest.mark.asyncio
async def test_client_post_timeout_raises_typed_error(cbr_client: CbrClient) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            side_effect=httpx.ReadTimeout("slow")
        )
        with pytest.raises(CbrTimeoutError):
            await cbr_client.fetch_key_rate(date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_client_post_5xx_raises_api_error(cbr_client: CbrClient) -> None:
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.post("/DailyInfoWebServ/DailyInfo.asmx").mock(
            return_value=httpx.Response(502, content=b"bad gateway")
        )
        with pytest.raises(CbrApiError):
            await cbr_client.fetch_key_rate(date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_client_handles_windows1251_encoded_response(cbr_client: CbrClient) -> None:
    """Real CBR responses use windows-1251 — make sure defusedxml decodes them."""
    body = (
        '<?xml version="1.0" encoding="windows-1251"?>'
        '<ValCurs Date="01.06.2024" name="Foreign Currency Market">'
        '<Valute ID="R01235">'
        "<NumCode>840</NumCode>"
        "<CharCode>USD</CharCode>"
        "<Nominal>1</Nominal>"
        "<Name>Доллар США</Name>"
        "<Value>91,1234</Value>"
        "<VunitRate>91.1234</VunitRate>"
        "</Valute>"
        "</ValCurs>"
    ).encode("cp1251")
    with respx.mock(base_url="https://www.cbr.ru") as router:
        router.get("/scripts/XML_daily.asp").mock(
            return_value=httpx.Response(200, content=body)
        )
        rates = await cbr_client.fetch_daily_rates()
    assert rates["USD"]["name"] == "Доллар США"


@pytest.mark.asyncio
async def test_client_currency_codes_normalize_rejects_garbage() -> None:
    from mcp_cbr_rates.currency_codes import normalize_char_code

    with pytest.raises(ValueError):
        normalize_char_code("US1")
    with pytest.raises(ValueError):
        normalize_char_code("VERYLONG")
    with pytest.raises(ValueError):
        normalize_char_code("")
