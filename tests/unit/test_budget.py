from __future__ import annotations

import json
from decimal import Decimal

import pytest

from creator_monitor.budget import BudgetGuard
from creator_monitor.errors import BudgetExceeded


def test_budget_guard_persists_charged_attempts(tmp_path) -> None:
    ledger = tmp_path / "budget.json"
    guard = BudgetGuard(
        ledger_path=ledger,
        run_id="run-1",
        max_total_usd=Decimal("0.50"),
        max_requests_per_run=3,
    )

    guard.reserve("douyin.profile", Decimal("0.01"))
    guard.reserve("douyin.posts", Decimal("0.02"))

    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["total_requests"] == 2
    assert saved["total_usd"] == "0.03"
    assert saved["runs"]["run-1"]["requests"] == 2


def test_budget_guard_rejects_request_limit_without_mutating_ledger(tmp_path) -> None:
    ledger = tmp_path / "budget.json"
    guard = BudgetGuard(
        ledger_path=ledger,
        run_id="run-limited",
        max_total_usd=Decimal("0.50"),
        max_requests_per_run=1,
    )
    guard.reserve("first", Decimal("0.01"))

    with pytest.raises(BudgetExceeded, match="request limit"):
        guard.reserve("second", Decimal("0.01"))

    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["total_requests"] == 1


def test_budget_guard_rejects_total_usd_limit(tmp_path) -> None:
    ledger = tmp_path / "budget.json"
    first = BudgetGuard(
        ledger_path=ledger,
        run_id="run-a",
        max_total_usd=Decimal("0.02"),
        max_requests_per_run=10,
    )
    first.reserve("first", Decimal("0.02"))

    second = BudgetGuard(
        ledger_path=ledger,
        run_id="run-b",
        max_total_usd=Decimal("0.02"),
        max_requests_per_run=10,
    )
    with pytest.raises(BudgetExceeded, match="USD limit"):
        second.reserve("second", Decimal("0.01"))

    saved = json.loads(ledger.read_text(encoding="utf-8"))
    assert saved["total_usd"] == "0.02"
