"""The plain gap: success after the cutoff minus success before it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from .intervals import newcombe, two_proportion_p
from .io import ItemTable, SystemView, parse_date


@dataclass(frozen=True)
class GapResult:
    system: str
    cutoff: date
    n_before: int
    n_after: int
    rate_before: float | None
    rate_after: float | None
    gap: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    conf: float
    reported: bool
    reason: str | None


def too_few(n_before: int, n_after: int, min_side: int) -> str | None:
    """A sentence saying which side is short, or None when both sides have enough items."""
    short = []
    if n_before < min_side:
        short.append(f"{n_before} before")
    if n_after < min_side:
        short.append(f"{n_after} after")
    if not short:
        return None
    return f"too few items ({' and '.join(short)} the cutoff; --min-side is {min_side})"


def plain_gap(
    view: SystemView | ItemTable,
    cutoff: Any,
    *,
    system: str | None = None,
    min_side: int = 20,
    conf: float = 0.95,
) -> GapResult:
    """Success rate after the cutoff minus the rate before it, with a Newcombe interval.

    Items dated on the cutoff day count as before. When either side has fewer than
    ``min_side`` items no gap is reported and ``reason`` says why.
    """
    if isinstance(view, ItemTable):
        if system is None:
            raise ValueError("system is required when a table is passed")
        view = view.view(system)
    cut = parse_date(cutoff)
    post = view.post(cut)
    n_after = int(post.sum())
    n_before = int(post.size - n_after)
    rate_before = float(view.y[~post].mean()) if n_before else None
    rate_after = float(view.y[post].mean()) if n_after else None
    reason = too_few(n_before, n_after, min_side)
    if reason is not None or n_before == 0 or n_after == 0:
        return GapResult(
            view.system, cut, n_before, n_after, rate_before, rate_after,
            None, None, None, None, conf, False, reason or "one side of the cutoff is empty",
        )
    s_after = float(view.y[post].sum())
    s_before = float(view.y[~post].sum())
    low, high = newcombe(s_after, n_after, s_before, n_before, conf)
    return GapResult(
        view.system, cut, n_before, n_after, rate_before, rate_after,
        rate_after - rate_before, low, high,
        two_proportion_p(s_after, n_after, s_before, n_before), conf, True, None,
    )
