"""Write the small synthetic example used in the README quickstart.

    python examples/make_example.py

Eight systems answer 600 dated items. Later items are harder for every system (shared
drift) and one system, sys-0, has an extra drop on items dated after 2024-01-01.
"""

from __future__ import annotations

import csv
from pathlib import Path

from datecut.simulate import simulate

OUT = Path(__file__).parent / "data"


def main() -> None:
    results, meta = simulate(
        n_items=600, n_systems=8, cutoff="2024-01-01", drop=1.0, drop_system=0, drift=1.0, seed=7
    )
    OUT.mkdir(exist_ok=True)
    for name, rows in (("results.csv", results), ("meta.csv", meta)):
        with open(OUT / name, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        print(f"wrote {OUT / name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
