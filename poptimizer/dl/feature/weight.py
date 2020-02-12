"""Вес данного примера."""
import torch

from poptimizer.dl.feature.feature import Feature, ModelParams
from poptimizer.ml.feature.std import LOW_STD


class Label(Feature):
    """Обратная величина СКО полной доходности обрезанная для низких значений."""

    def __init__(self, ticker: str, params: ModelParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker))
        self.price = torch.tensor(params.price(ticker))
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        price = self.price
        div = self.div

        price1 = price[item + 1 : item + history_days]
        div = div[item + 1 : item + history_days]
        price0 = price[item : item + history_days - 1]
        returns = (price1 + div) / price0
        std = torch.std(returns, dim=0, keepdim=True)
        std = torch.max(std, LOW_STD)
        return std ** -2
