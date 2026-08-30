from __future__ import annotations

import json
from pathlib import Path

from creator_monitor.feishu.bootstrap import _find_first
from creator_monitor.feishu.cli import LarkCLI


def create_dashboard(
    *,
    base_token: str,
    template_path: Path,
    cli: LarkCLI | None = None,
) -> dict[str, object]:
    runner = cli or LarkCLI()
    template = json.loads(template_path.read_text(encoding="utf-8"))
    dashboards = runner.run(
        ["lark-cli", "base", "+dashboard-list", "--base-token", base_token, "--as", "user"]
    )
    dashboard_id = _named_dashboard_id(dashboards, str(template["name"]))
    if not dashboard_id:
        created = runner.run(
            [
                "lark-cli",
                "base",
                "+dashboard-create",
                "--base-token",
                base_token,
                "--name",
                str(template["name"]),
                "--as",
                "user",
            ]
        )
        dashboard_id = _find_first(created, ("dashboard_id", "id"))
    if not dashboard_id:
        raise ValueError("lark-cli returned no dashboard id")

    existing_blocks = _block_name_map(
        runner.run(
            [
                "lark-cli",
                "base",
                "+dashboard-block-list",
                "--base-token",
                base_token,
                "--dashboard-id",
                dashboard_id,
                "--page-size",
                "100",
                "--as",
                "user",
            ]
        )
    )
    block_ids = dict(existing_blocks)
    for block in template["blocks"]:
        name = str(block["name"])
        if name in block_ids:
            continue
        created = runner.run(
            [
                "lark-cli",
                "base",
                "+dashboard-block-create",
                "--base-token",
                base_token,
                "--dashboard-id",
                dashboard_id,
                "--name",
                name,
                "--type",
                str(block["type"]),
                "--data-config",
                json.dumps(block["data_config"], ensure_ascii=False, separators=(",", ":")),
                "--as",
                "user",
            ]
        )
        block_id = _find_first(created, ("block_id", "id"))
        if block_id:
            block_ids[name] = block_id

    runner.run(
        [
            "lark-cli",
            "base",
            "+dashboard-arrange",
            "--base-token",
            base_token,
            "--dashboard-id",
            dashboard_id,
            "--as",
            "user",
        ]
    )
    return {
        "dashboard_name": template["name"],
        "dashboard_id": dashboard_id,
        "blocks": block_ids,
    }


def _named_dashboard_id(payload: dict[str, object], name: str) -> str | None:
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    items = data.get("dashboards") or data.get("items") or []
    if not isinstance(items, list):
        return None
    for item in items:
        if isinstance(item, dict) and item.get("name") == name:
            identifier = item.get("dashboard_id") or item.get("id")
            if isinstance(identifier, str):
                return identifier
    return None


def _block_name_map(payload: dict[str, object]) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return {}
    items = data.get("blocks") or data.get("items") or []
    if not isinstance(items, list):
        return {}
    result: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        identifier = item.get("block_id") or item.get("id")
        if isinstance(name, str) and isinstance(identifier, str):
            result[name] = identifier
    return result

