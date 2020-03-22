"""Формирование примеров для обучения в формате PyTorch."""
from typing import Dict, Tuple, Type, List, Union

import pandas as pd
from torch import Tensor
from torch.utils import data

from poptimizer.dl import features, data_params


class OneTickerDataset(data.Dataset):
    """Готовит обучающие примеры для одного тикера на основе параметров модели."""

    def __init__(self, ticker: str, params: data_params.DataParams):
        self.len = params.len(ticker)
        self.features = [
            getattr(features, feat_name)(ticker, params)
            for feat_name in params.get_all_feat()
        ]

    def __getitem__(self, item) -> Dict[str, Union[Tensor, List[Tensor]]]:
        example = {}
        for feature in self.features:
            key = feature.key()
            if feature.unique():
                example[key] = feature[item]
            else:
                example.setdefault(key, []).append(feature[item])
        return example

    def __len__(self) -> int:
        return self.len


def get_data_loader(
    tickers: Tuple[str, ...],
    end: pd.Timestamp,
    params: dict,
    params_type: Type[data_params.DataParams],
) -> data.DataLoader:
    """Формирует загрузчики данных для обучения, валидации, тестирования и прогнозирования для
    заданных тикеров и конечной даты на основе словаря с параметрами.

    :param tickers:
        Перечень тикеров, для которых будет строится модель.
    :param end:
        Конец диапазона дат статистики, которые будут использоваться для
        построения модели.
    :param params:
        Словарь с параметрами для построения признаков и других элементов модели.
    :param params_type:
        Тип формируемых признаков.
    :return:
        Загрузчик данных.
    """
    params = params_type(tickers, end, params)
    data_sets = [OneTickerDataset(ticker, params) for ticker in tickers]
    dataset = data.ConcatDataset(data_sets)
    return data.DataLoader(dataset, params.batch_size, params.shuffle, drop_last=False)
