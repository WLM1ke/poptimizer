import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import label, YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def make_feature():
    # noinspection PyTypeChecker
    return label.Label(("AKRN", "SNGSP", "MSTT"), pd.Timestamp("2018-12-11"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_get(feat):
    df = feat.get(pd.Timestamp("2018-11-12"), days=21)
    assert isinstance(df, pd.Series)
    assert df.size == 3
    assert df.at["SNGSP"] == pytest.approx(0.0995856337763434 / YEAR_IN_TRADING_DAYS)

    df = feat.get(pd.Timestamp("2018-05-17"), days=21)
    assert df.at["AKRN"] == pytest.approx(0.114643927228733 / YEAR_IN_TRADING_DAYS)
