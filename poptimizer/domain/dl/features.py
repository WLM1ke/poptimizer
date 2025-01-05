from enum import StrEnum, auto, unique

import pandas as pd
import torch
from pydantic import BaseModel, Field, FiniteFloat, field_validator

from poptimizer import errors
from poptimizer.domain import domain


class Days(BaseModel):
    history: int
    forecast: int
    test: int

    @property
    def minimal_returns_days(self) -> int:
        return self.history + 2 * self.forecast + self.test - 1


@unique
class FeatTypes(StrEnum):
    # Метки
    LABEL = auto()
    # Доходности для расчета ковариационной матрицы
    RETURNS = auto()
    # Численные признаки
    NUMERICAL = auto()


@unique
class NumFeat(StrEnum):
    OPEN = auto()
    CLOSE = auto()
    HIGH = auto()
    LOW = auto()
    DIVIDENDS = auto()
    RETURNS = auto()
    TURNOVER = auto()


Batch = dict[FeatTypes, torch.Tensor]


class Features(domain.Entity):
    numerical: list[dict[NumFeat, FiniteFloat]] = Field(default_factory=list)

    @field_validator("numerical")
    def _match_labels(cls, features: list[dict[str, FiniteFloat]]) -> list[dict[str, FiniteFloat]]:
        if not features:
            return features

        keys = set(NumFeat)

        if any(row.keys() != keys for row in features):
            raise ValueError("invalid numerical features")

        return features

    def update(self, day: domain.Day, num_feat_df: pd.DataFrame) -> None:
        self.day = day
        self.numerical = num_feat_df.to_dict("records")  # type: ignore[reportUnknownMemberType]

    def prepare_all_data_batch(self, days: Days, num_feat: set[NumFeat]) -> Batch:
        if not num_feat:
            raise errors.DomainError("no features")

        if len(self.numerical) < days.minimal_returns_days:
            raise errors.TooShortHistoryError(days.minimal_returns_days)

        all_feat_df = pd.DataFrame(self.numerical)

        return {
            FeatTypes.LABEL: torch.tensor(
                all_feat_df[NumFeat.RETURNS]
                .rolling(days.forecast)  # type: ignore[reportUnknownMemberType]
                .sum()
                .shift(-(days.forecast + days.history - 1))
                .values,
                dtype=torch.float,
            ).exp(),
            FeatTypes.NUMERICAL: torch.tensor(
                all_feat_df[sorted(num_feat)].values,  # type: ignore[reportUnknownMemberType]
                dtype=torch.float,
            ).T,
            FeatTypes.RETURNS: torch.tensor(
                all_feat_df[NumFeat.RETURNS].values,  # type: ignore[reportUnknownMemberType]
                dtype=torch.float,
            )
            .exp()
            .sub(1),
        }
