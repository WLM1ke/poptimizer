from typing import Protocol

from pydantic import BaseModel, ConfigDict

from poptimizer.evolve.dl import datasets
from poptimizer.evolve.models import evolve


class TrainingJob(BaseModel):
    model_config = ConfigDict(frozen=True)

    model: evolve.Model
    evolution: evolve.Evolution


class TrainingData(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    tickers_data: list[datasets.TickerData]
    emb_size: list[int]
    emb_seq_size: list[int]


class Forecast(BaseModel):
    model_config = ConfigDict(frozen=True)

    mean: list[list[float]]
    cov: list[list[float]]


class TrainingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    forecast: Forecast
    duration: float
    test: evolve.TestResults


class TrainingRunner(Protocol):
    async def __call__(self, job: TrainingJob, data: TrainingData) -> TrainingResult: ...
