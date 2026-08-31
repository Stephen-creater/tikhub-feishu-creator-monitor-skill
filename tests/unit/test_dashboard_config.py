from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_matches_source_information_hierarchy() -> None:
    config = json.loads((ROOT / "templates" / "dashboard.json").read_text(encoding="utf-8"))
    blocks = {item["name"]: item for item in config["blocks"]}

    assert len(blocks) >= 10
    assert blocks["监控账号"]["type"] == "statistics"
    assert blocks["真实作品"]["type"] == "statistics"
    assert blocks["🥇 TOP 1 热度"]["type"] == "statistics"
    assert blocks["平台内容分布"]["type"] == "ring"
    assert blocks["近60天发布趋势"]["type"] == "area"
    assert blocks["近60天发布趋势"]["data_config"]["group_by"][0]["field_name"] == "发布周"
    assert "使用说明" not in blocks
    assert blocks["账号互动表现"]["type"] == "combo"
    assert blocks["选题处理情况"]["type"] == "column"
    assert blocks["账号地区分布"]["data_config"]["table_name"] == "账号库"
    assert "运行日志" not in {b["data_config"].get("table_name") for b in blocks.values()}
