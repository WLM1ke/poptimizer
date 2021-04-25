import pytest

from poptimizer.portfolio import PORTFOLIO, portfolio
from poptimizer.reports import pdf_lower
from poptimizer.reports.pdf_lower import OTHER

POSITIONS = dict(
    AFLT=0,
    AKRN=795,
    BANEP=200,
    CHMF=0,
    ENRU=467_000,
    GAZP=0,
    GMKN=194,
    KBTK=90,
    LKOH=123,
    LSNGP=8100,
    LSRG=641,
    MAGN=0,
    MFON=550,
    MOEX=0,
    MRKC=36000,
    MRSB=0,
    MSRS=699_000,
    MSTT=44350,
    MTSS=7490,
    MVID=3260,
    NMTP=0,
    PHOR=0,
    PMSBP=17290,
    RSTIP=87000,
    RTKM=0,
    RTKMP=182_600,
    SNGSP=23500,
    TTLK=0,
    UPRO=1_267_000,
    VSMO=73,
)
CASH = 1_548_264
DATE = "2018-04-19"
TEST_PORTFOLIO = portfolio.Portfolio(date=DATE, cash=CASH, positions=POSITIONS)


def test_drop_small_positions():
    df = pdf_lower.drop_small_positions(TEST_PORTFOLIO)
    index = df.index
    assert len(df) == pdf_lower.MAX_TABLE_ROWS + 2
    assert index[-1] == PORTFOLIO
    assert df[PORTFOLIO] == pytest.approx(38525478)
    assert index[-2] == OTHER
    assert df[OTHER] == pytest.approx(5822654)
    assert index[0] == "RTKMP"
    assert df.iloc[0] == pytest.approx(11_167_816)
    assert index[-3] == "MVID"
    assert df.iloc[-3] == pytest.approx(1_310_520)


def test_make_list_of_lists_table():
    list_of_lists = pdf_lower.make_list_of_lists_table(TEST_PORTFOLIO)
    assert len(list_of_lists) == pdf_lower.MAX_TABLE_ROWS + 3
    assert list_of_lists[0] == ["Name", "Value", "Share"]
    assert list_of_lists[-1] == ["PORTFOLIO", "38 525 478", "100.0%"]
    assert list_of_lists[7] == ["CASH", "1 548 264", "4.0%"]
    assert list_of_lists[5] == ["MTSS", "2 168 355", "5.6%"]
