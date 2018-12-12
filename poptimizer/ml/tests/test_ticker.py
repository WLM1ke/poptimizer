import pandas as pd

from poptimizer.ml import ticker
from poptimizer.store import TICKER


def test_ticker():
    # noinspection PyTypeChecker
    feature = ticker.Ticker(("UPRO", "GMKN", "MSTT"), pd.Timestamp("2018-12-11"))

    assert feature.is_categorical()
    assert feature.get_param_space() == dict()

    df = feature.get()

    assert isinstance(df, pd.DataFrame)
    assert df.shape[1] == 1

    assert df.at[(pd.Timestamp("2006-12-27"), "GMKN"), TICKER] == "GMKN"
    assert df.at[(pd.Timestamp("2018-12-05"), "UPRO"), TICKER] == "UPRO"
    assert df.at[(pd.Timestamp("2018-12-07"), "MSTT"), TICKER] == "MSTT"
