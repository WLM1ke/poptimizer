from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel, FiniteFloat
from torch.utils import data

from poptimizer import errors
from poptimizer.domain.dl import features


class TrainBatch(NamedTuple):
    num_feat: torch.Tensor
    labels: torch.Tensor


class TickerTrainDataSet(data.Dataset[TrainBatch]):
    def __init__(self, history_days: int, num_feat: torch.Tensor, labels: torch.Tensor) -> None:
        self._history_days = history_days
        self._num_feat = num_feat
        self._labels = labels

    def __len__(self) -> int:
        return len(self._labels)

    def __getitem__(self, start_day: int) -> TrainBatch:
        return TrainBatch(
            num_feat=self._num_feat[:, start_day : start_day + self._history_days],
            labels=self._labels[start_day].reshape(-1),
        )


class TestBatch(NamedTuple):
    num_feat: torch.Tensor
    labels: torch.Tensor
    returns: torch.Tensor


class TickerTestDataSet(data.Dataset[TestBatch]):
    def __init__(self, history_days: int, num_feat: torch.Tensor, labels: torch.Tensor, returns: torch.Tensor) -> None:
        self._history_days = history_days
        self._num_feat = num_feat
        self._labels = labels
        self._returns = returns

    def __len__(self) -> int:
        return len(self._labels)

    def __getitem__(self, start_day: int) -> TestBatch:
        return TestBatch(
            num_feat=self._num_feat[:, start_day : start_day + self._history_days],
            labels=self._labels[start_day].reshape(-1),
            returns=self._returns[start_day : start_day + self._history_days],
        )


class ForecastBatch(NamedTuple):
    num_feat: torch.Tensor
    returns: torch.Tensor


class TickerForecastDataSet(data.Dataset[ForecastBatch]):
    def __init__(self, history_days: int, num_feat: torch.Tensor, returns: torch.Tensor) -> None:
        self._history_days = history_days
        self._num_feat = num_feat
        self._returns = returns

    def __len__(self) -> int:
        return 1

    def __getitem__(self, start_day: int) -> ForecastBatch:
        return ForecastBatch(
            num_feat=self._num_feat[:, start_day : start_day + self._history_days],
            returns=self._returns[start_day : start_day + self._history_days],
        )


class Days(BaseModel):
    history: int
    forecast: int
    test: int

    @property
    def minimal_returns_days(self) -> int:
        return self.history + 2 * self.forecast + self.test - 1


class TickerData:
    def __init__(
        self,
        num_feat: list[dict[features.NumFeat, FiniteFloat]],
        days: Days,
        num_feat_selected: set[features.NumFeat],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast
        self._all_days = len(num_feat)
        self._last_label = self._all_days - (self._history_days + self._forecast_days) + 1

        if not num_feat_selected:
            raise errors.DomainError("no features")

        if len(num_feat) < days.minimal_returns_days:
            raise errors.TooShortHistoryError(days.minimal_returns_days)

        all_feat_df = pd.DataFrame(num_feat)

        self._num_feat = torch.from_numpy(  # type: ignore[reportUnknownMemberType]
            all_feat_df[sorted(num_feat_selected)].to_numpy(np.float32),  # type: ignore[reportUnknownMemberType]
        ).T

        self._labels = torch.from_numpy(  # type: ignore[reportUnknownMemberType]
            all_feat_df[features.NumFeat.RETURNS]
            .rolling(days.forecast)  # type: ignore[reportUnknownMemberType]
            .sum()
            .shift(-(days.forecast + days.history - 1))
            .to_numpy(np.float32),
        ).exp()

        self._returns = (
            torch.from_numpy(  # type: ignore[reportUnknownMemberType]
                all_feat_df[features.NumFeat.RETURNS].to_numpy(np.float32),  # type: ignore[reportUnknownMemberType]
            )
            .exp()
            .sub(1)
        )

    def train_dataset(self) -> TickerTrainDataSet:
        end = (
            self._all_days
            - (self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return TickerTrainDataSet(
            history_days=self._history_days,
            num_feat=self._num_feat[:, : end + self._history_days],
            labels=self._labels[:end],
        )

    def test_dataset(self) -> TickerTestDataSet:
        end = self._all_days - (self._history_days + self._forecast_days - 1)

        return TickerTestDataSet(
            history_days=self._history_days,
            num_feat=self._num_feat[:, end - self._test_days : end + self._history_days],
            labels=self._labels[end - self._test_days : end],
            returns=self._returns[end - self._test_days : end + self._history_days],
        )

    def forecast_dataset(self) -> TickerForecastDataSet:
        start = self._all_days - self._history_days

        return TickerForecastDataSet(
            history_days=self._history_days,
            num_feat=self._num_feat[:, start : start + 1 + self._history_days],
            returns=self._returns[start : start + 1 + self._history_days],
        )
