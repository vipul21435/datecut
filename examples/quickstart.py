"""Use datecut from Python on a synthetic benchmark.

    python examples/quickstart.py

Eight systems answer 600 dated items. Later items are harder for every system, and sys-0
has an extra drop on items dated after 2024-01-01. The plain gap is negative for both
systems below; the adjusted gap and the difference in differences separate them.
"""

from __future__ import annotations

from datecut.adjust import adjusted_gap
from datecut.did import diff_in_diff
from datecut.gap import plain_gap
from datecut.io import build_table
from datecut.scan import scan
from datecut.simulate import simulate


def main() -> None:
    results, meta = simulate(
        n_items=600, n_systems=8, cutoff="2024-01-01", drop=1.0, drop_system=0, drift=1.0, seed=7
    )
    table = build_table(results, meta)
    for name in ("sys-0", "sys-4"):
        view = table.view(name, strata="source")
        gap = plain_gap(view, "2024-01-01")
        adj = adjusted_gap(view, "2024-01-01")
        did = diff_in_diff(view, "2024-01-01", n_boot=2000, seed=0)
        print(name)
        print(f"  plain gap     {100 * gap.gap:+6.1f} points "
              f"({100 * gap.ci_low:+.1f} to {100 * gap.ci_high:+.1f})")
        print(f"  adjusted gap  {100 * adj.adjusted_gap:+6.1f} points "
              f"({100 * adj.gap_low:+.1f} to {100 * adj.gap_high:+.1f})")
        print(f"  diff in diff  {100 * did.did:+6.1f} points "
              f"({100 * did.ci_low:+.1f} to {100 * did.ci_high:+.1f})")
    found = scan(table.view("sys-0"), n_perm=1000, seed=0)
    print(f"scan for sys-0: largest |z| {found.observed:.2f} at {found.best_cutoff}, "
          f"95 % permutation band {found.band:.2f}, p {found.p_value:.4f}")


if __name__ == "__main__":
    main()
