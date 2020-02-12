"""Динамика накопленных дивидендов нормированная на первоначальную цену."""
import torch

from poptimizer.dl.feature.feature import Feature, ModelParams


class Dividends(Feature):
    """Динамика накопленных дивидендов нормированная на первоначальную цену."""

    def __init__(self, ticker: str, params: ModelParams):
        super().__init__(ticker, params)
        self.div = torch.tensor(params.div(ticker))
        self.history_days = params.history_days

    def __getitem__(self, item: int) -> torch.Tensor:
        history_days = self.history_days
        div = self.div
        return div[item : item + history_days] / div[item] - 1
