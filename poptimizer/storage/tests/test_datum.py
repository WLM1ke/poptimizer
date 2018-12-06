import pandas as pd

import poptimizer.config
import poptimizer.storage.utils
from poptimizer.storage import utils


def test_data():
    time0 = pd.Timestamp.now(poptimizer.storage.utils.MOEX_TZ)
    data = utils.Datum(42)
    time1 = pd.Timestamp.now(poptimizer.storage.utils.MOEX_TZ)
    assert data.value == 42
    assert time0 <= data.timestamp <= time1
    data.value = 24
    time2 = pd.Timestamp.now(poptimizer.storage.utils.MOEX_TZ)
    assert data.value == 24
    assert time1 <= data.timestamp <= time2
