"""Тесты для проверки статуса дивидендов."""
import pandas as pd

from poptimizer.data.ports import col
from poptimizer.data.views import div_status
from poptimizer.data.views.crop import div


def test_smart_lab():
    """Проверка типа и структуры результата."""
    df = div_status.smart_lab()

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
    mocker.patch.object(div_status, "smart_lab", return_value=SMART_LAB_DF)
    mocker.patch.object(div, "dividends", side_effect=[PLZL_DF, KZOS_DF, TTLK_DF])

    assert div_status.new_on_smart_lab(("TTLK", "KZOS", "PLZL")) == ["PLZL", "KZOS"]
    captured = capsys.readouterr()
    assert "ДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ" in captured.out


def test_new_on_smart_lab_no_output(mocker, capsys):
    """Не печатается результат при пустом статусе."""
    mocker.patch.object(div_status, "smart_lab", return_value=SMART_LAB_DF)

    assert not div_status.new_on_smart_lab(())
    captured = capsys.readouterr()
    assert not captured.out


def test_compare(capsys):
    """Сравнение и распечатка результатов."""
    df = div_status._compare(
        "test_name",
        pd.DataFrame([1, 2]),
        pd.DataFrame([1, 3]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[1, 1, ""], [2, 3, "ERROR"]],
            columns=["LOCAL", "SOURCE", "STATUS"],
        ),
    )
    captured = capsys.readouterr()
    assert "test_name" in captured.out


def test_compare_all_empty(capsys):
    """Регрессионный тест на ошибку в сравнении пустых DataFrame."""
    df = div_status._compare(
        "all_empty",
        pd.DataFrame(columns=[1]),
        pd.DataFrame(columns=[2]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(columns=["LOCAL", "SOURCE", "STATUS"]),
    )
    captured = capsys.readouterr()
    assert "all_empty" in captured.out


def test_compare_with_empty(capsys):
    """Регрессионный тест на ошибку в сравнении с пустым DataFrame."""
    df = div_status._compare(
        "with_empty",
        pd.DataFrame([1, 2]),
        pd.DataFrame(columns=[1]),
    )

    pd.testing.assert_frame_equal(
        df,
        pd.DataFrame(
            [[1, None, "ERROR"], [2, None, "ERROR"]],
            columns=["LOCAL", "SOURCE", "STATUS"],
            index=[0, 1],
        ),
        check_index_type=False,
    )
    captured = capsys.readouterr()
    assert "with_empty" in captured.out


def test_dividends_validation(mocker):
    """Проверка количества запросов необходимой информации."""
    fake_dividends = mocker.patch.object(div, "dividends")
    fake_compare = mocker.patch.object(div_status, "_compare")
    fake_sources = [
        mocker.patch.object(div, "dohod"),
        mocker.patch.object(div, "conomy"),
        mocker.patch.object(div, "bcs"),
        mocker.patch.object(div_status, "smart_lab"),
    ]

    div_status.dividends_validation("TEST")

    assert fake_dividends.call_count == 1
    assert fake_compare.call_count == len(fake_sources)

    for source in fake_sources:
        assert source.call_count == 1
