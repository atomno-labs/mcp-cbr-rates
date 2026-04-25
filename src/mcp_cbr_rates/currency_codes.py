"""Static lookup table mapping ISO letter codes to CBR ``VAL_NM_RQ`` identifiers.

CBR's ``XML_dynamic.asp`` endpoint requires the internal CBR identifier, not the
ISO code. The mapping below covers the vast majority of currencies that have
been quoted by CBR continuously since the 1990s.

If a request arrives for a code not present here, ``CbrClient`` falls back to
``XML_valFull.asp`` to discover it dynamically.
"""

from __future__ import annotations

from typing import Final

CHAR_CODE_TO_CBR_ID: Final[dict[str, str]] = {
    "AUD": "R01010",
    "AZN": "R01020A",
    "GBP": "R01035",
    "AMD": "R01060",
    "BYN": "R01090B",
    "BGN": "R01100",
    "BRL": "R01115",
    "HUF": "R01135",
    "HKD": "R01200",
    "DKK": "R01215",
    "USD": "R01235",
    "EUR": "R01239",
    "INR": "R01270",
    "KZT": "R01335",
    "CAD": "R01350",
    "KGS": "R01370",
    "CNY": "R01375",
    "MDL": "R01500",
    "NOK": "R01535",
    "PLN": "R01565",
    "RON": "R01585F",
    "XDR": "R01589",
    "SGD": "R01625",
    "TJS": "R01670",
    "TRY": "R01700J",
    "TMT": "R01710A",
    "UZS": "R01717",
    "UAH": "R01720",
    "CZK": "R01760",
    "SEK": "R01770",
    "CHF": "R01775",
    "ZAR": "R01810",
    "KRW": "R01815",
    "JPY": "R01820",
    "RSD": "R01805F",
    "VND": "R01820A",
}


def normalize_char_code(char_code: str) -> str:
    """Return the canonical upper-case form, or raise ``ValueError`` if empty."""
    code = (char_code or "").strip().upper()
    if not code:
        raise ValueError("char_code must be a non-empty string")
    if not code.isalpha() or len(code) > 4:
        raise ValueError(f"invalid currency code: {char_code!r}")
    return code


def get_cbr_id(char_code: str) -> str | None:
    """Return the CBR ``VAL_NM_RQ`` for a currency ISO code, or ``None``."""
    return CHAR_CODE_TO_CBR_ID.get(normalize_char_code(char_code))
