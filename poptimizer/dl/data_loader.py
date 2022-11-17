"""Загрузчики данных."""
from enum import Enum, auto, unique
from typing import Iterator

import numpy as np
import pandas as pd
import torch
from torch.utils import data

from poptimizer.core import consts
from poptimizer.dl import exceptions


@unique
class FeatTypes(Enum):
    """Типы признаков.

    Являются ключами для словаря с отдельными обучающими примерами.
    """

    LABEL = auto()
    RETURNS = auto()
    NUMERICAL = auto()


Case = dict[FeatTypes, torch.Tensor]


class OneTickerData(data.Dataset[dict[FeatTypes, torch.Tensor]]):
    """Данные для построения признака по одному тикеру.

    Позволяет создавать Dataset(ы) для обучения, тестирования и прогнозирования.
    """

    def __init__(
        self,
        history_days: int,
        test_days: int,
        forecast_days: int,
        ret_total: pd.Series,
        num_feat: list[pd.Series],
    ) -> None:
        self._history_days = history_days
        self._test_days = test_days
        self._forecast_days = forecast_days

        self._days = len(ret_total)

        min_days_for_one_train_and_test = self._history_days + 2 * self._forecast_days + self._test_days - 1
        if self._days < min_days_for_one_train_and_test:
            raise exceptions.TooShortHistoryError(self._days)

        self._ret_total = torch.tensor(
            ret_total.values,
            dtype=torch.float,
            device=consts.DEVICE,
        ).reshape(-1, 1)

        ret = (
            pd.Series(np.log1p(ret_total))
            .rolling(forecast_days)
            .sum()
            .shift(-(forecast_days + history_days - 1))
            .values
        )
        self._label = torch.tensor(
            ret,
            dtype=torch.float,
            device=consts.DEVICE,
        ).reshape(-1, 1)

        if any(len(df) != self._days for df in num_feat):
            raise exceptions.WrongFeatLenError(self._days)

        self._num_feat = torch.column_stack(
            [
                torch.tensor(
                    feat.values,
                    dtype=torch.float,
                    device=consts.DEVICE,
                )
                for feat in num_feat
            ],
        )

    def __len__(self) -> int:
        """Количество доступных примеров."""
        return self._days - self._history_days + 1

    def __getitem__(self, start_day: int) -> Case:
        """Выдает обучающий пример с заданным номером.

        Метка может отсутствовать для конца семпла.
        """
        case = {
            FeatTypes.NUMERICAL: self._num_feat[start_day : start_day + self._history_days],
            FeatTypes.RETURNS: self._ret_total[start_day : start_day + self._history_days],
        }

        if start_day < self._days - (self._history_days + self._forecast_days) + 1:
            case[FeatTypes.LABEL] = self._label[start_day]

        return case

    def train_dataset(self) -> data.Subset[Case]:
        """Dataset для обучения."""
        end = (
            self._days
            - (self._history_days + self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return data.Subset(self, range(end))

    def test_dataset(self) -> data.Subset[Case]:
        """Dataset для тестирования."""
        end = self._days - (self._history_days + self._forecast_days - 1)

        return data.Subset(self, range(end - self._test_days, end))

    def forecast_dataset(self) -> data.Subset[Case]:
        """Dataset для построения прогноза."""
        start = self._days - self._history_days

        return data.Subset(self, range(start, start + 1))


def train_data_loader(
    datasets: list[OneTickerData],
    batch_size: int,
    num_workers: int = 0,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
) -> data.DataLoader[Case]:
    """Загрузчик данных для тренировки модели."""
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.train_dataset() for ticker in datasets),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,
        num_workers=num_workers,
    )


class _DaysSampler(data.Sampler[list[int]]):
    def __init__(self, datasets: list[OneTickerData]) -> None:
        super().__init__(None)
        self._test_days = len(datasets[0])
        self._tests = self._test_days * len(datasets)

        if any(len(dataset) != self._test_days for dataset in datasets):
            raise exceptions.TestLengthMissmatchError(self._test_days)

    def __len__(self) -> int:
        return self._test_days

    def __iter__(self) -> Iterator[list[int]]:
        yield from (
            list(
                range(
                    day,
                    self._tests,
                    self._test_days,
                ),
            )
            for day in range(self._test_days)
        )


def test_data_loader(
    datasets: list[OneTickerData],
    num_workers: int = 0,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
) -> data.DataLoader[Case]:
    """Загрузчик данных для тестирования модели."""
    return data.DataLoader(
        dataset=data.ConcatDataset(datasets),
        batch_sampler=_DaysSampler(datasets),
        drop_last=False,
        num_workers=num_workers,
    )


def forecast_data_loader(
    datasets: list[OneTickerData],
) -> data.DataLoader[Case]:
    """Загрузчик данных для построения прогноза."""
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.forecast_dataset() for ticker in datasets),
        batch_size=len(datasets),
        shuffle=False,
        drop_last=False,
    )
