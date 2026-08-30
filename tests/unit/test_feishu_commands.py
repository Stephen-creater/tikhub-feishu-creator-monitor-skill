from __future__ import annotations

import json
from pathlib import Path

from creator_monitor.feishu.bootstrap import BootstrapPlan, _named_id_map

ROOT = Path(__file__).resolve().parents[2]


def test_bootstrap_plan_creates_six_tables_and_six_views() -> None:
    plan = BootstrapPlan.from_templates(
        ROOT / "templates" / "base-schema.json",
        ROOT / "templates" / "views.json",
    )

    assert [table.name for table in plan.tables] == [
        "账号库",
        "内容库",
        "指标快照",
        "评论库",
        "运行日志",
        "失败队列",
    ]
    assert len(plan.views) == 6
    assert plan.views[-2].view_type == "gallery"
    assert plan.views[-1].view_type == "kanban"


def test_first_command_creates_base_and_account_table() -> None:
    plan = BootstrapPlan.from_templates(
        ROOT / "templates" / "base-schema.json",
        ROOT / "templates" / "views.json",
    )
    command = plan.base_create_command(dry_run=True)

    assert command[:3] == ["lark-cli", "base", "+base-create"]
    assert "--as" in command and "user" in command
    assert "--dry-run" in command
    fields = json.loads(command[command.index("--fields") + 1])
    assert fields[0]["name"] == "账号"
    assert fields[0]["type"] == "text"
    assert not any("token" in argument.casefold() for argument in command)


def test_remaining_tables_and_views_use_returned_base_token() -> None:
    plan = BootstrapPlan.from_templates(
        ROOT / "templates" / "base-schema.json",
        ROOT / "templates" / "views.json",
    )
    table_commands = plan.table_create_commands("bas_demo", dry_run=True)
    view_commands = plan.view_create_commands("bas_demo", dry_run=True)

    assert len(table_commands) == 5
    assert len(view_commands) == 6
    assert all("bas_demo" in command for command in table_commands + view_commands)
    assert all("--dry-run" in command for command in table_commands + view_commands)


def test_named_id_map_accepts_current_lark_cli_list_shape() -> None:
    payload = {
        "ok": True,
        "data": {"tables": [{"id": "tbl123", "name": "内容库", "records_count": 0}]},
    }

    assert _named_id_map(payload, collection="tables") == {"内容库": "tbl123"}
