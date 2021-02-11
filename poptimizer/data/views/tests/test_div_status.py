"""Тесты для проверки статуса дивидендов."""
import pandas as pd
import pytest

from poptimizer.data.views import div_status
from poptimizer.data.views.crop import div
from poptimizer.shared import col


def test_smart_lab_all():
    """Проверка типа и структуры результата."""
    df = div_status._smart_lab_all()

    assert isinstance(df, pd.DataFrame)
    assert df.columns.tolist() == [col.DATE, col.DIVIDENDS]


SMART_LAB_DF = pd.DataFrame(
    [
        ["2020-10-01", 1],
        ["2020-10-02", 2],
        ["2020-10-03", 3],
        ["2020-10-04", 4],
    ],
    columns=[col.DATE, col.DIVIDENDS],
    index=["NKNC", "PLZL", "KZOS", "TTLK"],
)
TTLK_DF = pd.DataFrame([4], columns=["TTLK"], index=["2020-10-04"])
KZOS_DF = pd.DataFrame()
PLZL_DF = pd.DataFrame([4], columns=["PLZL"], index=["2020-10-02"])


def test_new_on_smart_lab(mocker, capsys):
    """Различные варианты включения и не включения в статус."""
    mocker.patch.object(div_status, "_smart_lab_all", return_value=SMART_LAB_DF)
    mocker.patch.object(div, "dividends", side_effect=[PLZL_DF, KZOS_DF, TTLK_DF])

    assert div_status.new_on_smart_lab(("TTLK", "KZOS", "PLZL")) == ["PLZL", "KZOS"]
    captured = capsys.readouterr()
    assert "ДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ" in captured.out


def test_new_on_smart_lab_no_output(mocker, capsys):
    """Не печатается результат, если по запрашиваемым тикерам нет обновления."""
    mocker.patch.object(div_status, "_smart_lab_all", return_value=SMART_LAB_DF)

    assert not div_status.new_on_smart_lab(("GAZP",))
    captured = capsys.readouterr()
    assert not captured.out


def test_compare(capsys):
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


def test_compare_all_empty(capsys):
    """Регрессионный тест на ошибку в сравнении пустых DataFrame."""
    df = div_status._compare(
        pd.DataFrame(columns=[1]),
        pd.DataFrame(columns=[2]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(columns=[1, 2, "STATUS"]),
    )


def test_compare_with_empty(capsys):
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
    assert df.columns.tolist() == ["Dohod", "Conomy", "BCS", "MEDIAN", "LOCAL", "STATUS"]
    assert df.loc["2015-06-11", "MEDIAN"] == pytest.approx(0.53)
    assert df.loc["2016-06-18", "LOCAL"] == pytest.approx(0.53)
    assert df.loc["2016-06-18", "STATUS"] == ""
