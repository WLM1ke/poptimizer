import numpy as np
from numpy.typing import NDArray


def shrinkage(returns: NDArray[np.double]) -> tuple[NDArray[np.double], float, float]:
    """Shrinks sample covariance matrix towards constant correlation unequal variance matrix.

    Ledoit & Wolf ("Honey, I shrunk the sample covariance matrix", Portfolio Management, 30(2004),
    110-119) optimal asymptotic shrinkage between 0 (sample covariance matrix) and 1 (constant
    sample average correlation unequal sample variance matrix).

    Paper:
    http://www.ledoit.net/honey.pdf

    Matlab code:
    https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffffde5e2d4e/covCor.m.zip

    Special thanks to Evgeny Pogrebnyak https://github.com/epogrebnyak

    :param returns:
        t, n - returns of t observations of n shares.
    :return:
        Covariance matrix, sample average correlation, shrinkage.
    """
    t, n = returns.shape
    mean_returns = np.mean(returns, axis=0, keepdims=True)
    returns -= mean_returns
    sample_cov = returns.transpose() @ returns / t

    # sample average correlation
    variance = np.diag(sample_cov).reshape(-1, 1)
    sqrt_var = variance**0.5
    unit_cor_var = sqrt_var * sqrt_var.transpose()
    average_cor = ((sample_cov / unit_cor_var).sum() - n) / n / (n - 1)
    prior = average_cor * unit_cor_var
    np.fill_diagonal(prior, variance)

    # pi-hat
    y = returns**2
    phi_mat = (y.transpose() @ y) / t - sample_cov**2
    phi = phi_mat.sum()

    # rho-hat
    theta_mat = ((returns**3).transpose() @ returns) / t - variance * sample_cov
    np.fill_diagonal(theta_mat, 0)
    rho = np.diag(phi_mat).sum() + average_cor * (1 / sqrt_var @ sqrt_var.transpose() * theta_mat).sum()

    # gamma-hat
    gamma = np.linalg.norm(sample_cov - prior, "fro") ** 2

    # shrinkage constant
    kappa = (phi - rho) / gamma
    shrink = max(0, min(1, kappa / t))

    # estimator
    sigma = shrink * prior + (1 - shrink) * sample_cov

    return sigma, average_cor, shrink


def ledoit_wolf_cor(
    tot_ret: NDArray[np.double],
) -> tuple[NDArray[np.double], float, float]:
    tot_ret = tot_ret.T
    centered = tot_ret - tot_ret.mean(axis=0)
    normalized = centered / tot_ret.std(axis=0, ddof=0)

    return shrinkage(normalized)
