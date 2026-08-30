from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_six_views_have_expected_business_configuration() -> None:
    config = json.loads((ROOT / "templates" / "views.json").read_text(encoding="utf-8"))
    views = {view["name"]: view for view in config["views"]}

    assert len(views) == 6
    assert views["待处理"]["filter"]["conditions"] == [
        ["状态", "intersects", ["待处理"]]
    ]
    assert views["本周榜单"]["sort"][0] == {"field": "本周排名", "desc": False}
    assert views["高收藏选题"]["sort"][0] == {"field": "收藏数", "desc": True}
    assert views["封面灵感"]["type"] == "gallery"
    assert views["选题看板"]["group"] == [{"field": "状态", "desc": False}]
