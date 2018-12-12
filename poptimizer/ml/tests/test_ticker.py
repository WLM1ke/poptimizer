import pandas as pd

from poptimizer.ml import ticker
from poptimizer.store import TICKER


def test_ticker():
    # noinspection PyTypeChecker
    feature = ticker.Ticker(("UPRO", "GMKN", "MSTT"), pd.Timestamp("2018-12-11"))

    assert feature.is_categorical()
    assert feature.get_param_space() == dict()

    df = feature.get()

    assert isinstance(df, pd.Series)
    assert df.name == TICKER

    assert df[(pd.Timestamp("2006-12-27"), "GMKN")] == "GMKN"
    assert df[(pd.Timestamp("2018-12-05"), "UPRO")] == "UPRO"
    assert df[(pd.Timestamp("2018-12-07"), "MSTT")] == "MSTT"
