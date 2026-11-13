"""Success against item date in windows, for one system and for the pool."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np

from .intervals import wilson, z_value
from .io import SystemView, from_day


@dataclass(frozen=True)
class TrendWindow:
    start: date
    end: date
    n: int
    rate: float
    low: float
    high: float
    pool_rate: float | None
    pool_low: float | None
    pool_high: float | None
    diff: float | None
    diff_low: float | None
    diff_high: float | None


def _mean_band(values: np.ndarray, z: float) -> tuple[float, float, float]:
    mean = float(values.mean())
    if values.size < 2:
        return mean, mean, mean
    half = z * float(values.std(ddof=1)) / math.sqrt(values.size)
    return mean, mean - half, mean + half


def _window(view: SystemView, idx: np.ndarray, conf: float) -> TrendWindow:
    z = z_value(conf)
    y = view.y[idx]
    low, high = wilson(float(y.sum()), y.size, conf)
    has_pool = view.pool_n[idx] > 0
    pool = view.pool[idx][has_pool]
    pool_rate = pool_low = pool_high = diff = diff_low = diff_high = None
    if pool.size:
        pool_rate, pool_low, pool_high = _mean_band(pool, z)
        pool_low, pool_high = max(0.0, pool_low), min(1.0, pool_high)
        diff, diff_low, diff_high = _mean_band(y[has_pool] - pool, z)
    return TrendWindow(
        from_day(view.days[idx[0]]), from_day(view.days[idx[-1]]), int(y.size),
        float(y.mean()), low, high, pool_rate, pool_low, pool_high, diff, diff_low, diff_high,
    )


def _period(day: int, by: str) -> tuple[int, int]:
    d = from_day(day)
    if by == "year":
        return d.year, 0
    if by == "quarter":
        return d.year, (d.month - 1) // 3
    return d.year, d.month


def trend(
    view: SystemView,
    *,
    window: int = 100,
    step: int | None = None,
    by: str | None = None,
    conf: float = 0.95,
) -> list[TrendWindow]:
    """Success rate over item date.

    With ``by`` set to ``"month"``, ``"quarter"`` or ``"year"`` the windows are calendar
    periods. Otherwise they are rolling windows of ``window`` consecutive items in date
    order, moved ``step`` items at a time (default: half a window). The system's band is
    the Wilson interval; the pool's band and the band of the system-minus-pool difference
    are normal intervals over the items in the window.
    """
    n = view.y.size
    if n == 0:
        return []
    if by is not None:
        if by not in ("month", "quarter", "year"):
            raise ValueError("by must be 'month', 'quarter' or 'year'")
        keys = [_period(int(d), by) for d in view.days]
        out = []
        start = 0
        for i in range(1, n + 1):
            if i == n or keys[i] != keys[start]:
                out.append(_window(view, np.arange(start, i), conf))
                start = i
        return out
    if window < 1:
        raise ValueError("window must be at least 1")
    window = min(window, n)
    step = max(1, window // 2) if step is None else step
    if step < 1:
        raise ValueError("step must be at least 1")
    starts = list(range(0, n - window + 1, step))
    if starts[-1] != n - window:
        starts.append(n - window)
    return [_window(view, np.arange(s, s + window), conf) for s in starts]
