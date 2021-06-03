import numpy as np


def qis(returns: np.array, k=1) -> np.array:
    """The estimator keeps the eigenvectors of the sample covariance matrix and applies shrinkage
    to the inverse sample eigenvalues.
    Non-normality and the case where the matrix dimension exceeds the sample size are accommodated.

    Paper:
    http://www.econ.uzh.ch/static/wp/econwp335.pdf

    :param returns:
        n, p - returns of n observations of p shares.
    :param k:
        Adjustment for sample size
    :return:
        Covariance matrix.
    """

    n, p = returns.shape

    # Demean, adjust sample size, calculate sample covariance matrix
    mean_rets = np.mean(returns, axis=0, keepdims=True)
    returns -= mean_rets
    n = n - k
    c = p / n  # concentration ratio
    sample = returns.transpose() @ returns / n

    # Spectral decomposition
    # Extract sample eigenvalues and eigenvectors
    # Note that linalg.eigh function returns eigenvalues in ascending order
    lambda1, u = np.linalg.eigh(sample)

    # Take real parts of eigenvalues and reset negative values to 0
    lambda1 = lambda1.real.clip(min=0)

    # COMPUTE Quadratic-Inverse Shrinkage estimator of the covariance matrix
    # smoothing parameter
    h = (min(c ** 2, 1 / c ** 2) ** 0.35) / p ** 0.35

    # inverse of (non-null) eigenvalues
    invlambda = 1 / lambda1[max(1, p - n + 1) - 1:p]
    lj = np.tile(invlambda.reshape(-1, 1), (1, min(p, n)))
    lj_i = lj - lj.transpose()
    divider = lj_i * lj_i + lj * lj * h ** 2

    # Smoothed Stein shrinker
    theta = np.mean(lj * lj_i / divider, axis=0)

    # Conjugate
    htheta = np.mean(lj * lj * h / divider, axis=0)

    # Squared amplitude
    atheta2 = theta ** 2 + htheta ** 2

    if p <= n:
        # case where sample covariance matrix is not singular
        delta = 1 / ((1 - c) ** 2 * invlambda + 2 * c * (1 - c) * invlambda * theta
                     + c ** 2 * invlambda * atheta2)  # optimally shrunk eigenvalues
    else:
        # singular matrix case
        delta0 = 1 / ((c - 1) * np.mean(invlambda))  # shrinkage of null eigenvalues
        delta = np.repeat(delta0, p - n)
        delta = np.concatenate((delta, 1 / (invlambda * atheta2)), axis=None)

    # preserve trace
    deltaqis = delta * (sum(lambda1) / sum(delta))

    # reconstruct covariance matrix
    res = u @ np.diag(deltaqis) @ u.transpose().conjugate()

    return res


def analytical_shrinkage(returns: np.array, k=1) -> np.array:
    """This nonlinear shrinkage estimator explores connection between nonlinear shrinkage and
    nonparametric estimation of the Hilbert transform of the sample spectral density.
    Uses analytical formula for nonlinear shrinkage estimation of large-dimensional covariance matrices.

    Paper:
    https://www.econ.uzh.ch/dam/jcr:87976d27-67fa-442b-bceb-8af7a0681ba2/annals_2020.pdf

    :param returns:
        n, p - returns of n observations of p shares.
    :param k:
        Adjustment for sample size
    :return:
        Covariance matrix.
    """

    # sample size n must be greater or equal than 12
    n, p = returns.shape

    # Demean, adjust sample size, calculate sample covariance matrix
    n = n - k
    returns -= np.mean(returns, axis=0, keepdims=True)
    sample = returns.transpose() @ returns / n

    # Extract sample eigenvalues and eigenvectors
    lambda1, u = np.linalg.eigh(sample)

    # Take real parts of eigenvalues and reset negative values to 0
    lambda1 = lambda1.real.clip(min=0)

    # Compute analytical nonlinear shrinkage kernel formula
    lambd = lambda1[max(0, p - n):p]
    l = np.tile(lambd.reshape(-1, 1), min(p, n))

    # global bandwidth
    h = n ** (-1 / 3)

    # locally adaptive bandwidth
    hlocal = h * l.transpose()

    # Estimate the spectral density with the Epanechnikov kernel
    x = (l - l.transpose()) / hlocal
    ftilde = (3 / (4 * 5 ** 0.5)) * np.mean(np.maximum(1 - x ** 2 / 5, 0) / hlocal, axis=1)

    # Its Hilbert transform
    hftemp = (-3 / (10 * np.pi)) * x + (3 / (4 * 5 ** 0.5 * np.pi)) * (1 - x ** 2 / 5) * \
             np.log(np.abs((5 ** 0.5 - x) / (5 ** 0.5 + x)))
    hftemp[np.isclose(np.abs(x), 5 ** 0.5)] = (-3 / (10 * np.pi)) * x[np.isclose(np.abs(x), 5 ** 0.5)]
    hftilde = np.mean(hftemp / hlocal, axis=1)

    if p <= n:
        # case where sample covariance matrix is not singular
        arg1 = np.pi * p / n * lambd * ftilde
        arg2 = (1 - (p / n) - np.pi * (p / n) * lambda1 * hftilde)
        dtilde = lambd / (arg1 ** 2 + arg2 ** 2)
    else:
        # singular matrix case
        hftilde0 = (1 / np.pi) * (3 / (10 * h ** 2) + 3 / (4 * 5 ** 0.5 * h) * (1 - 1 / (5 * h ** 2)) *
                                  np.log((1 + 5 ** 0.5 * h) / (1 - 5 ** 0.5 * h))) * np.mean(1 / lambd)
        dtilde0 = 1 / (np.pi * (p - n) / n * hftilde0)
        dtilde1 = lambd / (np.pi ** 2 * lambd ** 2 * (ftilde ** 2 + hftilde ** 2))
        dtilde = np.concatenate((dtilde0 * np.ones((p - n, 1)), dtilde1.reshape(-1, 1)), axis=None)

    # reconstruct covariance matrix
    res = u @ np.diag(dtilde) @ u.transpose()

    return res
