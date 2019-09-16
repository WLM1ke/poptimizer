import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.data import div
from poptimizer.ml.feature import day_of_year, ON_OFF


@pytest.fixture(scope="function", autouse=True)
def set_stats_start(monkeypatch):
    monkeypatch.setattr(div, "STATS_START", pd.Timestamp("2010-07-19"))
    yield


def test_day_of_year():
    feature = day_of_year.DayOfYear(
        ("GMKN", "NMTP", "SIBN"), pd.Timestamp("2019-08-30"), dict()
    )

    assert feature.is_categorical("") == [False]
    space = feature.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space[ON_OFF], Apply)

    df = feature.get()
    assert isinstance(df, pd.Series)
    assert df.index[0] == (pd.Timestamp("2010-07-20"), "GMKN")
    assert df.index[-1] == (pd.Timestamp("2019-08-30"), "SIBN")

    assert df[(pd.Timestamp("2011-01-26"), "GMKN")] == 26
    assert df[(pd.Timestamp("2019-08-30"), "NMTP")] == 242
    assert df[(pd.Timestamp("2013-07-11"), "SIBN")] == 192
