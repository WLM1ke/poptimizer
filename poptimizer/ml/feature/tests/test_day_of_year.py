import pandas as pd

from poptimizer.ml.feature import day_of_year


def test_day_of_year():
    feature = day_of_year.DayOfYear(
        ("GMKN", "NMTP", "SIBN"), pd.Timestamp("2019-08-30"), dict()
    )

    assert feature.is_categorical("") == [True]
    assert feature.get_params_space() == dict(on_off=True)

    df = feature.get()
    assert isinstance(df, pd.Series)

    assert df[(pd.Timestamp("2007-01-26"), "GMKN")] == 26
    assert df[(pd.Timestamp("2019-08-30"), "NMTP")] == 242
    assert df[(pd.Timestamp("2003-07-11"), "SIBN")] == 192
