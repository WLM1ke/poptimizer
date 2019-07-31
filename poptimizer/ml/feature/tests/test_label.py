import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import label, YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def make_feature():
    return label.Label(
        ("AKRN", "SNGSP", "MSTT"),
        pd.Timestamp("2018-12-11"),
        {"days": 21, "div_share": 0.3},
    )


def test_is_categorical(feat):
    assert feat.is_categorical("") == [False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 3
    assert space["on_off"] is True
    assert space["div_share"] == 0.3
    assert isinstance(space["days"], Apply)


def test_get_returns(feat):
    df = feat.get({"days": 21, "div_share": 0.0})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2018-11-12"), "SNGSP")] == pytest.approx(
        0.0995856337763434 / YEAR_IN_TRADING_DAYS
    )

    assert df[(pd.Timestamp("2018-05-17"), "AKRN")] == pytest.approx(
        0.000454936219161647
    )


def test_get_0_3_div(feat):
    df = feat.get({"days": 21, "div_share": 0.3})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2018-11-12"), "SNGSP")] == pytest.approx(
        0.0995856337763434 / YEAR_IN_TRADING_DAYS * 0.7
    )

    assert df[(pd.Timestamp("2018-05-17"), "AKRN")] == pytest.approx(
        0.000851314151625369
    )


def test_get_1_0_div(feat):
    df = feat.get({"days": 21, "div_share": 1.0})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2018-11-12"), "SNGSP")] == pytest.approx(0)

    assert df[(pd.Timestamp("2018-05-17"), "AKRN")] == pytest.approx(
        185 * 0.87 / 4315 / 21
    )
