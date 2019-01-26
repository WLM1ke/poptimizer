import numpy as np
import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.config import AFTER_TAX, POptimizerError
from poptimizer.ml import examples
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="example")
def create_examples():
    # noinspection PyTypeChecker
    yield examples.Examples(("AKRN", "CHMF", "BANEP"), pd.Timestamp("2018-12-13"))


def test_get_features_names(example):
    assert example.get_features_names() == [
        "STD",
        "Ticker",
        "Mom12m",
        "DivYield",
        "Mom1m",
    ]


def test_categorical_features(example):
    assert example.categorical_features() == [1]


def test_get_params_space(example):
    space = example.get_params_space()
    assert isinstance(space, list)
    assert len(space) == 6
    assert space[0][0] is True
    assert isinstance(space[0][1], dict)
    for on_off, params in space[1:]:
        isinstance(on_off, Apply)
        isinstance(params, dict)


def test_check_bounds(example, capsys):
    example.check_bounds(
        (
            (True, {"days": -1}),
            (False, {"days": -1}),
            (True, {}),
            (True, {"days": 252}),
            (False, {"days": 252}),
        )
    )
    captured = capsys.readouterr()
    assert "Необходимо расширить Label_RANGE" in captured.out
    assert "Необходимо расширить STD_RANGE" in captured.out


def test_get(example):
    df = example.get(
        pd.Timestamp("2018-12-04"),
        (
            (True, {"days": 4}),
            (True, {"days": 5}),
            (True, {}),
            (True, {"days": 6}),
            (False, {"days": 7}),
        ),
    )
    assert (df.columns == ["Label", "STD", "Ticker", "Mom12m", "DivYield"]).all()
    assert (df.index == ["AKRN", "CHMF", "BANEP"]).all()
    assert df.loc["AKRN", "Label"] == pytest.approx(
        np.log(4590 / 4630) * YEAR_IN_TRADING_DAYS ** 0.5 / 4 / 0.051967880396035164
    )
    assert df.loc["CHMF", "STD"] == pytest.approx(
        0.17547200666439342 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert df.loc["BANEP", "Ticker"] == "BANEP"
    assert df.loc["AKRN", "Mom12m"] == pytest.approx(np.log(4630 / 4672) / 6)
    assert df.loc["CHMF", "DivYield"] == pytest.approx(44.39 * AFTER_TAX / 964.3)


def test_std_days(example):
    days = example.mean_std_days(
        (
            (True, {"days": 4}),
            (True, {"days": 22}),
            (True, {}),
            (True, {"days": 6}),
            (False, {"days": 7}),
        )
    )
    assert days == (4, 22)


def test_learn_pool(example):
    params = (
        (True, {"days": 4}),
        (True, {"days": 5}),
        (True, {}),
        (True, {"days": 6}),
        (False, {"days": 7}),
    )

    pool = example.learn_pool_params(params)
    assert isinstance(pool, dict)
    assert len(pool) == 4

    assert isinstance(pool["data"], pd.DataFrame)
    assert (pool["data"].columns == ["STD", "Ticker", "Mom12m", "DivYield"]).all()
    assert np.allclose(
        pool["data"].iloc[:3, [0, 2, 3]].values,
        example.get(pd.Timestamp("2018-12-07"), params).iloc[:, [1, 3, 4]].values,
    )
    assert np.allclose(
        pool["data"].iloc[3:6, [0, 2, 3]].values,
        example.get(pd.Timestamp("2018-12-03"), params).iloc[:, [1, 3, 4]].values,
    )

    assert isinstance(pool["label"], pd.Series)
    assert pool["label"].name == "Label"
    assert np.allclose(
        pool["label"].iloc[:3].values,
        example.get(pd.Timestamp("2018-12-07"), params).iloc[:, 0].values,
    )
    assert np.allclose(
        pool["label"].iloc[3:6].values,
        example.get(pd.Timestamp("2018-12-03"), params).iloc[:, 0].values,
    )

    assert pool["cat_features"] == [1]

    assert pool["feature_names"] == ["STD", "Ticker", "Mom12m", "DivYield"]


def test_learn_pool_bad_date():
    cases = examples.Examples(("AKRN", "CHMF", "BANEP"), pd.Timestamp("2019-01-13"))
    params = (
        (True, {"days": 4}),
        (True, {"days": 5}),
        (True, {}),
        (True, {"days": 6}),
        (False, {"days": 7}),
    )
    with pytest.raises(POptimizerError) as error:
        cases.learn_pool_params(params)
    assert str(error.value) == "Для даты 2019-01-13 отсутствуют исторические котировки"


def test_predict_pool(example):
    params = (
        (True, {"days": 6}),
        (True, {"days": 7}),
        (True, {}),
        (True, {"days": 3}),
        (False, {"days": 9}),
    )

    pool = example.predict_pool_params(params)
    assert isinstance(pool, dict)
    assert len(pool) == 4

    assert isinstance(pool["data"], pd.DataFrame)
    assert (pool["data"].columns == ["STD", "Ticker", "Mom12m", "DivYield"]).all()
    assert np.allclose(
        pool["data"].iloc[:, [0, 2, 3]].values,
        example.get(pd.Timestamp("2018-12-13"), params).iloc[:, [1, 3, 4]].values,
    )

    assert pool["label"] is None

    assert pool["cat_features"] == [1]

    assert pool["feature_names"] == ["STD", "Ticker", "Mom12m", "DivYield"]
