from datetime import date

import numpy as np
import pytest

from datecut.io import build_table, to_day
from datecut.scan import candidate_cutoffs, scan
from datecut.simulate import simulate
from datecut.trend import trend


def view_of(system="sys-0", strata=None, **kwargs):
    results, meta = simulate(**kwargs)
    return build_table(results, meta).view(system, strata=strata)


def test_candidate_cutoffs_respect_min_side():
    days = np.arange(100)
    cand = candidate_cutoffs(days, min_side=10, max_points=1000)
    assert cand[0] == 9 and cand[-1] == 89
    thin = candidate_cutoffs(days, min_side=10, max_points=5)
    assert thin.size == 5 and thin[0] == 9 and thin[-1] == 89
    assert candidate_cutoffs(days, min_side=60).size == 0
    assert candidate_cutoffs(np.array([]), min_side=1).size == 0
    with pytest.raises(ValueError):
        candidate_cutoffs(days, grid="weekly")


def test_month_grid_uses_month_ends():
    days = np.arange(to_day("2024-01-10"), to_day("2024-05-20"))
    cand = candidate_cutoffs(days, min_side=5, grid="month")
    assert [int(c) for c in cand] == [
        to_day("2024-01-31"), to_day("2024-02-29"), to_day("2024-03-31"), to_day("2024-04-30"),
    ]


def test_scan_finds_the_planted_date():
    view = view_of(n_items=900, n_systems=12, drop=1.5, seed=5)
    res = scan(view, n_perm=300, seed=1)
    assert res.reported
    assert res.p_value <= 0.01
    assert abs((res.best_cutoff - date(2024, 1, 1)).days) < 60
    assert res.observed > res.band
    assert any(p.outside_band for p in res.points)
    best = max(res.points, key=lambda p: abs(p.z))
    assert best.cutoff == res.best_cutoff and best.z < 0 and best.adjusted_gap < 0


def test_scan_is_deterministic_under_a_seed():
    view = view_of(n_items=300, drop=0.5, seed=6)
    a = scan(view, n_perm=100, seed=3)
    b = scan(view, n_perm=100, seed=3)
    c = scan(view, n_perm=100, seed=4)
    assert (a.band, a.p_value) == (b.band, b.p_value)
    assert a.observed == pytest.approx(c.observed)
    assert a.band != c.band


def test_scan_band_holds_its_error_rate_under_the_null():
    # No system-specific effect; later items are harder for every system. With 99
    # permutations a p-value of at most 0.05 has probability 0.05 under exchangeability.
    runs, rejected = 200, 0
    for seed in range(runs):
        view = view_of("sys-10", n_items=300, n_systems=20, drop=0.0, drift=1.0, seed=1000 + seed)
        res = scan(view, n_perm=99, max_points=20, seed=seed)
        rejected += res.p_value <= 0.05
    # 0.05 +- 3 standard errors of a binomial share over 200 runs is 0.004 to 0.096.
    assert rejected / runs <= 0.096


def test_one_sided_scan_and_strata_permutation():
    view = view_of(strata="source", n_items=600, n_systems=12, drop=1.5, seed=7)
    res = scan(view, n_perm=200, alternative="drop", within_strata=True, seed=2)
    assert res.reported and res.permuted_within_strata
    assert res.observed < res.band < 0 and res.p_value <= 0.01
    with pytest.raises(ValueError):
        scan(view_of(n_items=100, seed=1), within_strata=True, n_perm=10)
    with pytest.raises(ValueError):
        scan(view, alternative="rise")


def test_scan_refusals():
    view = view_of(n_items=60, seed=8)
    res = scan(view, min_side=40, n_perm=10)
    assert not res.reported and "no candidate date" in res.reason
    results, meta = simulate(n_items=100, n_systems=3, seed=8)
    constant = [dict(r, score=0) if r["system"] == "sys-0" else r for r in results]
    res = scan(build_table(constant, meta).view("sys-0"), n_perm=10)
    assert not res.reported and "every score is the same" in res.reason


def test_rolling_trend_windows():
    view = view_of(n_items=250, seed=9)
    rows = trend(view, window=100)
    assert [r.n for r in rows] == [100, 100, 100, 100]
    assert rows[0].start <= rows[0].end <= rows[-1].end
    first = view.y[:100]
    assert rows[0].rate == pytest.approx(first.mean())
    assert rows[0].low < rows[0].rate < rows[0].high
    assert rows[0].pool_rate == pytest.approx(view.pool[:100].mean())
    assert rows[0].diff == pytest.approx((first - view.pool[:100]).mean())
    assert rows[0].diff_low < rows[0].diff < rows[0].diff_high
    assert len(trend(view, window=1000)) == 1
    with pytest.raises(ValueError):
        trend(view, window=0)
    with pytest.raises(ValueError):
        trend(view, step=0)


def test_calendar_trend_windows():
    view = view_of(n_items=400, seed=10)
    quarters = trend(view, by="quarter")
    assert sum(r.n for r in quarters) == 400
    assert len(quarters) == 8
    assert len(trend(view, by="year")) == 2
    assert len(trend(view, by="month")) == 24
    with pytest.raises(ValueError):
        trend(view, by="week")


def test_trend_falls_when_a_drop_is_planted():
    view = view_of(n_items=800, drop=2.0, seed=11)
    years = trend(view, by="year")
    assert years[1].diff < years[0].diff - 0.1


def test_trend_without_a_pool():
    results, meta = simulate(n_items=50, n_systems=1, seed=12)
    rows = trend(build_table(results, meta).view("sys-0"), window=25)
    assert rows[0].pool_rate is None and rows[0].diff is None


def test_one_item_window_has_no_pool_band():
    results, meta = simulate(n_items=40, n_systems=4, seed=13)
    rows = trend(build_table(results, meta).view("sys-0"), window=1, step=20)
    assert rows[0].n == 1
    assert rows[0].pool_rate is not None
    assert rows[0].pool_low is None and rows[0].diff_low is None
