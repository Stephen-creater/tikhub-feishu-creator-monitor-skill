from __future__ import annotations

from collections.abc import Iterable


def _kpi_column(value: str, label: str) -> dict:
    return {
        "tag": "column",
        "width": "weighted",
        "weight": 1,
        "background_style": "blue-50",
        "padding": "12px",
        "vertical_spacing": "2px",
        "elements": [
            {
                "tag": "markdown",
                "content": f"## <font color='blue'>{value}</font>",
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
    updated_count: int,
    top_rows: Iterable[dict[str, object]],
    base_url: str,
    dashboard_url: str,
    analysis_url: str,
    reserved_usd: str,
) -> dict:
    rows = []
    for row in list(top_rows)[:3]:
        rows.append(
            {
                "platform": row["platform"],
                "title": f"[{str(row['title'])[:40]}]({row['url']})",
                "likes": int(row.get("likes") or 0),
                "saves": int(row.get("saves") or 0),
            }
        )
    return {
        "schema": "2.0",
        "config": {
            "update_multi": True,
            "width_mode": "fill",
            "summary": {"content": "自媒体竞品情报日报"},
        },
        "header": {
            "title": {"tag": "plain_text", "content": "自媒体竞品情报日报"},
            "subtitle": {"tag": "plain_text", "content": "TikHub × Codex Skill × 飞书 Base"},
            "template": "blue",
            "icon": {"tag": "standard_icon", "token": "wiki-bitable_colorful"},
            "text_tag_list": [
                {
                    "tag": "text_tag",
                    "text": {"tag": "plain_text", "content": "自动更新"},
                    "color": "green",
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
                        _kpi_column(str(content_count), "真实作品"),
                        _kpi_column(str(updated_count), "今日变化"),
                    ],
                },
                {
                    "tag": "table",
                    "columns": [
                        {"name": "platform", "display_name": "平台", "data_type": "text", "width": "90px"},
                        {"name": "title", "display_name": "高价值内容", "data_type": "lark_md", "width": "55%"},
                        {"name": "likes", "display_name": "点赞", "data_type": "number"},
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
                    "content": "**今日建议**\n优先查看榜单前三和高收藏内容，再决定标记为“已采用”或继续留在“待处理”。",
                    "text_size": "normal",
                },
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "horizontal_spacing": "8px",
                    "columns": [
                        _button_column("打开数据工作台", base_url, primary=True),
                        _button_column("查看仪表盘", dashboard_url, primary=False),
                        _button_column("查看拆解文档", analysis_url, primary=False),
                    ],
                },
            ],
        },
    }
