from __future__ import annotations

from typer.testing import CliRunner

from creator_monitor.cli import app


def test_cli_exposes_operational_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "doctor" in result.stdout
    assert "bootstrap" in result.stdout
    assert "scheduled-sync" in result.stdout
