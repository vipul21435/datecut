"""Rejection rate of the cutoff scan when no system has an effect of its own.

    python examples/scan_null.py

Each dataset has 20 systems and 300 items, with later items harder for every system and
no system-specific effect. The scan runs with 99 permutations and rejects when its
p-value for the maximum is at most 0.05. The share of rejections should be near 5 %.
"""

from __future__ import annotations

from datecut.io import build_table
from datecut.scan import scan
from datecut.simulate import simulate


def main() -> None:
    print("| drift (log-odds over the date range) | datasets | rejected at 5 % |")
    print("| --- | --- | --- |")
    for drift in (0.0, 1.0, 2.0):
        runs, rejected = 400, 0
        for seed in range(runs):
            results, meta = simulate(
                n_items=300, n_systems=20, drop=0.0, drift=drift, seed=5000 + seed
            )
            res = scan(build_table(results, meta).view("sys-10"), n_perm=99, max_points=20,
                       seed=seed)
            rejected += res.p_value <= 0.05
        print(f"| {drift:.1f} | {runs} | {rejected} ({100 * rejected / runs:.1f} %) |")


if __name__ == "__main__":
    main()
