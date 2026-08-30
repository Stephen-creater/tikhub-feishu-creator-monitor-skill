from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_matches_source_information_hierarchy() -> None:
    config = json.loads((ROOT / "templates" / "dashboard.json").read_text(encoding="utf-8"))
    blocks = {item["name"]: item for item in config["blocks"]}

    assert len(blocks) >= 10
    assert blocks["监控账号数"]["type"] == "statistics"
    assert blocks["内容总量"]["type"] == "statistics"
    assert blocks["平台内容分布"]["type"] == "pie"
    assert blocks["内容发布趋势"]["type"] == "line"
    assert blocks["账号互动表现"]["type"] == "combo"
    assert blocks["任务运行状态"]["data_config"]["table_name"] == "运行日志"
