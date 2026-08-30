from __future__ import annotations

from datetime import UTC, datetime, timedelta

from creator_monitor.domain.models import Account, Content, Platform
from creator_monitor.feishu.mappers import (
    account_pending,
    content_pending,
    prepare_account_update,
    prepare_content_update,
)
from creator_monitor.feishu.records import ExistingRecord


NOW = datetime(2026, 8, 30, 10, tzinfo=UTC)


def test_account_mapper_uses_feishu_cell_value_shapes() -> None:
    account = Account(
        platform=Platform.DOUYIN,
        account_id="sec-demo",
        nickname="演示账号",
        profile_url="https://example.com/account",
        followers=1000,
        works_count=12,
        fetched_at=NOW,
        raw_hash="account-hash",
    )

    pending = account_pending(account)

    assert pending.business_key == "douyin:sec-demo"
    assert pending.fields["平台"] == ["抖音"]
    assert pending.fields["启用监控"] is True
    assert pending.fields["监控状态"] == ["正常"]


def test_content_mapper_sets_inbox_defaults_and_recent_flag() -> None:
    content = Content(
        platform=Platform.XIAOHONGSHU,
        content_id="note-1",
        account_id="user-1",
        title="演示笔记",
        published_at=NOW - timedelta(days=2),
        fetched_at=NOW,
        likes=100,
        saves=25,
        comments=5,
        shares=2,
        raw_hash="content-hash",
    )

    pending = content_pending(content, now=NOW)

    assert pending.fields["平台"] == ["小红书"]
    assert pending.fields["已阅"] is False
    assert pending.fields["跟进状态"] == ["待处理"]
    assert pending.fields["拆解状态"] == ["未拆解"]
    assert pending.fields["近60天"] is True
    assert pending.fields["收藏率"] == 0.25


def test_account_update_preserves_controls_and_calculates_follower_gap() -> None:
    account = Account(
        platform=Platform.DOUYIN,
        account_id="sec-demo",
        nickname="演示账号",
        followers=1200,
        fetched_at=NOW,
        raw_hash="new-account-hash",
    )
    existing = ExistingRecord(
        record_id="rec-account",
        fields={"粉丝数": 1000, "启用监控": False, "监控状态": ["暂停"], "抓取频率小时": 24},
    )

    updated = prepare_account_update(account_pending(account), existing)

    assert updated.fields["粉丝增量"] == 200
    assert updated.fields["启用监控"] is False
    assert updated.fields["监控状态"] == ["暂停"]
    assert updated.fields["抓取频率小时"] == 24


def test_content_update_preserves_previous_metrics_and_calculates_gap() -> None:
    content = Content(
        platform=Platform.DOUYIN,
        content_id="video-1",
        account_id="account-1",
        title="视频",
        published_at=NOW - timedelta(days=1),
        fetched_at=NOW,
        views=1500,
        likes=180,
        saves=45,
        comments=20,
        shares=12,
        raw_hash="new-hash",
    )
    existing = ExistingRecord(
        record_id="rec-1",
        fields={
            "播放数": 1000,
            "点赞数": 100,
            "收藏数": 20,
            "评论数": 10,
            "分享数": 5,
            "已阅": True,
            "跟进状态": ["待拆解"],
            "拆解状态": ["待拆解"],
        },
    )

    updated = prepare_content_update(content_pending(content, now=NOW), existing)

    assert updated.fields["旧点赞数"] == 100
    assert updated.fields["点赞增量"] == 80
    assert updated.fields["收藏增量"] == 25
    assert updated.fields["已阅"] is True
    assert updated.fields["跟进状态"] == ["待拆解"]
    assert updated.fields["爆款指数"] > 0
