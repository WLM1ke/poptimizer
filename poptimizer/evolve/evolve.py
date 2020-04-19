"""Эволюция параметров модели."""
from typing import Tuple, NoReturn

import pandas as pd

from poptimizer.dl import ModelError
from poptimizer.evolve import population

# Максимальная популяция
MAX_POPULATION = 100


class Evolution:
    """Эволюция параметров модели.

    Одна эпоха эволюции проходит по всем организмам популяции и сравнивает их по качеству с потомком -
    выживает сильнейший. Более слабый родитель  может выжить, если в популяции организмов меньше
    необходимого.

    Организм погибает без сравнения, если во время его оценки произошло одна из ошибок оценки (слишком
    большая длинна истории, взрыв градиентов или вырожденная модель).
    """

    def __init__(self, max_population: int = MAX_POPULATION):
        self._max_population = max_population

    def evolve(self, tickers: Tuple[str, ...], end: pd.Timestamp) -> NoReturn:
        """Осуществляет одну эпоху эволюции.

        При необходимости создается начальная популяция из организмов по умолчанию.
        """
        self._setup()

        new_children = 0
        count = population.count()

        for step, parent in enumerate(population.get_all_organisms(), 1):
            print(f"***{end.date()}: Шаг эпохи - {step}/{count}***")
            population.print_stat()
            print()

            print(f"Родитель - {parent.wins} победы:")
            print(parent)
            try:
                parent_sharpe = parent.evaluate_fitness(tickers, end)
            except ModelError as error:
                parent.die()
                print(f"Удаляю родителя - {error.__class__.__name__}")
                print()
                continue
            else:
                print(f"IR: {parent_sharpe:.4f}")
                print()

            child = parent.make_child()
            print("Потомок:")
            new_children += 1
            print(child)
            try:
                child_sharpe = child.evaluate_fitness(tickers, end)
            except ModelError as error:
                child.die()
                new_children -= 1
                print(f"Удаляю ребенка - {error.__class__.__name__}")
                print()
                continue
            else:
                print(f"IR: {child_sharpe:.4f}")
                print()

            excess = population.count() > self._max_population

            if parent_sharpe > child_sharpe:
                child.die()
                new_children -= 1
                print("Удаляю потомка.")
            elif excess:
                parent.die()
                print("Удаляю родителя.")

            print(f"Добавлено потомков - {new_children}...")
            print()

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
