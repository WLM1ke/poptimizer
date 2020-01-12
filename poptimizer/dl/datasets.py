"""Формирование примеров для обучения в формате PyTorch."""
from typing import Tuple, Optional

import pandas as pd
import torch
from torch.utils import data as dataset

# Параметры формирования примеров для обучения сетей
from poptimizer import data
from poptimizer.ml.feature.std import LOW_STD

DL_PARAMS = {"history_days": 264, "forecast_days": 341, "div_share": 0.6}


class OneTickerDataset(dataset.Dataset):
    """Готовит обучающие примеры для одного тикера.

    Прирост цены акции в течении периода нормированный на цену акции в начале периода.
    Дивиденды рассчитываются нарастающим итогом в течении периода и нормируются на цену акции в начале
    периода.
    Доходность в течении нескольких дней после окончания исторического периода. Может быть
    произвольной пропорцией между дивидендной или полной доходностью.
    Вес обучающих примеров обратный квадрату СКО доходности - для имитации метода максимального
    правдоподобия. Низкое СКО обрезается, для избежания деления на 0.

    Каждая составляющая помещается в словарь в виде torch.Tensor.
    """

    def __init__(
        self,
        ticker: str,
        price: pd.DataFrame,
        div: pd.DataFrame,
        params: dict,
        dataset_end: Optional[pd.Timestamp],
    ):
        price = price[ticker]
        start = price.first_valid_index()
        self.price = price[start:]
        self.div = div.loc[start:, ticker]
        self.params = params
        self.dataset_end = dataset_end or price.index[-1]

    def __getitem__(self, item):
        norm = self.price.iloc[item]
        history_days = self.params["history_days"]

        price = self.price.iloc[item : item + history_days]
        div = self.div.iloc[item + 1 : item + history_days]
        price0 = price.shift(1)
        returns = (price + div) / price0
        returns = returns.iloc[1:]
        std = max(returns.std(), LOW_STD)

        weight = 1 / std ** 2
        price = price.iloc[1:] / norm - 1
        div = div.cumsum() / norm

        rez = dict(
            price=torch.tensor(price),
            div=torch.tensor(div),
            weight=torch.tensor(weight),
        )

        if self.dataset_end != self.price.index[-1]:
            last_history_price = self.price.iloc[item + history_days - 1]
            forecast_days = self.params["forecast_days"]
            last_forecast_price = self.price.iloc[
                item + history_days - 1 + forecast_days
            ]
            all_div = self.div.iloc[
                item + history_days : item + history_days + forecast_days
            ].sum()
            label = (
                (last_forecast_price - last_history_price)
                * (1 - self.params["div_share"])
                + all_div
            ) / last_history_price
            rez["label"] = torch.tensor(label)
        return rez

    def __len__(self):
        return (
            self.price.index.get_loc(self.dataset_end) + 2 - self.params["history_days"]
        )


def get_dataset(
    tickers: Tuple[str, ...],
    last_date: pd.Timestamp,
    params: dict,
    dataset_start: Optional[pd.Timestamp] = None,
    dataset_end: Optional[pd.Timestamp] = None,
) -> dataset.Dataset:
    """Сформировать набор обучающих примеров для заданных тикеров.

    :param tickers:
        Набор тикеров.
    :param last_date:
        Последний день статистики.
    :param params:
        Параметры формирования обучающих примеров.
    :param dataset_start:
        Первая дата для формирования х-ов обучающих примеров. Если отсутствует, то будут
        использоваться дынные с начала статистики.
    :param dataset_end:
        Последняя дата для формирования х-ов обучающих примеров. Если отсутствует, то будет
        использована last_date.
    :return:
        Искомый набор примеров для сети.
    """
    div, price = data.div_ex_date_prices(tickers, last_date)
    div = div.loc[dataset_start:]
    price = price.loc[dataset_start:]
    return dataset.ConcatDataset(
        [
            OneTickerDataset(ticker, price, div, params, dataset_end)
            for ticker in tickers
        ]
    )
