"""Тесты CLI-обвязки `atomno-mcp-cbr-rates`.

Покрывает:
  * `--help` / `-h` / `--version` / `-V` — exit 0, без запуска MCP-сервера.
  * `--transport` choices, `--host` / `--port` defaults.
  * Приоритет `--log-level` > MCP_CBR_LOG_LEVEL > legacy CBR_LOG_LEVEL > INFO.
  * Loud-fail на невалидный MCP_CBR_LOG_LEVEL (exit 2).
  * Backward-compat: legacy CBR_LOG_LEVEL работает с DeprecationWarning.

Тесты НЕ запускают `mcp.run()` — он мокается через monkeypatch.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from mcp_cbr_rates import __version__, server


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Изолировать тесты от глобальных env."""
    for var in (
        "MCP_CBR_LOG_LEVEL",
        "CBR_LOG_LEVEL",
        "MCP_CBR_HTTP_TIMEOUT",
        "CBR_HTTP_TIMEOUT",
        "MCP_CBR_CACHE_DAILY_TTL",
        "CBR_CACHE_DAILY_TTL",
        "MCP_CBR_CACHE_HISTORY_TTL",
        "CBR_CACHE_HISTORY_TTL",
    ):
        monkeypatch.delenv(var, raising=False)
    server._warned_legacy_envs.clear()


@pytest.fixture
def fake_run(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Substitute `mcp.run` with a recording stub — tests never actually start the server."""
    captured: dict[str, Any] = {"called": False, "kwargs": None}

    def _fake_run(**kwargs: Any) -> None:
        captured["called"] = True
        captured["kwargs"] = kwargs

    monkeypatch.setattr(server.mcp, "run", _fake_run)
    return captured


# ---------------------------------------------------------------------------
# --help / --version exit cleanly without starting the server.
# ---------------------------------------------------------------------------


class TestHelp:
    def test_long_flag_exits_zero(
        self, capsys: pytest.CaptureFixture[str], fake_run: dict[str, Any]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["--help"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "atomno-mcp-cbr-rates" in out
        assert "--transport" in out
        assert fake_run["called"] is False

    def test_short_flag_exits_zero(self, fake_run: dict[str, Any]) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["-h"])
        assert exc_info.value.code == 0
        assert fake_run["called"] is False


class TestVersion:
    def test_long_flag(
        self, capsys: pytest.CaptureFixture[str], fake_run: dict[str, Any]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["--version"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out.strip()
        assert out == f"atomno-mcp-cbr-rates {__version__}"
        assert fake_run["called"] is False

    def test_short_flag(
        self, capsys: pytest.CaptureFixture[str], fake_run: dict[str, Any]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["-V"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out.strip()
        assert out == f"atomno-mcp-cbr-rates {__version__}"

    def test_version_string_matches_package(self) -> None:
        """Защита от рассинхрона __init__.py vs pyproject.toml."""
        assert __version__ == server.__version__


# ---------------------------------------------------------------------------
# --transport — выбор и валидация.
# ---------------------------------------------------------------------------


class TestTransportValidation:
    def test_default_is_stdio(self, fake_run: dict[str, Any]) -> None:
        rc = server.main([])
        assert rc == 0
        assert fake_run["kwargs"] == {"transport": "stdio"}

    def test_explicit_stdio(self, fake_run: dict[str, Any]) -> None:
        rc = server.main(["--transport", "stdio"])
        assert rc == 0
        assert fake_run["kwargs"] == {"transport": "stdio"}

    @pytest.mark.parametrize("transport", ["http", "sse", "streamable-http"])
    def test_http_transports_pass_host_port(
        self, transport: str, fake_run: dict[str, Any]
    ) -> None:
        rc = server.main([
            "--transport", transport,
            "--host", "0.0.0.0",
            "--port", "9000",
        ])
        assert rc == 0
        assert fake_run["kwargs"] == {
            "transport": transport,
            "host": "0.0.0.0",
            "port": 9000,
        }

    def test_invalid_transport_exits_two(
        self, capsys: pytest.CaptureFixture[str], fake_run: dict[str, Any]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["--transport", "websocket"])
        assert exc_info.value.code == 2
        assert fake_run["called"] is False


# ---------------------------------------------------------------------------
# --log-level — приоритет CLI > MCP_CBR_LOG_LEVEL > CBR_LOG_LEVEL > INFO.
# ---------------------------------------------------------------------------


class TestLogLevelPrecedence:
    def test_cli_overrides_canonical_env(
        self, monkeypatch: pytest.MonkeyPatch, fake_run: dict[str, Any]
    ) -> None:
        monkeypatch.setenv("MCP_CBR_LOG_LEVEL", "WARNING")
        rc = server.main(["--log-level", "DEBUG"])
        assert rc == 0
        assert logging.getLogger().level == logging.DEBUG

    def test_cli_overrides_legacy_env(
        self, monkeypatch: pytest.MonkeyPatch, fake_run: dict[str, Any]
    ) -> None:
        monkeypatch.setenv("CBR_LOG_LEVEL", "WARNING")
        rc = server.main(["--log-level", "DEBUG"])
        assert rc == 0
        assert logging.getLogger().level == logging.DEBUG

    def test_canonical_env(
        self, monkeypatch: pytest.MonkeyPatch, fake_run: dict[str, Any]
    ) -> None:
        monkeypatch.setenv("MCP_CBR_LOG_LEVEL", "WARNING")
        rc = server.main([])
        assert rc == 0
        assert logging.getLogger().level == logging.WARNING

    def test_canonical_wins_over_legacy(
        self, monkeypatch: pytest.MonkeyPatch, fake_run: dict[str, Any]
    ) -> None:
        monkeypatch.setenv("MCP_CBR_LOG_LEVEL", "ERROR")
        monkeypatch.setenv("CBR_LOG_LEVEL", "DEBUG")
        rc = server.main([])
        assert rc == 0
        assert logging.getLogger().level == logging.ERROR

    def test_legacy_env_used_when_canonical_absent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        fake_run: dict[str, Any],
    ) -> None:
        monkeypatch.setenv("CBR_LOG_LEVEL", "WARNING")
        with caplog.at_level(logging.WARNING, logger="mcp_cbr_rates"):
            rc = server.main([])
        assert rc == 0
        assert logging.getLogger().level == logging.WARNING
        deprecations = [
            rec for rec in caplog.records
            if rec.name == "mcp_cbr_rates" and "CBR_LOG_LEVEL" in rec.message
        ]
        assert len(deprecations) >= 1
        assert "deprecated" in deprecations[0].message.lower()

    def test_default_info(self, fake_run: dict[str, Any]) -> None:
        rc = server.main([])
        assert rc == 0
        assert logging.getLogger().level == logging.INFO


class TestInvalidEnvBailsOutCleanly:
    def test_invalid_canonical_env_exits_two(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        fake_run: dict[str, Any],
    ) -> None:
        monkeypatch.setenv("MCP_CBR_LOG_LEVEL", "TRACE")
        with pytest.raises(SystemExit) as exc_info:
            server.main([])
        assert exc_info.value.code == 2
        assert fake_run["called"] is False
        err = capsys.readouterr().err
        assert "MCP_CBR_LOG_LEVEL" in err

    def test_invalid_cli_log_level_argparse_rejects(
        self, capsys: pytest.CaptureFixture[str], fake_run: dict[str, Any]
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            server.main(["--log-level", "TRACE"])
        assert exc_info.value.code == 2


# ---------------------------------------------------------------------------
# Парсер защищает дефолты host/port.
# ---------------------------------------------------------------------------


class TestParserDefaults:
    def test_host_default_is_localhost(self) -> None:
        ns = server._build_arg_parser().parse_args([])
        assert ns.host == "127.0.0.1"

    def test_port_default_is_8000(self) -> None:
        ns = server._build_arg_parser().parse_args([])
        assert ns.port == 8000

    def test_port_parsed_as_int(self) -> None:
        ns = server._build_arg_parser().parse_args(["--port", "12345"])
        assert ns.port == 12345
        assert isinstance(ns.port, int)


# ---------------------------------------------------------------------------
# Backward-compat: tunable env-vars (MCP_CBR_HTTP_TIMEOUT etc.) и legacy.
# ---------------------------------------------------------------------------


class TestEnvBackwardCompat:
    def test_legacy_http_timeout_used(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setenv("CBR_HTTP_TIMEOUT", "12.5")
        with caplog.at_level(logging.WARNING, logger="mcp_cbr_rates"):
            value = server._read_float_env("MCP_CBR_HTTP_TIMEOUT", default=10.0)
        assert value == 12.5
        deprecations = [
            rec for rec in caplog.records
            if rec.name == "mcp_cbr_rates" and "CBR_HTTP_TIMEOUT" in rec.message
        ]
        assert len(deprecations) == 1

    def test_canonical_http_timeout_no_warning(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setenv("MCP_CBR_HTTP_TIMEOUT", "7.0")
        with caplog.at_level(logging.WARNING, logger="mcp_cbr_rates"):
            value = server._read_float_env("MCP_CBR_HTTP_TIMEOUT", default=10.0)
        assert value == 7.0
        assert not any("deprecated" in rec.message.lower() for rec in caplog.records)

    def test_legacy_warning_emitted_only_once_per_process(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        monkeypatch.setenv("CBR_HTTP_TIMEOUT", "12.5")
        with caplog.at_level(logging.WARNING, logger="mcp_cbr_rates"):
            server._read_float_env("MCP_CBR_HTTP_TIMEOUT", default=10.0)
            server._read_float_env("MCP_CBR_HTTP_TIMEOUT", default=10.0)
            server._read_float_env("MCP_CBR_HTTP_TIMEOUT", default=10.0)
        deprecations = [
            rec for rec in caplog.records
            if rec.name == "mcp_cbr_rates" and "CBR_HTTP_TIMEOUT" in rec.message
        ]
        assert len(deprecations) == 1
