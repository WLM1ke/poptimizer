"""Constant correlation unequal variance shrinkage estimator."""
from typing import Tuple

import numpy as np
import pandas as pd


def ledoit_wolf(returns: np.array) -> Tuple[np.array, float, float]:
    """Shrinks sample covariance matrix towards constant correlation unequal variance matrix.

    Ledoit & Wolf ("Honey, I shrunk the sample covariance matrix", Portfolio Management, 30(2004),
    110-119) optimal asymptotic shrinkage between 0 (sample covariance matrix) and 1 (constant
    sample average correlation unequal sample variance matrix).

    The Ledoit & Wolf Matlab estimator was adjusted in n / (n - 1) times to get a unbiased estimator of
    the variance for small samples.

    Paper:
    http://www.ledoit.net/honey.pdf
    Matlab code:
    https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffffde5e2d4e/covCor.m.zip

    :param returns:
        t, n - returns of t observations on n shares
    :return:
        Covariance matrix, sample average correlation, shrinkage.
    """

    t, n = returns.shape
    mean_returns = np.mean(returns, axis=0, keepdims=True)
    returns -= mean_returns
    sample_cov = np.cov(returns, rowvar=False, ddof=0)
    var = np.diag(sample_cov).reshape(-1, 1)
    sqrt_var = var ** 0.5

    # sample average correlation
    average_cor = (
        ((sample_cov / sqrt_var / sqrt_var.transpose()).sum() - n) / n / (n - 1)
    )
    prior = average_cor * sqrt_var * sqrt_var.transpose()
    np.fill_diagonal(prior, var)

    # pi-hat
    y = returns ** 2
    phi_mat = (
        (y.transpose() @ y) / t
        - 2 * (returns.transpose() @ returns) * sample_cov / t
        + sample_cov ** 2
    )
    phi = phi_mat.sum()

    # rho-hat
    term1 = ((returns ** 3).transpose() @ returns) / t
    term2 = var * sample_cov
    term3 = sample_cov * var
    term4 = var * sample_cov
    theta_mat = term1 - term2 - term3 + term4
    np.fill_diagonal(theta_mat, 0)
    rho = (
        np.diag(phi_mat).sum()
        + average_cor * (1 / sqrt_var @ sqrt_var.transpose() * theta_mat).sum()
    )

    # gamma-hat
    gamma = np.linalg.norm(sample_cov - prior, "fro") ** 2

    # shrinkage constant
    kappa = (phi - rho) / gamma
    shrinkage = max(0, min(1, kappa / t))

    # estimator
    sigma = shrinkage * prior + (1 - shrinkage) * sample_cov

    return sigma * n / (n - 1), average_cor, shrinkage


if __name__ == "__main__":
    data = [
        [1.0, 2.0, 5.0],
        [4.0, 6.0, 8.0],
        [7.0, 8.0, 10.0],
        [1.0, 5.0, 7.0],
        [8.0, 9.0, 1.0],
    ]
    df = pd.DataFrame(data)
    print(*ledoit_wolf(df.values), sep="\n")

"""
   8.5600   2.0007   1.5413
   2.0007   6.0000   1.3459
   1.5413   1.3459   9.3600
"""
