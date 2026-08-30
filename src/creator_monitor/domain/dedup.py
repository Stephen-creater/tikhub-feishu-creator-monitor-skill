from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel


class Deduplicable(Protocol):
    @property
    def business_key(self) -> str: ...

    fetched_at: datetime


T = TypeVar("T", bound=Deduplicable)


@dataclass(frozen=True)
class DedupResult(Generic[T]):
    records: list[T]
    duplicate_count: int


def _completeness(record: Deduplicable) -> int:
    if isinstance(record, BaseModel):
        values = record.model_dump(exclude_none=True)
        return sum(value not in ("", [], {}) for value in values.values())
    return sum(value is not None for value in vars(record).values())


def deduplicate_latest(records: list[T]) -> DedupResult[T]:
    winners: dict[str, T] = {}
    order: list[str] = []
    duplicates = 0

    for record in records:
        key = record.business_key
        current = winners.get(key)
        if current is None:
            winners[key] = record
            order.append(key)
            continue

        duplicates += 1
        candidate_rank = (record.fetched_at, _completeness(record))
        current_rank = (current.fetched_at, _completeness(current))
        if candidate_rank > current_rank:
            winners[key] = record

    return DedupResult(records=[winners[key] for key in order], duplicate_count=duplicates)
