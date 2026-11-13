"""Difficulty-adjusted gap: a logistic model with a leave-one-system-out covariate."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from scipy.special import expit, ndtr

from .gap import too_few
from .intervals import z_value
from .io import SystemView, parse_date
from .logistic import LogisticFit, fit_logistic


def difficulty_covariate(pool: np.ndarray, pool_n: np.ndarray, kind: str = "logit") -> np.ndarray:
    """Item easiness from the other systems' mean success on the item.

    ``kind="logit"`` returns ``log((s + 0.5) / (m - s + 0.5))`` where ``m`` systems answered
    and ``s`` is the sum of their scores (the 0.5 keeps all-pass and all-fail items finite);
    ``kind="raw"`` returns the mean itself.
    """
    if kind == "raw":
        return np.asarray(pool, dtype=float)
    if kind != "logit":
        raise ValueError("kind must be 'logit' or 'raw'")
    s = pool * pool_n
    return np.log((s + 0.5) / (pool_n - s + 0.5))


@dataclass(frozen=True)
class AdjustResult:
    system: str
    cutoff: date
    n_before: int
    n_after: int
    n_no_pool: int
    coef: float | None
    se: float | None
    ci_low: float | None
    ci_high: float | None
    odds_ratio: float | None
    p_value: float | None
    difficulty_coef: float | None
    plain_gap: float | None
    adjusted_gap: float | None
    gap_low: float | None
    gap_high: float | None
    removed_share: float | None
    robust: bool
    converged: bool
    conf: float
    reported: bool
    reason: str | None


def design(view: SystemView, cutoff: Any, kind: str = "logit") -> tuple[np.ndarray, np.ndarray]:
    """Design matrix [1, after, difficulty] and outcome for items the pool also answered."""
    keep = view.pool_n > 0
    post = view.post(cutoff)[keep].astype(float)
    z = difficulty_covariate(view.pool[keep], view.pool_n[keep], kind)
    x = np.column_stack([np.ones(post.size), post, z])
    return x, view.y[keep]


def marginal_gap(fit: LogisticFit, x: np.ndarray, cov: np.ndarray) -> tuple[float, float]:
    """Average over items of P(success | after) - P(success | before), and its delta-method SE."""
    x1, x0 = x.copy(), x.copy()
    x1[:, 1], x0[:, 1] = 1.0, 0.0
    p1, p0 = expit(x1 @ fit.coef), expit(x0 @ fit.coef)
    grad = ((p1 * (1 - p1))[:, None] * x1 - (p0 * (1 - p0))[:, None] * x0).mean(axis=0)
    return float((p1 - p0).mean()), float(math.sqrt(max(grad @ cov @ grad, 0.0)))


def adjusted_gap(
    view: SystemView,
    cutoff: Any,
    *,
    min_side: int = 20,
    conf: float = 0.95,
    kind: str = "logit",
    robust: bool | None = None,
) -> AdjustResult:
    """Fit ``logit P(success) = b0 + b1 * after + b2 * difficulty`` and report ``b1``.

    ``difficulty`` comes from the other systems only (see :func:`difficulty_covariate`).
    ``adjusted_gap`` is the same model on the probability scale: the mean over items of
    the fitted success after minus before, holding each item's difficulty fixed.
    ``robust`` selects sandwich standard errors; by default they are used when any score
    is not 0 or 1.
    """
    cut = parse_date(cutoff)
    x, y = design(view, cut, kind)
    post = x[:, 1] > 0.5
    n_after, n_before = int(post.sum()), int((~post).sum())
    n_no_pool = int((view.pool_n == 0).sum())
    if robust is None:
        robust = bool(np.any((y > 0.0) & (y < 1.0)))

    def refuse(reason: str, converged: bool = True) -> AdjustResult:
        return AdjustResult(
            view.system, cut, n_before, n_after, n_no_pool, None, None, None, None, None,
            None, None, None, None, None, None, None, robust, converged, conf, False, reason,
        )

    if x.shape[0] == 0:
        return refuse("no item was answered by any other system")
    reason = too_few(n_before, n_after, min_side)
    if reason is not None:
        return refuse(reason)
    if float(y.min()) == float(y.max()):
        return refuse("every score is the same, so the model is not estimable")
    fit = fit_logistic(x, y)
    if not fit.converged:
        return refuse("the logistic fit did not converge (separated data)", converged=False)
    cov = fit.cov_robust if robust else fit.cov
    se = float(math.sqrt(cov[1, 1]))
    coef = float(fit.coef[1])
    z = z_value(conf)
    gap, gap_se = marginal_gap(fit, x, cov)
    plain = float(y[post].mean() - y[~post].mean())
    removed = 1.0 - gap / plain if abs(plain) > 1e-12 else None
    return AdjustResult(
        view.system, cut, n_before, n_after, n_no_pool, coef, se, coef - z * se, coef + z * se,
        math.exp(coef), float(2.0 * ndtr(-abs(coef / se))) if se > 0 else None,
        float(fit.coef[2]), plain, gap, gap - z * gap_se, gap + z * gap_se, removed,
        robust, True, conf, True, None,
    )
