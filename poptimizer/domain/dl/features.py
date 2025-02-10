from enum import StrEnum, auto, unique
from typing import Self

import pandas as pd
from pydantic import BaseModel, Field, FiniteFloat, NonNegativeInt, field_validator, model_validator

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
    MCFTRR = auto()
    MEOGTRR = auto()
    IMOEX = auto()
    RVI = auto()


@unique
class EmbeddingFeat(StrEnum):
    ticker = auto()


class EmbeddingFeatDesc(BaseModel):
    value: NonNegativeInt
    size: int = Field(ge=2)

    @model_validator(mode="after")
    def _value_less_than_size(self) -> Self:
        if self.value >= self.size:
            raise ValueError("embedding value not less size")

        return self


class Features(domain.Entity):
    numerical: list[dict[NumFeat, FiniteFloat]] = Field(default_factory=list)
    embedding: dict[EmbeddingFeat, EmbeddingFeatDesc] = Field(default_factory=dict)

    @field_validator("numerical")
    def _numerical_match_labels(
        cls,
        numerical: list[dict[str, FiniteFloat]],
    ) -> list[dict[str, FiniteFloat]]:
        if not numerical:
            return numerical

        keys = numerical[0].keys()
        if not set(NumFeat).issuperset(keys):
            raise ValueError("key are not numerical features")

        if any(row.keys() != keys for row in numerical):
            raise ValueError("numerical features keys mismatch")

        return numerical

    @field_validator("embedding")
    def _embedding_match_labels(
        cls,
        embedding: dict[EmbeddingFeat, EmbeddingFeatDesc],
    ) -> dict[EmbeddingFeat, EmbeddingFeatDesc]:
        if embedding and embedding.keys() != set(EmbeddingFeat):
            raise ValueError("key are not embedding features")

        return embedding

    def _check_new_day(self, day: domain.Day) -> None:
        if self.day != day:
            self.day = day
            self.numerical.clear()
            self.embedding.clear()

    def update_numerical(self, day: domain.Day, num_feat_df: pd.DataFrame) -> None:
        self._check_new_day(day)
        self.numerical = num_feat_df.to_dict("records")  # type: ignore[reportUnknownMemberType]
