import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import label, YEAR_IN_TRADING_DAYS


# noinspection PyUnresolvedReferences
@pytest.fixture(scope="module", name="feat")
def make_feature():
    return label.Label(
        ("AKRN", "SNGSP", "MSTT"), pd.Timestamp("2018-12-11"), {"days": 21}
    )


def test_is_categorical(feat):
    assert feat.is_categorical("") == [False]


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 2
    assert space["on_off"] is True
    assert isinstance(space["days"], Apply)


# noinspection PyUnresolvedReferences
def test_get(feat):
    df = feat.get()
    assert isinstance(df, pd.Series)
    assert df[(pd.Timestamp("2018-11-12"), "SNGSP")] == pytest.approx(
        0.0995856337763434 / YEAR_IN_TRADING_DAYS
    )

    assert df[(pd.Timestamp("2018-05-17"), "AKRN")] == pytest.approx(
        0.114643927228733 / YEAR_IN_TRADING_DAYS
    )
