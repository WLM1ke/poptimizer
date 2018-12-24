import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.ml.feature import mom12m
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


@pytest.fixture(scope="module", name="feat")
def test_srd_feature():
    # noinspection PyTypeChecker
    return mom12m.Mom12m(("VSMO", "BANEP", "ENRU"), pd.Timestamp("2018-12-07"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_check_bounds_middle(feat, capsys):
    lower, upper = mom12m.RANGE
    feat.check_bounds(days=(lower + upper) / 2)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_bounds_lower(feat, capsys):
    lower, upper = mom12m.RANGE
    feat.check_bounds(days=int(lower * 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(upper) in captured.out


def test_check_bounds_upper(feat, capsys):
    lower, upper = mom12m.RANGE
    feat.check_bounds(days=int(upper / 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(lower) in captured.out


def test_get(feat):
    df = feat.get(pd.Timestamp("2018-10-15"), days=53)
    assert isinstance(df, pd.Series)
    assert df.name == "Mom12m"
    assert df.size == 3
    assert df["VSMO"] == pytest.approx(-0.010316797368955 / YEAR_IN_TRADING_DAYS)

    df = feat.get(pd.Timestamp("2018-10-29"), days=53)
    assert df["BANEP"] == pytest.approx(0.413477629952859 / YEAR_IN_TRADING_DAYS)

    df = feat.get(pd.Timestamp("2018-10-02"), days=53)
    assert df["ENRU"] == pytest.approx(-0.150704229512325 / YEAR_IN_TRADING_DAYS)
