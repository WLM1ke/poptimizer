from pathlib import Path
from shutil import copyfile

import pandas as pd
import pytest

from poptimizer import config
from poptimizer.reports import simple


@pytest.fixture(scope="module", name="report_path")
def make_fake_report_data(tmpdir_factory):
    temp_dir = tmpdir_factory.mktemp("income_report")
    copyfile(Path(__file__).parent / "data" / "test.xlsx", temp_dir / "test.xlsx")
    return temp_dir


@pytest.fixture(autouse=True)
def fake_report_path(report_path, monkeypatch):
    monkeypatch.setattr(config, "REPORTS_PATH", report_path)
    yield


def test_get_investor_data():
    df = simple.get_investor_data("test", "Igor")
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["Inflow", "Value", "Dividends"]
    assert df.loc["2018-01-19", "Inflow"] == pytest.approx(-6300)
    assert df.loc["2018-04-19", "Value"] == pytest.approx(10094.11382)
    assert df.loc["2017-06-19", "Dividends"] == pytest.approx(12.18696831)


def test_constant_prices_data():
    df = simple.constant_prices_data("test", "Igor", 12)
    assert df.shape == (13, 3)
    assert df.loc["2018-01-19", "Inflow"] == pytest.approx(-6351.166136)
    assert df.loc["2017-07-19", "Value"] == pytest.approx(12875.75482)
    assert df.loc["2017-06-19", "Dividends"] == pytest.approx(12.38775237)


def test_rescale_and_format():
    assert simple.rescale_and_format(1234567, 1) == "1 235 000"
    assert simple.rescale_and_format(1234567, 10) == "  123 000"


def test_income_report(capsys):
    simple.income("test", "WLMike", 12)
    captured_string = capsys.readouterr().out
    assert "WLMike" in captured_string
    assert "1Y: Дивиденды =    28 000, Доход =    85 000" in captured_string
    assert "1M: Дивиденды =     2 000, Доход =     7 000" in captured_string
    assert "1W: Дивиденды =     1 000, Доход =     2 000" in captured_string
