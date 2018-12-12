import pandas as pd
import pytest

from poptimizer.ml import std


def test_std():
    # noinspection PyTypeChecker
    feature = std.STD(("PIKK", "RTKMP", "TATNP"), pd.Timestamp("2018-12-10"))

    assert not feature.is_categorical()
    assert feature.get_param_space() == dict()

    df = feature.get(10)

    assert isinstance(df, pd.Series)
    assert df.name == "STD"

    assert df[pd.Timestamp("2018-11-19"), "PIKK"] == pytest.approx(0.116674542313115)
    assert df[(pd.Timestamp("2018-10-26"), "RTKMP")] == pytest.approx(0.103606599752109)
    assert df[(pd.Timestamp("2018-10-09"), "TATNP")] == pytest.approx(0.221371480598971)
