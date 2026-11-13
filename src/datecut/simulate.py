"""Seeded synthetic results, used by the tests and the example."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np


def simulate(
    *,
    n_items: int = 600,
    n_systems: int = 8,
    start: str = "2023-01-01",
    days: int = 720,
    cutoff: str = "2024-01-01",
    drop: float = 0.0,
    drop_system: int = 0,
    drift: float = 0.0,
    n_strata: int = 4,
    seed: int = 0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return ``(results, meta)`` rows from a logistic model of success.

    Success of system ``s`` on item ``i`` has log-odds
    ``ability_s - difficulty_i - drift * t_i - drop * after_i`` where ``t_i`` runs from 0
    to 1 over the date range, ``after_i`` is 1 for items dated after ``cutoff`` and the
    ``drop`` term applies to ``drop_system`` only. ``drift`` makes later items harder for
    every system; ``drop`` is the planted post-cutoff effect for one system.
    """
    rng = np.random.default_rng(seed)
    first = date.fromisoformat(start)
    cut = (date.fromisoformat(cutoff) - first).days
    offsets = np.sort(rng.integers(0, days, size=n_items))
    strata = rng.integers(0, n_strata, size=n_items)
    stratum_shift = rng.normal(0.0, 0.5, size=n_strata)
    difficulty = rng.normal(0.0, 1.0, size=n_items) + stratum_shift[strata]
    ability = np.linspace(-0.5, 1.5, n_systems)
    t = offsets / max(days - 1, 1)
    after = offsets > cut
    meta = [
        {
            "item": f"item-{i:04d}",
            "date": (first + timedelta(days=int(offsets[i]))).isoformat(),
            "source": f"source-{int(strata[i])}",
        }
        for i in range(n_items)
    ]
    results = []
    for s in range(n_systems):
        logit = ability[s] - difficulty - drift * t
        if s == drop_system:
            logit = logit - drop * after
        prob = 1.0 / (1.0 + np.exp(-logit))
        wins = rng.random(n_items) < prob
        results.extend(
            {"item": f"item-{i:04d}", "system": f"sys-{s}", "score": int(wins[i])}
            for i in range(n_items)
        )
    return results, meta
