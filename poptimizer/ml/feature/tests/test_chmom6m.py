import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import chmom6m


@pytest.fixture(scope="module", name="feat")
def test_chmom6m_feature():
    return chmom6m.ChMom6m(
        ("ALRS", "BANEP", "CHMF"), pd.Timestamp("2019-04-26"), {"days": 4}
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
    df = feat.get({"days": 4})
    assert isinstance(df, pd.Series)
    assert df.name == "ChMom6m"
    assert df[(pd.Timestamp("2019-04-26"), "ALRS")] == pytest.approx(
        -0.00662237880468577
    )
    assert df[(pd.Timestamp("2019-03-15"), "BANEP")] == pytest.approx(
        -0.00318544860053294
    )
    assert df[(pd.Timestamp("2019-02-05"), "CHMF")] == pytest.approx(
        -0.0000780946941400067
    )
