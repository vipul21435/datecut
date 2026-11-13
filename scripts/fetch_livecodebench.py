"""Fetch LiveCodeBench per-problem results and write datecut input files.

    python scripts/fetch_livecodebench.py --out data/livecodebench

Downloads the per-problem code-generation results that the LiveCodeBench leaderboard page
loads (one JSON file) and writes ``results.csv`` (item, system, score) and ``meta.csv``
(item, date, difficulty, platform). ``score`` is the published pass@1 divided by 100.
Nothing from the file is executed. The downloaded file is not redistributed here.
"""

from __future__ import annotations

import argparse
import csv
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://livecodebench.github.io/performances_generation.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="data/livecodebench")
    parser.add_argument("--url", default=URL)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "performances_generation.json"
    if not raw.exists():
        with urllib.request.urlopen(args.url, timeout=120) as response:
            raw.write_bytes(response.read())
    data = json.loads(raw.read_text(encoding="utf-8"))

    meta: dict[str, dict[str, str]] = {}
    rows = []
    for rec in data["performances"]:
        item = str(rec["question_id"])
        day = datetime.fromtimestamp(rec["date"] / 1000.0, tz=timezone.utc).date().isoformat()
        meta[item] = {
            "item": item,
            "date": day,
            "difficulty": str(rec["difficulty"]),
            "platform": str(rec["platform"]),
        }
        rows.append({"item": item, "system": str(rec["model"]), "score": rec["pass@1"] / 100.0})

    with open(out / "results.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "system", "score"])
        writer.writeheader()
        writer.writerows(rows)
    with open(out / "meta.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "date", "difficulty", "platform"])
        writer.writeheader()
        writer.writerows(sorted(meta.values(), key=lambda m: (m["date"], m["item"])))
    systems = sorted({r["system"] for r in rows})
    print(f"{len(rows)} result rows, {len(meta)} items, {len(systems)} systems -> {out}")


if __name__ == "__main__":
    main()
