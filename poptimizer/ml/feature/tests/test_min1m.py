import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer import config
from poptimizer.ml.feature import min1m_old


@pytest.fixture(scope="module", name="feat")
def test_mim1m_feature():
    return min1m_old.Min1m(("MRKY", "PRTK", "UPRO"), pd.Timestamp("2019-02-25"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_check_bounds_middle(feat, capsys):
    lower, upper = config.MIN1M_RANGE
    feat.check_bounds(days=(lower + upper) / 2)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_bounds_lower(feat, capsys):
    lower, upper = config.MIN1M_RANGE
    feat.check_bounds(days=int(lower * 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(upper) in captured.out


def test_check_bounds_upper(feat, capsys):
    lower, upper = config.MIN1M_RANGE
    feat.check_bounds(days=int(upper / 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(lower) in captured.out


def test_get(feat):
    df = feat.get(pd.Timestamp("2019-02-25"), days=7)
    assert isinstance(df, pd.Series)
    assert df.name == "Min1m"
    assert df.size == 3
    assert df["MRKY"] == pytest.approx(-0.0414401923306994)

    df = feat.get(pd.Timestamp("2019-02-25"), days=7)
    assert df["PRTK"] == pytest.approx(-0.0103867061888096)

    df = feat.get(pd.Timestamp("2019-02-25"), days=7)
    assert df["UPRO"] == pytest.approx(-0.021099364024246)
