"""Markdown and JSON rendering shared by the commands."""

from __future__ import annotations

import dataclasses
import json
import math
from collections.abc import Sequence
from datetime import date
from typing import Any

import numpy as np


def num(value: float | None, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{value:.{digits}f}"


def pct(value: float | None, digits: int = 1, signed: bool = False) -> str:
    """A proportion as a percentage (or a difference as percentage points)."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    return f"{100.0 * value:+.{digits}f}" if signed else f"{100.0 * value:.{digits}f}"


def interval(low: float | None, high: float | None, digits: int = 1, scale: float = 100.0) -> str:
    if low is None or high is None:
        return "n/a"
    return f"{scale * low:+.{digits}f} to {scale * high:+.{digits}f}"


def pval(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


def table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """A GitHub-flavoured Markdown table; pipe characters inside cells are escaped."""

    def cell(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines = [
        "| " + " | ".join(cell(h) for h in headers) + " |",
        "|" + "|".join(" --- " for _ in headers) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def plain(obj: Any) -> Any:
    """Turn dataclasses, dates and numpy values into JSON-ready objects (NaN becomes null)."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: plain(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [plain(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return [plain(v) for v in obj.tolist()]
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def to_json(obj: Any) -> str:
    return json.dumps(plain(obj), indent=2, sort_keys=False)
