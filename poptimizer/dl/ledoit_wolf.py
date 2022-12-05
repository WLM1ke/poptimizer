"""Ledoit & Wolf constant correlation unequal variance shrinkage estimator."""
import numpy as np
import numpy.typing as npt


def shrinkage(returns: npt.NDArray[np.double]) -> tuple[npt.NDArray[np.double], float, float]:  # noqa: WPS210
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
    t, n = returns.shape  # noqa: WPS111
    mean_returns = np.mean(returns, axis=0, keepdims=True)
    returns -= mean_returns
    sample_cov = returns.transpose() @ returns / t

    # sample average correlation
    variance = np.diag(sample_cov).reshape(-1, 1)
    sqrt_var = variance**0.5
    unit_cor_var = sqrt_var * sqrt_var.transpose()
    average_cor = ((sample_cov / unit_cor_var).sum() - n) / n / (n - 1)  # noqa: WPS221
    prior = average_cor * unit_cor_var
    np.fill_diagonal(prior, variance)

    # pi-hat
    y = returns**2  # noqa: WPS111
    phi_mat = (y.transpose() @ y) / t - sample_cov**2
    phi = phi_mat.sum()

    # rho-hat
    theta_mat = ((returns**3).transpose() @ returns) / t - variance * sample_cov  # noqa: WPS221
    np.fill_diagonal(theta_mat, 0)
    rho = np.diag(phi_mat).sum() + average_cor * (1 / sqrt_var @ sqrt_var.transpose() * theta_mat).sum()  # noqa: WPS221

    # gamma-hat
    gamma = np.linalg.norm(sample_cov - prior, "fro") ** 2

    # shrinkage constant
    kappa = (phi - rho) / gamma
    shrink = max(0, min(1, kappa / t))

    # estimator
    sigma = shrink * prior + (1 - shrink) * sample_cov

    return sigma, average_cor, shrink


def ledoit_wolf_cor(
    tot_ret: npt.NDArray[np.double],
) -> tuple[npt.NDArray[np.double], float, float]:
    """Корреляционная матрица на основе Ledoit Wolf.

    В расчете учитывается, что при использовании котировок за history_days могут быть получены доходности за
    history_days - 1 день.
    """
    tot_ret = tot_ret.T
    tot_ret = (tot_ret - tot_ret.mean(axis=0)) / tot_ret.std(axis=0, ddof=0)

    return shrinkage(tot_ret)
