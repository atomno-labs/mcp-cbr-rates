# Changelog

All notable changes to `mcp-cbr-rates` are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-04-25

### Added

- Initial MVP release.
- Five MCP tools: `get_rate`, `history_rates`, `key_rate`, `inflation`, `statistics`.
- `CbrClient` wrapping CBR XML scripts and SOAP web service via `httpx.AsyncClient`.
- In-memory async TTL cache (1h for daily lookups, 24h for historical series).
- Pydantic v2 schemas for every tool input and output.
- `respx`-based unit tests with recorded XML fixtures, coverage ≥ 80 %.
- MIT license, README with quickstart for Cursor / Claude Desktop / Claude Code.
