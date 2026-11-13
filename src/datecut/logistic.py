"""Logistic regression by iteratively reweighted least squares."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import expit


@dataclass(frozen=True)
class LogisticFit:
    coef: np.ndarray
    cov: np.ndarray
    cov_robust: np.ndarray
    converged: bool
    iterations: int
    log_likelihood: float
    fitted: np.ndarray


def fit_logistic(
    x: np.ndarray, y: np.ndarray, *, max_iter: int = 100, tol: float = 1e-9
) -> LogisticFit:
    """Maximum likelihood fit of ``P(y = 1) = expit(x @ coef)`` by Newton steps.

    ``x`` must already contain the intercept column. ``y`` may hold numbers in [0, 1]
    (a fractional logit); ``cov`` is the model-based covariance ``(X'WX)^-1`` and
    ``cov_robust`` the HC0 sandwich ``(X'WX)^-1 X' diag((y - p)^2) X (X'WX)^-1``.
    ``converged`` is False when the steps do not settle, which is what separated data
    looks like.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n, k = x.shape
    coef = np.zeros(k)
    converged = False
    iterations = 0
    while iterations < max_iter:
        iterations += 1
        p = expit(x @ coef)
        w = np.clip(p * (1.0 - p), 1e-12, None)
        hessian = x.T @ (x * w[:, None])
        gradient = x.T @ (y - p)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(hessian, gradient, rcond=None)[0]
        if not np.all(np.isfinite(step)):
            break
        coef = coef + step
        if np.max(np.abs(coef)) > 30.0:
            break
        if np.max(np.abs(step)) < tol:
            converged = True
            break
    p = expit(x @ coef)
    w = np.clip(p * (1.0 - p), 1e-12, None)
    bread = np.linalg.pinv(x.T @ (x * w[:, None]))
    resid = y - p
    meat = x.T @ (x * (resid**2)[:, None])
    eps = 1e-12
    loglik = float(np.sum(y * np.log(p + eps) + (1.0 - y) * np.log(1.0 - p + eps)))
    return LogisticFit(coef, bread, bread @ meat @ bread, converged, iterations, loglik, p)
