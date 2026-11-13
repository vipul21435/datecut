"""How much shared drift the difficulty adjustment leaves, by size of the pool.

    python examples/pool_size.py

No system has an effect of its own; later items are harder for everyone (drift of 1.5 in
log-odds over the date range). The difficulty covariate is measured from the other
systems, so a small pool measures it with noise and part of the drift stays in the
post-cutoff coefficient. Forty seeded datasets of 500 items per pool size.
"""

from __future__ import annotations

import numpy as np

from datecut.adjust import adjusted_gap
from datecut.did import diff_in_diff
from datecut.io import build_table
from datecut.simulate import simulate


def main() -> None:
    print("| systems | mean after coefficient | adjusted interval covers 0 | "
          "diff-in-diff interval covers 0 | median share of plain gap removed |")
    print("| --- | --- | --- | --- | --- |")
    for n_systems in (4, 8, 16, 30):
        coefs, shares = [], []
        covers = did_covers = 0
        runs = 40
        for seed in range(runs):
            results, meta = simulate(
                n_items=500, n_systems=n_systems, drop=0.0, drift=1.5, seed=100 + seed
            )
            view = build_table(results, meta).view(f"sys-{n_systems // 2}")
            adj = adjusted_gap(view, "2024-01-01")
            did = diff_in_diff(view, "2024-01-01", n_boot=300, seed=seed)
            coefs.append(adj.coef)
            shares.append(adj.removed_share)
            covers += adj.ci_low <= 0.0 <= adj.ci_high
            did_covers += did.ci_low <= 0.0 <= did.ci_high
        print(f"| {n_systems} | {np.mean(coefs):+.3f} | {covers} of {runs} | "
              f"{did_covers} of {runs} | {100 * np.median(shares):.0f} % |")


if __name__ == "__main__":
    main()
