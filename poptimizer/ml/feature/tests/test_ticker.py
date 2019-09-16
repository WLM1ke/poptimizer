import pandas as pd
import pytest

from poptimizer.data import div
from poptimizer.ml.feature import ticker


@pytest.fixture(scope="function", autouse=True)
def set_stats_start(monkeypatch):
    monkeypatch.setattr(div, "STATS_START", pd.Timestamp("2010-08-20"))
    yield


def test_ticker():
    feature = ticker.Ticker(
        ("UPRO", "GMKN", "MSTT"), pd.Timestamp("2018-12-11"), dict()
    )

    assert feature.is_categorical("") == [True]
    assert feature.get_params_space() == dict(on_off=True)

    df = feature.get()
    assert isinstance(df, pd.Series)
    assert df.index[0] == (pd.Timestamp("2010-08-23"), "UPRO")
    assert df.index[-1] == (pd.Timestamp("2018-12-11"), "MSTT")

    assert df[(pd.Timestamp("2011-12-27"), "GMKN")] == "GMKN"
    assert df[(pd.Timestamp("2018-12-05"), "UPRO")] == "UPRO"
    assert df[(pd.Timestamp("2018-12-07"), "MSTT")] == "MSTT"
