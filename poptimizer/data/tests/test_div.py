import numpy as np
import pandas as pd
import pytest

from poptimizer.config import AFTER_TAX
from poptimizer.data import moex, div


@pytest.fixture(scope="function", autouse=True)
def set_stats_start(monkeypatch):
    monkeypatch.setattr(div, "STATS_START", pd.Timestamp("2010-06-15"))
    yield


def test_dividends_all():
    dividends = div.dividends_all(("CHMF", "GMKN"))

    assert isinstance(dividends, pd.DataFrame)
    assert dividends.shape[0] >= 41
    assert list(dividends.columns) == ["CHMF", "GMKN"]

    assert dividends.index[0] == pd.Timestamp("2010-05-21")
    assert dividends.index[-1] >= pd.Timestamp("2018-12-04")

    assert dividends.loc["2018-06-19", "CHMF"] == pytest.approx(
        (38.32 + 27.72) * AFTER_TAX
    )
    assert dividends.loc["2017-12-05", "CHMF"] == pytest.approx(35.61 * AFTER_TAX)
    assert dividends.loc["2010-11-12", "CHMF"] == pytest.approx(4.29 * AFTER_TAX)
    assert dividends.loc["2011-05-22", "CHMF"] == pytest.approx(
        (2.42 + 3.9) * AFTER_TAX
    )

    assert dividends.loc["2018-07-17", "GMKN"] == pytest.approx(607.98 * AFTER_TAX)
    assert dividends.loc["2017-10-19", "GMKN"] == pytest.approx(224.2 * AFTER_TAX)
    assert dividends.loc["2010-05-21", "GMKN"] == pytest.approx(210 * AFTER_TAX)
    assert dividends.loc["2011-05-16", "GMKN"] == pytest.approx(180 * AFTER_TAX)

    assert dividends.loc["2018-06-19", "GMKN"] == pytest.approx(0)
    assert dividends.loc["2018-07-17", "CHMF"] == pytest.approx(0)


def test_dividends_all_one_ticker():
    dividends = div.dividends_all(("CHMF",))

    assert isinstance(dividends, pd.DataFrame)
    assert dividends.shape[0] >= 28
    assert list(dividends.columns) == ["CHMF"]

    assert dividends.index[0] == pd.Timestamp("2010-11-12")
    assert dividends.index[-1] >= pd.Timestamp("2019-09-17")

    assert dividends.loc["2018-06-19", "CHMF"] == pytest.approx(
        (38.32 + 27.72) * AFTER_TAX
    )
    assert dividends.loc["2017-12-05", "CHMF"] == pytest.approx(35.61 * AFTER_TAX)
    assert dividends.loc["2010-11-12", "CHMF"] == pytest.approx(4.29 * AFTER_TAX)
    assert dividends.loc["2011-05-22", "CHMF"] == pytest.approx(
        (2.42 + 3.9) * AFTER_TAX
    )


def test_t2_shift():
    index = moex.prices(("NLMK", "GMKN"), pd.Timestamp("2018-10-08")).index
    assert pd.Timestamp("2018-05-14") == div.t2_shift(pd.Timestamp("2018-05-15"), index)
    assert pd.Timestamp("2018-07-05") == div.t2_shift(pd.Timestamp("2018-07-08"), index)
    assert pd.Timestamp("2018-09-28") == div.t2_shift(pd.Timestamp("2018-10-01"), index)
    assert pd.Timestamp("2018-10-09") == div.t2_shift(pd.Timestamp("2018-10-10"), index)
    assert pd.Timestamp("2018-10-11") == div.t2_shift(pd.Timestamp("2018-10-12"), index)
    assert pd.Timestamp("2018-10-11") == div.t2_shift(pd.Timestamp("2018-10-13"), index)
    assert pd.Timestamp("2018-10-11") == div.t2_shift(pd.Timestamp("2018-10-14"), index)
    assert pd.Timestamp("2018-10-12") == div.t2_shift(pd.Timestamp("2018-10-15"), index)
    assert pd.Timestamp("2018-10-17") == div.t2_shift(pd.Timestamp("2018-10-18"), index)


def test_div_ex_date_prices():
    rez = div.div_ex_date_prices(("KZOS", "LSRG", "LKOH"), pd.Timestamp("2019-09-13"))
    assert isinstance(rez, tuple)
    assert len(rez) == 2
    for df in rez:
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["KZOS", "LSRG", "LKOH"]
        assert df.index[0] == pd.Timestamp("2010-06-15")
        assert df.index[-1] == pd.Timestamp("2019-09-13")

    assert rez[0].loc["2011-03-03", "KZOS"] == pytest.approx(0.1752 * AFTER_TAX)
    assert rez[0].loc["2011-03-04", "KZOS"] == 0

    assert rez[0].loc["2012-02-16", "LSRG"] == pytest.approx(20 * AFTER_TAX)
    assert rez[0].loc["2012-02-17", "LSRG"] == 0

    assert rez[0].loc["2012-05-10", "LKOH"] == pytest.approx(75 * AFTER_TAX)
    assert rez[0].loc["2012-05-11", "LKOH"] == 0

    assert rez[1].loc["2019-09-13", "LSRG"] == pytest.approx(754)

    assert rez[1].loc["2019-09-12", "KZOS"] == pytest.approx(96.1)

    assert rez[1].loc["2019-09-11", "LKOH"] == pytest.approx(5540)


def test_log_total_returns():
    data = div.log_total_returns(("GMKN", "RTKMP", "MTSS"), pd.Timestamp("2018-10-17"))

    assert isinstance(data, pd.DataFrame)
    assert list(data.columns) == ["GMKN", "RTKMP", "MTSS"]

    assert data.index[0] == pd.Timestamp("2010-06-16")
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
