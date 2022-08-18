"""Основной процесс эволюции."""
import asyncio
import itertools
import logging

from evolve.population.population import Organism, Population


class Evolution:
    """Эволюция - бесконечный процесс создания и обора новых моделей для прогноза."""

    def __init__(
        self,
        population: Population,
    ) -> None:
        """Инициализирует эволюцию."""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._population = population

    async def run(self, event: asyncio.Event) -> None:
        """Запускает бесконечный процесс эволюцию."""
        async for org in self._population:
            await self._step(org)

            if event.is_set():
                return

    async def _step(self, org: Organism) -> None:
        for stat in await self._population.stats():
            self._logger.info(stat)

        self._logger.info("Parent:")
        if not await self._is_breeding(org):
            return

        for count in itertools.count(1):
            self._logger.info(f"Child {count}:")
            child = await self._population.breed(org)

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
