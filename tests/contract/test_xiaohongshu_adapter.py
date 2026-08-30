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

