"""Эволюция параметров модели."""
from typing import Optional

from numpy import random

from poptimizer import config
from poptimizer.data.views import indexes, listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers

DECAY = 1 / config.MIN_POPULATION


class Evolution:
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного сравнения пар организмов и выбора лучшего, и порождения новых
    претендентов для анализа. Размер популяция поддерживается на уровне не меньше заданного.

    За основу выбора следующего организма взяты подходы из алгоритма Метрополиса — Гастингса:

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
        self._scale = 1

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
            print(f"Доля принятых - {self._scale:.2%}")  # noqa: WPS421

            next_, new = self._step(current)

            if new:
                accepted = next_.id != current.id
                self._scale = self._scale * (1 - DECAY) + accepted * DECAY

            current = next_

    def _setup(self) -> None:
        if population.count() == 0:
            for n_org in range(1, self._min_population + 1):
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
        org, _ = self._next_org()

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

        Создается и оценивается потомок. Сравнивается с текущим. Если один из организмов значимо хуже, то
        он уничтожается. Сравнение происходит на половинной значимости, так как любой организ
        сравнивается два раза - с предыдущим и со следующим.

        Если уничтожение не произошло, то для старых организмов обязательно происходит смена
        охотника, чтобы сравнение двух организмов происходило все время с одним и тем жеб что требует
        тест на последовательное тестирование.

        Для новых организмов смена охотника происходит на основе алгоритма Метрополиса — Гастингса для
        более широкого исследования пространства признаков.
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

        if p_value == 0:
            prey.die()
            print("Добыча уничтожена...\n")  # noqa: WPS421

            return hunter, new

        if p_value == 1:
            hunter.die()
            print("Охотник уничтожен...\n")  # noqa: WPS421

            return prey, new

        if not new:
            print("Смена охотника...\n")  # noqa: WPS421

            return prey, new

        llh_ratio = hunter.timer / prey.timer

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
        """Оценка организмов.

        Если организм уже оценен для данной даты, то он не оценивается.
        Если организм старый, то оценивается один раз.
        Если организм новый, то он оценивается для минимального количества дат из истории, необходимых
        для последовательного тестирования.
        """
        print(organism, "\n")  # noqa: WPS421

        if organism.date == self._end:
            print("Уже оценен\n")  # noqa: WPS421

            return organism

        dates = [self._end]
        if not organism.llh:
            bounding_n = seq.minimum_bounding_n(config.P_VALUE / 2)
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

        print()  # noqa: WPS421

        return organism


def _hunt(hunter: population.Organism, prey: population.Organism) -> float:
    diffs = zip(hunter.llh, prey.llh)
    type_ = "llh"
    if len(prey.llh) == len(prey.ir):
        diffs = zip(hunter.ir, prey.ir)
        type_ = "ir"

    diffs = [diff[0] - diff[1] for diff in diffs]
    minimum = min(diffs)
    maximum = max(diffs)
    lower, upper = seq.median_conf_bound(diffs, config.P_VALUE / 2)

    print(  # noqa: WPS421
        f"Median {type_} differance - [{minimum:0.4f},",
        f"{lower:0.4f},",
        f"{upper:0.4f},",
        f"{maximum:0.4f}]",
    )

    return max(min(-lower / (upper - lower), 1), 0)
