from __future__ import annotations

from decimal import Decimal

import pytest

from creator_monitor.config import Settings
from creator_monitor.errors import ConfigurationError


def test_settings_load_and_redact_secrets(tmp_path) -> None:
    secret = "super-secret-tikhub-token"
    settings = Settings.from_env(
        {
            "TIKHUB_API_KEY": secret,
            "CREATOR_MONITOR_BASE_TOKEN": "base-token",
            "CREATOR_MONITOR_STATE_DIR": str(tmp_path),
            "CREATOR_MONITOR_MAX_USD": "0.50",
            "CREATOR_MONITOR_MAX_REQUESTS_PER_RUN": "20",
        }
    )

    assert settings.tikhub_api_key.get_secret_value() == secret
    assert settings.max_usd == Decimal("0.50")
    assert settings.max_requests_per_run == 20
    summary = settings.safe_summary()
    assert secret not in repr(summary)
    assert summary["tikhub_api_key"] == "configured"
    assert summary["base_token"] == "configured"


def test_live_config_fails_closed_without_api_key(tmp_path) -> None:
    settings = Settings.from_env({"CREATOR_MONITOR_STATE_DIR": str(tmp_path)})

    with pytest.raises(ConfigurationError, match="TIKHUB_API_KEY"):
        settings.require_tikhub()


def test_invalid_budget_does_not_echo_secret(tmp_path) -> None:
    secret = "never-print-this-value"
    with pytest.raises(ConfigurationError) as error:
        Settings.from_env(
            {
                "TIKHUB_API_KEY": secret,
                "CREATOR_MONITOR_STATE_DIR": str(tmp_path),
                "CREATOR_MONITOR_MAX_USD": "not-a-number",
            }
        )
    assert secret not in str(error.value)
