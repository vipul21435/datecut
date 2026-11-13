import numpy as np
import pytest
from statsmodels.stats.proportion import confint_proportions_2indep, proportion_confint

from datecut.intervals import newcombe, two_proportion_p, wilson, z_value


def test_z_value():
    assert z_value(0.95) == pytest.approx(1.959964, abs=1e-6)
    with pytest.raises(ValueError):
        z_value(1.0)


@pytest.mark.parametrize("x,n", [(0, 10), (3, 10), (10, 10), (57, 213), (1, 1000)])
@pytest.mark.parametrize("conf", [0.9, 0.95, 0.99])
def test_wilson_matches_statsmodels(x, n, conf):
    low, high = wilson(x, n, conf)
    ref_low, ref_high = proportion_confint(x, n, alpha=1 - conf, method="wilson")
    assert low == pytest.approx(ref_low, abs=1e-10)
    assert high == pytest.approx(ref_high, abs=1e-10)


def test_wilson_rejects_bad_counts():
    with pytest.raises(ValueError):
        wilson(1, 0)
    with pytest.raises(ValueError):
        wilson(5, 4)


def test_newcombe_worked_example():
    # 56/70 against 48/80, the worked example in Newcombe (1998): 0.0524 to 0.3339.
    low, high = newcombe(56, 70, 48, 80)
    assert low == pytest.approx(0.0524, abs=5e-5)
    assert high == pytest.approx(0.3339, abs=5e-5)


def test_newcombe_matches_statsmodels_on_random_counts():
    rng = np.random.default_rng(1)
    for _ in range(200):
        n1, n2 = (int(v) for v in rng.integers(5, 400, size=2))
        x1, x2 = int(rng.integers(0, n1 + 1)), int(rng.integers(0, n2 + 1))
        conf = float(rng.choice([0.8, 0.9, 0.95, 0.99]))
        low, high = newcombe(x1, n1, x2, n2, conf)
        ref_low, ref_high = confint_proportions_2indep(
            x1, n1, x2, n2, method="newcomb", compare="diff", alpha=1 - conf
        )
        assert low == pytest.approx(ref_low, abs=1e-9)
        assert high == pytest.approx(ref_high, abs=1e-9)


def test_newcombe_is_antisymmetric():
    low, high = newcombe(30, 100, 45, 90)
    low2, high2 = newcombe(45, 90, 30, 100)
    assert low == pytest.approx(-high2)
    assert high == pytest.approx(-low2)


def test_two_proportion_p():
    assert two_proportion_p(50, 100, 50, 100) == pytest.approx(1.0)
    assert two_proportion_p(0, 10, 0, 20) == pytest.approx(1.0)
    # z = (0.6 - 0.4) / sqrt(0.5 * 0.5 * (2 / 100)) = 2.828...
    assert two_proportion_p(60, 100, 40, 100) == pytest.approx(0.004678, abs=1e-6)
