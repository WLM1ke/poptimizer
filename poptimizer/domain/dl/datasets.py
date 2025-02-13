from __future__ import annotations

from typing import NamedTuple

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel, FiniteFloat
from torch.utils import data

from poptimizer import errors
from poptimizer.domain.dl import features


class Days(BaseModel):
    history: int
    forecast: int
    test: int

    @property
    def minimal_returns_days(self) -> int:
        return self.history + 2 * self.forecast + self.test - 1


class TrainBatch(NamedTuple):
    num_feat: torch.Tensor
    emb_feat: torch.Tensor
    labels: torch.Tensor


class TickerTrainDataSet(data.Dataset[TrainBatch]):
    def __init__(self, days: Days, num_feat: torch.Tensor, emb_feat: torch.Tensor, labels: torch.Tensor) -> None:
        self._len = num_feat.shape[1] - (days.forecast + days.test - 1) - (days.history + days.forecast - 1)
        self._history = days.history
        self._num_feat = num_feat
        self._emb_feat = emb_feat
        self._labels = labels

    def __len__(self) -> int:
        return self._len

    def __getitem__(self, n: int) -> TrainBatch:
        return TrainBatch(
            num_feat=self._num_feat[:, n : n + self._history],
            emb_feat=self._emb_feat,
            labels=self._labels[n].reshape(-1),
        )


class TestBatch(NamedTuple):
    num_feat: torch.Tensor
    emb_feat: torch.Tensor
    labels: torch.Tensor
    returns: torch.Tensor


class TickerTestDataSet(data.Dataset[TestBatch]):
    def __init__(
        self, days: Days, num_feat: torch.Tensor, emb_feat: torch.Tensor, labels: torch.Tensor, returns: torch.Tensor
    ) -> None:
        self._len = days.test
        self._start = num_feat.shape[1] - (days.history + days.forecast + days.test - 1)
        self._history = days.history
        self._num_feat = num_feat
        self._emb_feat = emb_feat
        self._labels = labels
        self._returns = returns

    def __len__(self) -> int:
        return self._len

    def __getitem__(self, n: int) -> TestBatch:
        start = self._start + n

        return TestBatch(
            num_feat=self._num_feat[:, start : start + self._history],
            emb_feat=self._emb_feat,
            labels=self._labels[start].reshape(-1),
            returns=self._returns[start : start + self._history],
        )


class ForecastBatch(NamedTuple):
    num_feat: torch.Tensor
    emb_feat: torch.Tensor
    returns: torch.Tensor


class TickerForecastDataSet(data.Dataset[ForecastBatch]):
    def __init__(self, days: Days, num_feat: torch.Tensor, emb_feat: torch.Tensor, returns: torch.Tensor) -> None:
        self._start = num_feat.shape[1] - days.history
        self._history = days.history
        self._num_feat = num_feat
        self._emb_feat = emb_feat
        self._returns = returns

    def __len__(self) -> int:
        return 1

    def __getitem__(self, n: int) -> ForecastBatch:
        start = self._start + n

        return ForecastBatch(
            num_feat=self._num_feat[:, start : start + self._history],
            emb_feat=self._emb_feat,
            returns=self._returns[start : start + self._history],
        )


class TickerData:
    def __init__(
        self,
        days: Days,
        num_feat: list[dict[features.NumFeat, FiniteFloat]],
        num_feat_selected: list[features.NumFeat],
        emb_feat: list[int],
    ) -> None:
        self._days = days

        if not num_feat_selected:
            raise errors.DomainError("no features")

        if len(num_feat) < days.minimal_returns_days:
            raise errors.TooShortHistoryError(days.minimal_returns_days)

        all_feat_df = pd.DataFrame(num_feat)

        self._num_feat = torch.from_numpy(  # type: ignore[reportUnknownMemberType]
            all_feat_df[num_feat_selected].to_numpy(np.float32),  # type: ignore[reportUnknownMemberType]
        ).T

        self._emb_feat = torch.tensor(emb_feat, dtype=torch.long)

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
        return TickerTrainDataSet(
            days=self._days,
            num_feat=self._num_feat,
            emb_feat=self._emb_feat,
            labels=self._labels,
        )

    def test_dataset(self) -> TickerTestDataSet:
        return TickerTestDataSet(
            days=self._days,
            num_feat=self._num_feat,
            emb_feat=self._emb_feat,
            labels=self._labels,
            returns=self._returns,
        )

    def forecast_dataset(self) -> TickerForecastDataSet:
        return TickerForecastDataSet(
            days=self._days,
            num_feat=self._num_feat,
            emb_feat=self._emb_feat,
            returns=self._returns,
        )
