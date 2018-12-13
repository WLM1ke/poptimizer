import numpy as np
import pandas as pd
import pytest

from poptimizer.config import AFTER_TAX
from poptimizer.data import moex, log_total_returns

# noinspection PyProtectedMember
from poptimizer.data.dividends import t2_shift, dividends_all


def test_dividends_all():
    div = dividends_all(("CHMF", "GMKN"))

    assert isinstance(div, pd.DataFrame)
    assert div.shape[0] >= 41
    assert list(div.columns) == ["CHMF", "GMKN"]

    assert div.index[0] == pd.Timestamp("2010-05-21")
    assert div.index[-1] >= pd.Timestamp("2018-12-04")

    assert div.loc["2018-06-19", "CHMF"] == pytest.approx((38.32 + 27.72) * AFTER_TAX)
    assert div.loc["2017-12-05", "CHMF"] == pytest.approx(35.61 * AFTER_TAX)
    assert div.loc["2010-11-12", "CHMF"] == pytest.approx(4.29 * AFTER_TAX)
    assert div.loc["2011-05-22", "CHMF"] == pytest.approx((2.42 + 3.9) * AFTER_TAX)

    assert div.loc["2018-07-17", "GMKN"] == pytest.approx(607.98 * AFTER_TAX)
    assert div.loc["2017-10-19", "GMKN"] == pytest.approx(224.2 * AFTER_TAX)
    assert div.loc["2010-05-21", "GMKN"] == pytest.approx(210 * AFTER_TAX)
    assert div.loc["2011-05-16", "GMKN"] == pytest.approx(180 * AFTER_TAX)

    assert div.loc["2018-06-19", "GMKN"] == pytest.approx(0)
    assert div.loc["2018-07-17", "CHMF"] == pytest.approx(0)


def test_t2_shift():
    index = moex.prices(("NLMK", "GMKN"), pd.Timestamp("2018-10-08")).index
    assert pd.Timestamp("2018-05-14") == t2_shift(pd.Timestamp("2018-05-15"), index)
    assert pd.Timestamp("2018-07-05") == t2_shift(pd.Timestamp("2018-07-08"), index)
    assert pd.Timestamp("2018-09-28") == t2_shift(pd.Timestamp("2018-10-01"), index)
    assert pd.Timestamp("2018-10-09") == t2_shift(pd.Timestamp("2018-10-10"), index)
    assert pd.Timestamp("2018-10-11") == t2_shift(pd.Timestamp("2018-10-12"), index)
    assert pd.Timestamp("2018-10-11") == t2_shift(pd.Timestamp("2018-10-13"), index)
    assert pd.Timestamp("2018-10-11") == t2_shift(pd.Timestamp("2018-10-14"), index)
    assert pd.Timestamp("2018-10-12") == t2_shift(pd.Timestamp("2018-10-15"), index)
    assert pd.Timestamp("2018-10-17") == t2_shift(pd.Timestamp("2018-10-18"), index)


def test_log_total_returns():
    data = log_total_returns(("GMKN", "RTKMP", "MTSS"), pd.Timestamp("2018-10-17"))

    assert isinstance(data, pd.DataFrame)
    assert list(data.columns) == ["GMKN", "RTKMP", "MTSS"]

    assert data.index[0] == pd.Timestamp("2003-10-02")
    assert data.index[-1] == pd.Timestamp("2018-10-17")

    assert data.loc["2018-10-08", "MTSS"] == pytest.approx(
        np.log(((269.9 + 2.6 * AFTER_TAX) / 275.1))
    )
    assert data.loc["2018-10-09", "MTSS"] == pytest.approx(np.log(((264 + 0) / 269.9)))

    assert data.loc["2018-10-01", "GMKN"] == pytest.approx(
        np.log(((11307 + 0) / 11388))
    )
    assert data.loc["2018-09-28", "GMKN"] == pytest.approx(
        np.log(((11388 + 776.02 * AFTER_TAX) / 11830))
    )

    assert data.loc["2018-07-05", "RTKMP"] == pytest.approx(
        np.log(((62.53 + 5.045825249373 * AFTER_TAX) / 66))
    )
    assert data.loc["2018-07-06", "RTKMP"] == pytest.approx(np.log(((62 + 0) / 62.53)))
