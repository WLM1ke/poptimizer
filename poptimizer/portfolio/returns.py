"""Метрики доходности."""
from poptimizer import ml
from poptimizer.portfolio.metrics import AbstractMetrics


class ReturnsMetrics(AbstractMetrics):
    """Метрики доходности портфеля."""

    def _forecast_func(self):
        portfolio = self._portfolio
        tickers = tuple(portfolio.index[:-2])
        date = portfolio.date
        return ml.make_forecast(tickers, date)
