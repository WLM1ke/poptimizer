"""Тесты для проверки статуса дивидендов."""
import logging

import pandas as pd
import pytest

from poptimizer.data.views import div_status
from poptimizer.data.views.crop import div
from poptimizer.shared import col


def test_new_div_all(mocker):
    """Проверка типа и структуры результата."""
    fake_raw_df = pd.DataFrame(
        [
            ["AKRN", "2020-01-01", 1],
            ["CHMF", "2020-01-02", 2],
            ["CHMF", "2020-01-02", 3],
            ["AKRN", "2020-01-03", 4],
            ["T-RM", "2020-01-04", None],
        ],
        columns=[col.TICKER, col.DATE, col.DIVIDENDS],
    ).set_index(col.TICKER)

    mocker.patch.object(div_status.bootstrap.VIEWER, "get_df", return_value=fake_raw_df)

    df = div_status._new_div_all()

    rez = pd.DataFrame(
        [
            ["AKRN", "2020-01-01", 1],
            ["AKRN", "2020-01-03", 4],
            ["CHMF", "2020-01-02", 5],
            ["T-RM", "2020-01-04", None],
        ],
        columns=[col.TICKER, col.DATE, col.DIVIDENDS],
    ).set_index(col.TICKER)

    pd.testing.assert_frame_equal(df, rez)


SMART_LAB_DF = pd.DataFrame(
    [
        ["2020-10-01", 1],
        ["2020-10-02", 2],
        ["2021-02-27", None],
        ["2020-10-03", 3],
        ["2020-10-04", 4],
    ],
    columns=[col.DATE, col.DIVIDENDS],
    index=["NKNC", "PLZL", "T-RM", "KZOS", "TTLK"],
)
TTLK_DF = pd.DataFrame([4], columns=["TTLK"], index=["2020-10-04"])
T_DF = pd.DataFrame([6], columns=["T-RM"], index=["2021-02-27"])
KZOS_DF = pd.DataFrame()
PLZL_DF = pd.DataFrame([4], columns=["PLZL"], index=["2020-10-02"])


def test_new_dividends(mocker, caplog):
    """Различные варианты включения и не включения в статус."""
    mocker.patch.object(div_status, "_new_div_all", return_value=SMART_LAB_DF)
    mocker.patch.object(div, "dividends", side_effect=[PLZL_DF, T_DF, KZOS_DF, TTLK_DF])

    with caplog.at_level(logging.INFO):
        assert div_status.new_dividends(("TTLK", "T-RM", "KZOS", "PLZL")) == {"PLZL", "KZOS"}
        assert "ДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ" in caplog.records[0].msg


def test_new_dividends_no_output(mocker, caplog):
    """Не печатается результат, если по запрашиваемым тикерам нет обновления."""
    mocker.patch.object(div_status, "_new_div_all", return_value=SMART_LAB_DF)

    with caplog.at_level(logging.INFO):
        assert not div_status.new_dividends(("GAZP",))
        assert not caplog.records


def test_compare():
    """Сравнение и распечатка результатов."""
    df = div_status._compare(
        pd.DataFrame([1, 2], columns=["a"]),
        pd.DataFrame([1, 3], columns=["b"]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[1, 1, ""], [2, 3, "ERROR"]],
            columns=["a", "b", "STATUS"],
        ),
    )


def test_compare_all_empty():
    """Регрессионный тест на ошибку в сравнении пустых DataFrame."""
    df = div_status._compare(
        pd.DataFrame(columns=[1]),
        pd.DataFrame(columns=[2]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(columns=[1, 2, "STATUS"]),
    )


def test_compare_with_empty():
    """Регрессионный тест на ошибку в сравнении с пустым DataFrame."""
    df = div_status._compare(
        pd.DataFrame([1, 2], columns=[3]),
        pd.DataFrame(columns=[1]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[1, None, "ERROR"], [2, None, "ERROR"]],
            columns=[3, 1, "STATUS"],
            index=[0, 1],
        ),
        check_index_type=False,
    )


def test_dividends_validation():
    """Наличие столбцов со сравнением и данных."""
    df = div_status.dividends_validation("IRGZ")

    assert isinstance(df, pd.DataFrame)
    assert df.columns.tolist()[-3:] == ["MEDIAN", "LOCAL", "STATUS"]
    assert df.loc["2015-06-11", "MEDIAN"] == pytest.approx(0.53)
    assert df.loc["2016-06-18", "LOCAL"] == pytest.approx(0.53)
    assert df.loc["2016-06-18", "STATUS"] == ""
