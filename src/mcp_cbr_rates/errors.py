"""Typed exceptions raised by the CBR client and tool layer.

These exceptions are caught at the MCP boundary in ``server.py`` and converted
into structured error responses for the agent.
"""

from __future__ import annotations


class CbrError(Exception):
    """Base class for all errors originating from this package."""


class CbrValidationError(CbrError):
    """Input validation failed before any HTTP call was made."""


class CbrNotFoundError(CbrError):
    """Requested resource (currency, date, etc.) was not found at CBR."""


class CbrApiError(CbrError):
    """CBR API returned an HTTP error or unexpected payload."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CbrTimeoutError(CbrError):
    """CBR API did not respond within the configured timeout."""


class CbrParseError(CbrError):
    """CBR API responded but the payload could not be parsed."""
