import pandas as pd

from poptimizer.ml.feature import ticker


def test_ticker():
    # noinspection PyTypeChecker
    feature = ticker.Ticker(("UPRO", "GMKN", "MSTT"), pd.Timestamp("2018-12-11"))

    assert feature.is_categorical()
    assert feature.get_params_space() == dict()

    df = feature.get(pd.Timestamp("2006-12-27"))
    assert isinstance(df, pd.Series)
    assert df.size == 3
    assert df.name == "Ticker"
    assert df["GMKN"] == "GMKN"

    df = feature.get(pd.Timestamp("2018-12-05"))
    assert df["UPRO"] == "UPRO"

    df = feature.get(pd.Timestamp("2018-12-07"))
    assert df["MSTT"] == "MSTT"
