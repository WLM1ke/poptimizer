"""Эволюция параметров модели."""
from typing import Tuple, NoReturn, Optional

import pandas as pd

from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import Portfolio

# Максимальная популяция
MAX_POPULATION = 100


class Evolution:
    """Эволюция параметров модели.

    Одна эпоха эволюции проходит по всем организмам популяции и сравнивает их по качеству с потомком.
    Более слабы конкурирует со всеми более слабыми, чем он организмами по времени обучения - умирает
    самый медленный. Таким образом, конкуренция идет по двум параметрам - в первую очередь по
    качеству, а во вторую по времени обучения. В результате популяция стремится к эффективному фронту
    по Парето.

    Организмы могут погибнуть без сравнения, если во время его оценки произошло одна из ошибок оценки
    (слишком большая длинна истории или взрыв градиентов).

    Организмы могут выжить без сравнения, если популяция меньше установленной величины.
    """

    def __init__(self, max_population: int = MAX_POPULATION):
        self._max_population = max_population

    def evolve(self, portfolio: Portfolio) -> NoReturn:
        """Осуществляет одну эпоху эволюции.

        При необходимости создается начальная популяция из организмов по умолчанию.
        """
        tickers = tuple(portfolio.index[:-2])
        end = portfolio.date

        self._setup()

        count = population.count()

        for step, parent in enumerate(population.get_all_organisms(), 1):
            print(f"***{end.date()}: Шаг эпохи - {step}/{count}***")
            population.print_stat()
            print()

            print("Родитель:")
            parent_fitness = self._eval_and_print(parent, tickers, end)
            if parent_fitness is None:
                continue

            child = parent.make_child()
            print("Потомок:")
            child_fitness = self._eval_and_print(child, tickers, end)
            if child_fitness is None:
                continue

            if population.count() <= self._max_population:
                continue

            weakest = parent
            if parent_fitness > child_fitness:
                weakest = child

            weakest = weakest.find_weaker()
            print("Более слабый и наиболее медленный - удаляю:")
            self._eval_and_print(weakest, tickers, end)
            weakest.die()

    @staticmethod
    def _eval_and_print(
        organism: population.Organism, tickers: Tuple[str, ...], end: pd.Timestamp
    ) -> Optional[float]:
        """Оценивает организм и распечатывает метрики.

        Обрабатывает ошибки оценки и возвращает None и убивает организм в случае их наличия, а если все
        нормально, то оценку качества.
        """
        print(f"Побед - {organism.wins}")
        print(organism)
        try:
            fitness = organism.evaluate_fitness(tickers, end)
        except ModelError as error:
            organism.die()
            print(f"Удаляю - {error.__class__.__name__}")
            print()
            return None
        else:
            print(f"LLH: {fitness:.4f}")
            print(f"Timer: {organism.timer / 10 ** 9:.0f}")
            print()
            return fitness

    def _setup(self) -> NoReturn:
        """Создает популяцию из организмов по умолчанию.

        Если организмов меньше 4 - минимальное количество для осуществления эволюции.
        """
        count = population.count()
        print(f"Имеется {count} организмов из {self._max_population}")
        print()

        if count < 4:
            for i in range(1, self._max_population - count + 1):
                print(f"Создаю базовые генотипы - {i}/{self._max_population - count}")
                organism = population.create_new_organism()
                print(organism)
                print()
