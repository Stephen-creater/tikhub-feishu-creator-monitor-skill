from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageInfo:
    next_cursor: str | None
    has_more: bool

