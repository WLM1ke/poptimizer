import numpy as np

from poptimizer.ml import ledoit_wolf


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

    cov1, average_cor1, shrinkage1 = ledoit_wolf.ledoit_wolf(data)
    assert np.allclose(cov1, result)

    cov2, average_cor2, shrinkage2 = ledoit_wolf.ledoit_wolf(np.vstack((data, data)))
    assert np.allclose(np.diag(cov1), np.diag(cov2))
    assert np.allclose(average_cor1, average_cor2)
    assert shrinkage2 < shrinkage1
