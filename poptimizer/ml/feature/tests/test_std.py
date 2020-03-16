import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import std


@pytest.fixture(scope="module", name="feat")
def test_std_feature():
    return std.Scaler(
        ("PIKK", "RTKMP", "TATNP"), pd.Timestamp("2018-12-10"), {"days": 10}
    )


def test_is_categorical(feat):
    assert feat.is_categorical("") == [False]


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
        0.007324056281990913
    )
    assert df[(pd.Timestamp("2018-10-26"), "RTKMP")] == pytest.approx(
        0.0065094393642531785
    )
    assert df[(pd.Timestamp("2018-10-09"), "TATNP")] == pytest.approx(
        0.01404605632913772
    )
    assert df.min() > std.LOW_STD
