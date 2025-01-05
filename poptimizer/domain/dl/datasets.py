from __future__ import annotations

import numpy as np
import pandas as pd
import torch
from torch.utils import data

from poptimizer import errors
from poptimizer.domain.dl import features


class OneTickerData(data.Dataset[dict[features.FeatTypes, torch.Tensor]]):
    def __init__(
        self,
        days: features.Days,
        ret_total: pd.Series[float],
        num_feat: list[pd.Series[float]],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast

        self._all_days = len(ret_total)

        min_days_for_one_train_and_test = days.minimal_returns_days

        if self._all_days < min_days_for_one_train_and_test:
            raise errors.TooShortHistoryError(min_days_for_one_train_and_test)

        if not num_feat:
            raise errors.DomainError("no features")

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
            raise errors.DomainError("features index mismatch")

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

    def __getitem__(self, start_day: int) -> features.Batch:
        case = {
            features.FeatTypes.NUMERICAL: self._num_feat[:, start_day : start_day + self._history_days],
            features.FeatTypes.RETURNS: self._ret_total[start_day : start_day + self._history_days],
        }

        if start_day < self._all_days - (self._history_days + self._forecast_days) + 1:
            case[features.FeatTypes.LABEL] = self._label1p[start_day].reshape(-1)

        return case

    def train_dataset(self) -> data.Subset[features.Batch]:
        end = (
            self._all_days
            - (self._forecast_days + self._test_days - 1)
            - (self._history_days + self._forecast_days - 1)
        )

        return data.Subset(self, range(end))

    def test_dataset(self) -> data.Subset[features.Batch]:
        end = self._all_days - (self._history_days + self._forecast_days - 1)

        return data.Subset(self, range(end - self._test_days, end))

    def forecast_dataset(self) -> data.Subset[features.Batch]:
        start = self._all_days - self._history_days

        return data.Subset(self, range(start, start + 1))
