import numpy as np
import pandas as pd
import pytest

from poptimizer.config import AFTER_TAX
from poptimizer.data import div
from poptimizer.ml import examples
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

FEAT_PARAMS = (
    ("Label", {"days": 6, "div_share": 0.0}),
    ("Scaler", {"on_off": True, "days": 7}),
    ("Ticker", {"on_off": True}),
    ("Mom12m", {"on_off": True, "days": 3, "periods": 1}),
    ("DivYield", {"on_off": True, "days": 9, "periods": 1}),
)


@pytest.fixture(scope="function", autouse=True)
def set_stats_start(monkeypatch):
    monkeypatch.setattr(div, "STATS_START", pd.Timestamp("2010-02-01"))
    yield


@pytest.fixture(name="example")
def create_examples():
    yield examples.Examples(
        ("AKRN", "CHMF", "BANEP"), pd.Timestamp("2018-12-13"), FEAT_PARAMS
    )


def test_tickers(example):
    assert example.tickers == ("AKRN", "CHMF", "BANEP")


def test_get_features_names(example):
    assert example.get_features_names() == [
        "Scaler",
        "Ticker",
        "Mom12m_0",
        "DivYield_0",
    ]


def test_categorical_features(example):
    assert example.categorical_features() == [1]


def test_get_params_space(example):
    space = example.get_params_space()
    assert isinstance(space, list)
    assert len(space) == 5
    for feat_name, feat_params in space:
        assert isinstance(feat_name, str)
        assert isinstance(feat_params, dict)


def test_get_all(example):
    df = example.get_all(
        (
            ("Label", {"days": 4, "div_share": 0.0}),
            ("Scaler", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )
    assert df.columns.to_list() == [
        "Test",
        "Label",
        "Scaler",
        "Ticker",
        "Mom12m_0",
        "DivYield_0",
    ]
    assert df.index.get_level_values(0).unique()[-1] == pd.Timestamp("2018-12-13")
    assert set(df.index.get_level_values(1).unique()) == {"CHMF", "AKRN", "BANEP"}

    assert df.iloc[:, 0][(pd.Timestamp("2018-12-04"), "AKRN")] == pytest.approx(
        4600 / 4630 - 1
    )
    assert df.iloc[:, 1][(pd.Timestamp("2018-12-04"), "AKRN")] == pytest.approx(
        -0.002_159_827_213_822_894_3
    )
    assert df.loc[(pd.Timestamp("2018-12-04"), "CHMF"), "Scaler"] == pytest.approx(
        0.175_472_006_664_393_42 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert df.loc[(pd.Timestamp("2018-12-04"), "BANEP"), "Ticker"] == "BANEP"
    assert df.loc[(pd.Timestamp("2018-12-04"), "AKRN"), "Mom12m_0"] == pytest.approx(
        np.log(4630 / 4672)
    )
    assert df.loc[(pd.Timestamp("2018-12-04"), "CHMF"), "DivYield_0"] == pytest.approx(
        44.39 * AFTER_TAX / 964.3
    )


def test_train_val_pool_params(example):
    train, val = example.train_val_pool_params(
        (
            ("Label", {"days": 4, "div_share": 0.0}),
            ("Scaler", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )

    assert isinstance(train, dict)
    assert len(train) == 5
    assert isinstance(val, dict)
    assert len(val) == 5

    assert train["cat_features"] == [1]
    assert val["cat_features"] == [1]

    assert train["feature_names"] == ["Scaler", "Ticker", "Mom12m_0", "DivYield_0"]
    assert val["feature_names"] == ["Scaler", "Ticker", "Mom12m_0", "DivYield_0"]

    assert train["data"].index.get_level_values(0)[0] == pd.Timestamp("2010-02-09")
    assert train["data"].index.get_level_values(0)[-1] == pd.Timestamp("2017-01-31")

    assert val["data"].index.get_level_values(0)[0] == pd.Timestamp("2017-02-06")
    assert val["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-07")

    df = example.get_all(
        (
            ("Label", {"days": 4, "div_share": 0.0}),
            ("Scaler", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )

    assert df.iloc[:, 2:].loc[train["data"].index].equals(train["data"])
    assert df.iloc[:, 1].loc[train["label"].index].equals(train["label"])
    assert np.allclose(
        1 / df.iloc[:, 2].loc[train["weight"].index] ** 2, train["weight"]
    )

    assert df.iloc[:, 2:].loc[val["data"].index].equals(val["data"])
    assert df.iloc[:, 1].loc[val["label"].index].equals(val["label"])
    assert np.allclose(1 / df.iloc[:, 2].loc[val["weight"].index] ** 2, val["weight"])


def test_test_pool_params(example):
    params = (
        ("Label", {"days": 5, "div_share": 0.0}),
        ("Scaler", {"on_off": True, "days": 5}),
        ("Ticker", {"on_off": True}),
        ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
        ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
    )
    test = example.test_pool_params(params)
    _, val = example.train_val_pool_params(params)
    assert isinstance(test, dict)
    assert len(test) == 5

    assert test["cat_features"] == [1]
    assert test["feature_names"] == ["Scaler", "Ticker", "Mom12m_0", "DivYield_0"]

    val_len = len(val["data"])
    assert len(test["data"]) > val_len

    assert test["data"].iloc[:val_len].equals(val["data"])
    assert test["weight"].iloc[:val_len].equals(val["weight"])


def test_train_predict_pool_params(example):
    train, predict = example.train_predict_pool_params()

    assert isinstance(train, dict)
    assert len(train) == 5
    assert isinstance(predict, dict)
    assert len(predict) == 5

    assert train["cat_features"] == [1]
    assert predict["cat_features"] == [1]

    assert train["feature_names"] == ["Scaler", "Ticker", "Mom12m_0", "DivYield_0"]
    assert predict["feature_names"] == ["Scaler", "Ticker", "Mom12m_0", "DivYield_0"]

    assert train["data"].index.get_level_values(0)[0] == pd.Timestamp("2010-02-11")
    assert train["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-05")

    assert predict["data"].index.get_level_values(0)[0] == pd.Timestamp("2018-12-13")
    assert predict["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-13")

    df = example.get_all(
        (
            ("Label", {"days": 6, "div_share": 0.0}),
            ("Scaler", {"on_off": True, "days": 7}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 3, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 9, "periods": 1}),
        )
    )

    assert df.iloc[:, 2:].loc[train["data"].index].equals(train["data"])
    assert df.iloc[:, 1].loc[train["label"].index].equals(train["label"])
    assert np.allclose(
        1 / df.iloc[:, 2].loc[train["weight"].index] ** 2, train["weight"]
    )

    assert df.iloc[:, 2:].loc[predict["data"].index].equals(predict["data"])
    assert predict["label"] is None
    assert np.allclose(
        1 / df.iloc[:, 2].loc[predict["weight"].index] ** 2, predict["weight"]
    )
