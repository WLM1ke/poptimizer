"""Эволюция параметров модели."""
from typing import Optional

import numpy as np
from scipy import stats

from poptimizer import config
from poptimizer.data.views import listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import load_tickers

# Целевая вероятность удачного перехода
# За основу выбора следующего организма взят алгоритм Метрополиса — Гастингса
# Оптимальной для многомерного случая вероятностью перехода является 0.234
ACCEPTANCE = 0.234
# Понижение масштаба дисперсии, если дисбаланс итераций удачного перехода достиг 1
SCALE_DOWN = 0.9


class Evolution:
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного сравнения пар организмов и выбора лучшего, и порождения новых
    претендентов для анализа. Популяция организмов поодерживается на заданном уровне. За основу выбора
    следующего организма взяты подходы из алгоритма Метрополиса — Гастингса:

    - Порождается случайная популяция, из которой выберается первый организм
    - Выбирается претендент - при отсутсвии свободных мест в популяции из популяции, а при наличии - в
    случайной окрестности текущего
    - Производится сравнение - если новый лучше, то он становится текущим, если новый хуже,
    то он становится текущим случайным образом с вероятностью убыващей пропорционально его качеству
    - Новый не принятый организм не включается в популяцию, а существующий не принятый может быть
    исключен из популяции, если он значимо хуже

    При создании нового оргнизма, окресность около текущего выбирается пропорционально расстоянию до
    случайного организма в популяции, а коэффициент пропорциональности динамически корректируется для
    достижения целевого уровня принятия нового организма 0.234
    """

    def __init__(self, max_population: int = config.MAX_POPULATION):
        """Сохраняет предельный размер популяции."""
        self._max_population = max_population
        self._tickers = load_tickers()
        self._end = None
        self._scale = 0

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        current = None
        step = 0

        while True:  # noqa: WPS457

            if (new_end := listing.last_history_date()) != self._end:
                step = 0
                self._end = new_end

            step += 1
            date = self._end.date()
            print(f"***{date}: Шаг эволюции — {step}***")  # noqa: WPS421
            population.print_stat()
            print(f"Фактор - {self.scale():.2%}\n")  # noqa: WPS421

            if current is None:
                current = self._setup()

            current = self._step(current)

    def scale(self) -> float:
        """Расчет фактора масштаба при порождении нового организма."""
        return SCALE_DOWN ** self._scale

    def _setup(self) -> population.Organism:
        """При необходимости создает популяцию из организмов по умолчанию и возвращает стартовый."""
        if population.count() == 0:
            for n_org in range(1, self._max_population + 1):
                print(f"Создаются базовые организмы — {n_org}")  # noqa: WPS421
                org = population.create_new_organism()
                print(org, "\n")  # noqa: WPS421

        return population.get_next()

    def _step(self, hunter: population.Organism) -> Optional[population.Organism]:

        print("Охотник:")  # noqa: WPS421
        if self._eval_organism(hunter) is None:
            return None

        prey, new = self._next_org(hunter)
        label = ""
        if new:
            self._scale -= 1 - ACCEPTANCE
            label = " - новый организм"
        print("Добыча", label, ":", sep="")  # noqa: WPS421
        if self._eval_organism(prey) is None:
            self._scale += 1

            return hunter

        p_value = _eval_p_value(hunter, prey)
        llh_ratio = np.inf
        if (1 - p_value) != 0:
            llh_ratio = p_value / (1 - p_value)

        accepted = False
        label = "Старый"
        sign = "<"
        if (rnd := np.random.uniform()) < llh_ratio:
            accepted = True
            hunter = prey
            label = "Новый"
            sign = ">"

        print(  # noqa: WPS421
            label,
            f"охотник - llh ratio={llh_ratio:.2%}",
            sign,
            f"rnd={rnd:.2%}\n",
        )

        if new and not accepted:
            self._scale += 1
            prey.die()
            print("Добыча не принята в популяцию...\n")  # noqa: WPS421

        if not new and not accepted and p_value < config.P_VALUE:
            prey.die()
            print(  # noqa: WPS421
                f"Добыча уничтожена - p_value={p_value:.2%}",
                "<=",
                f"{config.P_VALUE:.2%}\n",
            )

        return hunter

    def _next_org(self, parent: population.Organism) -> tuple[population.Organism, bool]:
        if population.count() < self._max_population:
            return parent.make_child(self.scale()), True

        return population.get_next(parent), False

    def _eval_organism(self, organism: population.Organism) -> Optional[population.Organism]:
        print(organism, "\n")  # noqa: WPS421

        try:
            organism.evaluate_fitness(self._tickers, self._end)
        except (ModelError, AttributeError) as error:
            organism.die()
            error = error.__class__.__name__
            print(f"Удаляю - {error}\n")  # noqa: WPS421

            return None

        print(f"Timer: {organism.timer:.0f}\n")  # noqa: WPS421

        return organism


def _eval_p_value(hunter: population.Organism, prey: population.Organism) -> float:
    p_value = 0.5

    if hunter.scores == 1 and prey.scores == 1:
        p_value = hunter.llh[0] < prey.llh[0]
    elif prey.scores == 1:
        p_value = stats.percentileofscore(hunter.llh, prey.llh[0]) / 100
    elif hunter.scores > 1 and prey.scores > 1:
        _, p_value = stats.ttest_ind(
            hunter.llh,
            prey.llh,
            permutations=10 ** 6,
            alternative="greater",
        )

    return p_value
