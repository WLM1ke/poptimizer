import pandas as pd
import pytest

from poptimizer.config import AFTER_TAX
from poptimizer.ml.feature import dividends
from poptimizer.ml.feature.label import YEAR_IN_TRADING_DAYS


def test_dividends():
    # noinspection PyTypeChecker
    div = dividends.Dividends(("PHOR", "TATN", "DSKY"), pd.Timestamp("2018-12-12"))

    assert not div.is_categorical()
    assert div.get_params_space() == dict(days=YEAR_IN_TRADING_DAYS)

    df = div.get(pd.Timestamp("2010-01-26"), days=13)

    assert isinstance(df, pd.Series)
    assert df.size == 3
    assert df.isna().all()
    assert df.name == "Dividends"

    df = div.get(pd.Timestamp("2010-01-26"), days=12)
    assert not df.isna().all()

    df = div.get(pd.Timestamp("2018-06-25"), days=9)
    assert df["PHOR"] == pytest.approx(AFTER_TAX * 15 / 2303)

    df = div.get(pd.Timestamp("2018-06-26"), days=9)
    assert df["PHOR"] == pytest.approx(0)

    df = div.get(pd.Timestamp("2018-06-13"), days=20)
    assert df["PHOR"] == pytest.approx(AFTER_TAX * 15 / 2322)

    df = div.get(pd.Timestamp("2018-10-12"), days=30)
    assert df["TATN"] == pytest.approx(30.27 * AFTER_TAX / 790)

    df = div.get(pd.Timestamp("2018-10-11"), days=30)
    assert df["TATN"] == pytest.approx(0)
