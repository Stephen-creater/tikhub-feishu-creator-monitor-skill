from __future__ import annotations

from creator_monitor.domain.models import MetricCounts, MetricDelta


def _difference(old: int | None, new: int | None) -> int | None:
    if old is None or new is None:
        return None
    return new - old


def calculate_delta(old: MetricCounts, new: MetricCounts) -> MetricDelta:
    return MetricDelta(
        views=_difference(old.views, new.views),
        likes=_difference(old.likes, new.likes),
        comments=_difference(old.comments, new.comments),
        shares=_difference(old.shares, new.shares),
        saves=_difference(old.saves, new.saves),
    )
