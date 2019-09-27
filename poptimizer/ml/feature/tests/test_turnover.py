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
