"""Формирование примеров для обучения в формате PyTorch."""
from typing import Dict, Tuple

import pandas as pd
from torch import Tensor
from torch.utils import data

from poptimizer.dl import features
from poptimizer.dl.data_params import DataParams, DataType


class OneTickerDataset(data.Dataset):
    """Готовит обучающие примеры для одного тикера на основе параметров модели.

    Каждая составляющая помещается в словарь в виде пары {название признака: Tensor}.
    """

    def __init__(self, ticker: str, params: DataParams):
        self.len = params.len(ticker)

        self.features = dict()
        for feat_name in params.get_all_feat():
            feature_cls = getattr(features, feat_name)
            self.features[feat_name] = feature_cls(ticker, params)

    def __getitem__(self, item) -> Dict[str, Tensor]:
        return {name: feature[item] for name, feature in self.features}

    def __len__(self) -> int:
        return self.len


def get_data_loader(
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        params: dict,
        feat_type: DataType,
        batch_size: int,
) -> data.DataLoader:
    """

    :param tickers:
        Перечень тикеров, для которых будет строится модель.
    :param end:
        Конец диапазона дат статистики по ценам и дивидендам, которые будут использоваться для
        построения модели.
    :param params:
        Словарь с параметрами для построения признаков и других элементов модели.
    :param feat_type:
        Тип формируемых признаков.
    :param batch_size:
        Размер батча.
    :return:
        Загрузчик данных.
    """
    params = DataParams(tickers, end, params, feat_type)
    dataset = data.ConcatDataset(
        [OneTickerDataset(ticker, params) for ticker in tickers]
    )

    shuffle = False
    if feat_type == DataType.TRAIN:
        shuffle = True

    return data.DataLoader(dataset, batch_size, shuffle, drop_last=False)
