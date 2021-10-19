import numpy as np

from poptimizer.portfolio import optimizer


def test_grad_conf_int():
    lower, upper = optimizer._grad_conf_int(np.random.random(100), 0.05)

    assert lower < 0.5
    assert 0.5 < upper
