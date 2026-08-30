from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from creator_monitor.errors import ConfigurationError


class Settings(BaseModel):
    """Validated local runtime configuration.

    Secrets are represented as ``SecretStr`` and are never included in the
    public summary used by commands or logs.
    """

    model_config = ConfigDict(frozen=True)

    tikhub_api_key: SecretStr | None = None
    base_token: SecretStr | None = None
    state_dir: Path = Path("runtime")
    config_path: Path = Path("runtime/config.json")
    max_usd: Decimal = Field(default=Decimal("0.50"), gt=0)
    max_requests_per_run: int = Field(default=20, ge=1, le=1000)
    keychain_service: str = "creator-monitor-tikhub"
    report_user_id: str | None = None
    analysis_url: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        api_key = source.get("TIKHUB_API_KEY") or None
        keychain_service = source.get(
            "CREATOR_MONITOR_KEYCHAIN_SERVICE", "creator-monitor-tikhub"
        )
        if api_key is None and env is None:
            api_key = _read_macos_keychain(keychain_service)
        raw_budget = source.get("CREATOR_MONITOR_MAX_USD", "0.50")
        try:
            budget = Decimal(raw_budget)
        except InvalidOperation as exc:
            raise ConfigurationError("CREATOR_MONITOR_MAX_USD must be a decimal") from exc

        try:
            return cls(
                tikhub_api_key=api_key,
                base_token=source.get("CREATOR_MONITOR_BASE_TOKEN") or None,
                state_dir=Path(source.get("CREATOR_MONITOR_STATE_DIR", "runtime")),
                config_path=Path(
                    source.get("CREATOR_MONITOR_CONFIG", "runtime/config.json")
                ),
                max_usd=budget,
                max_requests_per_run=int(
                    source.get("CREATOR_MONITOR_MAX_REQUESTS_PER_RUN", "20")
                ),
                keychain_service=keychain_service,
                report_user_id=source.get("CREATOR_MONITOR_REPORT_USER_ID") or None,
                analysis_url=source.get("CREATOR_MONITOR_ANALYSIS_URL") or None,
            )
        except (ValidationError, ValueError) as exc:
            raise ConfigurationError("creator monitor configuration is invalid") from exc

    def require_tikhub(self) -> str:
        if self.tikhub_api_key is None:
            raise ConfigurationError("TIKHUB_API_KEY is required for live TikHub calls")
        return self.tikhub_api_key.get_secret_value()

    def require_base(self) -> str:
        if self.base_token is None:
            raise ConfigurationError(
                "CREATOR_MONITOR_BASE_TOKEN is required for Feishu Base operations"
            )
        return self.base_token.get_secret_value()

    def safe_summary(self) -> dict[str, object]:
        return {
            "tikhub_api_key": "configured" if self.tikhub_api_key else "missing",
            "base_token": "configured" if self.base_token else "missing",
            "state_dir": str(self.state_dir),
            "config_path": str(self.config_path),
            "max_usd": str(self.max_usd),
            "max_requests_per_run": self.max_requests_per_run,
            "keychain_service": self.keychain_service,
            "report_user_id": "configured" if self.report_user_id else "missing",
            "analysis_url": "configured" if self.analysis_url else "missing",
        }


def _read_macos_keychain(service: str) -> str | None:
    if platform.system() != "Darwin":
        return None
    completed = subprocess.run(
        ["security", "find-generic-password", "-w", "-s", service],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None
