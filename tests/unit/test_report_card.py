from __future__ import annotations

from creator_monitor.feishu.card import build_daily_report_card


def test_report_card_has_single_focus_four_blocks_and_safe_links() -> None:
    card = build_daily_report_card(
        account_count=2,
        content_count=42,
        updated_count=3,
        top_rows=[
            {"platform": "抖音", "title": "视频", "url": "https://example.com/v", "likes": 10, "saves": 4}
        ],
        base_url="https://example.com/base",
        dashboard_url="https://example.com/dashboard",
        analysis_url="https://example.com/doc",
        reserved_usd="0.13",
    )

    assert card["schema"] == "2.0"
    assert card["config"]["width_mode"] == "fill"
    assert card["header"]["template"] == "blue"
    assert len(card["body"]["elements"]) == 4
    assert card["body"]["elements"][1]["tag"] == "table"
    buttons = card["body"]["elements"][3]["columns"]
    assert buttons[0]["elements"][0]["type"] == "primary_filled"
    assert all(
        column["elements"][0]["behaviors"][0]["type"] == "open_url" for column in buttons
    )
