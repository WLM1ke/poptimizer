import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import std
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def test_srd_feature():
    # noinspection PyTypeChecker
    return std.STD(("PIKK", "RTKMP", "TATNP"), pd.Timestamp("2018-12-10"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_check_bounds_middle(feat, capsys):
    lower, upper = std.RANGE
    feat.check_bounds(days=(lower + upper) / 2)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_bounds_lower(feat, capsys):
    lower, upper = std.RANGE
    feat.check_bounds(days=int(lower * 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(upper) in captured.out


def test_check_bounds_upper(feat, capsys):
    lower, upper = std.RANGE
    feat.check_bounds(days=int(upper / 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(lower) in captured.out


def test_get(feat):
    df = feat.get(pd.Timestamp("2018-11-19"), days=10)
    assert isinstance(df, pd.Series)
    assert df.name == "STD"
    assert df.size == 3
    assert df["PIKK"] == pytest.approx(0.116674542313115 / YEAR_IN_TRADING_DAYS ** 0.5)

    df = feat.get(pd.Timestamp("2018-10-26"), days=10)
    assert df["RTKMP"] == pytest.approx(0.103606599752109 / YEAR_IN_TRADING_DAYS ** 0.5)

    df = feat.get(pd.Timestamp("2018-10-09"), days=10)
    assert df["TATNP"] == pytest.approx(0.221371480598971 / YEAR_IN_TRADING_DAYS ** 0.5)
