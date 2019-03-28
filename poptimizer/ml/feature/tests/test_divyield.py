import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.config import AFTER_TAX
from poptimizer.ml.feature import divyield


@pytest.fixture(scope="module", name="feat")
def test_divyield_feature():
    return divyield.DivYield(
        ("PHOR", "TATN", "DSKY"), pd.Timestamp("2018-12-12"), {"days": 47, "periods": 1}
    )


def test_col_names(feat):
    assert feat.col_names == ["DivYield_0"]


def test_is_categorical(feat):
    assert feat.is_categorical({"days": 47, "periods": 2}) == [False, False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 3
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)
    assert isinstance(space["periods"], Apply)


def test_get(feat):
    df = feat.get({"days": 13, "periods": 1})
    assert isinstance(df, pd.DataFrame)

    assert pd.Timestamp("2018-12-12") in df.index
    assert pd.Timestamp("2018-12-13") not in df.index
    assert pd.Timestamp("2010-01-26") not in df.index

    df = feat.get(dict(days=9, periods=1))
    assert df.loc[(pd.Timestamp("2018-06-22"), "PHOR"), "DivYield_0"] == pytest.approx(
        AFTER_TAX * 15 / 2291
    )
    assert df.loc[(pd.Timestamp("2018-06-25"), "PHOR"), "DivYield_0"] == pytest.approx(
        0
    )

    df = feat.get(dict(days=20, periods=1))
    assert df.loc[(pd.Timestamp("2018-06-11"), "PHOR"), "DivYield_0"] == pytest.approx(
        AFTER_TAX * 15 / 2315
    )

    df = feat.get(dict(days=30, periods=1))
    assert df.loc[(pd.Timestamp("2018-10-11"), "TATN"), "DivYield_0"] == pytest.approx(
        30.27 * AFTER_TAX / 778.3
    )
    assert df.loc[(pd.Timestamp("2018-10-10"), "TATN"), "DivYield_0"] == pytest.approx(
        0
    )


def test_get_many_periods(feat):
    df = feat.get({"days": 9, "periods": 2})
    assert isinstance(df, pd.DataFrame)

    assert pd.Timestamp("2018-12-12") in df.index
    assert pd.Timestamp("2018-12-13") not in df.index

    assert df.columns.to_list() == ["DivYield_0", "DivYield_1"]

    assert df.loc[(pd.Timestamp("2018-06-08"), "PHOR"), "DivYield_0"] == pytest.approx(
        0
    )
    assert df.loc[(pd.Timestamp("2018-06-11"), "PHOR"), "DivYield_0"] == pytest.approx(
        AFTER_TAX * 15 / 2315
    )
    assert df.loc[(pd.Timestamp("2018-06-15"), "PHOR"), "DivYield_0"] == pytest.approx(
        AFTER_TAX * 15 / 2296
    )
    assert df.loc[(pd.Timestamp("2018-06-18"), "PHOR"), "DivYield_0"] == pytest.approx(
        0
    )

    assert df.loc[(pd.Timestamp("2018-06-15"), "PHOR"), "DivYield_1"] == pytest.approx(
        0
    )
    assert df.loc[(pd.Timestamp("2018-06-18"), "PHOR"), "DivYield_1"] == pytest.approx(
        AFTER_TAX * 15 / 2295
    )
    assert df.loc[(pd.Timestamp("2018-06-21"), "PHOR"), "DivYield_1"] == pytest.approx(
        AFTER_TAX * 15 / 2286
    )
    assert df.loc[(pd.Timestamp("2018-06-22"), "PHOR"), "DivYield_1"] == pytest.approx(
        0
    )
