import numpy as np
import pytest
import statsmodels.api as sm

from datecut.adjust import adjusted_gap, design, difficulty_covariate, marginal_gap
from datecut.io import build_table
from datecut.logistic import fit_logistic
from datecut.simulate import simulate


def test_logistic_matches_statsmodels():
    rng = np.random.default_rng(0)
    x = np.column_stack([np.ones(500), rng.integers(0, 2, 500), rng.normal(size=500)])
    p = 1 / (1 + np.exp(-(x @ np.array([0.3, -0.8, 1.1]))))
    y = (rng.random(500) < p).astype(float)
    fit = fit_logistic(x, y)
    ref = sm.GLM(y, x, family=sm.families.Binomial()).fit()
    assert fit.converged
    assert fit.coef == pytest.approx(ref.params, abs=1e-7)
    assert np.sqrt(np.diag(fit.cov)) == pytest.approx(ref.bse, rel=1e-4)
    assert fit.log_likelihood == pytest.approx(ref.llf, rel=1e-6)
    robust = sm.GLM(y, x, family=sm.families.Binomial()).fit(cov_type="HC0")
    assert np.sqrt(np.diag(fit.cov_robust)) == pytest.approx(robust.bse, rel=1e-4)


def test_fractional_outcomes_match_statsmodels():
    rng = np.random.default_rng(1)
    x = np.column_stack([np.ones(300), rng.integers(0, 2, 300), rng.normal(size=300)])
    p = 1 / (1 + np.exp(-(x @ np.array([-0.2, 0.5, 0.7]))))
    y = rng.binomial(10, p) / 10.0
    fit = fit_logistic(x, y)
    ref = sm.GLM(y, x, family=sm.families.Binomial()).fit(cov_type="HC0")
    assert fit.coef == pytest.approx(ref.params, abs=1e-7)
    assert np.sqrt(np.diag(fit.cov_robust)) == pytest.approx(ref.bse, rel=1e-4)


def test_separated_data_does_not_converge():
    x = np.column_stack([np.ones(40), np.repeat([0.0, 1.0], 20)])
    y = np.repeat([0.0, 1.0], 20)
    assert not fit_logistic(x, y).converged


def test_difficulty_covariate():
    pool = np.array([0.0, 0.5, 1.0])
    n = np.array([4, 4, 4])
    z = difficulty_covariate(pool, n)
    assert z == pytest.approx([np.log(0.5 / 4.5), 0.0, np.log(4.5 / 0.5)])
    assert difficulty_covariate(pool, n, "raw") == pytest.approx(pool)
    with pytest.raises(ValueError):
        difficulty_covariate(pool, n, "rank")


def test_marginal_gap_standard_error_against_finite_differences():
    results, meta = simulate(n_items=400, drop=0.8, drift=0.5, seed=2)
    view = build_table(results, meta).view("sys-0")
    x, y = design(view, "2024-01-01")
    fit = fit_logistic(x, y)
    gap, se = marginal_gap(fit, x, fit.cov)

    def gap_at(coef):
        x1, x0 = x.copy(), x.copy()
        x1[:, 1], x0[:, 1] = 1.0, 0.0
        return np.mean(1 / (1 + np.exp(-(x1 @ coef))) - 1 / (1 + np.exp(-(x0 @ coef))))

    assert gap == pytest.approx(gap_at(fit.coef))
    h = 1e-6
    grad = np.array([
        (gap_at(fit.coef + h * np.eye(3)[k]) - gap_at(fit.coef - h * np.eye(3)[k])) / (2 * h)
        for k in range(3)
    ])
    assert se == pytest.approx(np.sqrt(grad @ fit.cov @ grad), rel=1e-5)


def test_planted_drop_is_found():
    results, meta = simulate(n_items=800, drop=1.0, drift=1.0, seed=3)
    table = build_table(results, meta)
    res = adjusted_gap(table.view("sys-0"), "2024-01-01")
    assert res.reported and not res.robust
    assert res.coef == pytest.approx(-1.0, abs=0.45)
    assert res.ci_high < 0 and res.gap_high < 0
    assert res.odds_ratio == pytest.approx(np.exp(res.coef))
    assert res.p_value < 0.01


def test_shared_drift_is_removed_by_the_adjustment_with_a_large_pool():
    covered = 0
    plain_negative = 0
    shares = []
    for seed in range(30):
        results, meta = simulate(n_items=500, n_systems=30, drop=0.0, drift=1.5, seed=100 + seed)
        res = adjusted_gap(build_table(results, meta).view("sys-15"), "2024-01-01")
        covered += res.ci_low <= 0.0 <= res.ci_high
        plain_negative += res.plain_gap < -0.05
        shares.append(res.removed_share)
    assert plain_negative >= 27
    assert covered >= 26
    assert np.median(shares) > 0.75


def test_a_small_pool_removes_only_part_of_the_drift():
    # Seven other systems give a noisy difficulty covariate, so some drift stays in the
    # post-cutoff coefficient. The README states this limit; the test pins the behaviour.
    coefs = []
    shares = []
    for seed in range(30):
        results, meta = simulate(n_items=500, n_systems=8, drop=0.0, drift=1.5, seed=100 + seed)
        res = adjusted_gap(build_table(results, meta).view("sys-4"), "2024-01-01")
        coefs.append(res.coef)
        shares.append(res.removed_share)
    assert -0.45 < np.mean(coefs) < -0.05
    assert 0.4 < np.median(shares) < 0.9


def test_adjust_refusals():
    results, meta = simulate(n_items=200, n_systems=3, seed=5)
    table = build_table(results, meta)
    assert not adjusted_gap(table.view("sys-0"), "2024-12-20").reported
    alone = build_table([r for r in results if r["system"] == "sys-0"], meta)
    res = adjusted_gap(alone.view("sys-0"), "2024-01-01")
    assert not res.reported and "any other system" in res.reason
    constant = [dict(r, score=1) if r["system"] == "sys-0" else r for r in results]
    res = adjusted_gap(build_table(constant, meta).view("sys-0"), "2024-01-01")
    assert not res.reported and "every score is the same" in res.reason


def test_fractional_scores_use_sandwich_errors():
    results, meta = simulate(n_items=300, seed=6)
    rng = np.random.default_rng(6)
    soft = [dict(r, score=float(r["score"] * 0.8 + rng.random() * 0.2)) for r in results]
    res = adjusted_gap(build_table(soft, meta).view("sys-1"), "2024-01-01")
    assert res.reported and res.robust
