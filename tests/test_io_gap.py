import json

import numpy as np
import pytest

from datecut.gap import plain_gap
from datecut.io import DataError, build_table, load_cutoffs, load_table, parse_date, read_rows
from datecut.simulate import simulate

META = [
    {"item": "a", "date": "2024-01-01", "source": "x"},
    {"item": "b", "date": "2024-02-01T10:00:00Z", "source": "y"},
    {"item": "c", "date": "2024-03-01", "source": "x"},
    {"item": "d", "date": "", "source": "x"},
]
RESULTS = [
    {"item": "c", "system": "m2", "score": 1},
    {"item": "a", "system": "m1", "score": 1},
    {"item": "a", "system": "m2", "score": 0},
    {"item": "b", "system": "m1", "score": 0.5},
    {"item": "b", "system": "m1", "score": 1.0},
    {"item": "d", "system": "m1", "score": 1},
    {"item": "zz", "system": "m1", "score": 1},
]


def test_build_table_orders_items_and_averages_repeats():
    table = build_table(RESULTS, META)
    assert table.items == ("a", "b", "c")
    assert table.systems == ("m1", "m2")
    assert table.dropped_no_date == 2
    assert table.scores[1, 0] == pytest.approx(0.75)
    assert np.isnan(table.scores[2, 0])
    assert list(table.strata["source"]) == ["x", "y", "x"]


def test_threshold_binarises():
    table = build_table(RESULTS, META, threshold=0.8)
    assert table.scores[1, 0] == pytest.approx(0.0)


def test_view_leaves_the_system_out_of_the_pool():
    table = build_table(RESULTS, META)
    view = table.view("m1", strata="source")
    assert view.items == ("a", "b")
    assert view.pool[0] == pytest.approx(0.0)
    assert np.isnan(view.pool[1])
    assert list(view.post("2024-01-01")) == [False, True]
    assert list(view.strata) == ["x", "y"]


@pytest.mark.parametrize(
    "results,meta",
    [
        ([{"item": "a", "system": "m", "score": 2}], META),
        ([{"item": "a", "system": "m", "score": "high"}], META),
        ([{"item": "a", "system": "m"}], META),
        ([{"item": "q", "system": "m", "score": 1}], META),
        (RESULTS, [{"item": "a"}]),
        (RESULTS, [{"item": "a", "date": "yesterday"}]),
        (RESULTS, [{"item": "a", "date": ""}]),
    ],
)
def test_bad_input_is_rejected(results, meta):
    with pytest.raises(DataError):
        build_table(results, meta)


def test_unknown_names():
    table = build_table(RESULTS, META)
    with pytest.raises(DataError):
        table.view("nobody")
    with pytest.raises(DataError):
        table.view("m1", strata="colour")


def test_files_round_trip(tmp_path):
    results, meta = simulate(n_items=30, n_systems=2, seed=3)
    (tmp_path / "r.jsonl").write_text("\n".join(json.dumps(r) for r in results))
    header = "item,date,source\n"
    (tmp_path / "m.csv").write_text(
        header + "".join(f"{m['item']},{m['date']},{m['source']}\n" for m in meta)
    )
    (tmp_path / "c.tsv").write_text("system\tcutoff\nsys-0\t2024-01-01\n")
    (tmp_path / "m.json").write_text(json.dumps(meta))
    table = load_table(tmp_path / "r.jsonl", tmp_path / "m.csv")
    assert table.n_items == 30
    assert load_table(tmp_path / "r.jsonl", tmp_path / "m.json").n_items == 30
    assert load_cutoffs(tmp_path / "c.tsv") == {"sys-0": parse_date("2024-01-01")}
    (tmp_path / "x.txt").write_text("nothing")
    with pytest.raises(DataError):
        read_rows(tmp_path / "x.txt")
    (tmp_path / "bad.json").write_text("{}")
    with pytest.raises(DataError):
        read_rows(tmp_path / "bad.json")


def _table(before, after):
    """before/after are lists of 0/1 scores for one system."""
    meta, results = [], []
    for k, score in enumerate(before):
        meta.append({"item": f"b{k}", "date": "2023-06-01"})
        results.append({"item": f"b{k}", "system": "m", "score": score})
    for k, score in enumerate(after):
        meta.append({"item": f"a{k}", "date": "2024-06-01"})
        results.append({"item": f"a{k}", "system": "m", "score": score})
    return build_table(results, meta)


def test_plain_gap_counts_and_interval():
    table = _table([1] * 48 + [0] * 32, [1] * 56 + [0] * 14)
    res = plain_gap(table, "2024-01-01", system="m")
    assert (res.n_before, res.n_after) == (80, 70)
    assert res.rate_before == pytest.approx(0.6)
    assert res.rate_after == pytest.approx(0.8)
    assert res.gap == pytest.approx(0.2)
    assert res.ci_low == pytest.approx(0.0524, abs=5e-5)
    assert res.ci_high == pytest.approx(0.3339, abs=5e-5)
    assert res.reported and res.reason is None
    assert 0 < res.p_value < 0.05


def test_cutoff_day_counts_as_before():
    table = _table([1] * 30, [0] * 30)
    res = plain_gap(table, "2024-06-01", system="m", min_side=1)
    assert (res.n_before, res.n_after) == (60, 0)
    assert not res.reported


def test_gap_is_refused_when_a_side_is_short():
    table = _table([1] * 50, [1] * 5)
    res = plain_gap(table, "2024-01-01", system="m", min_side=20)
    assert not res.reported
    assert res.gap is None and res.ci_low is None
    assert "5 after" in res.reason
    assert plain_gap(table, "2024-01-01", system="m", min_side=5).reported
    with pytest.raises(ValueError):
        plain_gap(table, "2024-01-01")
