"""Эволюция параметров модели."""
from typing import Optional

import pandas as pd

from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import Portfolio

# Максимальная популяция
MAX_POPULATION = 90

# Понижение масштаба разницы между родителями
SCALE_DOWN = 0.9


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
        """Сохраняет предельный размер популяции."""
        self._max_population = max_population

    def evolve(self, portfolio: Portfolio) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из организмов по умолчанию.
        """
        self._setup()

        tickers = tuple(portfolio.index[:-2])
        end = portfolio.date
        scale = 1.0
        step = 0

        while True:
            step += 1
            print(f"***{end.date()}: Шаг эволюции — {step}***")
            population.print_stat()
            print(f"Фактор - {scale:.2%}\n")

            parent = population.get_parent()

            child = parent.make_child(scale)
            print("Потомок:")
            if _eval_and_print(child, tickers, end) is None:
                scale *= SCALE_DOWN
                continue

            if population.count() <= self._max_population:
                continue

            _kill_weakest(child)

            print("Переоцениваю родителя:")
            if _eval_and_print(parent, tickers, end) is None:
                scale *= SCALE_DOWN

    def _setup(self) -> None:
        """Создает популяцию из организмов по умолчанию.

        Если организмов меньше 2 - минимальное количество для осуществления эволюции.
        """
        count = population.count()
        print(f"Имеется {count} организмов из {self._max_population}")
        print()

        if count < 2:
            for n_org in range(1, self._max_population - count + 1):
                print(f"Создаю базовые генотипы — {n_org}/{self._max_population - count}")
                organism = population.create_new_organism()
                print(organism, end="\n\n")


def _eval_and_print(
    organism: population.Organism,
    tickers: tuple[str, ...],
    end: pd.Timestamp,
) -> Optional[float]:
    """Оценивает организм, распечатывает метрики.

    Обрабатывает ошибки оценки и возвращает None и убивает организм в случае их наличия, а если все
    нормально, то оценку качества.
    """
    print(f"Побед — {organism.wins}")
    print(organism)
    try:
        fitness = organism.evaluate_fitness(tickers, end)
    except ModelError as error:
        organism.die()
        print(f"Удаляю - {error.__class__.__name__}\n")
        return None

    print(f"LLH: {fitness:.4f}")
    print(f"Timer: {organism.timer / 10 ** 9:.0f}\n")
    return fitness


def _kill_weakest(child):
    weakest = child.find_weaker()
    print("Наиболее слабый — удаляю:")
    print(f"Побед - {weakest.wins}")
    print(weakest)
    print(f"LLH: {weakest.llh:.4f}")
    print(f"Timer: {weakest.timer / 10 ** 9:.0f}\n")
    weakest.die()
