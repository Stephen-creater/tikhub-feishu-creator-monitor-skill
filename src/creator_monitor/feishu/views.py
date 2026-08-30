from __future__ import annotations

import json
from pathlib import Path

from creator_monitor.feishu.bootstrap import _named_id_map
from creator_monitor.feishu.cli import LarkCLI


def _field_map(payload: dict[str, object]) -> dict[str, str]:
    data = payload.get("data")
    if not isinstance(data, dict) or not isinstance(data.get("fields"), list):
        return {}
    return {
        str(item["name"]): str(item["id"])
        for item in data["fields"]
        if isinstance(item, dict) and item.get("name") and item.get("id")
    }


def _replace_filter_fields(config: dict[str, object], fields: dict[str, str]) -> dict[str, object]:
    replaced = json.loads(json.dumps(config, ensure_ascii=False))
    for condition in replaced.get("conditions", []):
        condition[0] = fields[condition[0]]
    return replaced


def configure_views(
    *,
    base_token: str,
    table_id: str,
    template_path: Path,
    cli: LarkCLI | None = None,
) -> dict[str, str]:
    runner = cli or LarkCLI()
    template = json.loads(template_path.read_text(encoding="utf-8"))
    fields = _field_map(
        runner.run(
            [
                "lark-cli",
                "base",
                "+field-list",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--as",
                "user",
            ]
        )
    )
    views = _named_id_map(
        runner.run(
            [
                "lark-cli",
                "base",
                "+view-list",
                "--base-token",
                base_token,
                "--table-id",
                table_id,
                "--as",
                "user",
            ]
        ),
        collection="views",
    )

    for view in template["views"]:
        view_id = views[str(view["name"])]
        common = [
            "--base-token",
            base_token,
            "--table-id",
            table_id,
            "--view-id",
            view_id,
            "--as",
            "user",
        ]
        if "filter" in view:
            runner.run(
                [
                    "lark-cli",
                    "base",
                    "+view-set-filter",
                    *common,
                    "--json",
                    json.dumps(
                        _replace_filter_fields(view["filter"], fields),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ]
            )
        if "sort" in view:
            payload = {
                "sort_config": [
                    {"field": fields[item["field"]], "desc": bool(item.get("desc", False))}
                    for item in view["sort"]
                ]
            }
            runner.run(
                [
                    "lark-cli",
                    "base",
                    "+view-set-sort",
                    *common,
                    "--json",
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ]
            )
        if "group" in view:
            payload = {
                "group_config": [
                    {"field": fields[item["field"]], "desc": bool(item.get("desc", False))}
                    for item in view["group"]
                ]
            }
            runner.run(
                [
                    "lark-cli",
                    "base",
                    "+view-set-group",
                    *common,
                    "--json",
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ]
            )
        if "visible_fields" in view:
            payload = {"visible_fields": [fields[name] for name in view["visible_fields"]]}
            runner.run(
                [
                    "lark-cli",
                    "base",
                    "+view-set-visible-fields",
                    *common,
                    "--json",
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                ]
            )
    return {str(view["name"]): views[str(view["name"])] for view in template["views"]}
