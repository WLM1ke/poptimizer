from enum import StrEnum, auto, unique

import pandas as pd
from pydantic import Field, FiniteFloat, field_validator

from poptimizer.domain import domain


@unique
class NumFeat(StrEnum):
    OPEN = auto()
    CLOSE = auto()
    HIGH = auto()
    LOW = auto()
    DIVIDENDS = auto()
    RETURNS = auto()
    TURNOVER = auto()


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
