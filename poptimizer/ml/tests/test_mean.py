import pandas as pd
import pytest

from poptimizer.ml import mean


def test_mean():
    # noinspection PyTypeChecker
    feature = mean.Mean(("VSMO", "BANEP", "ENRU"), pd.Timestamp("2018-12-07"))

    assert not feature.is_categorical()
    assert feature.get_param_space() == dict()

    df = feature.get(53)

    assert isinstance(df, pd.Series)
    assert df.name == "MEAN"

    assert df[pd.Timestamp("2018-10-15"), "VSMO"] == pytest.approx(-0.010316797368955)
    assert df[(pd.Timestamp("2018-10-29"), "BANEP")] == pytest.approx(0.413477629952859)
    assert df[(pd.Timestamp("2018-10-02"), "ENRU")] == pytest.approx(-0.150704229512325)
