import numpy as np
import pandas as pd
import pytest

from poptimizer.config import AFTER_TAX
from poptimizer.ml import examples
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

FEAT_PARAMS = (
    ("Label", {"days": 6}),
    ("STD", {"on_off": True, "days": 7}),
    ("Ticker", {"on_off": True}),
    ("Mom12m", {"on_off": True, "days": 3, "periods": 1}),
    ("DivYield", {"on_off": True, "days": 9, "periods": 1}),
)


@pytest.fixture(name="example")
def create_examples():
    yield examples.Examples(
        ("AKRN", "CHMF", "BANEP"), pd.Timestamp("2018-12-13"), FEAT_PARAMS
    )


def test_get_features_names(example):
    assert example.get_features_names() == ["STD", "Ticker", "Mom12m_0", "DivYield_0"]


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
            ("Label", {"days": 4}),
            ("STD", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )
    assert df.columns.to_list() == ["Label", "STD", "Ticker", "Mom12m_0", "DivYield_0"]
    assert df.index.get_level_values(0).unique()[-1] == pd.Timestamp("2018-12-13")
    assert df.index.get_level_values(1).unique().to_list() == ["CHMF", "AKRN", "BANEP"]

    assert df.loc[(pd.Timestamp("2018-12-04"), "AKRN"), "Label"] == pytest.approx(
        np.log(4590 / 4630) * YEAR_IN_TRADING_DAYS ** 0.5 / 4 / 0.051967880396035164
    )
    assert df.loc[(pd.Timestamp("2018-12-04"), "CHMF"), "STD"] == pytest.approx(
        0.17547200666439342 / YEAR_IN_TRADING_DAYS ** 0.5
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
            ("Label", {"days": 4}),
            ("STD", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )

    assert isinstance(train, dict)
    assert len(train) == 4
    assert isinstance(val, dict)
    assert len(val) == 4

    assert train["cat_features"] == [1]
    assert val["cat_features"] == [1]

    assert train["feature_names"] == ["STD", "Ticker", "Mom12m_0", "DivYield_0"]
    assert val["feature_names"] == ["STD", "Ticker", "Mom12m_0", "DivYield_0"]

    assert train["data"].index.get_level_values(0)[0] == pd.Timestamp("2010-01-20")
    assert train["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-02-09")

    assert val["data"].index.get_level_values(0)[0] == pd.Timestamp("2018-02-15")
    assert val["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-07")

    df = example.get_all(
        (
            ("Label", {"days": 4}),
            ("STD", {"on_off": True, "days": 5}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 6, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 7, "periods": 1}),
        )
    )

    assert df.iloc[:, 1:].loc[train["data"].index].equals(train["data"])
    assert df.iloc[:, 0].loc[train["label"].index].equals(train["label"])

    assert df.iloc[:, 1:].loc[val["data"].index].equals(val["data"])
    assert df.iloc[:, 0].loc[val["label"].index].equals(val["label"])


def test_train_predict_pool_params(example):
    train, predict = example.train_predict_pool_params()

    assert isinstance(train, dict)
    assert len(train) == 4
    assert isinstance(predict, dict)
    assert len(predict) == 4

    assert train["cat_features"] == [1]
    assert predict["cat_features"] == [1]

    assert train["feature_names"] == ["STD", "Ticker", "Mom12m_0", "DivYield_0"]
    assert predict["feature_names"] == ["STD", "Ticker", "Mom12m_0", "DivYield_0"]

    assert train["data"].index.get_level_values(0)[0] == pd.Timestamp("2010-01-22")
    assert train["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-05")

    assert predict["data"].index.get_level_values(0)[0] == pd.Timestamp("2018-12-13")
    assert predict["data"].index.get_level_values(0)[-1] == pd.Timestamp("2018-12-13")

    df = example.get_all(
        (
            ("Label", {"days": 6}),
            ("STD", {"on_off": True, "days": 7}),
            ("Ticker", {"on_off": True}),
            ("Mom12m", {"on_off": True, "days": 3, "periods": 1}),
            ("DivYield", {"on_off": True, "days": 9, "periods": 1}),
        )
    )

    assert df.iloc[:, 1:].loc[train["data"].index].equals(train["data"])
    assert df.iloc[:, 0].loc[train["label"].index].equals(train["label"])

    assert df.iloc[:, 1:].loc[predict["data"].index].equals(predict["data"])
    assert predict["label"] is None
