from __future__ import annotations

import torch
from torch.utils import data

from poptimizer.domain.dl import features


class OneTickerData(data.Dataset[dict[features.FeatTypes, torch.Tensor]]):
    def __init__(
        self,
        feat: features.Features,
        days: features.Days,
        num_feat: set[features.NumFeat],
    ) -> None:
        self._history_days = days.history
        self._test_days = days.test
        self._forecast_days = days.forecast
        self._all_days = len(feat.numerical)
        self._last_label = self._all_days - (self._history_days + self._forecast_days) + 1

        all_data_batch = feat.prepare_all_data_batch(
            days,
            num_feat,
        )

        self._returns = all_data_batch[features.FeatTypes.RETURNS]
        self._label = all_data_batch[features.FeatTypes.LABEL]
        self._numerical = all_data_batch[features.FeatTypes.NUMERICAL]

    def __len__(self) -> int:
        return self._all_days - self._history_days + 1

    def __getitem__(self, start_day: int) -> features.Batch:
        case = {
            features.FeatTypes.NUMERICAL: self._numerical[:, start_day : start_day + self._history_days],
            features.FeatTypes.RETURNS: self._returns[start_day : start_day + self._history_days],
        }

        if start_day < self._last_label:
            case[features.FeatTypes.LABEL] = self._label[start_day].reshape(-1)

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
