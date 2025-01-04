import pandas as pd
from pydantic import Field, FiniteFloat, field_validator

from poptimizer.domain import domain


class Features(domain.Entity):
    features: list[dict[str, float]] = Field(default_factory=list)

    @field_validator("features")
    def _match_labels(cls, features: list[dict[str, FiniteFloat]]) -> list[dict[str, FiniteFloat]]:
        if not features:
            return features

        labels = features[0].keys()

        if any(row.keys() != labels for row in features):
            raise ValueError("invalid features")

        return features

    def update(self, day: domain.Day, df: pd.DataFrame) -> None:
        self.day = day
        self.features = df.to_dict("records")  # type: ignore[reportUnknownMemberType]
