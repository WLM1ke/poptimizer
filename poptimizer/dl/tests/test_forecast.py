import numpy as np
import pandas as pd

from poptimizer.dl import forecast, ledoit_wolf

TICKERS = ("CHEP", "MTSS", "PLZL")
DATE = pd.Timestamp("2020-05-19")
HISTORY_DAYS = 30

MEAN = pd.Series([0.1, 0.2, 0.3], index=list(TICKERS))
STD = pd.Series([0.15, 0.25, 0.35], index=list(TICKERS))


def test_forecast():
    data = forecast.Forecast(
        tickers=TICKERS,
        date=DATE,
        history_days=30,
        mean=MEAN,
        std=STD,
        risk_aversion=1.1,
        error_tolerance=0.2,
    )

    assert data.cov.shape == (3, 3)
    assert np.allclose(np.diag(data.cov), STD.values ** 2)
    assert np.allclose(data.cov, data.cov.transpose())

    cor, *_ = ledoit_wolf.ledoit_wolf_cor(TICKERS, DATE, HISTORY_DAYS)
    assert np.allclose(cor, data.cov / STD.values.reshape(1, -1) / STD.values.reshape(-1, 1))

    assert np.allclose(data.cor, 0.1579351254545552)
    assert np.allclose(data.shrinkage, 0.7074063618114778)
