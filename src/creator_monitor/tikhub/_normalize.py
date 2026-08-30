from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime


def first(mapping: Mapping[str, object], names: Iterable[str], default: object = None) -> object:
    for name in names:
        value = mapping.get(name)
        if value not in (None, ""):
            return value
    return default


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def nested(mapping: Mapping[str, object], *path: str) -> object:
    value: object = mapping
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def parse_count(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return max(0, int(value))
    text = str(value).strip().replace(",", "").replace("+", "")
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10_000
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100_000_000
        text = text[:-1]
    try:
        return max(0, int(float(text) * multiplier))
    except ValueError:
        return None


def parse_timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, str) and not value.isdigit():
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    number = float(value)
    if number > 10_000_000_000:
        number /= 1000
    return datetime.fromtimestamp(number, tz=UTC)


def first_url(value: object) -> str | None:
    if isinstance(value, str):
        return value or None
    if isinstance(value, list):
        for item in value:
            candidate = first_url(item)
            if candidate:
                return candidate
        return None
    if isinstance(value, dict):
        direct = first(
            value,
            (
                "url_size_large",
                "urlSizeLarge",
                "url",
                "url_default",
                "urlDefault",
                "thumbnail",
                "first_frame",
                "master_url",
            ),
        )
        if isinstance(direct, str):
            return direct
        return first_url(first(value, ("url_list", "urlList", "images")))
    return None


def raw_hash(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def anonymized_id(value: object) -> str | None:
    if value in (None, ""):
        return None
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:24]
