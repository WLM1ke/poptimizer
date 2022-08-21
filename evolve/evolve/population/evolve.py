"""Основной процесс эволюции."""
import asyncio
import itertools
import logging
from random import random
from typing import NamedTuple

import pandas as pd

from evolve.population.population import Population
from evolve.population.organism import Organism


class EvalResult(NamedTuple):
    """Результат оценки организма."""

    desc: str
    dead: bool
    slow: bool


class Evaluator:
    """Осуществляет оценку организмов."""

    async def last_date(self) -> pd.Timestamp:
        """Последняя дата с данными."""
        # TODO
        return pd.Timestamp("2022-08-19")

    def min_population_count(self) -> int:
        """Минимальная популяция для работы тестов."""
        # TODO - должна быть формула
        return 16  # noqa: WPS432

    async def eval(self, org: Organism, metrics: pd.DataFrame) -> EvalResult:
        """Оценивает организм - во время оценки организм может погибнуть."""
        # TODO

        dead = False
        if random() < 0.1:  # noqa: WPS459,S311
            dead = True

        return EvalResult(
            desc="some result",
            dead=dead,
            slow=random() < 0.4,  # noqa: WPS459,WPS432,S311
        )


class Evolution:
    """Эволюция - бесконечный процесс создания и обора новых моделей для прогноза."""

    def __init__(
        self,
        population: Population,
        evaluator: Evaluator,
    ) -> None:
        """Инициализирует эволюцию."""
        self._logger = logging.getLogger("Evolve")
        self._population = population
        self._evaluator = evaluator

    async def run(self, stop_event: asyncio.Event) -> None:
        """Запускает бесконечный процесс эволюцию."""
        count = self._evaluator.min_population_count()
        if await self._population.init(count):
            self._logger.info(f"create {count} initial organisms")

        while not stop_event.is_set():
            await self._step()

    async def _step(self) -> None:
        stats = await self._population.stats()
        self._logger.info(stats.timestamp)
        self._logger.info(stats.stats)

        self._logger.info("Parent:")
        last_date = await self._evaluator.last_date()
        org = await self._population.next(last_date)
        if await self._is_breeding(org, stats.metrics):
            await self._breed(org)

    async def _breed(self, org: Organism) -> None:
        for count in itertools.count(1):
            stats = await self._population.stats()

            self._logger.info(f"Child {count}:")
            child = await self._population.breed(org, stats.count**0.5)

            if not await self._is_breeding(child, stats.metrics):
                return

            org = child

    async def _is_breeding(self, org: Organism, metrics: pd.DataFrame) -> bool:
        self._logger.info(org)

        rez = await self._evaluator.eval(org, metrics)
        self._logger.info(rez.desc)

        if rez.dead:
            await self._population.delete(org)
            self._logger.info("removed...")

            return False

        await self._population.update(org)

        if rez.slow:
            self._logger.info("slow - do not breed...")

            return False

        return True
