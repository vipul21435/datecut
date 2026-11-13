# datecut

Given per-item benchmark results and each item's creation date, datecut compares a system's
success before and after a cutoff date, with intervals and the counts on each side.

This is an early version. The plan is to add stratified, difficulty-adjusted and
difference-in-differences comparisons and a scan over candidate dates; see "Status" below
for what exists today.

## Install

```
pip install git+https://github.com/vipul21435/datecut
```

## Input

- results: one row per (item, system) with a `score` that is 0/1 or a number in [0, 1]
- metadata: one row per item with a `date` (`YYYY-MM-DD`) and optional stratum columns
- a cutoff date (`--cutoff`), or a table with columns `system, cutoff` (`--cutoffs`)

CSV, TSV, JSON and JSON Lines files are read. Items dated strictly after the cutoff count
as "after".

## Quickstart

`examples/data/` holds a synthetic example written by `python examples/make_example.py`
(600 items, 8 systems; later items are harder for every system and `sys-0` has an extra
drop after 2024-01-01).

```
$ datecut gap --results examples/data/results.csv --meta examples/data/meta.csv \
    --cutoff 2024-01-01 --system sys-0 --system sys-4
| system | cutoff | n before | n after | before % | after % | gap (points) | 95 % Newcombe interval | p | p (BH) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sys-0 | 2024-01-01 | 285 | 315 | 33.0 | 11.4 | -21.6 | -28.0 to -15.0 | <0.0001 | <0.0001 |
| sys-4 | 2024-01-01 | 285 | 315 | 63.2 | 52.1 | -11.1 | -18.8 to -3.2 | 0.0061 | 0.0061 |
```

Both systems show a gap here, because the plain gap also picks up the drift shared by all
systems. Separating the two is the part that is not written yet.

## Status

Works today:

- `datecut gap`: success before and after, the difference with a Newcombe hybrid score
  interval, a two-proportion z-test, Benjamini-Hochberg adjusted p-values across systems,
  and a refusal to report a gap when a side has fewer than `--min-side` items
- `datecut power`: the smallest drop or rise the counts on each side could detect at 80 %
  power
- Markdown and JSON output

Not implemented yet: strata (Mantel-Haenszel), difference in differences against the other
systems, adjustment for item difficulty, the cutoff scan, the trend view, and results on
real public data.

## Licence

MIT

Built by Vipul Raj Jha · https://vipul21435.github.io
