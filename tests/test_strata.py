import numpy as np
import pytest
from statsmodels.stats.contingency_tables import StratifiedTable

from datecut.io import build_table
from datecut.simulate import simulate
from datecut.strata import mantel_haenszel, strata_gap, stratum_tables


def random_tables(rng, k):
    return rng.integers(3, 60, size=(k, 2, 2)).astype(float)


@pytest.mark.parametrize("k", [2, 3, 8, 25])
def test_mantel_haenszel_matches_statsmodels(k):
    rng = np.random.default_rng(k)
    for _ in range(20):
        tables = random_tables(rng, k)
        ref = StratifiedTable([t for t in tables])
        est = mantel_haenszel(tables, conf=0.9)
        assert est.odds_ratio == pytest.approx(ref.oddsratio_pooled, rel=1e-10)
        assert est.log_se == pytest.approx(ref.logodds_pooled_se, rel=1e-10)
        low, high = ref.oddsratio_pooled_confint(alpha=0.1)
        assert est.ci_low == pytest.approx(low, rel=1e-9)
        assert est.ci_high == pytest.approx(high, rel=1e-9)
        null = ref.test_null_odds(correction=False)
        assert est.cmh_statistic == pytest.approx(null.statistic, rel=1e-9)
        assert est.cmh_p == pytest.approx(null.pvalue, rel=1e-7, abs=1e-12)
        hom = ref.test_equal_odds(adjust=True)
        assert est.homogeneity_statistic == pytest.approx(hom.statistic, rel=1e-6, abs=1e-8)
        assert est.homogeneity_p == pytest.approx(hom.pvalue, rel=1e-6, abs=1e-10)
        assert est.homogeneity_df == k - 1


def test_single_table_is_the_cross_product_ratio():
    est = mantel_haenszel(np.array([[[20.0, 10.0], [15.0, 30.0]]]))
    assert est.odds_ratio == pytest.approx(20 * 30 / (10 * 15))
    # Woolf variance equals the Robins-Breslow-Greenland variance for one table.
    assert est.log_se == pytest.approx(np.sqrt(1 / 20 + 1 / 10 + 1 / 15 + 1 / 30))
    assert est.homogeneity_p is None


def test_identical_odds_ratios_are_homogeneous():
    tables = np.array([[[20.0, 10.0], [10.0, 20.0]], [[40.0, 20.0], [20.0, 40.0]]])
    est = mantel_haenszel(tables)
    assert est.odds_ratio == pytest.approx(4.0)
    assert est.homogeneity_statistic == pytest.approx(0.0, abs=1e-9)
    assert est.homogeneity_p == pytest.approx(1.0)


def test_opposite_odds_ratios_are_flagged():
    tables = np.array([[[40.0, 10.0], [10.0, 40.0]], [[10.0, 40.0], [40.0, 10.0]]])
    est = mantel_haenszel(tables)
    assert est.odds_ratio == pytest.approx(1.0)
    assert est.homogeneity_p < 1e-6


def test_degenerate_tables():
    assert mantel_haenszel(np.zeros((0, 2, 2))).odds_ratio is None
    one_row = mantel_haenszel(np.array([[[5.0, 5.0], [0.0, 0.0]]]))
    assert one_row.n_strata == 0 and one_row.odds_ratio is None
    no_failures = mantel_haenszel(np.array([[[5.0, 0.0], [7.0, 0.0]]]))
    assert no_failures.odds_ratio is None and no_failures.cmh_statistic is None


def test_strata_gap_finds_a_planted_drop():
    results, meta = simulate(n_items=800, drop=1.2, seed=4)
    table = build_table(results, meta)
    res = strata_gap(table.view("sys-0", strata="source"), "2024-01-01", column="source")
    assert res.reported and res.n_strata == 4
    assert res.estimate.odds_ratio < 1 and res.estimate.ci_high < 1
    assert sum(r.n_before for r in res.rows) == res.n_before
    other = strata_gap(table.view("sys-5", strata="source"), "2024-01-01", column="source")
    assert other.estimate.ci_low < 1 < other.estimate.ci_high


def test_strata_gap_refusals():
    results, meta = simulate(n_items=200, seed=4)
    table = build_table(results, meta)
    view = table.view("sys-0", strata="source")
    short = strata_gap(view, "2024-12-01", column="source", min_side=50)
    assert not short.reported and "too few" in short.reason
    with pytest.raises(ValueError):
        stratum_tables(table.view("sys-0"), "2024-01-01")


def test_strata_on_one_side_only_are_counted():
    meta = [{"item": f"o{k}", "date": "2023-01-01", "source": "old"} for k in range(30)]
    meta += [{"item": f"n{k}", "date": "2024-06-01", "source": "new"} for k in range(30)]
    results = [{"item": m["item"], "system": "m", "score": k % 2} for k, m in enumerate(meta)]
    res = strata_gap(build_table(results, meta).view("m", strata="source"), "2024-01-01")
    assert not res.reported and res.n_strata_one_sided == 2
    assert "no stratum has items on both sides" in res.reason
