from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from creator_monitor.domain.models import Account, Comment, Content, MetricSnapshot, Platform
from creator_monitor.feishu.records import ExistingRecord, PendingRecord


SHANGHAI = ZoneInfo("Asia/Shanghai")
PLATFORM_LABEL = {Platform.DOUYIN: "抖音", Platform.XIAOHONGSHU: "小红书"}


def _date(value: datetime | None) -> str | None:
    if value is None:
        return None
    aware = value if value.tzinfo else value.replace(tzinfo=UTC)
    return aware.astimezone(SHANGHAI).strftime("%Y-%m-%d %H:%M")


def _without_none(fields: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in fields.items() if value is not None}


def _digest(value: object) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def account_pending(account: Account) -> PendingRecord:
    digest = account.raw_hash or _digest(account.model_dump(mode="json"))
    fields = _without_none(
        {
            "账号键": account.business_key,
            "平台": [PLATFORM_LABEL[account.platform]],
            "账号ID": account.account_id,
            "昵称": account.nickname,
            "账号主页": account.profile_url,
            "头像原始链接": account.avatar_url,
            "简介": account.bio,
            "粉丝数": account.followers,
            "关注数": account.following,
            "作品数": account.works_count,
            "总获赞数": account.total_likes,
            "启用监控": True,
            "抓取频率小时": 6,
            "监控状态": ["正常"],
            "首次发现时间": _date(account.fetched_at),
            "最后抓取时间": _date(account.fetched_at),
            "最近成功时间": _date(account.fetched_at),
            "下次抓取时间": _date(account.fetched_at + timedelta(hours=6)),
            "数据哈希": digest,
        }
    )
    return PendingRecord(account.business_key, digest, fields)


def prepare_account_update(pending: PendingRecord, existing: ExistingRecord) -> PendingRecord:
    fields = dict(pending.fields)
    previous = existing.fields.get("粉丝数")
    current = fields.get("粉丝数")
    if isinstance(previous, (int, float)) and isinstance(current, (int, float)):
        fields["粉丝增量"] = int(current - previous)
    for control in ("启用监控", "监控状态", "抓取频率小时", "首次发现时间"):
        if control in existing.fields:
            fields[control] = existing.fields[control]
    return PendingRecord(pending.business_key, pending.raw_hash, fields)


def content_pending(content: Content, *, now: datetime) -> PendingRecord:
    digest = content.raw_hash or _digest(content.model_dump(mode="json"))
    save_rate = (
        content.saves / content.likes
        if content.saves is not None and content.likes not in (None, 0)
        else 0
    )
    published = content.published_at
    published_aware = published if published.tzinfo else published.replace(tzinfo=UTC)
    now_aware = now if now.tzinfo else now.replace(tzinfo=UTC)
    fields = _without_none(
        {
            "内容键": content.business_key,
            "平台": [PLATFORM_LABEL[content.platform]],
            "内容ID": content.content_id,
            "账号键": f"{content.platform.value}:{content.account_id}",
            "标题": content.title or content.description or content.content_id,
            "正文摘要": content.description,
            "内容链接": content.canonical_url,
            "封面原始链接": content.cover_url,
            "媒体原始链接": content.media_url,
            "发布时间": _date(content.published_at),
            "时长秒": content.duration_seconds,
            "播放数": content.views,
            "点赞数": content.likes,
            "收藏数": content.saves,
            "评论数": content.comments,
            "分享数": content.shares,
            "播放增量": 0,
            "点赞增量": 0,
            "收藏增量": 0,
            "评论增量": 0,
            "分享增量": 0,
            "收藏率": save_rate,
            "爆款指数": 0,
            "爆款等级": ["C"],
            "近60天": (now_aware - published_aware).days <= 60,
            "已阅": False,
            "跟进状态": ["待处理"],
            "拆解状态": ["未拆解"],
            "首次发现时间": _date(now),
            "最后抓取时间": _date(content.fetched_at),
            "数据哈希": digest,
        }
    )
    return PendingRecord(content.business_key, digest, fields)


def prepare_content_update(pending: PendingRecord, existing: ExistingRecord) -> PendingRecord:
    fields = dict(pending.fields)
    pairs = [
        ("播放数", "旧播放数", "播放增量"),
        ("点赞数", "旧点赞数", "点赞增量"),
        ("收藏数", "旧收藏数", "收藏增量"),
        ("评论数", "旧评论数", "评论增量"),
        ("分享数", "旧分享数", "分享增量"),
    ]
    deltas: dict[str, int] = {}
    for current_name, old_name, delta_name in pairs:
        previous = existing.fields.get(current_name)
        current = fields.get(current_name)
        if isinstance(previous, (int, float)) and isinstance(current, (int, float)):
            fields[old_name] = previous
            fields[delta_name] = int(current - previous)
            deltas[delta_name] = int(current - previous)

    index = (
        deltas.get("点赞增量", 0)
        + 3 * deltas.get("收藏增量", 0)
        + 2 * deltas.get("评论增量", 0)
        + 4 * deltas.get("分享增量", 0)
    )
    fields["爆款指数"] = index
    if index >= 5000:
        grade = "S"
    elif index >= 1000:
        grade = "A"
    elif index >= 200:
        grade = "B"
    else:
        grade = "C"
    fields["爆款等级"] = [grade]

    for control in ("已阅", "跟进状态", "拆解状态", "拆解文档", "ASR文案", "跟进建议"):
        if control in existing.fields:
            fields[control] = existing.fields[control]
    if "首次发现时间" in existing.fields:
        fields["首次发现时间"] = existing.fields["首次发现时间"]
    return PendingRecord(pending.business_key, pending.raw_hash, fields)


def comment_pending(comment: Comment) -> PendingRecord:
    digest = comment.raw_hash or _digest(comment.model_dump(mode="json"))
    fields = _without_none(
        {
            "评论键": comment.business_key,
            "平台": [PLATFORM_LABEL[comment.platform]],
            "评论ID": comment.comment_id,
            "内容键": f"{comment.platform.value}:{comment.content_id}",
            "父评论ID": comment.parent_comment_id,
            "评论内容": comment.text,
            "发布时间": _date(comment.published_at),
            "点赞数": comment.likes,
            "回复数": comment.replies,
            "匿名作者ID": comment.author_id_hash,
            "采集时间": _date(comment.fetched_at),
            "数据哈希": digest,
        }
    )
    return PendingRecord(comment.business_key, digest, fields)


def snapshot_pending(snapshot: MetricSnapshot) -> PendingRecord:
    fields = _without_none(
        {
            "快照键": snapshot.snapshot_id,
            "对象类型": ["内容"],
            "对象键": snapshot.content_key,
            "时间桶": _date(snapshot.bucket_time),
            "采集时间": _date(snapshot.captured_at),
            "播放数": snapshot.metrics.views,
            "点赞数": snapshot.metrics.likes,
            "收藏数": snapshot.metrics.saves,
            "评论数": snapshot.metrics.comments,
            "分享数": snapshot.metrics.shares,
            "运行ID": snapshot.run_id,
        }
    )
    return PendingRecord(snapshot.snapshot_id, snapshot.snapshot_id, fields)
