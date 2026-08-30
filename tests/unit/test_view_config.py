from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_six_views_have_expected_business_configuration() -> None:
    config = json.loads((ROOT / "templates" / "views.json").read_text(encoding="utf-8"))
    views = {view["name"]: view for view in config["views"]}

    assert len(views) == 6
    assert views["待处理新内容"]["filter"]["conditions"] == [
        ["已阅", "==", False],
        ["跟进状态", "intersects", ["待处理"]],
    ]
    assert views["爆款排行榜"]["sort"][0] == {"field": "点赞增量", "desc": True}
    assert views["干货收藏榜"]["sort"][0] == {"field": "收藏率", "desc": True}
    assert views["灵感画册"]["type"] == "gallery"
    assert views["翻拍执行看板"]["group"] == [{"field": "跟进状态", "desc": False}]
