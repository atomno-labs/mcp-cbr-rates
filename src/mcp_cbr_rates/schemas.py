"""Pydantic v2 models describing inputs and outputs of every MCP tool.

All public tool functions accept primitive arguments (validated via Pydantic
adapters in ``tools.py``) and return one of the response models defined here.
"""

from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_SOURCE = "Центральный банк РФ"


class CbrModel(BaseModel):
    """Base model with strict configuration for safer round-trips."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
        str_strip_whitespace=True,
    )


class CurrencyRate(CbrModel):
    """A single currency quote at a given date."""

    char_code: str = Field(..., description="ISO-letter code, e.g. 'USD'.")
    num_code: str = Field(..., description="Numeric ISO 4217 code as string, e.g. '840'.")
    name: str = Field(..., description="Russian-language currency name from CBR.")
    nominal: int = Field(..., ge=1, description="Number of foreign units the rate is given for.")
    value: Decimal = Field(..., description="Rate of <nominal> units in RUB.")
    vunit_rate: Decimal = Field(..., description="Rate per single unit (value / nominal).")
    date: _dt.date = Field(..., description="Effective quote date as published by CBR.")
    source: str = DEFAULT_SOURCE


class RatePoint(CbrModel):
    """One observation in a historical rate series."""

    date: _dt.date
    value: Decimal
    vunit_rate: Decimal


class HistoryRates(CbrModel):
    """A historical series of quotes for a single currency."""

    char_code: str
    name: str
    nominal: int
    date_from: _dt.date
    date_to: _dt.date
    points: list[RatePoint]
    source: str = DEFAULT_SOURCE


class KeyRatePoint(CbrModel):
    """One observation in the CBR key-rate series."""

    date: _dt.date
    rate: Decimal = Field(..., description="Key rate as a percentage, e.g. 16.00.")


class KeyRateHistory(CbrModel):
    """Key-rate observations between ``date_from`` and ``date_to`` (inclusive)."""

    date_from: _dt.date
    date_to: _dt.date
    points: list[KeyRatePoint]
    source: str = DEFAULT_SOURCE


class InflationPoint(CbrModel):
    """Monthly inflation observation."""

    year: int = Field(..., ge=1900, le=2100)
    month: int = Field(..., ge=1, le=12)
    cpi_mom_pct: Decimal | None = Field(
        default=None,
        description="Month-over-month CPI change in percent (e.g. 0.50).",
    )
    cpi_yoy_pct: Decimal | None = Field(
        default=None,
        description="Year-over-year CPI change in percent (e.g. 7.50).",
    )


class InflationData(CbrModel):
    """A range of monthly inflation observations."""

    year_from: int
    year_to: int
    points: list[InflationPoint]
    source: str = DEFAULT_SOURCE
    note: str | None = Field(
        default=None,
        description="Optional caveat (for example, when data is bundled rather than live-fetched).",
    )


class MacroSnapshot(CbrModel):
    """High-level dashboard combining several CBR indicators."""

    as_of: _dt.date
    key_rate_pct: Decimal | None = None
    usd_rate: Decimal | None = None
    eur_rate: Decimal | None = None
    cny_rate: Decimal | None = None
    inflation_yoy_pct: Decimal | None = None
    inflation_period: str | None = Field(
        default=None,
        description="ISO 'YYYY-MM' string of the inflation observation included in the snapshot.",
    )
    source: str = DEFAULT_SOURCE
