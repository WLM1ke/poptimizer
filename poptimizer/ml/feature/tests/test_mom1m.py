import numpy as np
import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import mom1m


@pytest.fixture(scope="module", name="feat")
def test_mom1m_feature():
    return mom1m.Mom1m(
        ("GCHE", "LSRG", "PMSBP"), pd.Timestamp("2019-01-25"), {"days": 7}
    )


def test_is_categorical(feat):
    assert feat.is_categorical("") == [False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 2
    assert isinstance(space["on_off"], Apply)
    assert isinstance(space["days"], Apply)


def test_get(feat):
    df = feat.get({"days": 7})
    assert isinstance(df, pd.Series)
    assert df.name == "Mom1m"
    assert df[(pd.Timestamp("2018-12-25"), "GCHE")] == pytest.approx(0.0)

    assert df[(pd.Timestamp("2018-12-25"), "LSRG")] == pytest.approx(
        np.log(598.4 / 636.4) / 7
    )

    assert df[(pd.Timestamp("2018-12-25"), "PMSBP")] == pytest.approx(
        np.log(72.7 / 73.4) / 7
    )
