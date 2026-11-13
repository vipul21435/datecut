"""Stratified comparison: the Mantel-Haenszel common odds ratio across strata."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
from scipy.special import chdtrc

from .gap import too_few
from .intervals import z_value
from .io import SystemView, parse_date


@dataclass(frozen=True)
class MHEstimate:
    odds_ratio: float | None
    log_se: float | None
    ci_low: float | None
    ci_high: float | None
    cmh_statistic: float | None
    cmh_p: float | None
    homogeneity_statistic: float | None
    homogeneity_df: int | None
    homogeneity_p: float | None
    n_strata: int


def _expected_cell(table: np.ndarray, psi: float) -> tuple[float, float]:
    """Expected top-left cell and its variance when the stratum's odds ratio is ``psi``."""
    a, b = table[0]
    c, d = table[1]
    n1, n0, m1 = a + b, c + d, a + c
    low, high = max(0.0, m1 - n0), min(n1, m1)
    if abs(psi - 1.0) < 1e-12:
        e = n1 * m1 / (n1 + n0)
    else:
        qa = 1.0 - psi
        qb = n0 - m1 + psi * (n1 + m1)
        qc = -psi * n1 * m1
        disc = math.sqrt(max(qb * qb - 4.0 * qa * qc, 0.0))
        roots = [(-qb + disc) / (2.0 * qa), (-qb - disc) / (2.0 * qa)]
        inside = [r for r in roots if low - 1e-9 <= r <= high + 1e-9]
        e = inside[0] if inside else min(roots, key=lambda r: min(abs(r - low), abs(r - high)))
    cells = [e, n1 - e, m1 - e, n0 - m1 + e]
    if min(cells) <= 0.0:
        return e, 0.0
    return e, 1.0 / sum(1.0 / v for v in cells)


def mantel_haenszel(tables: np.ndarray, conf: float = 0.95) -> MHEstimate:
    """Mantel-Haenszel analysis of K 2x2 tables of shape (K, 2, 2).

    Each table is ``[[a, b], [c, d]]`` with rows after/before and columns success/failure.
    Returns the common odds ratio ``sum(a d / n) / sum(b c / n)`` with the
    Robins-Breslow-Greenland interval on the log scale, the Cochran-Mantel-Haenszel test
    of a common odds ratio of 1 (no continuity correction) and the Breslow-Day test of
    homogeneity with Tarone's correction. Strata with an empty row are ignored.
    """
    t = np.asarray(tables, dtype=float).reshape(-1, 2, 2)
    rows = t.sum(axis=2)
    t = t[(rows[:, 0] > 0) & (rows[:, 1] > 0)]
    k = t.shape[0]
    empty = MHEstimate(None, None, None, None, None, None, None, None, None, k)
    if k == 0:
        return empty
    a, b, c, d = t[:, 0, 0], t[:, 0, 1], t[:, 1, 0], t[:, 1, 1]
    n = a + b + c + d
    r, s = a * d / n, b * c / n
    sum_r, sum_s = float(r.sum()), float(s.sum())

    expected = (a + b) * (a + c) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        var = np.where(n > 1, (a + b) * (c + d) * (a + c) * (b + d) / (n * n * (n - 1.0)), 0.0)
    cmh_stat = cmh_p = None
    if var.sum() > 0:
        cmh_stat = float((a.sum() - expected.sum()) ** 2 / var.sum())
        cmh_p = float(chdtrc(1, cmh_stat))
    if sum_r <= 0.0 or sum_s <= 0.0:
        return MHEstimate(None, None, None, None, cmh_stat, cmh_p, None, None, None, k)

    odds_ratio = sum_r / sum_s
    p, q = (a + d) / n, (b + c) / n
    log_var = (
        float((p * r).sum()) / (2.0 * sum_r**2)
        + float((p * s + q * r).sum()) / (2.0 * sum_r * sum_s)
        + float((q * s).sum()) / (2.0 * sum_s**2)
    )
    log_se = math.sqrt(log_var)
    z = z_value(conf)
    low = math.exp(math.log(odds_ratio) - z * log_se)
    high = math.exp(math.log(odds_ratio) + z * log_se)

    hom_stat = hom_p = None
    hom_df = None
    terms = [_expected_cell(table, odds_ratio) for table in t]
    usable = [(obs, e, v) for obs, (e, v) in zip(a, terms, strict=True) if v > 0.0]
    if len(usable) >= 2:
        diff = np.array([obs - e for obs, e, _ in usable])
        v = np.array([v for _, _, v in usable])
        hom_stat = float((diff**2 / v).sum() - diff.sum() ** 2 / v.sum())
        hom_stat = max(hom_stat, 0.0)
        hom_df = len(usable) - 1
        hom_p = float(chdtrc(hom_df, hom_stat))
    return MHEstimate(
        odds_ratio, log_se, low, high, cmh_stat, cmh_p, hom_stat, hom_df, hom_p, k
    )


@dataclass(frozen=True)
class StratumRow:
    stratum: str
    n_before: int
    n_after: int
    rate_before: float | None
    rate_after: float | None
    odds_ratio: float | None


@dataclass(frozen=True)
class StrataResult:
    system: str
    cutoff: date
    column: str
    n_before: int
    n_after: int
    n_strata: int
    n_strata_one_sided: int
    estimate: MHEstimate | None
    conf: float
    reported: bool
    reason: str | None
    rows: list[StratumRow] = field(default_factory=list)


def stratum_tables(view: SystemView, cutoff: Any) -> tuple[list[str], np.ndarray]:
    """One 2x2 table per stratum label: rows after/before, columns success/failure."""
    if view.strata is None:
        raise ValueError("the view has no stratum labels (pass strata=COLUMN to table.view)")
    post = view.post(cutoff)
    names = sorted({str(v) for v in view.strata})
    tables = np.zeros((len(names), 2, 2))
    for k, name in enumerate(names):
        mask = view.strata == name
        for row, side in enumerate((post, ~post)):
            sel = mask & side
            wins = float(view.y[sel].sum())
            tables[k, row] = (wins, float(sel.sum()) - wins)
    return names, tables


def strata_gap(
    view: SystemView, cutoff: Any, *, column: str = "stratum", min_side: int = 20,
    conf: float = 0.95,
) -> StrataResult:
    """Mantel-Haenszel odds ratio of success after against before the cutoff, across strata.

    An odds ratio below 1 means lower odds of success after the cutoff within strata.
    """
    cut = parse_date(cutoff)
    names, tables = stratum_tables(view, cut)
    post = view.post(cut)
    n_after = int(post.sum())
    n_before = int(post.size - n_after)
    rows = []
    for name, t in zip(names, tables, strict=True):
        na, nb = int(round(t[0].sum())), int(round(t[1].sum()))
        cross = t[0, 1] * t[1, 0]
        rows.append(StratumRow(
            name, nb, na,
            float(t[1, 0] / nb) if nb else None,
            float(t[0, 0] / na) if na else None,
            float(t[0, 0] * t[1, 1] / cross) if na and nb and cross > 0 else None,
        ))
    one_sided = sum(1 for r in rows if r.n_before == 0 or r.n_after == 0)
    reason = too_few(n_before, n_after, min_side)
    if reason is None and one_sided == len(rows):
        reason = "no stratum has items on both sides of the cutoff"
    if reason is not None:
        return StrataResult(
            view.system, cut, column, n_before, n_after, len(rows) - one_sided, one_sided,
            None, conf, False, reason, rows,
        )
    estimate = mantel_haenszel(tables, conf)
    if estimate.odds_ratio is None:
        reason = "the common odds ratio is not estimable (a zero cell in every stratum)"
    return StrataResult(
        view.system, cut, column, n_before, n_after, estimate.n_strata, one_sided,
        estimate, conf, reason is None, reason, rows,
    )
