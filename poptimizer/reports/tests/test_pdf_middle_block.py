from pathlib import Path

import pandas as pd
import pytest

from poptimizer.reports import pdf_middle_block


@pytest.fixture(name="df")
def read_test_df():
    return pd.read_excel(
        Path(__file__).parent / "data" / "test.xlsx",
        sheet_name="Data",
        header=0,
        index_col=0,
        converters={"Date": pd.to_datetime},
    )[-61:]


def test_portfolio_cum_return(df):
    df = pdf_middle_block.portfolio_cum_return(df)
    assert df.shape == (61,)
    assert df[0] == 1
    assert df["18-12-2015"] == pytest.approx(1.8971256293939)
    assert df[-1] == pytest.approx(3.45575233973774)


def test_index_cum_return(df):
    df = pdf_middle_block.index_cum_return(df)
    assert df.shape == (61,)
    assert df[0] == 1
    assert df["18-12-2015"] == pytest.approx(1.44858482937086)
    assert df[-1] == pytest.approx(2.06371017305515)


def test_make_list_of_lists_table(df):
    list_of_lists = pdf_middle_block.make_list_of_lists_table(df)
    assert len(list_of_lists) == 7
    assert list_of_lists[0] == ["Period", "Portfolio", "MOEX"]
    assert list_of_lists[-1] == ["5Y", " 245.6%", " 106.4%"]
    assert list_of_lists[1] == ["1M", "-2.9%", "-2.2%"]
