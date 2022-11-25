"""Загрузчики данных."""
from enum import Enum, auto, unique
from typing import Iterator

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel
from torch.utils import data

from poptimizer.core import consts
from poptimizer.dl import exceptions


class DataDays(BaseModel):
    """Описание, как использовать доступные дни для построения тренировочной и тестовой выборки."""

    history: int
    forecast: int
    test: int


@unique
class FeatTypes(Enum):
    """Типы признаков.

    Являются ключами для словаря с отдельными обучающими примерами.
    """

    LABEL1P = auto()
    RETURNS = auto()
    NUMERICAL = auto()


Case = dict[FeatTypes, torch.Tensor]
DataLoader = data.DataLoader[Case]


class OneTickerData(data.Dataset[dict[FeatTypes, torch.Tensor]]):
    """Данные для построения признака по одному тикеру.

    Позволяет создавать Dataset(ы) для обучения, тестирования и прогнозирования.
    """

    def __init__(
        self,
        days: DataDays,
        ret_total: pd.Series,
        num_feat: list[pd.Series],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast

        self._all_days = len(ret_total)

        min_days_for_one_train_and_test = self._history_days + 2 * self._forecast_days + self._test_days - 1
        if self._all_days < min_days_for_one_train_and_test:
            raise exceptions.FeaturesError("too short history")

        self._ret_total = torch.tensor(
            ret_total.values,
            dtype=torch.float,
            device=consts.DEVICE,
        )

        ret = (
            pd.Series(np.log1p(ret_total))
            .rolling(self._forecast_days)
            .sum()
            .shift(-(self._forecast_days + self._history_days - 1))
            .values
        )
        self._label1p = torch.tensor(
            np.exp(ret),
            dtype=torch.float,
            device=consts.DEVICE,
        )

        if any(not ret_total.index.equals(df.index) for df in num_feat):
            raise exceptions.FeaturesError("features index missmatch")

        self._num_feat = torch.vstack(
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
        return self._all_days - self._history_days + 1

    def __getitem__(self, start_day: int) -> Case:
        """Выдает обучающий пример с заданным номером.

        Метка может отсутствовать для конца семпла.
        """
        case = {
            FeatTypes.NUMERICAL: self._num_feat[:, start_day : start_day + self._history_days],
            FeatTypes.RETURNS: self._ret_total[start_day : start_day + self._history_days],
        }

        if start_day < self._all_days - (self._history_days + self._forecast_days) + 1:
            case[FeatTypes.LABEL1P] = self._label1p[start_day]

        return case

    def train_dataset(self) -> data.Subset[Case]:
        """Dataset для обучения."""
        end = (
            self._all_days
            - (self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return data.Subset(self, range(end))

    def test_dataset(self) -> data.Subset[Case]:
        """Dataset для тестирования."""
        end = self._all_days - (self._history_days + self._forecast_days - 1)

        return data.Subset(self, range(end - self._test_days, end))

    def forecast_dataset(self) -> data.Subset[Case]:
        """Dataset для построения прогноза."""
        start = self._all_days - self._history_days

        return data.Subset(self, range(start, start + 1))


def train(
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
    def __init__(self, datasets: list[data.Subset[Case]]) -> None:
        super().__init__(None)
        self._test_days = len(datasets[0])
        self._tests = self._test_days * len(datasets)

        if any(len(dataset) != self._test_days for dataset in datasets):
            raise exceptions.FeaturesError("test length missmatch")

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


def test(
    datasets: list[OneTickerData],
    num_workers: int = 0,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
) -> data.DataLoader[Case]:
    """Загрузчик данных для тестирования модели."""
    test_dataset = [ticker.test_dataset() for ticker in datasets]

    return data.DataLoader(
        dataset=data.ConcatDataset(test_dataset),
        batch_sampler=_DaysSampler(test_dataset),
        drop_last=False,
        num_workers=num_workers,
    )


def forecast(
    datasets: list[OneTickerData],
) -> data.DataLoader[Case]:
    """Загрузчик данных для построения прогноза."""
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.forecast_dataset() for ticker in datasets),
        batch_size=len(datasets),
        shuffle=False,
        drop_last=False,
    )
