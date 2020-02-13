"""Формирование примеров для обучения в формате PyTorch."""
from typing import Dict

from torch import Tensor
from torch.utils.data import Dataset

from poptimizer.dl import features
from poptimizer.dl.params import ModelParams


class OneTickerDataset(Dataset):
    """Готовит обучающие примеры для одного тикера на основе параметров модели.

    Каждая составляющая помещается в словарь в виде пары {название признака: Tensor}.
    """

    def __init__(self, ticker: str, params: ModelParams):
        self.len = params.len(ticker)

        self.features = dict()
        for feat_name in params.get_all_feat():
            feature_cls = getattr(features, feat_name)
            self.features[feat_name] = feature_cls(ticker, params)

    def __getitem__(self, item) -> Dict[str, Tensor]:
        return {name: feature[item] for name, feature in self.features}

    def __len__(self) -> int:
        return self.len
