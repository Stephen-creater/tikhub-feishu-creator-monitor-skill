from __future__ import annotations

import json
import os
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from creator_monitor.errors import BudgetExceeded

try:  # pragma: no cover - Windows fallback is exercised only off Unix.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]


class BudgetGuard:
    """Persist billed attempts before sending them to TikHub.

    TikHub may charge failed upstream lookups, so every authorized attempt is
    reserved before network I/O. The ledger is local runtime state and must not
    be committed.
    """

    def __init__(
        self,
        *,
        ledger_path: Path,
        run_id: str,
        max_total_usd: Decimal,
        max_requests_per_run: int,
    ) -> None:
        self.ledger_path = ledger_path
        self.lock_path = ledger_path.with_suffix(f"{ledger_path.suffix}.lock")
        self.run_id = run_id
        self.max_total_usd = max_total_usd
        self.max_requests_per_run = max_requests_per_run

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def reserve(self, endpoint: str, cost_usd: Decimal) -> dict[str, object]:
        if cost_usd < 0:
            raise ValueError("cost_usd cannot be negative")

        with self._locked():
            ledger = self._read()
            runs = ledger.setdefault("runs", {})
            run = runs.setdefault(self.run_id, {"requests": 0, "usd": "0", "events": []})
            run_requests = int(run["requests"])
            total_usd = Decimal(str(ledger["total_usd"]))

            if run_requests + 1 > self.max_requests_per_run:
                raise BudgetExceeded(
                    f"TikHub request limit reached for run {self.run_id}: "
                    f"{self.max_requests_per_run}"
                )
            if total_usd + cost_usd > self.max_total_usd:
                raise BudgetExceeded(
                    f"TikHub USD limit would be exceeded: {self.max_total_usd}"
                )

            new_total = total_usd + cost_usd
            new_run_usd = Decimal(str(run["usd"])) + cost_usd
            ledger["total_requests"] = int(ledger["total_requests"]) + 1
            ledger["total_usd"] = str(new_total)
            run["requests"] = run_requests + 1
            run["usd"] = str(new_run_usd)
            run["events"].append({"endpoint": endpoint, "cost_usd": str(cost_usd)})
            self._write(ledger)
            return {
                "total_requests": ledger["total_requests"],
                "total_usd": ledger["total_usd"],
                "run_requests": run["requests"],
                "run_usd": run["usd"],
            }

    def snapshot(self) -> dict[str, object]:
        with self._locked():
            return self._read()

    def _read(self) -> dict[str, object]:
        if not self.ledger_path.exists():
            return {"total_requests": 0, "total_usd": "0", "runs": {}}
        return json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def _write(self, ledger: dict[str, object]) -> None:
        temporary = self.ledger_path.with_suffix(f"{self.ledger_path.suffix}.tmp")
        temporary.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(temporary, 0o600)
        temporary.replace(self.ledger_path)
