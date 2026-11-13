"""Intervals for one proportion and for the difference of two proportions."""

from __future__ import annotations

import math

from scipy.special import ndtr, ndtri


def z_value(conf: float) -> float:
    """Two-sided standard normal quantile for a confidence level in (0, 1)."""
    if not 0.0 < conf < 1.0:
        raise ValueError("conf must be between 0 and 1")
    return float(ndtri(0.5 + conf / 2.0))


def wilson(successes: float, n: float, conf: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a proportion.

    ``successes`` may be a sum of scores in [0, 1]; the interval then uses the binomial
    variance p(1-p), which is an upper bound for any variable confined to [0, 1].
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0.0 <= successes <= n:
        raise ValueError("successes must lie between 0 and n")
    z = z_value(conf)
    p = successes / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe(
    successes1: float, n1: float, successes2: float, n2: float, conf: float = 0.95
) -> tuple[float, float]:
    """Newcombe's hybrid score interval for p1 - p2 (his method 10).

    The limits combine the Wilson limits of the two proportions:
    lower = d - sqrt((p1 - l1)^2 + (u2 - p2)^2), upper = d + sqrt((u1 - p1)^2 + (p2 - l2)^2).
    """
    p1 = successes1 / n1
    p2 = successes2 / n2
    l1, u1 = wilson(successes1, n1, conf)
    l2, u2 = wilson(successes2, n2, conf)
    d = p1 - p2
    lower = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    upper = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return max(-1.0, lower), min(1.0, upper)


def two_proportion_p(successes1: float, n1: float, successes2: float, n2: float) -> float:
    """Two-sided p-value of the pooled two-proportion z-test.

    Returns 1.0 when the pooled rate is 0 or 1.
    """
    pooled = (successes1 + successes2) / (n1 + n2)
    var = pooled * (1.0 - pooled) * (1.0 / n1 + 1.0 / n2)
    if var <= 0.0:
        return 1.0
    z = (successes1 / n1 - successes2 / n2) / math.sqrt(var)
    return float(2.0 * ndtr(-abs(z)))
