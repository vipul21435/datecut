"""Command line interface: ``datecut <command> --results FILE --meta FILE ...``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from . import __version__, report
from .gap import plain_gap
from .io import DataError, ItemTable, load_cutoffs, load_table, parse_date
from .multi import bh_adjust
from .power import detectable

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
    p = add("power", cmd_power, "smallest gap the counts on each side could detect")
    p.add_argument("--power", type=float, default=0.8, help="target power (default 0.8)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload, text = args.func(args)
    except (DataError, OSError) as exc:
        print(f"datecut: {exc}", file=sys.stderr)
        return 2
    print(report.to_json(payload) if args.format == "json" else text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
