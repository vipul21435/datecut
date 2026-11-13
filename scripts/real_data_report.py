"""Reproduce the real-data numbers quoted in the README.

    python scripts/fetch_livecodebench.py --out data/livecodebench
    python scripts/fetch_swebench_verified.py --out data/swebench_verified
    python scripts/real_data_report.py --lcb data/livecodebench --swe data/swebench_verified

Prints Markdown. The split dates below are analysis choices near the middle of each
benchmark's item dates; they are not the training cutoff of any system.
"""

from __future__ import annotations

import argparse
import statistics
from pathlib import Path

from datecut.cli import build_parser

LCB_SPLIT = "2024-06-30"
SWE_SPLIT = "2020-12-31"


def run(argv: list[str]):
    args = build_parser().parse_args(argv)
    return args.func(args)


def spread(values: list[float], scale: float = 100.0, digits: int = 1) -> str:
    low, mid, high = min(values), statistics.median(values), max(values)
    return f"{scale * low:+.{digits}f} / {scale * mid:+.{digits}f} / {scale * high:+.{digits}f}"


def excludes(low: float, high: float, null: float = 0.0) -> bool:
    return low > null or high < null


def livecodebench(folder: Path) -> None:
    base = ["--results", str(folder / "results.csv"), "--meta", str(folder / "meta.csv")]
    payload, text = run(["summary", *base, "--cutoff", LCB_SPLIT, "--seed", "0"])
    n = len(payload)
    plain = [e["gap"].gap for e in payload]
    adj = [e["adjust"].adjusted_gap for e in payload]
    did = [e["did"].did for e in payload]
    removed = [e["adjust"].removed_share for e in payload]
    print(f"## LiveCodeBench code generation, split at {LCB_SPLIT}\n")
    print(f"{n} systems, {payload[0]['gap'].n_before} items before and "
          f"{payload[0]['gap'].n_after} after the split.\n")
    print("| quantity (min / median / max over systems) | value | intervals excluding 0 |")
    print("| --- | --- | --- |")
    count = sum(excludes(e["gap"].ci_low, e["gap"].ci_high) for e in payload)
    print(f"| plain gap, points | {spread(plain)} | {count} of {n} |")
    count = sum(excludes(e["adjust"].gap_low, e["adjust"].gap_high) for e in payload)
    print(f"| adjusted gap, points | {spread(adj)} | {count} of {n} |")
    count = sum(excludes(e["did"].ci_low, e["did"].ci_high) for e in payload)
    print(f"| difference in differences, points | {spread(did)} | {count} of {n} |")
    print(f"| share of the plain gap removed, % | {spread(removed, digits=0)} | |")
    smaller = sum(abs(a) < abs(p) for a, p in zip(adj, plain, strict=True))
    flagged = sum(e["adjust_p_bh"] < 0.05 for e in payload)
    print(f"\nThe adjusted gap is smaller in size than the plain gap for {smaller} of {n} "
          f"systems; {flagged} of {n} adjusted gaps have a BH-adjusted p below 0.05.\n")
    print(text)

    payload, text = run(["scan", *base, "--grid", "month", "--perm", "1000", "--seed", "0"])
    bands = [r["band"] for r in payload]
    outside = sum(r["observed"] > r["band"] for r in payload)
    after_bh = sum(r["p_bh"] < 0.05 for r in payload)
    print("\n## LiveCodeBench cutoff scan, month-end candidates\n")
    print(f"Permutation band for the largest |z|: {min(bands):.2f} to {max(bands):.2f} across "
          f"systems (a single pre-chosen date would use 1.96). The largest |z| is outside "
          f"the band for {outside} of {len(payload)} systems, and for {after_bh} after the "
          f"Benjamini-Hochberg adjustment across systems.\n")
    print(text)

    payload, text = run(["power", *base, "--cutoff", LCB_SPLIT])
    drops = [r.detectable_drop for r in payload]
    print("\n## LiveCodeBench power at the split\n")
    print(f"Smallest drop detectable at 80 % power (min / median / max over systems): "
          f"{spread(drops).replace('+', '')} points.")


def swebench(folder: Path) -> None:
    base = ["--results", str(folder / "results.csv"), "--meta", str(folder / "meta.csv")]
    gaps, _ = run(["gap", *base, "--cutoff", SWE_SPLIT])
    strata, _ = run(["strata", *base, "--cutoff", SWE_SPLIT, "--strata", "repo"])
    gaps = [g for g in gaps if g["reported"]]
    strata = [s for s in strata if s["reported"]]
    n = len(gaps)
    crude = []
    for g in gaps:
        before, after = g["rate_before"], g["rate_after"]
        if 0 < before < 1 and 0 < after < 1:
            crude.append((after / (1 - after)) / (before / (1 - before)))
    odds = [s["estimate"]["odds_ratio"] for s in strata]
    print(f"\n## SWE-bench Verified, issues created after against before {SWE_SPLIT}\n")
    print(f"{n} submissions, {gaps[0]['n_before']} items before and {gaps[0]['n_after']} after; "
          f"{strata[0]['n_strata']} repositories have items on both sides.\n")
    print("| quantity (min / median / max over submissions) | value | intervals excluding "
          "the null |")
    print("| --- | --- | --- |")
    count = sum(excludes(g["ci_low"], g["ci_high"]) for g in gaps)
    print(f"| plain gap, points | {spread([g['gap'] for g in gaps])} | {count} of {n} |")
    print(f"| crude odds ratio | {spread(crude, 1.0, 2).replace('+', '')} | |")
    count = sum(
        excludes(s["estimate"]["ci_low"], s["estimate"]["ci_high"], 1.0) for s in strata
    )
    print(f"| Mantel-Haenszel odds ratio across repositories | "
          f"{spread(odds, 1.0, 2).replace('+', '')} | {count} of {len(strata)} |")
    hom = sum(
        s["estimate"]["homogeneity_p"] is not None and s["estimate"]["homogeneity_p"] < 0.05
        for s in strata
    )
    print(f"\nHomogeneity test p below 0.05 for {hom} of {len(strata)} submissions.\n")

    totals: dict[str, float] = {}
    with open(folder / "results.csv", encoding="utf-8") as handle:
        next(handle)
        for line in handle:
            _, system, score = line.rstrip("\n").rsplit(",", 2)
            totals[system] = totals.get(system, 0.0) + float(score)
    top = sorted(totals, key=lambda name: (-totals[name], name))[0]
    _, text = run(["trend", *base, "--system", top, "--window", "100"])
    print("## SWE-bench Verified trend, rolling windows of 100 issues\n")
    print("The system shown is the submission with the most resolved instances "
          "(first by name among ties); the pool is every other submission.\n")
    print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lcb", help="folder written by fetch_livecodebench.py")
    parser.add_argument("--swe", help="folder written by fetch_swebench_verified.py")
    args = parser.parse_args()
    if args.lcb:
        livecodebench(Path(args.lcb))
    if args.swe:
        swebench(Path(args.swe))


if __name__ == "__main__":
    main()
