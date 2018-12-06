import pandas as pd

from poptimizer.storage import datum


def test_data():
    time0 = pd.Timestamp.now(datum.MOEX_TZ)
    data = datum.Datum(42)
    time1 = pd.Timestamp.now(datum.MOEX_TZ)
    assert data.value == 42
    assert time0 <= data.last_update <= time1
    data.value = 24
    time2 = pd.Timestamp.now(datum.MOEX_TZ)
    assert data.value == 24
    assert time1 <= data.last_update <= time2
