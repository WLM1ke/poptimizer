import numpy as np
import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.dl.trainer import YEAR_IN_TRADING_DAYS
from poptimizer.ml.feature import mom12m


@pytest.fixture(scope="module", name="feat")
def test_mom12m_feature():
    return mom12m.Mom12m(
        ("VSMO", "BANEP", "ENRU"), pd.Timestamp("2018-12-07"), {"days": 8, "periods": 2}
    )


def test_col_names(feat):
    assert feat.col_names == ["Mom12m_0", "Mom12m_1"]


def test_is_categorical(feat):
    assert feat.is_categorical({"days": 57, "periods": 1}) == [False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 3
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)
    assert isinstance(space["periods"], Apply)


def test_get(feat):
    df = feat.get({"days": 53, "periods": 1})
    assert isinstance(df, pd.DataFrame)
    assert df.columns.to_list() == ["Mom12m_0"]

    assert df.loc[(pd.Timestamp("2018-10-15"), "VSMO"), "Mom12m_0"] == pytest.approx(
        -0.010316797368955 / YEAR_IN_TRADING_DAYS * 53
    )
    assert df.loc[(pd.Timestamp("2018-10-29"), "BANEP"), "Mom12m_0"] == pytest.approx(
        0.413477629952859 / YEAR_IN_TRADING_DAYS * 53
    )
    assert df.loc[(pd.Timestamp("2018-10-02"), "ENRU"), "Mom12m_0"] == pytest.approx(
        -0.150704229512325 / YEAR_IN_TRADING_DAYS * 53
    )


def test_get_many_periods(feat):
    df = feat.get({"days": 11, "periods": 3})
    assert isinstance(df, pd.DataFrame)
    assert df.columns.to_list() == ["Mom12m_0", "Mom12m_1", "Mom12m_2"]

    assert pd.Timestamp("2018-12-07") in df.index
    assert pd.Timestamp("2018-12-08") not in df.index
    assert pd.Timestamp("2018-12-10") not in df.index

    assert df.loc[(pd.Timestamp("2018-06-08"), "BANEP"), "Mom12m_1"] == pytest.approx(
        np.log(1736.5 / 1739)
    )
