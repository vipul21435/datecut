"""Load per-item results and item metadata into one aligned table."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

_EPOCH = date(1970, 1, 1)


class DataError(ValueError):
    """Raised when the input files cannot be turned into an item table."""


def parse_date(value: Any) -> date:
    """Parse ``YYYY-MM-DD`` (a longer ISO timestamp is cut to its date part)."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise DataError(f"not an ISO date: {text!r}") from exc


def to_day(value: Any) -> int:
    """Days since 1970-01-01 for a date or ISO date string."""
    return (parse_date(value) - _EPOCH).days


def from_day(day: int) -> date:
    return _EPOCH + timedelta(days=int(day))


def read_rows(path: str | Path) -> list[dict[str, Any]]:
    """Read a CSV, TSV, JSON (list of objects) or JSON Lines file into a list of dicts."""
    p = Path(path)
    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")
    if suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    elif suffix == ".json":
        rows = json.loads(text)
    elif suffix in (".csv", ".tsv"):
        delimiter = "\t" if suffix == ".tsv" else ","
        rows = list(csv.DictReader(text.splitlines(), delimiter=delimiter))
    else:
        raise DataError(f"unsupported file type {suffix!r} (use .csv, .tsv, .json or .jsonl)")
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise DataError(f"{p.name}: expected a list of records")
    return rows


@dataclass(frozen=True)
class SystemView:
    """The items one system was scored on, in date order."""

    system: str
    items: tuple[str, ...]
    days: np.ndarray
    y: np.ndarray
    pool: np.ndarray
    pool_n: np.ndarray
    strata: np.ndarray | None

    def post(self, cutoff: Any) -> np.ndarray:
        """True for items dated strictly after the cutoff."""
        return self.days > to_day(cutoff)


@dataclass(frozen=True)
class ItemTable:
    """Items in date order, systems, and a score matrix with NaN where a result is missing."""

    items: tuple[str, ...]
    days: np.ndarray
    systems: tuple[str, ...]
    scores: np.ndarray
    strata: Mapping[str, np.ndarray] = field(default_factory=dict)
    dropped_no_date: int = 0

    @property
    def n_items(self) -> int:
        return len(self.items)

    def system_index(self, system: str) -> int:
        try:
            return self.systems.index(system)
        except ValueError:
            raise DataError(f"unknown system {system!r}") from None

    def stratum(self, column: str | None) -> np.ndarray | None:
        if column is None:
            return None
        if column not in self.strata:
            known = ", ".join(sorted(self.strata)) or "none"
            raise DataError(f"unknown stratum column {column!r} (metadata has: {known})")
        return self.strata[column]

    def view(
        self,
        system: str,
        pool: Sequence[str] | None = None,
        strata: str | None = None,
    ) -> SystemView:
        """Rows where ``system`` has a score, with the mean score of the reference pool.

        The pool is every other system unless ``pool`` names a subset; the system itself is
        always left out, so ``pool`` is a leave-one-system-out mean. ``pool`` is NaN on
        items that no pool system answered.
        """
        j = self.system_index(system)
        if pool is None:
            cols = [k for k in range(len(self.systems)) if k != j]
        else:
            cols = [self.system_index(s) for s in pool if s != system]
        keep = ~np.isnan(self.scores[:, j])
        others = self.scores[keep][:, cols] if cols else np.empty((int(keep.sum()), 0))
        counts = (~np.isnan(others)).sum(axis=1)
        sums = np.nansum(others, axis=1) if cols else np.zeros(int(keep.sum()))
        with np.errstate(invalid="ignore", divide="ignore"):
            pool_mean = np.where(counts > 0, sums / np.maximum(counts, 1), np.nan)
        labels = self.stratum(strata)
        return SystemView(
            system=system,
            items=tuple(self.items[i] for i in np.flatnonzero(keep)),
            days=self.days[keep],
            y=self.scores[keep, j],
            pool=pool_mean,
            pool_n=counts,
            strata=None if labels is None else labels[keep],
        )


def build_table(
    results: Iterable[Mapping[str, Any]],
    meta: Iterable[Mapping[str, Any]],
    *,
    item_col: str = "item",
    system_col: str = "system",
    score_col: str = "score",
    date_col: str = "date",
    threshold: float | None = None,
) -> ItemTable:
    """Join result rows with item metadata.

    Scores must lie in [0, 1]; repeated rows for one (item, system) are averaged. With
    ``threshold`` every averaged score becomes 1 if it is at least the threshold and 0
    otherwise. Items without a date are dropped and counted in ``dropped_no_date``.
    """
    dates: dict[str, int] = {}
    extra: dict[str, dict[str, str]] = {}
    columns: list[str] = []
    for row in meta:
        if item_col not in row or date_col not in row:
            raise DataError(f"metadata rows need {item_col!r} and {date_col!r} columns")
        item = str(row[item_col])
        if row[date_col] in (None, ""):
            continue
        dates[item] = to_day(row[date_col])
        extra[item] = {}
        for key, value in row.items():
            if key in (item_col, date_col):
                continue
            if key not in columns:
                columns.append(key)
            extra[item][key] = "" if value is None else str(value)
    if not dates:
        raise DataError("no dated items in the metadata")

    sums: dict[tuple[str, str], float] = {}
    counts: dict[tuple[str, str], int] = {}
    systems: list[str] = []
    seen: set[str] = set()
    undated: set[str] = set()
    for row in results:
        for col in (item_col, system_col, score_col):
            if col not in row:
                raise DataError(f"result rows need a {col!r} column")
        item, system = str(row[item_col]), str(row[system_col])
        try:
            score = float(row[score_col])
        except (TypeError, ValueError):
            raise DataError(f"score is not a number: {row[score_col]!r}") from None
        if not 0.0 <= score <= 1.0:
            raise DataError(f"score outside [0, 1]: {score!r} (item {item!r}, system {system!r})")
        if item not in dates:
            undated.add(item)
            continue
        if system not in seen:
            seen.add(system)
            systems.append(system)
        key = (item, system)
        sums[key] = sums.get(key, 0.0) + score
        counts[key] = counts.get(key, 0) + 1
    if not sums:
        raise DataError("no result row matches a dated item")

    used = sorted({item for item, _ in sums}, key=lambda it: (dates[it], it))
    systems.sort()
    row_of = {item: i for i, item in enumerate(used)}
    col_of = {system: j for j, system in enumerate(systems)}
    scores = np.full((len(used), len(systems)), np.nan)
    for (item, system), total in sums.items():
        value = total / counts[(item, system)]
        if threshold is not None:
            value = 1.0 if value >= threshold else 0.0
        scores[row_of[item], col_of[system]] = value
    strata = {
        col: np.array([extra[item].get(col, "") for item in used], dtype=object) for col in columns
    }
    return ItemTable(
        items=tuple(used),
        days=np.array([dates[item] for item in used], dtype=np.int64),
        systems=tuple(systems),
        scores=scores,
        strata=strata,
        dropped_no_date=len(undated),
    )


def load_table(results_path: str | Path, meta_path: str | Path, **kwargs: Any) -> ItemTable:
    """Read the two files and join them (see :func:`build_table`)."""
    return build_table(read_rows(results_path), read_rows(meta_path), **kwargs)


def load_cutoffs(
    path: str | Path, *, system_col: str = "system", cutoff_col: str = "cutoff"
) -> dict[str, date]:
    """Read a (system, cutoff) table."""
    out: dict[str, date] = {}
    for row in read_rows(path):
        if system_col not in row or cutoff_col not in row:
            raise DataError(f"cutoff rows need {system_col!r} and {cutoff_col!r} columns")
        out[str(row[system_col])] = parse_date(row[cutoff_col])
    return out
