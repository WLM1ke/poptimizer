import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import turnover


@pytest.fixture(scope="module", name="feat")
def test_std_feature():
    return turnover.TurnOver(
        ("KZOS", "LSNGP", "NVTK"), pd.Timestamp("2019-09-26"), {"days": 5}
    )


def test_is_categorical(feat):
    assert feat.is_categorical("") == [False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 3
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)
    assert isinstance(space["normalize"], Apply)


def test_get(feat):
    df = feat.get({"days": 5, "normalize": False})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2019-09-26"), "KZOS")] == pytest.approx(14.8079083367957)
    assert df[(pd.Timestamp("2019-09-25"), "LSNGP")] == pytest.approx(16.8591448871503)
    assert df[(pd.Timestamp("2019-09-24"), "NVTK")] == pytest.approx(20.4823293869329)


def test_get_normalize(feat):
    df = feat.get({"days": 5, "normalize": True})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2019-09-26"), "KZOS")] == pytest.approx(-4.68356826666262)
    assert df[(pd.Timestamp("2019-09-26"), "LSNGP")] == pytest.approx(-2.80320394254991)
    assert df[(pd.Timestamp("2019-09-26"), "NVTK")] == pytest.approx(1.07504968970922)


@pytest.fixture(scope="module", name="var")
def test_var_feature():
    return turnover.TurnOverVar(
        ("LSNGP", "MGTSP", "PLZL"), pd.Timestamp("2019-10-31"), {"days": 4}
    )


def test_is_categorical_var(var):
    assert var.is_categorical("") == [False]


def test_get_params_space_var(var):
    space = var.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 2
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)


def test_get_var(var):
    df = var.get({"days": 4, "normalize": False})
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2019-10-25"), "LSNGP")] == pytest.approx(0.209651032823892)
    assert df[(pd.Timestamp("2019-10-24"), "MGTSP")] == pytest.approx(0.241766516648416)
    assert df[(pd.Timestamp("2019-10-23"), "PLZL")] == pytest.approx(0.263376076528282)
