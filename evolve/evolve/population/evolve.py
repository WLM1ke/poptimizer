"""Основной процесс эволюции."""
import itertools
import logging
from typing import AsyncIterable, AsyncIterator, NamedTuple


class Organism:
    """Организм."""


class EvalResult(NamedTuple):
    """Результат оценки организма."""

    desc: str
    dead: bool
    slow: bool


class Population(AsyncIterable[Organism]):
    """Представляет популяцию организмов."""

    def __aiter__(self) -> AsyncIterator[Organism]:
        """Последовательно выдает организмы для эволюционного отбора."""
        raise NotImplementedError

    async def stats(self) -> str:
        """Представляет информацию о популяции."""
        raise NotImplementedError

    async def breed_org(self, org: Organism) -> Organism:
        """Создает и возвращает потомка организма."""
        raise NotImplementedError

    async def eval(self, org: Organism) -> EvalResult:
        """Оценивает организм - во время оценки организм может погибнуть."""
        raise NotImplementedError


class Evolution:
    """Эволюция - бесконечный процесс создания и обора новых моделей для прогноза."""

    def __init__(
        self,
        population: Population,
    ) -> None:
        """Инициализирует эволюцию."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._population = population

    async def run(self) -> None:
        """Запускает бесконечный процесс эволюцию."""
        async for org in self._population:
            await self._step(org)
            self._logger.info("stopping...")

            return

    async def _step(self, org: Organism) -> None:
        self._logger.info(await self._population.stats())

        self._logger.info("Parent:")
        if not await self._is_breeding(org):
            return

        for count in itertools.count(1):
            self._logger.info(f"Child {count}:")
            child = await self._population.breed_org(org)

            if not await self._is_breeding(child):
                return

            org = child

    async def _is_breeding(self, org: Organism) -> bool:
        self._logger.info(org)

        rez = await self._population.eval(org)
        self._logger.info(rez.desc)

        if rez.dead:
            self._logger.info("removed...")

            return False

        if rez.slow:
            self._logger.info("slow - do not breed...")

            return False

        return True
