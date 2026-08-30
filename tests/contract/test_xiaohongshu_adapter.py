from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from creator_monitor.domain.models import Platform
from creator_monitor.tikhub.xiaohongshu import (
    normalize_comments,
    normalize_notes,
    normalize_profile,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tikhub"
FETCHED_AT = datetime(2026, 8, 30, 10, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_normalize_xiaohongshu_profile() -> None:
    account = normalize_profile(_load("xhs_profile.json"), fetched_at=FETCHED_AT)
    assert account.platform is Platform.XIAOHONGSHU
    assert account.account_id == "61b46d790000000010008153"
    assert account.followers == 23000
    assert account.total_likes == 156000


def test_normalize_xiaohongshu_notes_and_comments() -> None:
    notes, page = normalize_notes(_load("xhs_notes.json"), fetched_at=FETCHED_AT)
    comments, comment_page = normalize_comments(
        _load("xhs_comments.json"), fetched_at=FETCHED_AT
    )
    assert notes[0].content_id == "697c0eee000000000a03c308"
    assert notes[0].likes == 3560
    assert notes[0].saves == 890
    assert page.next_cursor == "next-note-cursor"
    assert comments[0].text == "求一个完整教程"
    assert comment_page.has_more is False


def test_normalize_current_xiaohongshu_app_v2_note_shape() -> None:
    payload = {
        "code": 200,
        "data": {
            "data": {
                "has_more": True,
                "notes": [
                    {
                        "id": "note-current",
                        "title": "当前响应结构",
                        "desc": "真实封面不能丢失",
                        "create_time": 1787848258,
                        "cursor": "next-current",
                        "likes": 1200,
                        "collected_count": 340,
                        "comments_count": 56,
                        "share_count": 78,
                        "user": {"userid": "user-current", "nickname": "示例账号"},
                        "images_list": [
                            {
                                "url": "https://example.com/small.webp",
                                "url_size_large": "https://example.com/large.webp",
                            }
                        ],
                    }
                ],
            }
        },
    }

    notes, page = normalize_notes(payload, fetched_at=FETCHED_AT)

    assert notes[0].account_id == "user-current"
    assert notes[0].cover_url == "https://example.com/large.webp"
    assert notes[0].likes == 1200
    assert notes[0].saves == 340
    assert notes[0].comments == 56
    assert notes[0].shares == 78
    assert page.next_cursor == "next-current"
    assert page.has_more is True


def test_normalize_current_xiaohongshu_app_v2_profile_shape() -> None:
    payload = {
        "code": 200,
        "data": {
            "data": {
                "userid": "user-current",
                "nickname": "示例账号",
                "images": "https://example.com/avatar.webp",
                "desc": "简介",
                "ndiscovery": 231,
                "interactions": [
                    {"type": "fans", "count": 49907},
                    {"type": "follows", "count": 96},
                    {"type": "interaction", "count": 496023},
                ],
            }
        },
    }

    account = normalize_profile(payload, fetched_at=FETCHED_AT)

    assert account.account_id == "user-current"
    assert account.nickname == "示例账号"
    assert account.followers == 49907
    assert account.works_count == 231
    assert account.total_likes == 496023
