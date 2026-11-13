"""Scan over candidate cutoff dates with a permutation band for the maximum."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import numpy as np

from .adjust import adjusted_gap, difficulty_covariate
from .io import SystemView, from_day
from .logistic import fit_logistic


def candidate_cutoffs(
    days: np.ndarray, min_side: int = 20, max_points: int = 40, grid: str = "auto"
) -> np.ndarray:
    """Candidate cutoff days that leave at least ``min_side`` items on each side.

    ``grid="auto"`` uses the distinct item dates, thinned evenly by rank to at most
    ``max_points``; ``grid="month"`` uses the last day of each calendar month.
    """
    days = np.sort(np.asarray(days))
    if days.size == 0:
        return np.array([], dtype=np.int64)
    if grid == "month":
        first, last = from_day(days[0]), from_day(days[-1])
        cand = []
        year, month = first.year, first.month
        while (year, month) <= (last.year, last.month):
            nxt = date(year + (month == 12), month % 12 + 1, 1)
            cand.append((nxt - date(1970, 1, 1)).days - 1)
            year, month = nxt.year, nxt.month
        cand = np.array(cand, dtype=np.int64)
    elif grid == "auto":
        cand = np.unique(days)
    else:
        raise ValueError("grid must be 'auto' or 'month'")
    n_before = np.searchsorted(days, cand, side="right")
    cand = cand[(n_before >= min_side) & (days.size - n_before >= min_side)]
    if grid == "auto" and cand.size > max_points:
        pick = np.unique(np.round(np.linspace(0, cand.size - 1, max_points)).astype(int))
        cand = cand[pick]
    return cand


def score_z(
    post: np.ndarray, resid: np.ndarray, weight: np.ndarray, x0: np.ndarray, robust: bool
) -> np.ndarray:
    """Score statistic for adding each column of ``post`` to the fitted null model.

    ``U = post' (y - p)`` with variance ``post' W post - post' W X (X'WX)^-1 X' W post``
    (or its sandwich form when ``robust``); the result is ``U / sqrt(variance)``.
    """
    inv = np.linalg.pinv(x0.T @ (x0 * weight[:, None]))
    wp = post * weight[:, None]
    a = x0.T @ wp
    u = post.T @ resid
    if robust:
        e = post - x0 @ (inv @ a)
        v = (e**2).T @ (resid**2)
    else:
        v = wp.sum(axis=0) - np.einsum("kg,kl,lg->g", a, inv, a)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(v > 1e-12, u / np.sqrt(np.where(v > 1e-12, v, 1.0)), 0.0)
    return z


@dataclass(frozen=True)
class ScanPoint:
    cutoff: date
    n_before: int
    n_after: int
    plain_gap: float | None
    adjusted_gap: float | None
    gap_low: float | None
    gap_high: float | None
    z: float
    outside_band: bool


@dataclass(frozen=True)
class ScanResult:
    system: str
    alternative: str
    n_items: int
    n_candidates: int
    n_perm: int
    permuted_within_strata: bool
    observed: float | None
    best_cutoff: date | None
    band: float | None
    p_value: float | None
    alpha: float
    reported: bool
    reason: str | None
    points: list[ScanPoint] = field(default_factory=list)


def _statistic(z: np.ndarray, alternative: str) -> float:
    return float(np.max(np.abs(z))) if alternative == "two-sided" else float(np.min(z))


def scan(
    view: SystemView,
    *,
    min_side: int = 20,
    max_points: int = 40,
    grid: str = "auto",
    n_perm: int = 1000,
    alpha: float = 0.05,
    conf: float = 0.95,
    alternative: str = "two-sided",
    within_strata: bool = False,
    kind: str = "logit",
    seed: int = 0,
) -> ScanResult:
    """Adjusted gap at every candidate cutoff, with a permutation band for the best one.

    For each candidate date the score statistic ``z`` tests the post-cutoff indicator in
    the difficulty-adjusted logistic model. The scan statistic is the largest ``|z|``
    (``alternative="two-sided"``) or the most negative ``z`` (``"drop"``). Its null
    distribution comes from reassigning the item dates at random (within strata when
    ``within_strata``) and repeating the whole scan, so the search over dates is part of
    the null. ``band`` is the ``1 - alpha`` quantile of that distribution and ``p_value``
    the share of permuted scans at least as extreme as the observed one.
    """
    if alternative not in ("two-sided", "drop"):
        raise ValueError("alternative must be 'two-sided' or 'drop'")
    keep = view.pool_n > 0
    days, y = view.days[keep], view.y[keep]
    n = int(keep.sum())
    cand = candidate_cutoffs(days, min_side, max_points, grid) if n else np.array([])

    def refuse(reason: str) -> ScanResult:
        return ScanResult(
            view.system, alternative, n, int(cand.size), n_perm, within_strata, None, None,
            None, None, alpha, False, reason,
        )

    if cand.size == 0:
        return refuse(f"no candidate date leaves {min_side} items on each side")
    if float(y.min()) == float(y.max()):
        return refuse("every score is the same, so the model is not estimable")
    z_cov = difficulty_covariate(view.pool[keep], view.pool_n[keep], kind)
    x0 = np.column_stack([np.ones(n), z_cov])
    null = fit_logistic(x0, y)
    if not null.converged:
        return refuse("the null logistic fit did not converge")
    robust = bool(np.any((y > 0.0) & (y < 1.0)))
    resid = y - null.fitted
    weight = null.fitted * (1.0 - null.fitted)
    post = (days[:, None] > cand[None, :]).astype(float)
    z_obs = score_z(post, resid, weight, x0, robust)
    observed = _statistic(z_obs, alternative)

    rng = np.random.default_rng(seed)
    groups = None
    if within_strata:
        if view.strata is None:
            raise ValueError("within_strata needs stratum labels (pass strata=COLUMN)")
        codes = np.unique(view.strata[keep].astype(str), return_inverse=True)[1]
        groups = [np.flatnonzero(codes == c) for c in range(int(codes.max()) + 1)]
    stats = np.empty(n_perm)
    for b in range(n_perm):
        if groups is None:
            order = rng.permutation(n)
        else:
            order = np.arange(n)
            for g in groups:
                order[g] = rng.permutation(g)
        stats[b] = _statistic(score_z(post[order], resid, weight, x0, robust), alternative)
    if alternative == "two-sided":
        band = float(np.quantile(stats, 1.0 - alpha))
        p_value = float((np.sum(stats >= observed) + 1) / (n_perm + 1))
        outside = np.abs(z_obs) > band
        best = int(np.argmax(np.abs(z_obs)))
    else:
        band = float(np.quantile(stats, alpha))
        p_value = float((np.sum(stats <= observed) + 1) / (n_perm + 1))
        outside = z_obs < band
        best = int(np.argmin(z_obs))

    points = []
    for k, day in enumerate(cand):
        res = adjusted_gap(view, from_day(day), min_side=min_side, conf=conf, kind=kind)
        points.append(ScanPoint(
            from_day(day), res.n_before, res.n_after, res.plain_gap, res.adjusted_gap,
            res.gap_low, res.gap_high, float(z_obs[k]), bool(outside[k]),
        ))
    return ScanResult(
        view.system, alternative, n, int(cand.size), n_perm, within_strata, observed,
        from_day(cand[best]), band, p_value, alpha, True, None, points,
    )
