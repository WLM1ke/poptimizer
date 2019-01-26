import numpy as np
import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer import config
from poptimizer.ml.feature import mom1m


@pytest.fixture(scope="module", name="feat")
def test_mom1m_feature():
    return mom1m.Mom1m(("GCHE", "LSRG", "PMSBP"), pd.Timestamp("2019-01-25"))


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_check_bounds_middle(feat, capsys):
    lower, upper = config.MOM1M_RANGE
    feat.check_bounds(days=(lower + upper) / 2)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_bounds_lower(feat, capsys):
    lower, upper = config.MOM1M_RANGE
    feat.check_bounds(days=int(lower * 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(upper) in captured.out


def test_check_bounds_upper(feat, capsys):
    lower, upper = config.MOM1M_RANGE
    feat.check_bounds(days=int(upper / 1.05))
    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out
    assert str(lower) in captured.out


def test_get(feat):
    df = feat.get(pd.Timestamp("2018-12-25"), days=7)
    assert isinstance(df, pd.Series)
    assert df.name == "Mom1m"
    assert df.size == 3
    assert df["GCHE"] == pytest.approx(0.0)

    df = feat.get(pd.Timestamp("2018-12-25"), days=7)
    assert df["LSRG"] == pytest.approx(np.log(598.4 / 636.4) / 7)

    df = feat.get(pd.Timestamp("2018-12-25"), days=7)
    assert df["PMSBP"] == pytest.approx(np.log(72.7 / 73.4) / 7)
