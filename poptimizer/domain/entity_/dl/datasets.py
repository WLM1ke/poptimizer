from __future__ import annotations

from enum import Enum, auto, unique

import numpy as np
import pandas as pd
import torch
from pydantic import BaseModel
from torch.utils import data

from poptimizer.domain import consts


@unique
class FeatTypes(Enum):
    LABEL1P = auto()
    RETURNS = auto()
    NUMERICAL = auto()


Batch = dict[FeatTypes, torch.Tensor]


class Days(BaseModel):
    history: int
    forecast: int
    test: int


class OneTickerData(data.Dataset[dict[FeatTypes, torch.Tensor]]):
    def __init__(
        self,
        days: Days,
        ret_total: pd.Series[float],
        num_feat: list[pd.Series[float]],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast

        self._all_days = len(ret_total)

        min_days_for_one_train_and_test = self._history_days + 2 * self._forecast_days + self._test_days - 1
        if self._all_days < min_days_for_one_train_and_test:
            raise consts.DomainError("too short history")

        if not num_feat:
            raise consts.DomainError("no features")

        self._ret_total = torch.tensor(
            ret_total.values,
            dtype=torch.float,
        )

        ret: pd.Series[float] = (
            pd.Series(np.log1p(ret_total))
            .rolling(self._forecast_days)  # type: ignore[reportUnknownMemberType]
            .sum()
            .shift(-(self._forecast_days + self._history_days - 1))
            .to_numpy()  # type: ignore[reportUnknownMemberType]
        )
        self._label1p = torch.tensor(
            np.exp(ret),
            dtype=torch.float,
        )

        if any(not ret_total.index.equals(df.index) for df in num_feat):  # type: ignore[reportUnknownMemberType]
            raise consts.DomainError("features index mismatch")

        self._num_feat = torch.vstack(
            [
                torch.tensor(
                    feat.values,
                    dtype=torch.float,
                )
                for feat in num_feat
            ],
        )

    def __len__(self) -> int:
        return self._all_days - self._history_days + 1

    def __getitem__(self, start_day: int) -> Batch:
        case = {
            FeatTypes.NUMERICAL: self._num_feat[:, start_day : start_day + self._history_days],
            FeatTypes.RETURNS: self._ret_total[start_day : start_day + self._history_days],
        }

        if start_day < self._all_days - (self._history_days + self._forecast_days) + 1:
            case[FeatTypes.LABEL1P] = self._label1p[start_day].reshape(-1)

        return case

    def train_dataset(self) -> data.Subset[Batch]:
        end = (
            self._all_days
            - (self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return data.Subset(self, range(end))

    def test_dataset(self) -> data.Subset[Batch]:
        end = self._all_days - (self._history_days + self._forecast_days - 1)

        return data.Subset(self, range(end - self._test_days, end))

    def forecast_dataset(self) -> data.Subset[Batch]:
        start = self._all_days - self._history_days

        return data.Subset(self, range(start, start + 1))
