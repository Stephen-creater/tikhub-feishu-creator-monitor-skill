from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence

from creator_monitor.errors import CreatorMonitorError


class LarkCLIError(CreatorMonitorError):
    """A lark-cli command failed or returned unreadable output."""


class LarkCLI:
    def run(self, command: Sequence[str]) -> dict:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            operation = " ".join(command[:3])
            message = completed.stderr.strip() or completed.stdout.strip() or "unknown failure"
            raise LarkCLIError(f"{operation} failed: {message}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            operation = " ".join(command[:3])
            raise LarkCLIError(f"{operation} returned invalid JSON") from exc

