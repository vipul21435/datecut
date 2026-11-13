"""Plot the cutoff scan for every system in a results file.

    python scripts/plot_scan.py --results data/livecodebench/results.csv \
        --meta data/livecodebench/meta.csv --out docs/livecodebench_scan.png

One line per system: the score z of the after-date term at each month-end candidate.
Dashed lines mark the pointwise 1.96 and the median permutation band for the largest |z|.
Needs matplotlib (``pip install datecut[plot]``).
"""

from __future__ import annotations

import argparse
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from datecut.io import load_table  # noqa: E402
from datecut.scan import scan  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", required=True)
    parser.add_argument("--meta", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--perm", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--title", default="Cutoff scan")
    args = parser.parse_args()

    table = load_table(args.results, args.meta)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bands = []
    for name in table.systems:
        res = scan(table.view(name), grid="month", n_perm=args.perm, seed=args.seed)
        if not res.reported:
            continue
        bands.append(res.band)
        outside = res.observed > res.band
        ax.plot(
            [p.cutoff for p in res.points], [p.z for p in res.points],
            color="#b03a2e" if outside else "#7f8c8d", linewidth=1.1 if outside else 0.8,
            alpha=0.9 if outside else 0.6,
        )
    band = statistics.median(bands)
    for level, style, label in (
        (1.96, ":", "pointwise 1.96"),
        (band, "--", f"median permutation band for the largest |z| ({band:.2f})"),
    ):
        ax.axhline(level, color="black", linestyle=style, linewidth=0.9, label=label)
        ax.axhline(-level, color="black", linestyle=style, linewidth=0.9)
    ax.axhline(0.0, color="black", linewidth=0.5)
    ax.plot([], [], color="#b03a2e", linewidth=1.1, label="largest |z| outside its own band")
    ax.plot([], [], color="#7f8c8d", linewidth=0.8, label="largest |z| inside its own band")
    ax.set_xlabel("candidate date (items dated later count as after)")
    ax.set_ylabel("score z of the after-date term")
    ax.set_title(args.title)
    ax.legend(fontsize=8, loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(args.out, dpi=130)
    print(f"wrote {args.out} ({len(bands)} systems, median band {band:.2f})")


if __name__ == "__main__":
    main()
