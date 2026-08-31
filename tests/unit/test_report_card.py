from __future__ import annotations

import json

from creator_monitor.feishu.card import build_daily_report_card


def test_report_card_is_plain_business_language_with_safe_links() -> None:
    card = build_daily_report_card(
        account_count=6,
        content_count=110,
        pending_count=51,
        adopted_count=34,
        eliminated_count=25,
        top_rows=[
            {
                "title": "视频",
                "account": "账号A",
                "url": "https://example.com/v",
                "likes": 10,
                "comments": 3,
                "saves": 4,
            }
        ],
        base_url="https://example.com/base",
        dashboard_url="https://example.com/dashboard",
    )

    assert card["schema"] == "2.0"
    assert card["config"]["width_mode"] == "fill"
    assert card["header"]["title"]["content"] == "竞品内容日报"
    assert card["header"]["subtitle"]["content"] == "6 个账号 · 110 条作品"
    assert len(card["body"]["elements"]) == 5
    table = card["body"]["elements"][2]
    assert table["tag"] == "table"
    assert [column["display_name"] for column in table["columns"]] == [
        "作品",
        "账号",
        "点赞",
        "评论",
        "收藏",
    ]
    buttons = card["body"]["elements"][4]["columns"]
    assert buttons[0]["elements"][0]["type"] == "primary_filled"
    assert all(
        column["elements"][0]["behaviors"][0]["type"] == "open_url" for column in buttons
    )
    rendered = json.dumps(card, ensure_ascii=False)
    for forbidden in ("MVP", "TikHub", "Codex", "Base", "预算", "业务键", "partial", "运行说明"):
        assert forbidden not in rendered
