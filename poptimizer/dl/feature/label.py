"""Метка данных."""
import torch

from poptimizer.dl.feature.feature import Feature, ModelParams


class Label(Feature):
    """Метка линейная комбинация полной и дивидендной доходности с суммарным весом 1."""

    def __init__(self, ticker: str, params: ModelParams):
        super().__init__(ticker, params)
        div = torch.tensor(params.div(ticker))
        self.cum_div = torch.cumsum(div, dim=0)
        self.price = torch.tensor(params.price(ticker))
        self.history_days = params.history_days
        self.forecast_days = params.forecast_days
        self.div_share = params[self.name]["div_share"]

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        forecast_days = self.forecast_days
        price = self.price
        div = self.cum_div
        last_history_price = price[item + history_days - 1]
        last_forecast_price = price[item + history_days - 1 + forecast_days]
        div = (
            div[item + history_days - 1 + forecast_days] - div[item + history_days - 1]
        )
        price_growth = (last_forecast_price - last_history_price) * (1 - self.div_share)
        label = (price_growth + div) / last_history_price
        return label.reshape(-1)
