"""Эволюция параметров модели."""
from typing import Optional

import numpy as np
from numpy import random

from poptimizer import config
from poptimizer.data.views import indexes, listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers

DECAY = 1 / config.TARGET_POPULATION


class Evolution:
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного сравнения пар организмов и выбора лучшего, и порождения новых
    претендентов для анализа. Размер популяция поддерживается на уровне не меньше заданного.

    За основу выбора следующего организма взяты подходы из алгоритма Метрополиса — Гастингса:

    - Текущий организм порождает потомка в некой окрестности пространства генов
    - Производится сравнение - если новый быстрее и обладает минимально допустимым качеством,
    то он становится текущим, если медленнее и обладает минимально допустимым качеством, то он становится
    текущим случайным образом с вероятностью убывающей пропорционально его скорости
    - Организмы, не обладающие минимально допустимым качеством, погибают сразу

    Масштаб окрестности изменяется, если организмы принимаются слишком часто или редко.
    """

    def __init__(self, target_population: int = config.TARGET_POPULATION):
        """Сохраняет предельный размер популяции."""
        self._target_population = target_population
        self._tickers = None
        self._end = None
        self._scale = DECAY

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        self._setup()

        step = 0
        current = None

        while True:  # noqa: WPS457
            step, current = self._step_setup(step, current)

            date = self._end.date()
            print(f"***{date}: Шаг эволюции — {step}***")  # noqa: WPS421
            population.print_stat()
            print(f"Доля принятых - {self._scale:.2%}\n")  # noqa: WPS421

            next_, new = self._step(current)

            if new:
                accepted = next_.id != current.id
                self._scale = self._scale * (1 - DECAY) + accepted * DECAY

            current = next_

    def _setup(self) -> None:
        if population.count() == 0:
            for n_org in range(1, self._target_population + 1):
                print(f"Создаются базовые организмы — {n_org}")  # noqa: WPS421
                org = population.create_new_organism()
                print(org, "\n")  # noqa: WPS421

    def _step_setup(
        self,
        step: int,
        org: Optional[population.Organism],
    ) -> tuple[int, population.Organism]:
        d_min, d_max = population.min_max_date()
        if org is None:
            self._end = d_max or listing.last_history_date()
            self._tickers = load_tickers()
            org, _ = self._next_org()

        dates = indexes.mcftrr(listing.last_history_date()).loc[self._end :].index
        if (d_min != d_max) or (len(dates) == 1):
            return step + 1, org

        self._tickers = load_tickers()
        self._end = dates[1]

        return 1, org

    def _next_org(
        self,
        current: Optional[population.Organism] = None,
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

        return population.get_next_one(None), False

    def _step(self, hunter: population.Organism) -> tuple[population.Organism, bool]:
        """Один шаг эволюции.

        Создается и оценивается потомок. Если он не обладает минимальным качеством, то погибает. Для
        оценки качества используется тест на последовательное тестирование по IR. Минимальное IR равно 0
        или больше, если популяция превышает установленный целевой уровень.

        Смена родителя происходит на основе алгоритма Метрополиса — Гастингса для более широкого
        исследования пространства признаков.
        """
        print("Родитель:")  # noqa: WPS421
        if self._eval_organism(hunter) is None:
            return self._next_org(None)

        prey, new = self._next_org(hunter)
        label = ""
        if new:
            label = " - новый организм"
        print("Претендент", label, ":", sep="")  # noqa: WPS421
        if self._eval_organism(prey) is None:
            return hunter, new

        llh_ratio = hunter.timer / prey.timer

        label = "Старый"
        sign = "<"
        if (rnd := random.uniform()) < llh_ratio:
            hunter = prey
            label = "Новый"
            sign = ">"

        print(  # noqa: WPS421
            label,
            f"родитель - timer ratio={llh_ratio:.2%}",
            sign,
            f"rnd={rnd:.2%}\n",
        )

        return hunter, new

    def _eval_organism(self, organism: population.Organism) -> Optional[population.Organism]:
        """Оценка организмов.

        Если организм уже оценен для данной даты, то он не оценивается.
        Если организм старый, то оценивается один раз.
        Если организм новый, то он оценивается для минимального количества дат из истории, необходимых
        для последовательного тестирования.
        """
        print(organism, "\n")  # noqa: WPS421

        if organism.date == self._end:
            return organism

        dates = [self._end]
        if not organism.llh:
            bounding_n = seq.minimum_bounding_n(config.P_VALUE * 2)
            dates = indexes.mcftrr(listing.last_history_date()).loc[: self._end]
            dates = dates.index[-bounding_n:].tolist()

        for date in dates:
            try:
                organism.evaluate_fitness(self._tickers, date)
            except (ModelError, AttributeError) as error:
                organism.die()
                error = error.__class__.__name__
                print(f"Удаляю - {error}\n")  # noqa: WPS421

                return None

        if self._is_dead(organism):
            return None

        return organism

    def _is_dead(self, org: population.Organism) -> bool:
        min_ir = max(0, population.count() * DECAY - 1)

        ir = org.ir
        minimum = min(ir)
        median = np.median(ir)
        lower, _ = seq.median_conf_bound(ir, config.P_VALUE * 2)

        print(  # noqa: WPS421
            f"RET required {min_ir:0.4f}:",
            f"min - {minimum:0.4f},",
            f"lower - {lower:0.4f},",
            f"median - {median:0.4f}",
        )
        if lower < min_ir:
            org.die()
            print("Умер...\n")

            return True

        print("Жив...\n")

        return False
