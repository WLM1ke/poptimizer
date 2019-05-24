import pandas as pd

from poptimizer.data import status
from poptimizer.store import DATE, TICKER, DIVIDENDS

RESULT = """
ДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ 

PIKK
"""


def test_smart_lab():
    df = status.smart_lab()
    assert isinstance(df, pd.DataFrame)
    assert df.index.name == DATE
    assert list(df.columns) == [TICKER, DIVIDENDS]
    assert df.dtypes[DIVIDENDS] == float


def test_smart_lab_status(monkeypatch, capsys):
    data = {
        "TICKER": ["PIKK", "ALRS", "CHMF", "MTSS", "NLMK"],
        "DIVIDENDS": [22.0, 5.930, 45.940, 2.600, 5.0],
    }
    index = [
        pd.Timestamp("2018-09-04"),
        pd.Timestamp("2018-10-16"),
        pd.Timestamp("2018-09-25"),
        pd.Timestamp("2018-10-09"),
        pd.Timestamp("2018-10-12"),
    ]
    fake_df = pd.DataFrame(data=data, index=index)
    monkeypatch.setattr(status, "smart_lab", lambda: fake_df)
    status.smart_lab_status(tuple(["PIKK", "CHMF"]))
    captured = capsys.readouterr()
    assert RESULT == captured.out


def test_smart_lab_no_status(monkeypatch, capsys):
    data = {"TICKER": ["CHMF", "MTSS"], "DIVIDENDS": [45.940, 2.600]}
    index = [pd.Timestamp("2018-09-25"), pd.Timestamp("2018-10-09")]
    fake_df = pd.DataFrame(data=data, index=index)
    monkeypatch.setattr(status, "smart_lab", lambda: fake_df)
    status.smart_lab_status(tuple(["PIKK", "CHMF"]))
    captured = capsys.readouterr()
    assert "" == captured.out


def test_dividends_status(capsys):
    result = status.dividends_status("ENRU")
    captured = capsys.readouterr()

    assert isinstance(result, list)
    assert len(result) == 3

    assert result[0].shape >= (4, 3)
    assert result[0].iloc[0, 2] == ""
    assert result[0].iloc[3, 2] == "ERROR"
    assert "СРАВНЕНИЕ ОСНОВНЫХ ДАННЫХ С Dohod" in captured.out

    assert result[1].shape >= (4, 3)
    assert result[1].iloc[2, 2] == ""
    assert result[1].iloc[1, 2] == "ERROR"
    assert "СРАВНЕНИЕ ОСНОВНЫХ ДАННЫХ С Conomy" in captured.out

    assert "СРАВНЕНИЕ ОСНОВНЫХ ДАННЫХ С SmartLab" in captured.out


def test_dividends_status_no_web_data():
    """Обработка тикеров, которых нет на dohod.ru"""
    result = status.dividends_status("VRSB")

    assert isinstance(result[0], Exception)
