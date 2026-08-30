from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from creator_monitor.domain.models import Platform


def _stable_key(platform: Platform, identifier: str) -> str:
    normalized = identifier.strip()
    if not normalized:
        raise ValueError("stable identifier cannot be empty")
    return f"{platform.value}:{normalized}"


def account_key(platform: Platform, account_id: str) -> str:
    return _stable_key(platform, account_id)


def content_key(platform: Platform, content_id: str) -> str:
    return _stable_key(platform, content_id)


def comment_key(platform: Platform, comment_id: str) -> str:
    return _stable_key(platform, comment_id)


def bucket_time(captured_at: datetime, *, bucket_minutes: int) -> datetime:
    if bucket_minutes <= 0:
        raise ValueError("bucket_minutes must be positive")
    aware = captured_at if captured_at.tzinfo else captured_at.replace(tzinfo=UTC)
    utc_value = aware.astimezone(UTC)
    epoch = int(utc_value.timestamp())
    bucket_seconds = bucket_minutes * 60
    floored = epoch - (epoch % bucket_seconds)
    return datetime.fromtimestamp(floored, tz=UTC)


def snapshot_key(
    business_key: str,
    captured_at: datetime,
    *,
    bucket_minutes: int,
) -> str:
    bucket = bucket_time(captured_at, bucket_minutes=bucket_minutes)
    stamp = bucket.isoformat(timespec="seconds").replace("+00:00", "Z")
    return f"{business_key}:{stamp}"


def weak_content_key(
    *,
    platform: Platform,
    account_id: str,
    published_at: datetime,
    text: str,
) -> str:
    normalized_text = re.sub(r"\s+", " ", text.strip()).casefold()
    aware = published_at if published_at.tzinfo else published_at.replace(tzinfo=UTC)
    source = "|".join(
        [platform.value, account_id.strip(), aware.astimezone(UTC).isoformat(), normalized_text]
    )
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]
    return f"weak:{platform.value}:{digest}"
