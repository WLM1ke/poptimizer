import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import mom12m
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def test_mom12m_feature():
    return mom12m.Mom12m(
        ("VSMO", "BANEP", "ENRU"), pd.Timestamp("2018-12-07"), {"days": 8}
    )


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 2
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)


def test_get(feat):
    df = feat.get({"days": 53})
    assert isinstance(df, pd.Series)
    assert df.name == "Mom12m"
    assert df[(pd.Timestamp("2018-10-15"), "VSMO")] == pytest.approx(
        -0.010316797368955 / YEAR_IN_TRADING_DAYS
    )
    assert df[(pd.Timestamp("2018-10-29"), "BANEP")] == pytest.approx(
        0.413477629952859 / YEAR_IN_TRADING_DAYS
    )
    assert df[(pd.Timestamp("2018-10-02"), "ENRU")] == pytest.approx(
        -0.150704229512325 / YEAR_IN_TRADING_DAYS
    )
