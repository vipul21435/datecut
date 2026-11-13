"""Difference in differences: a system's gap minus the reference pool's gap."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

from .gap import too_few
from .io import SystemView, parse_date


@dataclass(frozen=True)
class DidResult:
    system: str
    cutoff: date
    n_before: int
    n_after: int
    n_no_pool: int
    system_gap: float | None
    pool_gap: float | None
    did: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    n_boot: int
    n_boot_used: int
    clustered: bool
    n_clusters: int | None
    conf: float
    reported: bool
    reason: str | None


def _ratio_diff(sum_a: np.ndarray, n_a: np.ndarray, sum_b: np.ndarray, n_b: np.ndarray):
    with np.errstate(divide="ignore", invalid="ignore"):
        return sum_a / n_a - sum_b / n_b


def diff_in_diff(
    view: SystemView,
    cutoff: Any,
    *,
    min_side: int = 20,
    conf: float = 0.95,
    n_boot: int = 2000,
    seed: int = 0,
    cluster: bool = False,
) -> DidResult:
    """The system's gap minus the pool's gap on the same items, with a bootstrap interval.

    With ``d_i`` the system's score minus the pool's mean score on item ``i`` the estimate
    is ``mean(d_i | after) - mean(d_i | before)``. Items are resampled with replacement
    within each side of the cutoff; with ``cluster=True`` whole strata (the labels in
    ``view.strata``) are resampled instead, which keeps the dependence between items of
    one source. The interval is the percentile interval and the p-value is twice the
    smaller tail share of resampled estimates on either side of zero.
    """
    cut = parse_date(cutoff)
    keep = view.pool_n > 0
    post = view.post(cut)[keep]
    y, pool = view.y[keep], view.pool[keep]
    d = y - pool
    n_after, n_before = int(post.sum()), int((~post).sum())
    n_no_pool = int((~keep).sum())
    labels = None
    n_clusters = None
    if cluster:
        if view.strata is None:
            raise ValueError("cluster=True needs stratum labels (pass strata=COLUMN to table.view)")
        labels = view.strata[keep]
        n_clusters = len(set(labels.tolist()))
    reason = too_few(n_before, n_after, min_side)
    if reason is None and cluster and n_clusters is not None and n_clusters < 2:
        reason = "clustered resampling needs at least two strata"
    if reason is not None:
        return DidResult(
            view.system, cut, n_before, n_after, n_no_pool, None, None, None, None, None, None,
            n_boot, 0, cluster, n_clusters, conf, False, reason,
        )
    system_gap = float(y[post].mean() - y[~post].mean())
    pool_gap = float(pool[post].mean() - pool[~post].mean())
    estimate = float(d[post].mean() - d[~post].mean())

    rng = np.random.default_rng(seed)
    if labels is None:
        d_after, d_before = d[post], d[~post]
        draws = np.empty(n_boot)
        chunk = max(1, min(n_boot, 4_000_000 // max(n_after + n_before, 1)))
        for start in range(0, n_boot, chunk):
            size = min(chunk, n_boot - start)
            ia = rng.integers(0, n_after, size=(size, n_after))
            ib = rng.integers(0, n_before, size=(size, n_before))
            draws[start:start + size] = d_after[ia].mean(axis=1) - d_before[ib].mean(axis=1)
    else:
        names, codes = np.unique(labels.astype(str), return_inverse=True)
        k = names.size
        sum_a = np.bincount(codes, weights=d * post, minlength=k)
        cnt_a = np.bincount(codes, weights=post.astype(float), minlength=k)
        sum_b = np.bincount(codes, weights=d * ~post, minlength=k)
        cnt_b = np.bincount(codes, weights=(~post).astype(float), minlength=k)
        pick = rng.integers(0, k, size=(n_boot, k))
        draws = _ratio_diff(
            sum_a[pick].sum(axis=1), cnt_a[pick].sum(axis=1),
            sum_b[pick].sum(axis=1), cnt_b[pick].sum(axis=1),
        )
    draws = draws[np.isfinite(draws)]
    if draws.size == 0:
        return DidResult(
            view.system, cut, n_before, n_after, n_no_pool, system_gap, pool_gap, estimate,
            None, None, None, n_boot, 0, cluster, n_clusters, conf, False,
            "no resample had items on both sides of the cutoff",
        )
    alpha = 1.0 - conf
    low, high = np.quantile(draws, [alpha / 2.0, 1.0 - alpha / 2.0])
    below = (np.sum(draws <= 0.0) + 1) / (draws.size + 1)
    above = (np.sum(draws >= 0.0) + 1) / (draws.size + 1)
    tail = min(below, above)
    return DidResult(
        view.system, cut, n_before, n_after, n_no_pool, system_gap, pool_gap, estimate,
        float(low), float(high), float(min(1.0, 2.0 * tail)), n_boot, int(draws.size),
        cluster, n_clusters, conf, True, None,
    )
