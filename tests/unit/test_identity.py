from __future__ import annotations

from datetime import UTC, datetime

import pytest

from creator_monitor.domain.identity import (
    account_key,
    comment_key,
    content_key,
    snapshot_key,
    weak_content_key,
)
from creator_monitor.domain.models import Platform


def test_platform_is_part_of_every_stable_key() -> None:
    assert account_key(Platform.DOUYIN, "42") == "douyin:42"
    assert account_key(Platform.XIAOHONGSHU, "42") == "xiaohongshu:42"
    assert content_key(Platform.DOUYIN, "99") == "douyin:99"
    assert comment_key(Platform.XIAOHONGSHU, "7") == "xiaohongshu:7"


def test_empty_stable_identifier_is_rejected() -> None:
    with pytest.raises(ValueError, match="identifier"):
        content_key(Platform.DOUYIN, "  ")


def test_snapshot_key_uses_utc_hour_bucket() -> None:
    captured = datetime(2026, 8, 30, 9, 42, 51, tzinfo=UTC)
    assert snapshot_key("douyin:99", captured, bucket_minutes=60) == (
        "douyin:99:2026-08-30T09:00:00Z"
    )


def test_weak_content_key_is_deterministic_and_marked() -> None:
    first = weak_content_key(
        platform=Platform.XIAOHONGSHU,
        account_id="author",
        published_at=datetime(2026, 8, 30, tzinfo=UTC),
        text="  同一个 标题  ",
    )
    second = weak_content_key(
        platform=Platform.XIAOHONGSHU,
        account_id="author",
        published_at=datetime(2026, 8, 30, tzinfo=UTC),
        text="同一个 标题",
    )
    assert first == second
    assert first.startswith("weak:xiaohongshu:")

