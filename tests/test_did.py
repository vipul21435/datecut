import numpy as np
import pytest

from datecut.did import diff_in_diff
from datecut.gap import plain_gap
from datecut.io import build_table
from datecut.simulate import simulate


def view_of(strata=None, **kwargs):
    results, meta = simulate(**kwargs)
    return build_table(results, meta).view("sys-0", strata=strata)


def test_estimate_is_the_gap_minus_the_pool_gap():
    view = view_of(n_items=300, drop=0.7, seed=1)
    res = diff_in_diff(view, "2024-01-01", n_boot=200)
    post = view.post("2024-01-01")
    system_gap = view.y[post].mean() - view.y[~post].mean()
    pool_gap = view.pool[post].mean() - view.pool[~post].mean()
    assert res.system_gap == pytest.approx(system_gap)
    assert res.pool_gap == pytest.approx(pool_gap)
    assert res.did == pytest.approx(system_gap - pool_gap)
    assert res.ci_low < res.did < res.ci_high


def test_bootstrap_is_deterministic_under_a_seed():
    view = view_of(n_items=300, drop=0.7, seed=1)
    a = diff_in_diff(view, "2024-01-01", n_boot=300, seed=42)
    b = diff_in_diff(view, "2024-01-01", n_boot=300, seed=42)
    c = diff_in_diff(view, "2024-01-01", n_boot=300, seed=43)
    assert (a.ci_low, a.ci_high, a.p_value) == (b.ci_low, b.ci_high, b.p_value)
    assert (a.ci_low, a.ci_high) != (c.ci_low, c.ci_high)
    assert a.did == pytest.approx(c.did)


def test_planted_drop_is_found():
    res = diff_in_diff(view_of(n_items=800, drop=1.0, drift=1.0, seed=3), "2024-01-01")
    assert res.reported and res.did < 0 and res.ci_high < 0 and res.p_value < 0.01


def test_shared_drift_fools_the_plain_gap_but_not_the_difference_in_differences():
    plain_excludes_zero = 0
    did_covers_zero = 0
    runs = 30
    for seed in range(runs):
        results, meta = simulate(n_items=600, drop=0.0, drift=1.5, seed=200 + seed)
        view = build_table(results, meta).view("sys-3")
        gap = plain_gap(view, "2024-01-01")
        did = diff_in_diff(view, "2024-01-01", n_boot=400, seed=seed)
        plain_excludes_zero += gap.ci_high < 0.0
        did_covers_zero += did.ci_low <= 0.0 <= did.ci_high
    assert plain_excludes_zero >= 24
    assert did_covers_zero >= 25


def test_clustered_resampling():
    view = view_of(strata="source", n_items=600, n_strata=12, drop=1.0, seed=8)
    res = diff_in_diff(view, "2024-01-01", cluster=True, n_boot=500, seed=1)
    again = diff_in_diff(view, "2024-01-01", cluster=True, n_boot=500, seed=1)
    assert res.reported and res.clustered and res.n_clusters == 12
    assert res.ci_low < res.did < res.ci_high
    assert (res.ci_low, res.ci_high) == (again.ci_low, again.ci_high)
    with pytest.raises(ValueError):
        diff_in_diff(view_of(n_items=100, seed=1), "2024-01-01", cluster=True)


def test_refusals():
    view = view_of(n_items=200, seed=9)
    res = diff_in_diff(view, "2024-12-20", min_side=30)
    assert not res.reported and "too few" in res.reason and res.did is None
    one = view_of(strata="source", n_items=200, n_strata=1, seed=9)
    res = diff_in_diff(one, "2024-01-01", cluster=True)
    assert not res.reported and "two strata" in res.reason


def test_items_without_a_pool_answer_are_dropped():
    results, meta = simulate(n_items=200, n_systems=2, seed=10)
    results = [r for r in results if not (r["system"] == "sys-1" and r["item"] < "item-0050")]
    view = build_table(results, meta).view("sys-0")
    res = diff_in_diff(view, "2024-01-01", n_boot=100)
    assert res.n_no_pool == 50
    assert res.n_before + res.n_after == 150
    assert np.isfinite(res.did)
