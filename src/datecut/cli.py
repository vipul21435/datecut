"""Command line interface: ``datecut <command> --results FILE --meta FILE ...``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from . import __version__, report
from .adjust import adjusted_gap
from .did import diff_in_diff
from .gap import plain_gap
from .io import DataError, ItemTable, SystemView, load_cutoffs, load_table, parse_date
from .multi import bh_adjust
from .power import detectable
from .scan import scan
from .strata import strata_gap
from .trend import trend

Rendered = tuple[Any, str]


def _common() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--results", required=True, help="per-item results: item, system, score")
    p.add_argument("--meta", required=True, help="item metadata: item, date, stratum columns")
    p.add_argument("--system", action="append", help="system to analyse (repeatable; default all)")
    p.add_argument("--cutoff", help="cutoff date, YYYY-MM-DD; items dated after it are 'after'")
    p.add_argument("--cutoffs", help="file with columns system, cutoff (one cutoff per system)")
    p.add_argument("--strata", help="metadata column to stratify or cluster by")
    p.add_argument("--pool", action="append", help="reference system (repeatable; default others)")
    p.add_argument("--min-side", type=int, default=20, help="fewest items per side (default 20)")
    p.add_argument("--conf", type=float, default=0.95, help="confidence level (default 0.95)")
    p.add_argument("--alpha", type=float, default=0.05, help="test level (default 0.05)")
    p.add_argument("--threshold", type=float, help="binarise scores: 1 if score >= threshold")
    p.add_argument("--seed", type=int, default=0, help="random seed (default 0)")
    p.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p.add_argument("--item-col", default="item")
    p.add_argument("--system-col", default="system")
    p.add_argument("--score-col", default="score")
    p.add_argument("--date-col", default="date")
    return p


def _load(args: argparse.Namespace) -> ItemTable:
    return load_table(
        args.results, args.meta, item_col=args.item_col, system_col=args.system_col,
        score_col=args.score_col, date_col=args.date_col, threshold=args.threshold,
    )


def _systems(table: ItemTable, args: argparse.Namespace) -> list[str]:
    names = list(args.system) if args.system else list(table.systems)
    for name in names:
        table.system_index(name)
    return names


def _cutoffs(table: ItemTable, args: argparse.Namespace) -> dict[str, date]:
    """The cutoff of each selected system, from --cutoff or the --cutoffs table."""
    names = _systems(table, args)
    if args.cutoffs and args.cutoff:
        raise DataError("give either --cutoff or --cutoffs, not both")
    if args.cutoffs:
        known = load_cutoffs(args.cutoffs)
        chosen = {name: known[name] for name in names if name in known}
        if not chosen:
            raise DataError("no selected system has a row in the --cutoffs table")
        return chosen
    if not args.cutoff:
        raise DataError("a cutoff is required: --cutoff DATE or --cutoffs FILE")
    cut = parse_date(args.cutoff)
    return dict.fromkeys(names, cut)


def cmd_gap(args: argparse.Namespace) -> Rendered:
    table = _load(args)
    results = [
        plain_gap(table.view(name), cut, min_side=args.min_side, conf=args.conf)
        for name, cut in _cutoffs(table, args).items()
    ]
    adjusted = bh_adjust([r.p_value for r in results])
    level = f"{100 * args.conf:g} %"
    rows = []
    for r, q in zip(results, adjusted, strict=True):
        rows.append([
            r.system, r.cutoff.isoformat(), r.n_before, r.n_after,
            report.pct(r.rate_before), report.pct(r.rate_after),
            report.pct(r.gap, signed=True) if r.reported else "not reported",
            report.interval(r.ci_low, r.ci_high), report.pval(r.p_value), report.pval(q),
        ])
    headers = [
        "system", "cutoff", "n before", "n after", "before %", "after %",
        "gap (points)", f"{level} Newcombe interval", "p", "p (BH)",
    ]
    text = report.table(headers, rows)
    notes = [f"- {r.system}: {r.reason}" for r in results if not r.reported]
    if notes:
        text += "\n\nNo gap is reported for:\n" + "\n".join(notes)
    payload = [dict(report.plain(r), p_bh=q) for r, q in zip(results, adjusted, strict=True)]
    return payload, text


def cmd_power(args: argparse.Namespace) -> Rendered:
    table = _load(args)
    results = [
        detectable(table.view(name), cut, alpha=args.alpha, power=args.power)
        for name, cut in _cutoffs(table, args).items()
    ]
    rows = [
        [
            r.system, r.cutoff.isoformat(), r.n_before, r.n_after, report.pct(r.rate_before),
            report.pct(r.detectable_drop), report.pct(r.detectable_rise),
        ]
        for r in results
    ]
    headers = [
        "system", "cutoff", "n before", "n after", "before %",
        f"smallest drop at {100 * args.power:g} % power (points)", "smallest rise (points)",
    ]
    return results, report.table(headers, rows)


def _view(table: ItemTable, args: argparse.Namespace, name: str) -> SystemView:
    return table.view(name, pool=args.pool, strata=args.strata)


def _refusals(results: Sequence[Any]) -> str:
    notes = [f"- {r.system}: {r.reason}" for r in results if not r.reported]
    return "\n\nNot reported:\n" + "\n".join(notes) if notes else ""


def cmd_strata(args: argparse.Namespace) -> Rendered:
    if not args.strata:
        raise DataError("strata needs --strata COLUMN")
    table = _load(args)
    results = [
        strata_gap(_view(table, args, name), cut, column=args.strata, min_side=args.min_side,
                   conf=args.conf)
        for name, cut in _cutoffs(table, args).items()
    ]
    p_values = [r.estimate.cmh_p if r.reported else None for r in results]
    adjusted = bh_adjust(p_values)
    rows = []
    for r, q in zip(results, adjusted, strict=True):
        e = r.estimate
        rows.append([
            r.system, r.cutoff.isoformat(), r.n_before, r.n_after, r.n_strata,
            report.num(e.odds_ratio) if r.reported else "not reported",
            f"{report.num(e.ci_low)} to {report.num(e.ci_high)}" if r.reported else "n/a",
            report.pval(e.cmh_p) if r.reported else "n/a", report.pval(q),
            f"{report.num(e.homogeneity_statistic, 2)} (df {e.homogeneity_df})"
            if r.reported and e.homogeneity_df else "n/a",
            report.pval(e.homogeneity_p) if r.reported else "n/a",
        ])
    headers = [
        "system", "cutoff", "n before", "n after", "strata", "MH odds ratio",
        f"{100 * args.conf:g} % interval", "p (CMH)", "p (BH)", "homogeneity", "p (homogeneity)",
    ]
    text = f"Strata: `{args.strata}`. Odds ratio of success after against before the cutoff.\n\n"
    text += report.table(headers, rows)
    if len(results) == 1:
        detail = [
            [r.stratum, r.n_before, r.n_after, report.pct(r.rate_before),
             report.pct(r.rate_after), report.num(r.odds_ratio)]
            for r in results[0].rows
        ]
        text += "\n\n" + report.table(
            ["stratum", "n before", "n after", "before %", "after %", "odds ratio"], detail
        )
    text += _refusals(results)
    payload = [dict(report.plain(r), p_bh=q) for r, q in zip(results, adjusted, strict=True)]
    return payload, text


def cmd_did(args: argparse.Namespace) -> Rendered:
    if args.cluster and not args.strata:
        raise DataError("--cluster needs --strata COLUMN")
    table = _load(args)
    results = [
        diff_in_diff(_view(table, args, name), cut, min_side=args.min_side, conf=args.conf,
                     n_boot=args.boot, seed=args.seed, cluster=args.cluster)
        for name, cut in _cutoffs(table, args).items()
    ]
    adjusted = bh_adjust([r.p_value for r in results])
    rows = [
        [
            r.system, r.cutoff.isoformat(), r.n_before, r.n_after,
            report.pct(r.system_gap, signed=True), report.pct(r.pool_gap, signed=True),
            report.pct(r.did, signed=True) if r.reported else "not reported",
            report.interval(r.ci_low, r.ci_high), report.pval(r.p_value), report.pval(q),
        ]
        for r, q in zip(results, adjusted, strict=True)
    ]
    headers = [
        "system", "cutoff", "n before", "n after", "system gap", "pool gap",
        "difference in differences", f"{100 * args.conf:g} % bootstrap interval", "p", "p (BH)",
    ]
    how = f"strata of `{args.strata}`" if args.cluster else "items within each side"
    text = f"Gaps in percentage points; {args.boot} resamples of {how}, seed {args.seed}.\n\n"
    text += report.table(headers, rows) + _refusals(results)
    payload = [dict(report.plain(r), p_bh=q) for r, q in zip(results, adjusted, strict=True)]
    return payload, text


def cmd_adjust(args: argparse.Namespace) -> Rendered:
    table = _load(args)
    results = [
        adjusted_gap(_view(table, args, name), cut, min_side=args.min_side, conf=args.conf,
                     kind=args.difficulty, robust=True if args.robust else None)
        for name, cut in _cutoffs(table, args).items()
    ]
    adjusted = bh_adjust([r.p_value for r in results])
    rows = [
        [
            r.system, r.cutoff.isoformat(), r.n_before, r.n_after,
            report.num(r.coef) if r.reported else "not reported",
            f"{report.num(r.ci_low)} to {report.num(r.ci_high)}" if r.reported else "n/a",
            report.num(r.odds_ratio), report.pct(r.plain_gap, signed=True),
            report.pct(r.adjusted_gap, signed=True), report.interval(r.gap_low, r.gap_high),
            report.pval(r.p_value), report.pval(q),
        ]
        for r, q in zip(results, adjusted, strict=True)
    ]
    headers = [
        "system", "cutoff", "n before", "n after", "after coefficient (log-odds)",
        f"{100 * args.conf:g} % interval", "odds ratio", "plain gap", "adjusted gap",
        "adjusted gap interval", "p", "p (BH)",
    ]
    text = "Logistic model: success ~ after + difficulty (from the other systems). "
    text += "Gaps in percentage points.\n\n" + report.table(headers, rows) + _refusals(results)
    payload = [dict(report.plain(r), p_bh=q) for r, q in zip(results, adjusted, strict=True)]
    return payload, text


def cmd_summary(args: argparse.Namespace) -> Rendered:
    if args.cluster and not args.strata:
        raise DataError("--cluster needs --strata COLUMN")
    table = _load(args)
    payload, rows, p_values, notes = [], [], [], []
    for name, cut in _cutoffs(table, args).items():
        view = _view(table, args, name)
        gap = plain_gap(view, cut, min_side=args.min_side, conf=args.conf)
        adj = adjusted_gap(view, cut, min_side=args.min_side, conf=args.conf)
        did = diff_in_diff(view, cut, min_side=args.min_side, conf=args.conf, n_boot=args.boot,
                           seed=args.seed, cluster=args.cluster)
        payload.append({"system": name, "gap": gap, "adjust": adj, "did": did})
        p_values.append(adj.p_value)
        for r in (gap, adj, did):
            if not r.reported and f"- {name}: {r.reason}" not in notes:
                notes.append(f"- {name}: {r.reason}")
        rows.append([
            name, cut.isoformat(), gap.n_before, gap.n_after,
            report.pct(gap.gap, signed=True), report.interval(gap.ci_low, gap.ci_high),
            report.pct(adj.adjusted_gap, signed=True), report.interval(adj.gap_low, adj.gap_high),
            report.pct(did.did, signed=True), report.interval(did.ci_low, did.ci_high),
            report.pct(adj.removed_share, 0), report.pval(adj.p_value),
        ])
    adjusted = bh_adjust(p_values)
    for row, entry, q in zip(rows, payload, adjusted, strict=True):
        row.append(report.pval(q))
        entry["adjust_p_bh"] = q
    headers = [
        "system", "cutoff", "n before", "n after", "plain gap", "interval", "adjusted gap",
        "interval", "diff in diff", "interval", "removed %", "p (adjusted)", "p (BH)",
    ]
    text = "Gaps in percentage points, after minus before. `removed %` is the share of the "
    text += "plain gap that the difficulty adjustment removes.\n\n" + report.table(headers, rows)
    if notes:
        text += "\n\nNot reported:\n" + "\n".join(notes)
    return payload, text


def cmd_scan(args: argparse.Namespace) -> Rendered:
    if args.within_strata and not args.strata:
        raise DataError("--within-strata needs --strata COLUMN")
    table = _load(args)
    results = [
        scan(_view(table, args, name), min_side=args.min_side, max_points=args.max_points,
             grid=args.grid, n_perm=args.perm, alpha=args.alpha, conf=args.conf,
             alternative=args.alternative, within_strata=args.within_strata,
             kind=args.difficulty, seed=args.seed)
        for name in _systems(table, args)
    ]
    adjusted = bh_adjust([r.p_value for r in results])
    stat = "largest |z|" if args.alternative == "two-sided" else "most negative z"
    how = f"within strata of `{args.strata}`" if args.within_strata else "across all items"
    rows = [
        [
            r.system, r.n_items, r.n_candidates,
            r.best_cutoff.isoformat() if r.best_cutoff else "not reported",
            report.num(r.observed, 2), report.num(r.band, 2), report.pval(r.p_value),
            report.pval(q),
        ]
        for r, q in zip(results, adjusted, strict=True)
    ]
    headers = [
        "system", "items", "candidate dates", "best date", stat,
        f"{100 * (1 - args.alpha):g} % permutation band", "p (maximum)", "p (BH)",
    ]
    text = f"Scan statistic: {stat} of the after-date term over the candidate dates; "
    text += f"{args.perm} permutations of item dates {how}, seed {args.seed}.\n\n"
    text += report.table(headers, rows)
    if len(results) == 1 and results[0].reported:
        detail = [
            [
                p.cutoff.isoformat(), p.n_before, p.n_after, report.pct(p.plain_gap, signed=True),
                report.pct(p.adjusted_gap, signed=True), report.interval(p.gap_low, p.gap_high),
                report.num(p.z, 2), "yes" if p.outside_band else "no",
            ]
            for p in results[0].points
        ]
        text += "\n\n" + report.table(
            ["candidate date", "n before", "n after", "plain gap", "adjusted gap",
             "pointwise interval", "z", "outside band"], detail,
        )
    text += _refusals(results)
    payload = [dict(report.plain(r), p_bh=q) for r, q in zip(results, adjusted, strict=True)]
    return payload, text


def cmd_trend(args: argparse.Namespace) -> Rendered:
    table = _load(args)
    payload, parts = [], []
    for name in _systems(table, args):
        windows = trend(_view(table, args, name), window=args.window, step=args.step,
                        by=args.by, conf=args.conf)
        payload.append({"system": name, "windows": windows})
        rows = [
            [
                w.start.isoformat(), w.end.isoformat(), w.n, report.pct(w.rate),
                f"{report.pct(w.low)} to {report.pct(w.high)}", report.pct(w.pool_rate),
                f"{report.pct(w.pool_low)} to {report.pct(w.pool_high)}"
                if w.pool_low is not None else "n/a",
                report.pct(w.diff, signed=True), report.interval(w.diff_low, w.diff_high),
            ]
            for w in windows
        ]
        headers = ["from", "to", "n", f"{name} %", "band", "pool %", "band", "system - pool",
                   "band"]
        parts.append(f"### {name}\n\n" + report.table(headers, rows))
    return payload, "\n\n".join(parts)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datecut",
        description="Success on benchmark items before and after a cutoff date.",
    )
    parser.add_argument("--version", action="version", version=f"datecut {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    common = _common()

    def add(name: str, func: Callable[[argparse.Namespace], Rendered], text: str):
        p = sub.add_parser(name, parents=[common], help=text, description=text)
        p.set_defaults(func=func)
        return p

    add("gap", cmd_gap, "plain before/after gap with a Newcombe interval")
    add("strata", cmd_strata, "Mantel-Haenszel common odds ratio across strata")
    p = add("did", cmd_did, "the system's gap minus the reference pool's gap")
    p.add_argument("--boot", type=int, default=2000, help="bootstrap resamples (default 2000)")
    p.add_argument("--cluster", action="store_true", help="resample whole strata, not items")
    p = add("adjust", cmd_adjust, "gap adjusted for item difficulty by a logistic model")
    p.add_argument("--difficulty", choices=["logit", "raw"], default="logit")
    p.add_argument("--robust", action="store_true", help="always use sandwich standard errors")
    p = add("scan", cmd_scan, "adjusted gap over candidate dates with a permutation band")
    p.add_argument("--grid", choices=["auto", "month"], default="auto")
    p.add_argument("--max-points", type=int, default=40, help="most candidate dates (default 40)")
    p.add_argument("--perm", type=int, default=1000, help="permutations (default 1000)")
    p.add_argument("--alternative", choices=["two-sided", "drop"], default="two-sided")
    p.add_argument("--within-strata", action="store_true", help="permute dates within strata")
    p.add_argument("--difficulty", choices=["logit", "raw"], default="logit")
    p = add("trend", cmd_trend, "success against item date in windows, system and pool")
    p.add_argument("--window", type=int, default=100, help="items per window (default 100)")
    p.add_argument("--step", type=int, help="items between windows (default half a window)")
    p.add_argument("--by", choices=["month", "quarter", "year"], help="calendar windows instead")
    p = add("power", cmd_power, "smallest gap the counts on each side could detect")
    p.add_argument("--power", type=float, default=0.8, help="target power (default 0.8)")
    p = add("summary", cmd_summary, "plain, adjusted and difference-in-differences gap together")
    p.add_argument("--boot", type=int, default=2000, help="bootstrap resamples (default 2000)")
    p.add_argument("--cluster", action="store_true", help="resample whole strata, not items")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload, text = args.func(args)
    except (DataError, OSError, ValueError) as exc:
        print(f"datecut: {exc}", file=sys.stderr)
        return 2
    print(report.to_json(payload) if args.format == "json" else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
