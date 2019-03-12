import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import std
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def test_std_feature():
    return std.STD(("PIKK", "RTKMP", "TATNP"), pd.Timestamp("2018-12-10"), {"days": 10})


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 2
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)


def test_get(feat):
    df = feat.get()
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2018-11-19"), "PIKK")] == pytest.approx(
        0.116674542313115 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert df[(pd.Timestamp("2018-10-26"), "RTKMP")] == pytest.approx(
        0.103606599752109 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert df[(pd.Timestamp("2018-10-09"), "TATNP")] == pytest.approx(
        0.221371480598971 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert df.min() > std.LOW_STD
