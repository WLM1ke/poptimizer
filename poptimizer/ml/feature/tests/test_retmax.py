import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import retmax


@pytest.fixture(scope="module", name="feat")
def test_retmax_feature():
    return retmax.RetMax(
        ("MRKY", "PRTK", "UPRO"), pd.Timestamp("2019-02-25"), {"days": 7}
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
    assert df[(pd.Timestamp("2019-02-25"), "MRKY")] == pytest.approx(0.0535561044689621)
    assert df[(pd.Timestamp("2019-02-25"), "PRTK")] == pytest.approx(
        0.010374732825551644
    )
    assert df[(pd.Timestamp("2019-02-25"), "UPRO")] == pytest.approx(
        0.012103577063856594
    )
