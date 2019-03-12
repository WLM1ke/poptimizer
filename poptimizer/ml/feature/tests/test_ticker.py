import pandas as pd

from poptimizer.ml.feature import ticker


def test_ticker():
    feature = ticker.Ticker(
        ("UPRO", "GMKN", "MSTT"), pd.Timestamp("2018-12-11"), dict()
    )

    assert feature.is_categorical()
    assert feature.get_params_space() == dict(on_off=True)

    df = feature.get()
    assert isinstance(df, pd.Series)

    assert df[(pd.Timestamp("2006-12-27"), "GMKN")] == "GMKN"
    assert df[(pd.Timestamp("2018-12-05"), "UPRO")] == "UPRO"
    assert df[(pd.Timestamp("2018-12-07"), "MSTT")] == "MSTT"
