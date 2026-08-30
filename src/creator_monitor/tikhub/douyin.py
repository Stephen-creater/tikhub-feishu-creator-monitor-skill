from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from creator_monitor.domain.models import Account, Comment, Content, Platform
from creator_monitor.tikhub._normalize import (
    anonymized_id,
    as_dict,
    as_list,
    first,
    first_url,
    parse_count,
    parse_timestamp,
    raw_hash,
)
from creator_monitor.tikhub.client import Endpoint
from creator_monitor.tikhub.models import PageInfo


PROFILE = Endpoint(
    "douyin.profile", "/api/v1/douyin/app/v3/handler_user_profile", Decimal("0.01")
)
POSTS = Endpoint(
    "douyin.posts", "/api/v1/douyin/app/v3/fetch_user_post_videos", Decimal("0.01")
)
COMMENTS = Endpoint(
    "douyin.comments", "/api/v1/douyin/app/v3/fetch_video_comments", Decimal("0.01")
)


def normalize_profile(payload: dict, *, fetched_at: datetime) -> Account:
    data = as_dict(payload.get("data"))
    user = as_dict(first(data, ("user", "user_info", "userInfo"), data))
    account_id = str(first(user, ("sec_uid", "sec_user_id", "secUid", "uid")))
    return Account(
        platform=Platform.DOUYIN,
        account_id=account_id,
        nickname=first(user, ("nickname", "name")),
        unique_handle=first(user, ("unique_id", "short_id", "uniqueId")),
        profile_url=f"https://www.douyin.com/user/{account_id}",
        avatar_url=first_url(first(user, ("avatar_larger", "avatar_medium", "avatar_thumb"))),
        bio=first(user, ("signature", "bio", "desc")),
        followers=parse_count(first(user, ("follower_count", "followerCount"))),
        following=parse_count(first(user, ("following_count", "followingCount"))),
        works_count=parse_count(first(user, ("aweme_count", "works_count", "post_count"))),
        total_likes=parse_count(first(user, ("total_favorited", "total_likes"))),
        fetched_at=fetched_at,
        raw_hash=raw_hash(user),
    )


def normalize_posts(payload: dict, *, fetched_at: datetime) -> tuple[list[Content], PageInfo]:
    data = as_dict(payload.get("data"))
    raw_posts = as_list(first(data, ("aweme_list", "awemeList", "items"), []))
    records: list[Content] = []
    for value in raw_posts:
        item = as_dict(value)
        content_id = str(first(item, ("aweme_id", "awemeId", "id")))
        author = as_dict(first(item, ("author", "authorInfo"), {}))
        stats = as_dict(first(item, ("statistics", "stats"), {}))
        video = as_dict(item.get("video"))
        duration_ms = first(video, ("duration", "duration_ms"))
        records.append(
            Content(
                platform=Platform.DOUYIN,
                content_id=content_id,
                account_id=str(first(author, ("sec_uid", "sec_user_id", "uid"))),
                title=first(item, ("desc", "title")),
                description=first(item, ("desc", "title")),
                canonical_url=f"https://www.douyin.com/video/{content_id}",
                cover_url=first_url(first(video, ("cover", "origin_cover", "dynamic_cover"))),
                media_url=first_url(first(video, ("play_addr", "download_addr"))),
                published_at=parse_timestamp(first(item, ("create_time", "createTime"))),
                duration_seconds=(float(duration_ms) / 1000 if duration_ms is not None else None),
                fetched_at=fetched_at,
                views=parse_count(first(stats, ("play_count", "view_count"))),
                likes=parse_count(first(stats, ("digg_count", "like_count"))),
                comments=parse_count(first(stats, ("comment_count",))),
                shares=parse_count(first(stats, ("share_count",))),
                saves=parse_count(first(stats, ("collect_count", "favorite_count"))),
                raw_hash=raw_hash(item),
            )
        )
    cursor = first(data, ("max_cursor", "cursor"))
    return records, PageInfo(
        next_cursor=str(cursor) if cursor not in (None, "") else None,
        has_more=bool(first(data, ("has_more", "hasMore"), False)),
    )


def normalize_comments(payload: dict, *, fetched_at: datetime) -> tuple[list[Comment], PageInfo]:
    data = as_dict(payload.get("data"))
    raw_comments = as_list(first(data, ("comments", "comment_list", "items"), []))
    records: list[Comment] = []
    for value in raw_comments:
        item = as_dict(value)
        user = as_dict(first(item, ("user", "user_info"), {}))
        records.append(
            Comment(
                platform=Platform.DOUYIN,
                comment_id=str(first(item, ("cid", "comment_id", "id"))),
                content_id=str(first(item, ("aweme_id", "item_id"))),
                parent_comment_id=first(item, ("reply_id", "parent_id")),
                text=str(first(item, ("text", "content"))),
                published_at=parse_timestamp(first(item, ("create_time", "createTime"))),
                fetched_at=fetched_at,
                likes=parse_count(first(item, ("digg_count", "like_count"))),
                replies=parse_count(first(item, ("reply_comment_total", "reply_count"))),
                author_id_hash=anonymized_id(first(user, ("uid", "sec_uid", "id"))),
                raw_hash=raw_hash(item),
            )
        )
    cursor = first(data, ("cursor", "max_cursor"))
    return records, PageInfo(
        next_cursor=str(cursor) if cursor not in (None, "") else None,
        has_more=bool(first(data, ("has_more", "hasMore"), False)),
    )
