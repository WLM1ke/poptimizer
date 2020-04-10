"""Номер тикера данного примера."""
import torch

from poptimizer.dl.data_params import DataParams
from poptimizer.dl.features.feature import Feature


class Ticker(Feature):
    """Обратная величина СКО полной доходности обрезанная для низких значений."""

    def __init__(self, ticker: str, params: DataParams):
        super().__init__(ticker, params)
        tickers = params.tickers
        self._idx = torch.tensor(
            [params.tickers.index(ticker), len(tickers)], dtype=torch.long
        )

    def __getitem__(self, item: int) -> torch.Tensor:
        return self._idx

    @staticmethod
    def key() -> str:
        """Ключ по которому нужно сохранять признак."""
        return "Embedding"

    @staticmethod
    def unique() -> bool:
        """Является ли признак единственным для данного ключа."""
        return True
