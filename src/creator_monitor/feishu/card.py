from __future__ import annotations

from collections.abc import Iterable


def _kpi_column(
    value: str,
    label: str,
    *,
    background: str = "grey-50",
    color: str = "blue",
    weight: int = 1,
) -> dict:
    return {
        "tag": "column",
        "width": "weighted",
        "weight": weight,
        "background_style": background,
        "padding": "12px",
        "vertical_spacing": "2px",
        "elements": [
            {
                "tag": "markdown",
                "content": f"## <font color='{color}'>{value}</font>",
                "text_align": "center",
            },
            {
                "tag": "markdown",
                "content": f"<font color='grey'>{label}</font>",
                "text_align": "center",
                "text_size": "notation",
            },
        ],
    }


def _button_column(text: str, url: str, *, primary: bool) -> dict:
    return {
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "elements": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": text},
                "type": "primary_filled" if primary else "default",
                "width": "fill",
                "behaviors": [{"type": "open_url", "default_url": url}],
            }
        ],
    }


def build_daily_report_card(
    *,
    account_count: int,
    content_count: int,
    pending_count: int,
    adopted_count: int,
    eliminated_count: int,
    top_rows: Iterable[dict[str, object]],
    base_url: str,
    dashboard_url: str,
) -> dict:
    rows = []
    for rank, row in enumerate(list(top_rows)[:3], start=1):
        rows.append(
            {
                "title": f"{rank}. {str(row['title'])[:32]}",
                "account": str(row.get("account") or ""),
                "likes": int(row.get("likes") or 0),
                "comments": int(row.get("comments") or 0),
                "saves": int(row.get("saves") or 0),
            }
        )
    return {
        "schema": "2.0",
        "config": {
            "update_multi": True,
            "width_mode": "fill",
            "summary": {"content": "竞品内容日报"},
        },
        "header": {
            "title": {"tag": "plain_text", "content": "竞品内容日报"},
            "subtitle": {
                "tag": "plain_text",
                "content": f"{account_count} 个账号 · {content_count} 条作品",
            },
            "template": "blue",
            "icon": {"tag": "standard_icon", "token": "wiki-bitable_colorful"},
            "text_tag_list": [
                {
                    "tag": "text_tag",
                    "text": {"tag": "plain_text", "content": "每日更新"},
                    "color": "blue",
                }
            ],
        },
        "body": {
            "direction": "vertical",
            "padding": "12px 12px 20px 12px",
            "vertical_spacing": "12px",
            "elements": [
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "horizontal_spacing": "12px",
                    "columns": [
                        _kpi_column(str(account_count), "监控账号"),
                        _kpi_column(str(content_count), "作品总数"),
                    ],
                },
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "horizontal_spacing": "12px",
                    "columns": [
                        _kpi_column(
                            str(pending_count),
                            "待处理",
                            background="blue-50",
                            color="blue",
                            weight=2,
                        ),
                        _kpi_column(str(adopted_count), "已采用"),
                        _kpi_column(str(eliminated_count), "已淘汰", color="grey"),
                    ],
                },
                {
                    "tag": "table",
                    "columns": [
                        {"name": "title", "display_name": "作品", "data_type": "text", "width": "55%"},
                        {"name": "account", "display_name": "账号", "data_type": "text", "width": "130px"},
                        {"name": "likes", "display_name": "点赞", "data_type": "number"},
                        {"name": "comments", "display_name": "评论", "data_type": "number"},
                        {"name": "saves", "display_name": "收藏", "data_type": "number"},
                    ],
                    "rows": rows,
                    "page_size": 3,
                    "row_height": "auto",
                    "row_max_height": "88px",
                    "freeze_first_column": True,
                    "header_style": {"background_style": "grey", "bold": True, "lines": 1},
                },
                {
                    "tag": "markdown",
                    "content": (
                        f"**今天先处理这 {pending_count} 条内容**\n"
                        "优先查看榜单前三，再决定采用或淘汰。"
                    ),
                    "text_size": "normal",
                },
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "horizontal_spacing": "8px",
                    "columns": [
                        _button_column("打开内容库", base_url, primary=True),
                        _button_column("查看完整数据", dashboard_url, primary=False),
                    ],
                },
            ],
        },
    }
