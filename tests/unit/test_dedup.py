from __future__ import annotations

from datetime import UTC, datetime, timedelta

from creator_monitor.domain.dedup import deduplicate_latest
from creator_monitor.domain.models import Content, Platform


NOW = datetime(2026, 8, 30, 9, tzinfo=UTC)


def _content(*, fetched_at: datetime, title: str | None, likes: int) -> Content:
    return Content(
        platform=Platform.DOUYIN,
        content_id="video-1",
        account_id="account-1",
        title=title,
        published_at=NOW - timedelta(days=1),
        fetched_at=fetched_at,
        likes=likes,
    )


def test_deduplicate_latest_keeps_newest_record() -> None:
    old = _content(fetched_at=NOW, title="old", likes=10)
    new = _content(fetched_at=NOW + timedelta(minutes=5), title="new", likes=20)

    result = deduplicate_latest([old, new])

    assert result.duplicate_count == 1
    assert result.records == [new]


def test_same_timestamp_keeps_more_complete_record() -> None:
    incomplete = _content(fetched_at=NOW, title=None, likes=20)
    complete = _content(fetched_at=NOW, title="title", likes=20)

    result = deduplicate_latest([incomplete, complete])

    assert result.records == [complete]


def test_dedup_preserves_first_seen_key_order() -> None:
    first = _content(fetched_at=NOW, title="first", likes=1)
    second = first.model_copy(update={"content_id": "video-2", "title": "second"})
    first_new = first.model_copy(update={"fetched_at": NOW + timedelta(minutes=1), "likes": 2})

    result = deduplicate_latest([first, second, first_new])

    assert [record.content_id for record in result.records] == ["video-1", "video-2"]
    assert result.records[0].likes == 2

