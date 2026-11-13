"""Fetch SWE-bench Verified item dates and public per-instance results.

    python scripts/fetch_swebench_verified.py --out data/swebench_verified

Item metadata (instance id, repository, creation date) comes from the dataset's rows on
the Hugging Face dataset viewer API. Per-instance outcomes come from the ``results.json``
file of each submission under ``evaluation/verified`` in the public swe-bench/experiments
repository: an instance scores 1 if the submission lists it as resolved and 0 otherwise.
Writes ``results.csv`` (item, system, score) and ``meta.csv`` (item, date, repo, year).
Nothing fetched is executed, and the fetched files are not redistributed here.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROWS = "https://datasets-server.huggingface.co/rows"
DATASET = "princeton-nlp/SWE-bench_Verified"
LISTING = "https://api.github.com/repos/swe-bench/experiments/contents/evaluation/verified"
RAW = "https://raw.githubusercontent.com/swe-bench/experiments/main/evaluation/verified"


def get_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "datecut-fetch"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_items(cache: Path) -> list[dict[str, str]]:
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    items = []
    offset = 0
    while True:
        query = urllib.parse.urlencode(
            {"dataset": DATASET, "config": "default", "split": "test", "offset": offset,
             "length": 100}
        )
        page = get_json(f"{ROWS}?{query}")
        for entry in page["rows"]:
            row = entry["row"]
            items.append({
                "item": row["instance_id"],
                "date": str(row["created_at"])[:10],
                "repo": row["repo"],
                "year": str(row["created_at"])[:4],
            })
        offset += 100
        if offset >= page["num_rows_total"]:
            break
        time.sleep(0.5)
    cache.write_text(json.dumps(items), encoding="utf-8")
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="data/swebench_verified")
    parser.add_argument("--max-systems", type=int, default=0, help="0 means every submission")
    args = parser.parse_args()
    out = Path(args.out)
    (out / "submissions").mkdir(parents=True, exist_ok=True)

    items = fetch_items(out / "items.json")
    ids = [m["item"] for m in items]
    listing_path = out / "listing.json"
    if not listing_path.exists():
        listing_path.write_text(json.dumps(get_json(LISTING)), encoding="utf-8")
    names = sorted(e["name"] for e in json.loads(listing_path.read_text()) if e["type"] == "dir")
    if args.max_systems:
        names = names[: args.max_systems]

    rows = []
    kept = 0
    for name in names:
        path = out / "submissions" / f"{name}.json"
        if not path.exists():
            try:
                data = get_json(f"{RAW}/{urllib.parse.quote(name)}/results/results.json")
            except (urllib.error.URLError, ValueError) as exc:
                print(f"skip {name}: {exc}")
                continue
            path.write_text(json.dumps(data), encoding="utf-8")
            time.sleep(0.2)
        data = json.loads(path.read_text(encoding="utf-8"))
        resolved = data.get("resolved") if isinstance(data, dict) else None
        if not isinstance(resolved, list):
            print(f"skip {name}: no resolved list")
            continue
        solved = set(resolved)
        rows.extend({"item": i, "system": name, "score": int(i in solved)} for i in ids)
        kept += 1

    with open(out / "results.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "system", "score"])
        writer.writeheader()
        writer.writerows(rows)
    with open(out / "meta.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["item", "date", "repo", "year"])
        writer.writeheader()
        writer.writerows(sorted(items, key=lambda m: (m["date"], m["item"])))
    print(f"{len(rows)} result rows, {len(items)} items, {kept} systems -> {out}")


if __name__ == "__main__":
    main()
