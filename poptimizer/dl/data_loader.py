"""Формирование примеров для обучения в формате PyTorch."""
from typing import Dict, Tuple, Type

import pandas as pd
from torch import Tensor
from torch.utils import data

from poptimizer.dl import features, data_params
from poptimizer.dl.data_params import DataParams


class OneTickerDataset(data.Dataset):
    """Готовит обучающие примеры для одного тикера на основе параметров модели.

    Каждая составляющая помещается в словарь в виде пары {название признака: Tensor}.
    """

    def __init__(self, ticker: str, params: data_params.DataParams):
        self.len = params.len(ticker)

        self.features = dict()
        for feat_name in params.get_all_feat():
            feature_cls = getattr(features, feat_name)
            self.features[feat_name] = feature_cls(ticker, params)

    def __getitem__(self, item) -> Dict[str, Tensor]:
        return {name: feature[item] for name, feature in self.features.items()}

    def __len__(self) -> int:
        return self.len


def get_data_loader(
    tickers: Tuple[str, ...],
    end: pd.Timestamp,
    params: dict,
    params_type: Type[DataParams],
) -> data.DataLoader:
    """

    :param tickers:
        Перечень тикеров, для которых будет строится модель.
    :param end:
        Конец диапазона дат статистики по ценам и дивидендам, которые будут использоваться для
        построения модели.
    :param params:
        Словарь с параметрами для построения признаков и других элементов модели.
    :param params_type:
        Тип формируемых признаков.
    :return:
        Загрузчик данных.
    """
    params = params_type(tickers, end, params)
    dataset = data.ConcatDataset(
        [OneTickerDataset(ticker, params) for ticker in tickers]
    )

    return data.DataLoader(dataset, params.batch_size, params.shuffle, drop_last=False)
