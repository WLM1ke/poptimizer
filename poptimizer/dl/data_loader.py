"""Формирование примеров для обучения в формате PyTorch."""
from typing import Dict, Tuple, Type, List, Union, Any

import pandas as pd
from torch import Tensor
from torch.utils import data

from poptimizer.dl import features

# Описание фенотипа и его подразделов
PhenotypeData = Dict[str, Union[Any, "PhenotypeType"]]


class OneTickerDataset(data.Dataset):
    """Готовит обучающие примеры для одного тикера на основе параметров модели."""

    def __init__(self, ticker: str, params: features.DataParams):
        self.len = params.len(ticker)
        self.features = [
            getattr(features, feat_name)(ticker, params)
            for feat_name in params.get_all_feat()
        ]

    def __getitem__(self, item) -> Dict[str, Union[Tensor, List[Tensor]]]:
        example = {}
        for feature in self.features:
            key = feature.__class__.__name__
            example[key] = feature[item]
        return example

    def __len__(self) -> int:
        return self.len

    @property
    def features_description(self) -> Dict[str, Tuple[features.FeatureType, int]]:
        """Словарь с описанием всех признаков."""
        features_description = {}
        for feature in self.features:
            key = feature.__class__.__name__
            features_description[key] = feature.type_and_size
        return features_description


class DescribedDataLoader(data.DataLoader):
    """Загрузчик данных, который дополнительно хранит описание параметров данных."""

    def __init__(
        self,
        tickers: Tuple[str, ...],
        end: pd.Timestamp,
        params: PhenotypeData,
        params_type: Type[features.DataParams],
    ):
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
        """
        params = params_type(tickers, end, params)
        data_sets = [OneTickerDataset(ticker, params) for ticker in tickers]
        super().__init__(
            dataset=data.ConcatDataset(data_sets),
            batch_size=params.batch_size,
            shuffle=params.shuffle,
            drop_last=False,
            num_workers=1,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
        )
        self._features_description = data_sets[0].features_description

    @property
    def features_description(self) -> Dict[str, Tuple[features.FeatureType, int]]:
        """Словарь с описанием всех признаков."""
        return self._features_description
