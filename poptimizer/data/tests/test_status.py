import pandas as pd

from poptimizer.data import status
from poptimizer.store import DATE, TICKER, DIVIDENDS

RESULT = """
ДАННЫЕ ПО ДИВИДЕНДАМ ТРЕБУЮТ ОБНОВЛЕНИЯ 

PIKK

В БАЗУ ДАННЫХ ДИВИДЕНДОВ МОЖНО ДОБАВИТЬ 

ALRS, NLMK
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
