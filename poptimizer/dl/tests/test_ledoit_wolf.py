import numpy as np
import pandas as pd

from poptimizer.dl import ledoit_wolf


def test_ledoit_wolf():
    data = np.array(
        [
            [1.0, 2.0, 5.0],
            [4.0, 6.0, 8.0],
            [7.0, 8.0, 10.0],
            [1.0, 5.0, 7.0],
            [8.0, 9.0, 1.0],
        ]
    )
    result = [
        [8.56000000000000, 2.00071631947653, 1.54132176377468],
        [2.00071631947653, 6.00000000000000, 1.34594278490159],
        [1.54132176377468, 1.34594278490159, 9.36000000000000],
    ]

    cov1, average_cor1, shrinkage1 = ledoit_wolf.shrinkage(data)
    assert np.allclose(cov1, result)

    cov2, average_cor2, shrinkage2 = ledoit_wolf.shrinkage(np.vstack((data, data)))
    assert np.allclose(np.diag(cov1), np.diag(cov2))
    assert np.allclose(average_cor1, average_cor2)
    assert shrinkage2 < shrinkage1


def test_ledoit_wolf_cor():
    cor, average_cor, shrink = ledoit_wolf.ledoit_wolf_cor(
        ("CHEP", "MTSS", "PLZL"),
        pd.Timestamp("2020-05-19"),
        30,
    )

    assert cor.shape == (3, 3)
    assert np.allclose(cor, cor.transpose())
    assert np.allclose(np.diag(cor), 1)

    assert np.allclose(average_cor, 0.3009843442553877)
    assert np.allclose(average_cor, (cor.sum() - 3) / 6)

    assert np.allclose(shrink, 0.8625220790109036)


def test_ledoit_wolf_cor_forecast_days():
    sigma, average_cor, shrink = ledoit_wolf.ledoit_wolf_cor(
        ("CHEP", "MTSS", "PLZL"),
        pd.Timestamp("2021-09-30"),
        30,
    )
    sigma2, average_cor2, shrink2 = ledoit_wolf.ledoit_wolf_cor(
        ("CHEP", "MTSS", "PLZL"),
        pd.Timestamp("2021-10-01"),
        30,
        1,
    )

    assert np.allclose(sigma, sigma2)
    assert average_cor == average_cor2
    assert shrink == shrink2
