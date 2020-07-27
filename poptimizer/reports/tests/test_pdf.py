from pathlib import Path
from shutil import copyfile

import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.portfolio import portfolio, PORTFOLIO
from poptimizer.reports import pdf

POSITIONS = dict(MSTT=440, RTKMP=1500, MTSS=140, AKRN=12, MSRS=57000, UPRO=13000, PMSBP=480)
CASH = 32412
DATE_OLD = "2018-04-30"
DATE_NEW = "2018-05-07"


@pytest.fixture(scope="module", name="report_path")
def make_fake_path(tmpdir_factory):
    return Path(tmpdir_factory.mktemp("test_pdf"))


@pytest.fixture(autouse=True)
def fake_report_path(report_path, monkeypatch):
    copyfile(Path(__file__).parent / "data" / "test.xlsx", report_path / "test.xlsx")
    monkeypatch.setattr(pdf, "REPORTS_PATH", report_path)
    monkeypatch.setattr(pdf, "PDF_PATH", report_path / "pdf")
    yield


def test_read_data():
    df = pdf.read_data("test")
    assert df.shape == (240, 6)
    assert df.index[0] == pd.Timestamp("2008-02-21")
    assert df.index[-1] == pd.Timestamp("2018-04-19")
    assert df.loc["2018-04-19", "Value"] == pytest.approx(392_261.78)


def test_update_data():
    port = portfolio.Portfolio(date=DATE_NEW, cash=CASH, positions=POSITIONS)
    pdf.update_data("test", port.date, port.value[PORTFOLIO], dict(WLMike=1000, Igor=-2000), 1234)
    df = pdf.read_data("test")
    assert df.shape == (241, 6)
    assert df.index[-1] == pd.Timestamp("2018-05-07")
    assert df.loc["2018-05-07", "WLMike"] == pytest.approx(1000)
    assert df.loc["2018-05-07", "Igor"] == pytest.approx(-2000)
    assert df.loc["2018-05-07", "Value_WLMike"] == pytest.approx(384_396.431_074_62)
    assert df.loc["2018-05-07", "Value_Igor"] == pytest.approx(8126.568_925_380_33)
    assert df.loc["2018-05-07", "Value"] == pytest.approx(392_523)
    assert df.loc["2018-05-07", "Dividends"] == pytest.approx(1234)


def test_update_data_bad_date():
    port = portfolio.Portfolio(date=DATE_OLD, cash=CASH, positions=POSITIONS)
    with pytest.raises(POptimizerError) as error:
        pdf.update_data(
            "test", port.date, port.value[PORTFOLIO], dict(WLMike=1000, Igor=-2000), 1234,
        )
    assert str(error.value) == "В этом месяце данные уже вносились в отчет"


def test_update_data_bad_investor_name():
    port = portfolio.Portfolio(date=DATE_NEW, cash=CASH, positions=POSITIONS)
    with pytest.raises(POptimizerError) as error:
        pdf.update_data("test", port.date, port.value[PORTFOLIO], dict(WLMike1=1000), 1234)
    assert str(error.value) == "Неверное имя инвестора - WLMike1"


def test_report_files_path(report_path):
    pdf_path, xlsx_path = pdf.make_report_files_path("test", pd.Timestamp(DATE_OLD))
    assert pdf_path.parent.exists()
    assert pdf_path == report_path / "pdf" / "test 2018-04-30" / "2018-04-30.pdf"
    assert xlsx_path.parent.exists()
    assert xlsx_path == report_path / "pdf" / "test 2018-04-30" / "2018-04-30.xlsx"


def test_report_new_month():
    port = portfolio.Portfolio(date=DATE_NEW, cash=CASH, positions=POSITIONS)
    pdf.report("test", port, dict(WLMike=10000, Igor=-5000), 4321)
    df = pdf.read_data("test")
    date = port.date
    assert df.index[-1] == date
    assert df.loc[date, "WLMike"] == pytest.approx(10000)
    assert df.loc[date, "Igor"] == pytest.approx(-5000)
    assert df.loc[date, "Value_WLMike"] == pytest.approx(387_550.829_708_377)
    assert df.loc[date, "Value_Igor"] == pytest.approx(4972.170_292)
    assert df.loc[date, "Value"] == pytest.approx(392_523)
    assert df.loc[date, "Dividends"] == pytest.approx(4321)


def test_report_no_dividends():
    port = portfolio.Portfolio(date=DATE_NEW, cash=CASH, positions=POSITIONS)
    pdf.report("test", port, dict(WLMike=10000, Igor=-5000), 0)
    df = pdf.read_data("test")
    date = port.date
    assert df.index[-1] == date
    assert df.loc[date, "WLMike"] == pytest.approx(10000)
    assert df.loc[date, "Igor"] == pytest.approx(-5000)
    assert df.loc[date, "Value_WLMike"] == pytest.approx(387_550.829_708_377)
    assert df.loc[date, "Value_Igor"] == pytest.approx(4972.170_292)
    assert df.loc[date, "Value"] == pytest.approx(392_523)
    assert pd.isnull(df.loc[date, "Dividends"])
