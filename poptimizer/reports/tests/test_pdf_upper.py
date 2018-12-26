from pathlib import Path

import pandas as pd
import pytest

from poptimizer.reports import pdf_upper_block


@pytest.fixture(name="df")
def read_test_df():
    return pd.read_excel(
        Path(__file__).parent / "data" / "test.xlsx",
        sheet_name="Data",
        header=0,
        index_col=0,
        converters={"Date": pd.to_datetime},
    )[-63:-2]


def test_get_last_values(df):
    df = pdf_upper_block.get_last_values(df)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["WLMike", "Igor", "Portfolio"]
    assert list(df.index) == ["2018-01-19", "2018-02-19"]
    assert df.loc["2018-02-19", "Portfolio"] == pytest.approx(396004.8544)
    assert df.loc["2018-01-19", "Igor"] == pytest.approx(10194.7850236232)


def test_get_investors_names(df):
    df = pdf_upper_block.get_investors_names(df)
    assert isinstance(df, pd.Index)
    assert list(df) == ["WLMike", "Igor"]


def test_get_inflows(df):
    df = pdf_upper_block.get_inflows(df)
    assert isinstance(df, pd.Series)
    assert list(df.index) == ["WLMike", "Igor", "Portfolio"]
    assert df["Portfolio"] == pytest.approx(1091.60460000001)
    assert df["WLMike"] == pytest.approx(1091.60460000001)


def test_make_flow_df(df):
    df = pdf_upper_block.make_flow_df(df)
    assert isinstance(df, pd.DataFrame)
    assert df.shape == (7, 3)
    assert df.loc["2018-01-19", "WLMike"] == pytest.approx(384887.052476377)
    assert df.iat[1, 1] == pytest.approx(0.0258042361251882)
    assert df.loc["Pre Inflow", "Portfolio"] == pytest.approx(394913.2498)
    assert df.iat[3, 0] == pytest.approx(0.974195763874812)
    assert df.loc["Inflow", "WLMike"] == pytest.approx(1091.60460000001)
    assert df.loc["2018-02-19", "Igor"] == pytest.approx(10190.4347468046)
    assert df.iat[-1, -1] == pytest.approx(1)


def test_make_list_of_lists_flow(df):
    list_of_lists = pdf_upper_block.make_list_of_lists_flow(df)
    assert len(list_of_lists) == 8
    assert list_of_lists[0] == ["", "WLMike", "Igor", "Portfolio"]
    assert list_of_lists[1] == ["2018-01-19", "384 887", "10 195", "395 082"]
    assert list_of_lists[2] == ["%", "97.42%", "2.58%", "100.00%"]
    assert list_of_lists[3] == ["Pre Inflow", "384 723", "10 190", "394 913"]
    assert list_of_lists[4] == ["%", "97.42%", "2.58%", "100.00%"]
    assert list_of_lists[5] == ["Inflow", "1 092", "0", "1 092"]
    assert list_of_lists[6] == ["2018-02-19", "385 814", "10 190", "396 005"]
    assert list_of_lists[7] == ["%", "97.43%", "2.57%", "100.00%"]


def test_make_12m_dividends_df(df):
    df = pdf_upper_block.make_12m_dividends_df(df)
    assert df.iloc[-1] == pytest.approx(28948.1439)
    assert df.iloc[-27] == pytest.approx(11919.4743)
    assert df.iloc[-29] == pytest.approx(11609.3758)


def test_make_list_of_lists_dividends(df):
    list_of_lists = pdf_upper_block.make_list_of_lists_dividends(df)
    assert len(list_of_lists) == 7
    assert list_of_lists[0] == ["Period", "Dividends"]
    assert list_of_lists[1] == ["2018-01-19 - 2018-02-19", "999"]
    assert list_of_lists[2] == ["2017-02-17 - 2018-02-19", "28 948"]
    assert list_of_lists[-1] == ["2013-02-19 - 2014-02-19", "3 865"]
