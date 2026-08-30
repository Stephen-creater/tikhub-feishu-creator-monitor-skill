from __future__ import annotations

import json
from decimal import Decimal

from creator_monitor.budget import BudgetGuard
from creator_monitor.tikhub.client import Endpoint, TikHubClient


def test_client_caches_response_and_reserves_only_once(tmp_path) -> None:
    calls: list[str] = []

    def transport(url: str, headers: dict[str, str], timeout: float) -> dict:
        calls.append(url)
        assert headers["Authorization"] == "Bearer secret"
        return {"code": 200, "request_id": "request-1", "data": {"ok": True}}

    guard = BudgetGuard(
        ledger_path=tmp_path / "budget.json",
        run_id="run-1",
        max_total_usd=Decimal("0.50"),
        max_requests_per_run=20,
    )
    client = TikHubClient(
        api_key="secret",
        budget=guard,
        cache_dir=tmp_path / "cache",
        transport=transport,
    )
    endpoint = Endpoint("test", "/api/v1/test", Decimal("0.01"))

    first = client.get(endpoint, {"id": "123"})
    second = client.get(endpoint, {"id": "123"})

    assert first == second
    assert len(calls) == 1
    assert guard.snapshot()["total_requests"] == 1
    cache_files = list((tmp_path / "cache").glob("*.json"))
    assert len(cache_files) == 1
    assert "secret" not in cache_files[0].read_text(encoding="utf-8")


def test_client_retries_retryable_response(tmp_path) -> None:
    attempts = 0

    def transport(url: str, headers: dict[str, str], timeout: float) -> dict:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return {"code": 500, "message": "temporary"}
        return {"code": 200, "data": {"ok": True}}

    guard = BudgetGuard(
        ledger_path=tmp_path / "budget.json",
        run_id="retry-run",
        max_total_usd=Decimal("0.50"),
        max_requests_per_run=20,
    )
    client = TikHubClient(
        api_key="secret",
        budget=guard,
        cache_dir=tmp_path / "cache",
        transport=transport,
        sleeper=lambda _: None,
    )

    result = client.get(Endpoint("retry", "/retry", Decimal("0.01")), {})

    assert result["data"]["ok"] is True
    assert attempts == 2
    assert guard.snapshot()["total_requests"] == 2

