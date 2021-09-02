"""Эволюция параметров модели."""
from typing import Optional

import numpy as np
import pandas as pd
from numpy import random
from scipy import stats

from poptimizer import config
from poptimizer.data.views import indexes, listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population
from poptimizer.portfolio.portfolio import load_tickers

# За основу выбора следующего организма взят алгоритм Метрополиса — Гастингса. В рамках него
# оптимальную долю принятых предложений рекомендуется брать от 0.234 для многомерного случая до 0.44 для
# одномерного. В тоже время алгоритм сохраняет свою эффективность в диапазоне от 0.1 до 0.6
# http://probability.ca/jeff/ftpdir/galinart.pdf
#
# Библиотеке PyMC3 ориентируются не на конкретное целевое значение, а на диапазон 0.2-0.5
MIN_ACCEPTANCE = 0.234
MAX_ACCEPTANCE = 0.44
# Штраф за большое время тренировки
TIME_TEMPERATURE = 0


class Evolution:
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного сравнения пар организмов и выбора лучшего, и порождения новых
    претендентов для анализа. Размер популяция поддерживается на уровне не меньше заданного.

    За основу
    выбора следующего организма взяты подходы из алгоритма Метрополиса — Гастингса:

    - Текущий организм порождает потомка в некой окрестности пространства генов
    - Производится сравнение - если новый лучше, то он становится текущим, если новый хуже,
      то он становится текущим случайным образом с вероятностью убывающей пропорционально его качеству

    Масштаб окрестности изменяется, если организмы принимаются слишком часто или редко.

    При появлении новых данных происходит сравнение существующих организмов - статистически значимо
    более плохие удаляются.
    """

    def __init__(self, min_population: int = config.MIN_POPULATION):
        """Сохраняет предельный размер популяции."""
        self._min_population = min_population
        self._tickers = None
        self._end = None
        self._scale = random.uniform()

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        step = 0
        trial = 0
        acceptance = 0
        current = self._setup()

        while True:  # noqa: WPS457
            d_min, d_max = population.min_max_date()

            if (population.count() >= self._min_population) and (d_min == d_max):
                dates = indexes.mcftrr(listing.last_history_date()).loc[self._end :].index
                if len(dates) > 1:
                    step = 0
                    self._tickers = load_tickers()
                    self._end = dates[1]

            step += 1
            date = self._end.date()
            print(f"***{date}: Шаг эволюции — {step}***")  # noqa: WPS421
            population.print_stat()
            print(  # noqa: WPS421
                f"Доля принятых - {acceptance:.2%}",
                "/",
                f"Фактор - {self._scale:.2%}\n",
            )

            next_, new = self._step(current)

            accepted = next_.id != current.id

            if new:
                acceptance = (acceptance * trial + accepted) / (trial + 1)
                trial += 1
                self._scale = _tune_scale(self._scale, acceptance)

            current = next_

    def _setup(self) -> pd.Timestamp:
        """При необходимости создает популяцию из организмов по умолчанию и устанавливает дату."""
        self._tickers = load_tickers()
        self._end = population.min_max_date()[1]

        if population.count() == 0:
            self._end = listing.last_history_date()
            for n_org in range(1, self._min_population + 1):
                print(f"Создаются базовые организмы — {n_org}")  # noqa: WPS421
                org = population.create_new_organism()
                print(org, "\n")  # noqa: WPS421

        return self._next_org(None)[0]

    def _next_org(
        self,
        current: Optional[population.Organism],
    ) -> tuple[population.Organism, bool]:
        """Возвращает следующий организм и информацию новый ли он.

        В первую очередь берутся не переоцененные существующие организмы. При их отсутствии создается
        потомок текущего в окрестности. При отсутствии текущего (обычно после возобновления прерванной
        эволюции) берется самый старый организм.
        """
        if (org := population.get_next_one(self._end)) is not None:
            return org, False

        if current is not None:
            return current.make_child(self._scale), True

        return next(population.get_oldest()), False

    def _step(self, hunter: population.Organism) -> tuple[population.Organism, bool]:
        """Один шаг эволюции.

        Создается и оценивается потомок. Если это существующий организм, то он может быть уничтожен,
        если он значимо хуже текущего.

        После этого любой потомок (старый или новый) принимается на основе алгоритма
        Метрополиса — Гастингса.
        """
        print("Охотник:")  # noqa: WPS421
        if self._eval_organism(hunter) is None:
            return self._next_org(None)

        prey, new = self._next_org(hunter)
        label = ""
        if new:
            label = " - новый организм"
        print("Добыча", label, ":", sep="")  # noqa: WPS421
        if self._eval_organism(prey) is None:
            return hunter, new

        p_value = _hunt(hunter, prey)
        print(f"p_value={p_value:.2%}")  # noqa: WPS421

        if p_value < config.P_VALUE:
            prey.die()
            print("Добыча уничтожена...\n")  # noqa: WPS421

            return hunter, new

        llh_ratio = np.inf
        if p_value != 1:
            temperature = (prey.timer / hunter.timer) ** TIME_TEMPERATURE
            llh_ratio = (p_value / (1 - p_value)) ** temperature

        label = "Старый"
        sign = "<"
        if (rnd := random.uniform()) < llh_ratio:
            hunter = prey
            label = "Новый"
            sign = ">"

        print(  # noqa: WPS421
            label,
            f"охотник - llh ratio={llh_ratio:.2%}",
            sign,
            f"rnd={rnd:.2%}\n",
        )

        return hunter, new

    def _eval_organism(self, organism: population.Organism) -> Optional[population.Organism]:
        print(organism, "\n")  # noqa: WPS421

        if organism.date == self._end:
            print("Уже оценен\n")  # noqa: WPS421

            return organism

        try:
            organism.evaluate_fitness(self._tickers, self._end)
        except (ModelError, AttributeError) as error:
            organism.die()
            error = error.__class__.__name__
            print(f"Удаляю - {error}\n")  # noqa: WPS421

            return None

        print()  # noqa: WPS421

        return organism


def _hunt(hunter: population.Organism, prey: population.Organism) -> float:
    if len(prey.llh) == 1:
        return _p_value_new(hunter, prey)

    test_func = stats.ttest_rel
    if len(hunter.llh) != len(prey.llh):
        test_func = stats.ttest_ind

    _, p_value = test_func(
        hunter.llh,
        prey.llh,
        alternative="greater",
    )

    return p_value


def _p_value_new(hunter: population.Organism, prey: population.Organism) -> float:
    llh_delta = prey.llh[0] - hunter.llh[0]

    sample = population.get_llh(hunter.date)
    sample = np.array(sample)
    sample = sample.reshape(-1, 1) - sample.reshape(1, -1)
    sample = sample.flatten()

    return stats.percentileofscore(sample, llh_delta, "mean") / 100


def _tune_scale(scale: float, acc_rate: float) -> float:
    """Корректировка размера шага."""
    if acc_rate < MIN_ACCEPTANCE:
        return min(scale, random.uniform())
    elif acc_rate > MAX_ACCEPTANCE:
        return max(scale, random.uniform())

    return scale
