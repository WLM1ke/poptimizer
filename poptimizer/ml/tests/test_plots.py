import numpy as np
import pandas as pd
import pytest

from poptimizer import config
from poptimizer.ml import plots, feature_old, examples_old

ML_PARAMS = (
    (
        (True, {"days": 58}),
        (True, {"days": 195}),
        (False, {}),
        (True, {"days": 282}),
        (True, {"days": 332}),
        (False, {"days": 21}),
    ),
    {
        "bagging_temperature": 0.9388504407881838,
        "depth": 5,
        "l2_leaf_reg": 3.2947929042414654,
        "learning_rate": 0.07663371920281654,
        "one_hot_max_size": 100,
        "random_strength": 0.9261064363697566,
        "ignored_features": [1],
    },
)
FEATURES = [
    feature_old.Label,
    feature_old.STD,
    feature_old.Ticker,
    feature_old.Mom12m,
    feature_old.DivYield,
    feature_old.Mom1m,
]
TICKERS = ("BANEP", "DSKY", "LKOH", "MOEX", "NKNCP")
DATE = pd.Timestamp("2019-01-03")


@pytest.fixture(autouse=True)
def patch_params_and_show(monkeypatch):
    monkeypatch.setattr(config, "ML_PARAMS", ML_PARAMS)
    monkeypatch.setattr(plots.plt, "show", lambda: None)


def test_learning_curve(monkeypatch):
    monkeypatch.setattr(plots, "FRACTIONS", [0.1, 0.5, 1.0])
    train_sizes, train_scores, test_scores = plots.learning_curve(TICKERS, DATE)
    assert np.allclose([11, 55, 110], train_sizes)
    assert np.allclose([0.77440018, 0.86681678, 0.8870834], train_scores)
    assert np.allclose([1.04168629, 1.02808554, 1.02049696], test_scores)


def test_partial_dependence_curve(monkeypatch):
    monkeypatch.setattr(examples_old.Examples, "FEATURES", FEATURES)
    monkeypatch.setattr(plots, "QUANTILE", [0.3, 0.7])
    result = plots.partial_dependence_curve(TICKERS, DATE)
    assert len(result) == 4
    assert len(result[0]) == 2


def test_draw_cross_val_predict():
    x, y = plots.cross_val_predict_plot(TICKERS, DATE)
    assert len(x) == len(y) == 116
    assert np.allclose(x[:3].values, [-0.13702667, 0.16367253, 0.16657164])
    assert np.allclose(y[-3:].values, [0.17200295, -0.02747856, 0.02692788])
