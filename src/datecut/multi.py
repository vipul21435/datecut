"""Several systems in one table: Benjamini-Hochberg adjusted p-values."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def bh_adjust(p_values: Sequence[float | None]) -> list[float | None]:
    """Benjamini-Hochberg adjusted p-values; None entries are skipped and stay None.

    With m tested hypotheses and p-values sorted ascending, the adjusted value of the
    k-th smallest is min over j >= k of p_(j) * m / j, capped at 1.
    """
    idx = [i for i, p in enumerate(p_values) if p is not None and not np.isnan(p)]
    out: list[float | None] = [None] * len(p_values)
    if not idx:
        return out
    p = np.array([p_values[i] for i in idx], dtype=float)
    order = np.argsort(p, kind="stable")
    m = p.size
    scaled = p[order] * m / np.arange(1, m + 1)
    adjusted = np.minimum(np.minimum.accumulate(scaled[::-1])[::-1], 1.0)
    for rank, pos in enumerate(order):
        out[idx[pos]] = float(adjusted[rank])
    return out
