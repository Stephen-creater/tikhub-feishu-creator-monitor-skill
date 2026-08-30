from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from creator_monitor.domain.models import Platform
from creator_monitor.tikhub.douyin import normalize_comments, normalize_posts, normalize_profile


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "tikhub"
FETCHED_AT = datetime(2026, 8, 30, 10, tzinfo=UTC)


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_normalize_douyin_profile() -> None:
    account = normalize_profile(_load("douyin_profile.json"), fetched_at=FETCHED_AT)
    assert account.platform is Platform.DOUYIN
    assert account.account_id == "MS4wLjAB-DEMO"
    assert account.followers == 12000
    assert account.business_key == "douyin:MS4wLjAB-DEMO"


def test_normalize_douyin_posts_and_comments() -> None:
    posts, page = normalize_posts(_load("douyin_posts.json"), fetched_at=FETCHED_AT)
    comments, comment_page = normalize_comments(
        _load("douyin_comments.json"), fetched_at=FETCHED_AT
    )
    assert posts[0].content_id == "7500000000000000001"
    assert posts[0].duration_seconds == 18.5
    assert posts[0].saves == 310
    assert page.next_cursor == "1788060000000"
    assert comments[0].comment_id == "comment-dy-1"
    assert comments[0].author_id_hash != "viewer-1"
    assert comment_page.has_more is False

