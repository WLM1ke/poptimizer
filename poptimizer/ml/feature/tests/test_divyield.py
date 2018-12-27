import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.config import AFTER_TAX
from poptimizer.ml.feature import divyield


@pytest.fixture(scope="module", name="feat")
def test_divyield_feature():
    return divyield.DivYield(("PHOR", "TATN", "DSKY"), pd.Timestamp("2018-12-12"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_check_bounds_middle(feat, capsys):
    lower, upper = divyield.RANGE
    feat.check_bounds(days=(lower + upper) / 2)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_bounds_lower(feat, capsys):
    lower, upper = divyield.RANGE
    feat.check_bounds(days=int(lower * 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(upper) in captured.out


def test_check_bounds_upper(feat, capsys):
    lower, upper = divyield.RANGE
    feat.check_bounds(days=int(upper / 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(lower) in captured.out


def test_get(feat):
    df = feat.get(pd.Timestamp("2010-01-26"), days=13)

    assert isinstance(df, pd.Series)
    assert df.size == 3
    assert df.isna().all()
    assert df.name == "DivYield"

    df = feat.get(pd.Timestamp("2010-01-26"), days=12)
    assert not df.isna().all()

    df = feat.get(pd.Timestamp("2018-06-25"), days=9)
    assert df["PHOR"] == pytest.approx(AFTER_TAX * 15 / 2303)

    df = feat.get(pd.Timestamp("2018-06-26"), days=9)
    assert df["PHOR"] == pytest.approx(0)

    df = feat.get(pd.Timestamp("2018-06-13"), days=20)
    assert df["PHOR"] == pytest.approx(AFTER_TAX * 15 / 2322)

    df = feat.get(pd.Timestamp("2018-10-12"), days=30)
    assert df["TATN"] == pytest.approx(30.27 * AFTER_TAX / 790)

    df = feat.get(pd.Timestamp("2018-10-11"), days=30)
    assert df["TATN"] == pytest.approx(0)
