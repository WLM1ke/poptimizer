"""Тесты для подготовки прогнозов."""
import pandas as pd

from poptimizer.evolve import forecaster


def test_forecasts_is_not_none():
    """При наличии прогнозов в конструкторе не создаются новые."""
    tickers = ("AKRN", "GAZP")
    date = pd.Timestamp("2021-09-01")

    forecasts = forecaster.Forecasts(tickers, date, [tickers, date])

    assert list(forecasts) == [tickers, date]
    assert len(forecasts) == 2
    assert forecasts.tickers == tickers
    assert forecasts.date == date


def test_forecasts_is_none(mocker):
    """При отсутствии прогнозов создаются новые."""
    fake_forecasts = list(range(11))
    fake_prepare_forecasts = mocker.patch.object(
        forecaster,
        "_prepare_forecasts",
        return_value=fake_forecasts,
    )

    tickers = ("AKRN", "GAZP")
    date = pd.Timestamp("2021-09-01")

    forecasts = forecaster.Forecasts(tickers, date)

    assert list(forecasts) == fake_forecasts
    assert len(forecasts) == len(fake_forecasts)
    assert forecasts.tickers == tickers
    assert forecasts.date == date

    fake_prepare_forecasts.assert_called_once_with(tickers, date)
