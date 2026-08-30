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
    "xiaohongshu.profile", "/api/v1/xiaohongshu/app_v2/get_user_info", Decimal("0.01")
)
NOTES = Endpoint(
    "xiaohongshu.notes",
    "/api/v1/xiaohongshu/app_v2/get_user_posted_notes",
    Decimal("0.01"),
)
COMMENTS = Endpoint(
    "xiaohongshu.comments",
    "/api/v1/xiaohongshu/app_v2/get_note_comments",
    Decimal("0.01"),
)


def _business_data(payload: dict) -> dict[str, object]:
    data = as_dict(payload.get("data"))
    nested_data = data.get("data")
    return as_dict(nested_data) if isinstance(nested_data, dict) else data


def normalize_profile(payload: dict, *, fetched_at: datetime) -> Account:
    data = _business_data(payload)
    user = as_dict(first(data, ("userBasicInfo", "user_info", "userInfo", "user"), data))
    interactions = {
        str(first(as_dict(item), ("type", "name"), "")).casefold(): first(
            as_dict(item), ("count", "value")
        )
        for item in as_list(first(data, ("interactions", "interactionInfo"), []))
    }
    account_id = str(first(user, ("userId", "user_id", "id")))
    return Account(
        platform=Platform.XIAOHONGSHU,
        account_id=account_id,
        nickname=first(user, ("nickname", "name")),
        unique_handle=first(user, ("redId", "red_id", "xhsId")),
        profile_url=f"https://www.xiaohongshu.com/user/profile/{account_id}",
        avatar_url=first_url(first(user, ("images", "avatar", "image"))),
        bio=first(user, ("desc", "description", "bio")),
        followers=parse_count(interactions.get("fans") or interactions.get("followers")),
        following=parse_count(interactions.get("follows") or interactions.get("following")),
        works_count=parse_count(first(data, ("noteCount", "note_count", "notes"))),
        total_likes=parse_count(
            interactions.get("interaction") or interactions.get("likes")
        ),
        fetched_at=fetched_at,
        raw_hash=raw_hash(data),
    )


def normalize_notes(payload: dict, *, fetched_at: datetime) -> tuple[list[Content], PageInfo]:
    data = _business_data(payload)
    raw_notes = as_list(first(data, ("notes", "noteList", "items"), []))
    records: list[Content] = []
    for value in raw_notes:
        item = as_dict(value)
        note_id = str(first(item, ("noteId", "note_id", "id")))
        stats = as_dict(first(item, ("interactInfo", "interact_info", "statistics"), {}))
        cover = first(item, ("cover", "coverInfo", "imageList"))
        records.append(
            Content(
                platform=Platform.XIAOHONGSHU,
                content_id=note_id,
                account_id=str(first(item, ("userId", "user_id", "authorId"))),
                title=first(item, ("title", "displayTitle")),
                description=first(item, ("desc", "description", "content")),
                canonical_url=f"https://www.xiaohongshu.com/explore/{note_id}",
                cover_url=first_url(cover),
                media_url=first_url(first(item, ("video", "videoInfo", "videoUrl"))),
                published_at=parse_timestamp(first(item, ("time", "createTime", "create_time"))),
                fetched_at=fetched_at,
                views=parse_count(first(stats, ("viewCount", "view_count", "readCount"))),
                likes=parse_count(first(stats, ("likedCount", "likeCount", "likes"))),
                comments=parse_count(first(stats, ("commentCount", "comments"))),
                shares=parse_count(first(stats, ("shareCount", "shares"))),
                saves=parse_count(first(stats, ("collectedCount", "collectCount", "saves"))),
                raw_hash=raw_hash(item),
            )
        )
    cursor = first(data, ("cursor", "nextCursor"))
    return records, PageInfo(
        next_cursor=str(cursor) if cursor not in (None, "") else None,
        has_more=bool(first(data, ("hasMore", "has_more"), False)),
    )


def normalize_comments(payload: dict, *, fetched_at: datetime) -> tuple[list[Comment], PageInfo]:
    data = _business_data(payload)
    raw_comments = as_list(first(data, ("comments", "commentList", "items"), []))
    records: list[Comment] = []
    for value in raw_comments:
        item = as_dict(value)
        user = as_dict(first(item, ("userInfo", "user_info", "user"), {}))
        records.append(
            Comment(
                platform=Platform.XIAOHONGSHU,
                comment_id=str(first(item, ("id", "commentId", "comment_id"))),
                content_id=str(first(item, ("noteId", "note_id", "targetId"))),
                parent_comment_id=first(item, ("parentCommentId", "parent_id")),
                text=str(first(item, ("content", "text"))),
                published_at=parse_timestamp(first(item, ("createTime", "create_time", "time"))),
                fetched_at=fetched_at,
                likes=parse_count(first(item, ("likeCount", "likedCount", "likes"))),
                replies=parse_count(first(item, ("subCommentCount", "replyCount", "replies"))),
                author_id_hash=anonymized_id(first(user, ("userId", "user_id", "id"))),
                raw_hash=raw_hash(item),
            )
        )
    cursor = first(data, ("cursor", "nextCursor"))
    return records, PageInfo(
        next_cursor=str(cursor) if cursor not in (None, "") else None,
        has_more=bool(first(data, ("hasMore", "has_more"), False)),
    )
