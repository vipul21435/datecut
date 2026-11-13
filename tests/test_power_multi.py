import numpy as np
import pytest
from statsmodels.stats.multitest import multipletests

from datecut.io import build_table
from datecut.multi import bh_adjust
from datecut.power import detectable, min_detectable_gap, power_two_proportions


def test_power_at_no_difference_is_alpha():
    assert power_two_proportions(0.4, 200, 0.4, 300, alpha=0.05) == pytest.approx(0.05, abs=1e-9)


def test_power_grows_with_the_difference_and_the_counts():
    small = power_two_proportions(0.5, 100, 0.45, 100)
    large = power_two_proportions(0.5, 100, 0.30, 100)
    more = power_two_proportions(0.5, 1000, 0.45, 1000)
    assert small < large and small < more


def test_min_detectable_gap_reaches_the_target_power():
    gap = min_detectable_gap(0.6, 300, 200, alpha=0.05, power=0.8, direction="drop")
    assert power_two_proportions(0.6 - gap, 200, 0.6, 300) == pytest.approx(0.8, abs=1e-6)
    rise = min_detectable_gap(0.6, 300, 200, direction="rise")
    assert power_two_proportions(0.6 + rise, 200, 0.6, 300) == pytest.approx(0.8, abs=1e-6)


def test_min_detectable_gap_matches_simulation():
    n_before, n_after, rate = 250, 180, 0.55
    gap = min_detectable_gap(rate, n_before, n_after)
    rng = np.random.default_rng(5)
    reps = 4000
    x_before = rng.binomial(n_before, rate, size=reps)
    x_after = rng.binomial(n_after, rate - gap, size=reps)
    pooled = (x_before + x_after) / (n_before + n_after)
    se = np.sqrt(pooled * (1 - pooled) * (1 / n_before + 1 / n_after))
    z = (x_after / n_after - x_before / n_before) / se
    assert np.mean(np.abs(z) > 1.959964) == pytest.approx(0.8, abs=0.03)


def test_min_detectable_gap_none_when_counts_are_tiny():
    assert min_detectable_gap(0.1, 3, 3, direction="drop") is None
    assert min_detectable_gap(0.5, 0, 10) is None
    with pytest.raises(ValueError):
        min_detectable_gap(0.5, 10, 10, direction="sideways")


def test_detectable_on_a_view():
    dates = ["2023-01-01"] * 100 + ["2024-06-01"] * 80
    meta = [{"item": f"i{k}", "date": day} for k, day in enumerate(dates)]
    results = [{"item": f"i{k}", "system": "m", "score": k % 2} for k in range(180)]
    view = build_table(results, meta).view("m")
    res = detectable(view, "2024-01-01")
    assert (res.n_before, res.n_after) == (100, 80)
    assert res.rate_before == pytest.approx(0.5)
    assert 0.15 < res.detectable_drop < 0.25
    empty = detectable(view, "2025-01-01")
    assert empty.detectable_drop is None and empty.n_after == 0


def test_bh_matches_statsmodels():
    rng = np.random.default_rng(2)
    for m in (1, 2, 7, 40):
        p = rng.random(m) ** 2
        ours = bh_adjust(list(p))
        ref = multipletests(p, method="fdr_bh")[1]
        assert ours == pytest.approx(list(ref), abs=1e-12)


def test_bh_skips_missing_values():
    out = bh_adjust([0.01, None, 0.04, float("nan")])
    assert out[1] is None and out[3] is None
    assert out[0] == pytest.approx(0.02)
    assert out[2] == pytest.approx(0.04)
    assert bh_adjust([None]) == [None]
