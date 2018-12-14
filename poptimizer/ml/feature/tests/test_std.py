import pandas as pd
import pytest

from poptimizer.ml.feature import std
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


def test_std():
    # noinspection PyTypeChecker
    feature = std.STD(("PIKK", "RTKMP", "TATNP"), pd.Timestamp("2018-12-10"))

    assert not feature.is_categorical()
    assert feature.get_params_space() == dict(days=YEAR_IN_TRADING_DAYS)

    df = feature.get(pd.Timestamp("2018-11-19"), days=10)
    assert isinstance(df, pd.Series)
    assert df.name == "STD"
    assert df.size == 3
    assert df["PIKK"] == pytest.approx(0.116674542313115)

    df = feature.get(pd.Timestamp("2018-10-26"), days=10)
    assert df["RTKMP"] == pytest.approx(0.103606599752109)

    df = feature.get(pd.Timestamp("2018-10-09"), days=10)
    assert df["TATNP"] == pytest.approx(0.221371480598971)
