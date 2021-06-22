"""Эволюция параметров модели."""
from typing import Optional

import pandas as pd

from poptimizer.config import MAX_POPULATION
from poptimizer.data.views import listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import load_from_yaml

# Понижение масштаба разницы между родителями
SCALE_DOWN = 0.9


class Evolution:
    """Эволюция параметров модели.

    Эволюция бесконечный процесс обновления параметров модели. В начале каждого шага осуществляется
    проверка наличия новых данных. В случае их появления счетчик шага сбрасывается и начинается
    очередной этап с новыми данными.

    Шаг состоит из:
    - перетренировки одной из существующих моделей для исключения возможности случайной удачно
    тренировки, так как в первую очередь интересует получение параметров обеспечивающий стабильность
    хороших результатов
    - создания потом на основе этой модели
    - уничтожения самого плохого организма в популяции

    Организмы могут погибнуть вне очереди, если во время его оценки произошло ошибка (взрыв
    градиентов, невалидные параметры и т.д.).

    Уничтожение может быть пропущено, если размер популяции меньше установленной величины.

    Процесс выбора организма для перетренировки, размножения и уничтожения регулируется функциями
    модуля популяции.
    """

    def __init__(self, max_population: int = MAX_POPULATION):
        """Сохраняет предельный размер популяции."""
        self._max_population = max_population

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из организмов по умолчанию.
        """
        self._setup()

        end = listing.last_history_date()
        port = load_from_yaml(end)
        tickers = tuple(port.index[:-2])
        scale = 1.0
        step = 0

        while True:

            if (new_end := listing.last_history_date()) != end:
                end = new_end
                scale = 1.0
                step = 0

            step += 1
            print(f"***{end.date()}: Шаг эволюции — {step}***")
            population.print_stat()
            print(f"Фактор - {scale:.2%}\n")

            parent = population.get_parent()
            print("Переоцениваю родителя:")
            if _eval_and_print(parent, tickers, end) is None:
                scale *= SCALE_DOWN
                continue

            child = parent.make_child(scale)
            print("Потомок:")
            if _eval_and_print(child, tickers, end) is None:
                scale *= SCALE_DOWN
                continue

            if population.count() > self._max_population:
                _kill_weakest(child)

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
    try:
        print(organism)
        fitness = organism.evaluate_fitness(tickers, end)
    except (ModelError, AttributeError) as error:
        organism.die()
        print(f"Удаляю - {error.__class__.__name__}\n")
        return None

    print(f"LLH: {fitness:.4f}")
    print(f"Timer: {organism.timer / 10 ** 9:.0f}\n")
    return fitness


def _kill_weakest(organism: population.Organism) -> None:
    weakest = organism.find_weaker()
    print("Наиболее слабый — удаляю:")
    print(f"Побед - {weakest.wins}")
    print(weakest)
    print(f"LLH: {weakest.llh:.4f}")
    print(f"Timer: {weakest.timer / 10 ** 9:.0f}\n")
    weakest.die()
