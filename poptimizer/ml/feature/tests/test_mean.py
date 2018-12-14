import pandas as pd
import pytest

from poptimizer.ml.feature import mean
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


def test_mean():
    # noinspection PyTypeChecker
    feature = mean.Mean(("VSMO", "BANEP", "ENRU"), pd.Timestamp("2018-12-07"))

    assert not feature.is_categorical()
    assert feature.get_params_space() == dict(days=YEAR_IN_TRADING_DAYS)

    df = feature.get(pd.Timestamp("2018-10-15"), days=53)
    assert isinstance(df, pd.Series)
    assert df.name == "Mean"
    assert df.size == 3
    assert df["VSMO"] == pytest.approx(-0.010316797368955)

    df = feature.get(pd.Timestamp("2018-10-29"), days=53)
    assert df["BANEP"] == pytest.approx(0.413477629952859)

    df = feature.get(pd.Timestamp("2018-10-02"), days=53)
    assert df["ENRU"] == pytest.approx(-0.150704229512325)
