import pandas as pd
import pytest

from poptimizer.data import cpi


def test_monthly_cpi():
    df = cpi.monthly_cpi(pd.Timestamp("2018-12-23"))
    assert isinstance(df, pd.Series)
    assert df.name == "CPI"
    assert df.index.is_monotonic_increasing
    assert df.index.is_unique
    assert len(df) == (2018 - 1991) * 12 + 11
    assert df.index[0] == pd.Timestamp("1991-01-31")
    assert df.index[-1] == pd.Timestamp("2018-11-30")
    assert df["2018-11-30"] == pytest.approx(1.005)
    assert df["2018-06-30"] == pytest.approx(1.0049)
    assert df["2017-07-31"] == pytest.approx(1.0007)
    assert df["2017-08-31"] == pytest.approx(0.9946)
