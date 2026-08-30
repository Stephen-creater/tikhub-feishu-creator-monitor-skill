from __future__ import annotations

from creator_monitor.domain.metrics import calculate_delta
from creator_monitor.domain.models import MetricCounts


def test_calculate_metric_delta() -> None:
    old = MetricCounts(views=100, likes=10, comments=3, shares=2, saves=4)
    new = MetricCounts(views=160, likes=25, comments=5, shares=3, saves=9)

    delta = calculate_delta(old, new)

    assert delta.views == 60
    assert delta.likes == 15
    assert delta.comments == 2
    assert delta.shares == 1
    assert delta.saves == 5


def test_metric_drop_is_not_silently_clamped() -> None:
    old = MetricCounts(likes=100)
    new = MetricCounts(likes=90)

    assert calculate_delta(old, new).likes == -10


def test_missing_platform_metric_remains_missing() -> None:
    old = MetricCounts(views=None, likes=10)
    new = MetricCounts(views=None, likes=20)

    delta = calculate_delta(old, new)

    assert delta.views is None
    assert delta.likes == 10
