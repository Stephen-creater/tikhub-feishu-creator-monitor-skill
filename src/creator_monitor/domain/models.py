from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Platform(StrEnum):
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"


class KeyQuality(StrEnum):
    STABLE = "stable"
    WEAK = "weak"


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def strip_blank_strings(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class MetricCounts(DomainModel):
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)


class MetricDelta(DomainModel):
    views: int | None = None
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    saves: int | None = None


class Account(DomainModel):
    platform: Platform
    account_id: str
    nickname: str | None = None
    unique_handle: str | None = None
    profile_url: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    followers: int | None = Field(default=None, ge=0)
    following: int | None = Field(default=None, ge=0)
    works_count: int | None = Field(default=None, ge=0)
    total_likes: int | None = Field(default=None, ge=0)
    fetched_at: datetime
    source_updated_at: datetime | None = None
    raw_hash: str | None = None
    key_quality: KeyQuality = KeyQuality.STABLE

    @property
    def business_key(self) -> str:
        from creator_monitor.domain.identity import account_key

        return account_key(self.platform, self.account_id)


class Content(DomainModel):
    platform: Platform
    content_id: str
    account_id: str
    title: str | None = None
    description: str | None = None
    canonical_url: str | None = None
    cover_url: str | None = None
    media_url: str | None = None
    published_at: datetime
    duration_seconds: float | None = Field(default=None, ge=0)
    fetched_at: datetime
    source_updated_at: datetime | None = None
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
    shares: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    raw_hash: str | None = None
    key_quality: KeyQuality = KeyQuality.STABLE

    @property
    def business_key(self) -> str:
        from creator_monitor.domain.identity import content_key

        return content_key(self.platform, self.content_id)

    @property
    def metrics(self) -> MetricCounts:
        return MetricCounts(
            views=self.views,
            likes=self.likes,
            comments=self.comments,
            shares=self.shares,
            saves=self.saves,
        )


class Comment(DomainModel):
    platform: Platform
    comment_id: str
    content_id: str
    parent_comment_id: str | None = None
    text: str
    published_at: datetime | None = None
    fetched_at: datetime
    likes: int | None = Field(default=None, ge=0)
    replies: int | None = Field(default=None, ge=0)
    author_id_hash: str | None = None
    raw_hash: str | None = None

    @property
    def business_key(self) -> str:
        from creator_monitor.domain.identity import comment_key

        return comment_key(self.platform, self.comment_id)


class MetricSnapshot(DomainModel):
    snapshot_id: str
    content_key: str
    captured_at: datetime
    bucket_time: datetime
    metrics: MetricCounts
    run_id: str


class RunSummary(DomainModel):
    run_id: str
    status: str
    fetched: int = Field(default=0, ge=0)
    deduped_in_batch: int = Field(default=0, ge=0)
    inserted: int = Field(default=0, ge=0)
    updated: int = Field(default=0, ge=0)
    unchanged: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)

