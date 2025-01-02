from typing import Self

from pydantic import Field, model_validator

from poptimizer.domain import domain


class Features(domain.Entity):
    labels: list[list[float]] = Field(default_factory=list)
    features: list[list[float]] = Field(default_factory=list)

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.labels) != len(self.features):
            raise ValueError("features length not match labels")

        if any(len(row) != 1 for row in self.labels):
            raise ValueError("invalid labels")

        features_count = self.features and len(self.features[0])

        if any(len(row) != features_count for row in self.features):
            raise ValueError("invalid features")

        return self
