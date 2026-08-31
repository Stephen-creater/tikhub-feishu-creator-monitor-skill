from __future__ import annotations

import json
import re

from creator_monitor.config import Settings
from creator_monitor.errors import ConfigurationError
from creator_monitor.feishu.card import build_daily_report_card
from creator_monitor.feishu.cli import LarkCLI


def _plain_url(value: object) -> str:
    text = str(value or "")
    match = re.search(r"\((https?://[^)]+)\)$", text)
    return match.group(1) if match else text


def send_daily_report(*, settings: Settings, cli: LarkCLI | None = None) -> dict[str, object]:
    manifest = json.loads(settings.config_path.read_text(encoding="utf-8"))
    report_chat_id = manifest.get("report_chat_id")
    if not settings.report_user_id and not report_chat_id:
        raise ConfigurationError(
            "CREATOR_MONITOR_REPORT_USER_ID or runtime report_chat_id is required for daily-report"
        )
    latest_path = settings.state_dir / "latest-normalized.json"
    if not latest_path.exists():
        latest_path = settings.state_dir / "live-normalized.json"
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    last_run_path = settings.state_dir / "last-run.json"
    last_run = json.loads(last_run_path.read_text(encoding="utf-8")) if last_run_path.exists() else {}
    dashboard_path = settings.state_dir / "dashboard.json"
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8")) if dashboard_path.exists() else {}

    runner = cli or LarkCLI()
    record_payload = runner.run(
        [
            "lark-cli",
            "base",
            "+record-list",
            "--base-token",
            manifest["base_token"],
            "--table-id",
            manifest["tables"]["内容库"],
            "--field-id",
            "作品",
            "--field-id",
            "账号昵称",
            "--field-id",
            "点赞数",
            "--field-id",
            "评论数",
            "--field-id",
            "收藏数",
            "--field-id",
            "状态",
            "--field-id",
            "本周排名",
            "--field-id",
            "内容链接",
            "--limit",
            "200",
            "--format",
            "json",
            "--as",
            "user",
        ]
    )
    data = record_payload.get("data", {})
    names = data.get("fields", [])
    records = [
        dict(zip(names, row, strict=False))
        for row in data.get("data", [])
        if isinstance(row, list)
    ]
    state_counts = {"待处理": 0, "已采用": 0, "已淘汰": 0}
    for record in records:
        states = record.get("状态") or []
        if states and states[0] in state_counts:
            state_counts[states[0]] += 1

    ranked = sorted(
        (record for record in records if record.get("本周排名") is not None),
        key=lambda record: int(record["本周排名"]),
    )
    top_rows = [
        {
            "title": record.get("作品") or "未命名作品",
            "account": record.get("账号昵称") or "",
            "url": _plain_url(record.get("内容链接")),
            "likes": record.get("点赞数") or 0,
            "comments": record.get("评论数") or 0,
            "saves": record.get("收藏数") or 0,
        }
        for record in ranked[:3]
    ]
    base_url = f"https://my.feishu.cn/base/{manifest['base_token']}"
    dashboard_url = (
        f"{base_url}?table={dashboard['dashboard_id']}" if dashboard.get("dashboard_id") else base_url
    )
    card = build_daily_report_card(
        account_count=len(latest["accounts"]),
        content_count=len(records),
        pending_count=state_counts["待处理"],
        adopted_count=state_counts["已采用"],
        eliminated_count=state_counts["已淘汰"],
        top_rows=top_rows,
        base_url=base_url,
        dashboard_url=dashboard_url,
    )
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    (settings.state_dir / "report-card.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    content = json.dumps(card, ensure_ascii=False, separators=(",", ":"))
    target_args = (
        ["--user-id", settings.report_user_id]
        if settings.report_user_id
        else ["--chat-id", str(report_chat_id)]
    )
    result = runner.run(
        [
            "lark-cli",
            "im",
            "+messages-send",
            *target_args,
            "--msg-type",
            "interactive",
            "--content",
            content,
            "--as",
            "bot",
            "--idempotency-key",
            f"creator-monitor-{last_run.get('run_id', 'manual')}-v7",
        ]
    )
    return {
        "ok": bool(result.get("ok")),
        "message_id": result.get("data", {}).get("message_id"),
        "chat_id": result.get("data", {}).get("chat_id"),
    }
