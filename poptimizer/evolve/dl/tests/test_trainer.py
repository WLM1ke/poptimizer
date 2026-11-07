from datetime import date
from typing import cast, override

import pytest
from pydantic import ValidationError

from poptimizer.core import domain, errors, fsm
from poptimizer.evolve.dl import builder, datasets, trainer, training, worker
from poptimizer.evolve.models import evolve, genotype


def _check_keys(phenotype, cfg) -> None:
    for k, v in phenotype.items():
        assert k in cfg

        if isinstance(v, dict):
            _check_keys(v, cfg[k])


def test_cfg_match_phenotype():
    phenotype = genotype.Genotype().phenotype
    cfg = worker.Cfg.model_validate(phenotype).model_dump()
    _check_keys(phenotype, cfg)


class _FakeRunner:
    def __init__(self, script: list[training.TrainingResult | Exception]) -> None:
        self._script = script

    @override
    async def __call__(
        self,
        job: training.TrainingJob,
        data: training.TrainingData,
    ) -> training.TrainingResult:
        item = self._script.pop(0)
        if isinstance(item, Exception):
            raise item

        return item


class _FakeBuilder(builder.Builder):
    def __init__(self) -> None:
        super().__init__()
        self.built: list[tuple[domain.Day, domain.Tickers, datasets.Days, builder.Batch]] = []

    @override
    async def build(
        self,
        ctx: fsm.Ctx,
        day: domain.Day,
        tickers: domain.Tickers,
        days: datasets.Days,
        batch: builder.Batch,
    ) -> tuple[list[datasets.TickerData], list[int], list[int]]:
        self.built.append((day, tickers, days, batch))

        return [], [1], [1]


class _FakeCtx:
    def __init__(self) -> None:
        self.infos: list[tuple[str, tuple[object, ...]]] = []
        self.warnings: list[str] = []
        self.deleted: list[object] = []

    def info(self, msg: str, *args: object) -> None:
        self.infos.append((msg, args))

    def warning(self, msg: str, *args: object) -> None:
        self.warnings.append(msg % args)

    async def count_models(self) -> int:
        return 1

    async def delete(self, entity: object) -> None:
        self.deleted.append(entity)


def _result() -> training.TrainingResult:
    return training.TrainingResult(
        forecast=training.Forecast(mean=[[1.0]], cov=[[2.0]]),
        duration=5.0,
        test=evolve.TestResults(llh=[1.0, 3.0], alfa=0.1, ret=0.2),
    )


async def test_success_applies_result():
    result = _result()
    step = trainer.Trainer(_FakeRunner([result]), _FakeBuilder())
    ctx = _FakeCtx()
    model = evolve.Model(uid=evolve.random_model_uid())
    evolution = evolve.Evolution(uid=evolve.random_model_uid())

    test = await step.update_model_metrics(cast("fsm.Ctx", ctx), evolution, model)

    assert test == result.test
    assert model.mean == [[1.0]]
    assert model.cov == [[2.0]]
    assert model.alfa == 0.1
    assert model.llh == 2.0
    assert model.duration == 5.0
    assert evolution.step == 2
    assert model.day == evolution.day
    assert not ctx.deleted
    assert not ctx.warnings


async def test_short_history_adjusts_and_retries():
    result = _result()
    step = trainer.Trainer(
        _FakeRunner([errors.TooShortHistoryError("TEST", 1000), result]),
        _FakeBuilder(),
    )
    ctx = _FakeCtx()
    model = evolve.Model(uid=evolve.random_model_uid(), mean=[[0.0]], cov=[[0.0]])
    evolution = evolve.Evolution(uid=evolve.random_model_uid(), test_days=5)

    test = await step.update_model_metrics(cast("fsm.Ctx", ctx), evolution, model)

    assert test == result.test
    assert model.mean == [[1.0]]
    assert evolution.minimal_returns_days == 1000
    assert evolution.test_days == 4
    assert ctx.warnings == [
        "Minimal return days increased - 1000",
        "Test days reset - 4",
    ]
    assert not ctx.deleted


async def test_other_error_deletes_model():
    step = trainer.Trainer(_FakeRunner([errors.UseCasesError("boom")]), _FakeBuilder())
    ctx = _FakeCtx()
    model = evolve.Model(uid=evolve.random_model_uid())
    evolution = evolve.Evolution(uid=evolve.random_model_uid())

    assert await step.update_model_metrics(cast("fsm.Ctx", ctx), evolution, model) is None

    assert ctx.deleted == [model]


async def test_failed_evaluation_advances_step_and_day():
    step = trainer.Trainer(_FakeRunner([errors.UseCasesError("boom")]), _FakeBuilder())
    ctx = _FakeCtx()
    model = evolve.Model(uid=evolve.random_model_uid())
    day = date(2020, 2, 2)
    evolution = evolve.Evolution(uid=evolve.random_model_uid(), day=day, tickers=("TEST",))

    assert await step.update_model_metrics(cast("fsm.Ctx", ctx), evolution, model) is None

    assert evolution.step == 2
    assert model.day == day


async def test_invalid_batch_config_fails_validation():
    genes = genotype.Genotype().genes
    genes["batch"] = 1.0
    model = evolve.Model(uid=evolve.random_model_uid(), genes=genes)
    step = trainer.Trainer(_FakeRunner([]), _FakeBuilder())

    with pytest.raises(ValidationError):
        await step.update_model_metrics(
            cast("fsm.Ctx", _FakeCtx()), evolve.Evolution(uid=evolve.random_model_uid()), model
        )
