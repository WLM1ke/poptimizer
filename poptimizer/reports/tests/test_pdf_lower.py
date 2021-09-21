import pytest

from poptimizer.portfolio import PORTFOLIO, portfolio
from poptimizer.reports import pdf_lower

POSITIONS = {
    "AFLT": 0,
    "AKRN": 795,
    "BANEP": 200,
    "CHMF": 0,
    "ENRU": 467_000,
    "GAZP": 0,
    "GMKN": 194,
    "LKOH": 123,
    "LSNGP": 8100,
    "LSRG": 641,
    "MAGN": 0,
    "MFON": 550,
    "MOEX": 0,
    "MRKC": 36000,
    "MRSB": 0,
    "MSRS": 699_000,
    "MSTT": 44350,
    "MTSS": 7490,
    "MVID": 3260,
    "NMTP": 0,
    "PHOR": 0,
    "PMSBP": 17290,
    "RSTIP": 87000,
    "RTKM": 0,
    "RTKMP": 182_600,
    "SNGSP": 23500,
    "TTLK": 0,
    "GOOG-RM": 3,
    "FXMM": 73,
}
CASH = 1_548_264
DATE = "2021-04-19"
TEST_PORTFOLIO = portfolio.Portfolio(date=DATE, cash=CASH, positions=POSITIONS)


def test_drop_small_positions():
    df = pdf_lower.drop_small_positions(TEST_PORTFOLIO)
    index = df.index
    assert len(df) == pdf_lower.MAX_TABLE_ROWS + 1
    assert index[-1] == PORTFOLIO
    assert df[PORTFOLIO] == pytest.approx(TEST_PORTFOLIO.value[PORTFOLIO])
    assert index[0] == "RTKMP"
    assert df.iloc[0] == pytest.approx(TEST_PORTFOLIO.value["RTKMP"])
    assert index[-5] == "MVID"
    assert df.iloc[-5] == pytest.approx(TEST_PORTFOLIO.value["MVID"])
    assert index[-4] == "ETF"
    assert df.iloc[-4] == pytest.approx(TEST_PORTFOLIO.value["FXMM"])
    assert index[-3] == "Foreign"
    assert df.iloc[-3] == pytest.approx(TEST_PORTFOLIO.value["GOOG-RM"])
    assert index[-2] == "Russian"
    assert df.iloc[:-1].sum() == pytest.approx(df[PORTFOLIO])


def test_make_list_of_lists_table():
    list_of_lists = pdf_lower.make_list_of_lists_table(TEST_PORTFOLIO)
    assert len(list_of_lists) == pdf_lower.MAX_TABLE_ROWS + 2
    assert list_of_lists[0] == ["Name", "Value", "Share"]
    assert list_of_lists[-1] == ["PORTFOLIO", "46 434 477", "100.0%"]
    assert list_of_lists[7] == ["MVID", "2 273 850", "4.9%"]
    assert list_of_lists[5] == ["PMSBP", "2 569 294", "5.5%"]
