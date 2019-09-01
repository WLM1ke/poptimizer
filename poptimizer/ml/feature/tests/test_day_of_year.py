import pandas as pd
from hyperopt.pyll import Apply

from poptimizer.ml.feature import day_of_year, ON_OFF


def test_day_of_year():
    feature = day_of_year.DayOfYear(
        ("GMKN", "NMTP", "SIBN"), pd.Timestamp("2019-08-30"), dict()
    )

    assert feature.is_categorical("") == [True]
    space = feature.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space[ON_OFF], Apply)

    df = feature.get()
    assert isinstance(df, pd.Series)

    assert df[(pd.Timestamp("2007-01-26"), "GMKN")] == 26
    assert df[(pd.Timestamp("2019-08-30"), "NMTP")] == 242
    assert df[(pd.Timestamp("2003-07-11"), "SIBN")] == 192
