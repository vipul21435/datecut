"""Power of the before/after comparison: the smallest gap the counts could detect."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from scipy.special import ndtr, ndtri

from .io import SystemView, parse_date


def power_two_proportions(p1: float, n1: float, p2: float, n2: float, alpha: float = 0.05) -> float:
    """Power of the two-sided pooled z-test for two proportions (normal approximation)."""
    d = abs(p1 - p2)
    pooled = (n1 * p1 + n2 * p2) / (n1 + n2)
    s0 = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n1 + 1.0 / n2))
    s1 = math.sqrt(p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2)
    z = float(ndtri(1.0 - alpha / 2.0))
    if s1 == 0.0:
        return 1.0 if d > z * s0 else 0.0
    return float(ndtr((d - z * s0) / s1) + ndtr((-d - z * s0) / s1))


def min_detectable_gap(
    rate_before: float,
    n_before: int,
    n_after: int,
    *,
    alpha: float = 0.05,
    power: float = 0.8,
    direction: str = "drop",
) -> float | None:
    """Smallest absolute gap detected with the given power, or None if no gap is.

    ``direction`` is ``"drop"`` (after below before) or ``"rise"``. The before rate is held
    at ``rate_before`` and the after rate is moved away from it by bisection until the
    pooled z-test at level ``alpha`` reaches the requested power.
    """
    if direction not in ("drop", "rise"):
        raise ValueError("direction must be 'drop' or 'rise'")
    if n_before <= 0 or n_after <= 0:
        return None
    far = 0.0 if direction == "drop" else 1.0
    if power_two_proportions(far, n_after, rate_before, n_before, alpha) < power:
        return None
    near = rate_before
    for _ in range(60):
        mid = 0.5 * (near + far)
        if power_two_proportions(mid, n_after, rate_before, n_before, alpha) >= power:
            far = mid
        else:
            near = mid
    return abs(far - rate_before)


@dataclass(frozen=True)
class PowerResult:
    system: str
    cutoff: date
    n_before: int
    n_after: int
    rate_before: float | None
    alpha: float
    power: float
    detectable_drop: float | None
    detectable_rise: float | None


def detectable(
    view: SystemView, cutoff: Any, *, alpha: float = 0.05, power: float = 0.8
) -> PowerResult:
    """Minimum detectable drop and rise for one system at one cutoff."""
    cut = parse_date(cutoff)
    post = view.post(cut)
    n_after = int(post.sum())
    n_before = int(post.size - n_after)
    if n_before == 0 or n_after == 0:
        rate = float(view.y[~post].mean()) if n_before else None
        return PowerResult(view.system, cut, n_before, n_after, rate, alpha, power, None, None)
    rate = float(view.y[~post].mean())
    return PowerResult(
        view.system, cut, n_before, n_after, rate, alpha, power,
        min_detectable_gap(rate, n_before, n_after, alpha=alpha, power=power, direction="drop"),
        min_detectable_gap(rate, n_before, n_after, alpha=alpha, power=power, direction="rise"),
    )
