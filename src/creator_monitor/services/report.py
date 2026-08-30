from __future__ import annotations

import json
from pathlib import Path

from creator_monitor.config import Settings
from creator_monitor.errors import ConfigurationError
from creator_monitor.feishu.card import build_daily_report_card
from creator_monitor.feishu.cli import LarkCLI


def send_daily_report(*, settings: Settings, cli: LarkCLI | None = None) -> dict[str, object]:
    if not settings.report_user_id:
        raise ConfigurationError("CREATOR_MONITOR_REPORT_USER_ID is required for daily-report")
    manifest = json.loads(settings.config_path.read_text(encoding="utf-8"))
    latest_path = settings.state_dir / "latest-normalized.json"
    if not latest_path.exists():
        latest_path = settings.state_dir / "live-normalized.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    budget = json.loads((settings.state_dir / "budget.json").read_text(encoding="utf-8"))
    last_run_path = settings.state_dir / "last-run.json"
    last_run = json.loads(last_run_path.read_text(encoding="utf-8")) if last_run_path.exists() else {}
    dashboard_path = settings.state_dir / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8")) if dashboard_path.exists() else {}

    items = sorted(latest["contents"], key=lambda item: item.get("likes") or 0, reverse=True)
    top_rows = [
        {
            "platform": "抖音" if item["platform"] == "douyin" else "小红书",
            "title": item.get("title") or item["content_id"],
            "url": item.get("canonical_url"),
            "likes": item.get("likes") or 0,
            "saves": item.get("saves") or 0,
        }
        for item in items[:3]
    ]
    base_url = f"https://my.feishu.cn/base/{manifest['base_token']}"
    dashboard_url = (
        f"{base_url}?table={dashboard['dashboard_id']}" if dashboard.get("dashboard_id") else base_url
    )
    card = build_daily_report_card(
        account_count=len(latest["accounts"]),
        content_count=len(latest["contents"]),
        updated_count=int(last_run.get("updated", 0)),
        top_rows=top_rows,
        base_url=base_url,
        dashboard_url=dashboard_url,
        analysis_url=settings.analysis_url or base_url,
        reserved_usd=str(budget.get("total_usd", "0")),
    )
    content = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
    runner = cli or LarkCLI()
    result = runner.run(
        [
            "lark-cli",
            "im",
            "+messages-send",
            "--user-id",
            settings.report_user_id,
            "--msg-type",
            "interactive",
            "--content",
            content,
            "--as",
            "bot",
            "--idempotency-key",
            f"creator-monitor-{last_run.get('run_id', 'manual')}",
        ]
    )
    return {
        "ok": bool(result.get("ok")),
        "message_id": result.get("data", {}).get("message_id"),
        "chat_id": result.get("data", {}).get("chat_id"),
    }
