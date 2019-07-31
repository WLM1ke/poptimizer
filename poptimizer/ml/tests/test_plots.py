import collections

import matplotlib
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.ml import plots

ML_PARAMS = {
    "data": (
        ("Label", {"days": 58, "div_share": 0.0}),
        ("Scaler", {"days": 195}),
        ("Ticker", {}),
        ("Mom12m", {"days": 282, "periods": 1}),
        ("DivYield", {"days": 332, "periods": 2}),
        ("Mom1m", {"days": 21}),
    ),
    "model": {
        "bagging_temperature": 0.9388504407881838,
        "depth": 5,
        "l2_leaf_reg": 3.2947929042414654,
        "learning_rate": 0.07663371920281654,
        "one_hot_max_size": 100,
        "random_strength": 0.9261064363697566,
        "ignored_features": [1],
    },
}

TICKERS = ("BANEP", "DSKY", "LKOH", "MOEX", "NKNCP")
DATE = pd.Timestamp("2019-01-03")

test_data = [(2, 2), (3, 3), (4, 4), (5, 6), (6, 6), (7, 8), (9, 9), (10, 12)]


@pytest.mark.parametrize("n_plots,size", test_data)
def test_axs_iter(n_plots, size):
    rez = plots.axs_iter(n_plots)
    assert isinstance(rez, collections.Iterator)
    rez_list = list(rez)
    assert len(rez_list) == size
    # noinspection PyUnresolvedReferences
    assert isinstance(rez_list[0], matplotlib.axes.Axes)


@pytest.fixture(autouse=True)
def patch_params_and_show(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    monkeypatch.setattr(plots.plt, "show", lambda: None)


def test_partial_dependence_curve(monkeypatch):
    monkeypatch.setattr(plots, "QUANTILE", [0.3, 0.7])
    result = plots.partial_dependence_curve(TICKERS, DATE)
    assert len(result) == 5
    assert len(result[0]) == 2
