"""Эволюция параметров модели."""
import datetime
import functools
import logging
import operator
from typing import Optional

import numpy as np
from numpy import random

from poptimizer import config
from poptimizer.data.views import indexes, listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers

DECAY = 1 / config.TARGET_POPULATION
# Делается поправка на множественное тестирование для одностороннего теста для двух метрик
ALFA = config.P_VALUE * 2 / (config.TARGET_POPULATION * 2)


class Evolution:  # noqa: WPS214
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного сравнения пар организмов и выбора лучшего, и порождения новых
    претендентов для анализа. Размер популяция поддерживается на уровне не меньше заданного.

    За основу выбора следующего организма взяты подходы из алгоритма Метрополиса — Гастингса:

    - Текущий организм порождает потомка в некой окрестности пространства генов
    - Производится сравнение - если новый быстрее и обладает минимально допустимым качеством, то он
      становится текущим, если медленнее и обладает минимально допустимым качеством, то он становится
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
        self._logger = logging.getLogger()

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        self._setup()

        step = 0
        current = None

        while _check_time_range():
            step, current = self._step_setup(step, current)

            date = self._end.date()
            self._logger.info(f"***{date}: Шаг эволюции — {step}***")  # noqa: WPS421
            population.print_stat()
            self._logger.info(f"Доля принятых - {self._scale:.2%}\n")  # noqa: WPS421

            next_, new = self._step(current)

            if new:
                accepted = next_.id != current.id
                self._scale = self._scale * (1 - DECAY) + accepted * DECAY

            current = next_

    def _setup(self) -> None:
        if population.count() == 0:
            for n_org in range(1, self._target_population + 1):
                self._logger.info(f"Создаются базовые организмы — {n_org}")  # noqa: WPS421
                org = population.create_new_organism()
                self._logger.info(org, "\n")  # noqa: WPS421

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
        self._logger.info("Родитель:")  # noqa: WPS421
        if self._eval_organism(hunter) is None:
            return self._next_org(None)

        prey, new = self._next_org(hunter)
        label = ""
        if new:
            label = " - новый организм"
        self._logger.info(f"Претендент{label}:")  # noqa: WPS421
        if self._eval_organism(prey) is None:
            return hunter, new

        llh_ratio = hunter.timer / prey.timer

        label = "Старый"
        sign = "<"
        if (rnd := random.uniform()) < llh_ratio:
            hunter = prey
            label = "Новый"
            sign = ">"

        self._logger.info(f"{label} родитель - timer ratio={llh_ratio:.2%} {sign} rnd={rnd:.2%}" + "\n")

        return hunter, new

    def _eval_organism(self, organism: population.Organism) -> Optional[population.Organism]:
        """Оценка организмов.

        Если организм уже оценен для данной даты, то он не оценивается.
        Если организм старый, то оценивается один раз.
        Если организм новый, то он оценивается для минимального количества дат из истории, необходимых
        для последовательного тестирования.
        """
        try:
            self._logger.info(str(organism) + "\n")  # noqa: WPS421
        except AttributeError as error:
            organism.die()
            error = error.__class__.__name__
            self._logger.error(f"Удаляю - {error}\n")
            return None

        if organism.date == self._end:
            return organism

        dates = [self._end]
        if not organism.llh:
            bounding_n = seq.minimum_bounding_n(ALFA)
            dates = indexes.mcftrr(listing.last_history_date()).loc[: self._end]
            dates = dates.index[-bounding_n:].tolist()

        for date in dates:
            try:
                organism.evaluate_fitness(self._tickers, date)
            except (ModelError, AttributeError) as error:
                organism.die()
                error = error.__class__.__name__
                self._logger.error(f"Удаляю - {error}\n")  # noqa: WPS421

                return None

        if self._is_dead(organism):
            return None

        return organism

    def _is_dead(self, org: population.Organism) -> bool:
        """Используется тестирование разницы llh и ret против всех организмов базовой популяции.

        Используются тесты для связанных выборок, поэтому предварительно происходит выравнивание по
        датам и отбрасывание значений не имеющих пары (возможно первое значение и хвост из старых
        значений более старого организма).
        """
        for metric in ("LLH", "RET"):
            maximum, median, upper = _select_worst_bound(
                targets=list(population.base_pop_metrics()),
                candidate={"date": org.date, "llh": org.llh, "ir": org.ir},
                metric=metric,
            )

            self._logger.info(  # noqa: WPS421
                f"{metric} worst difference: median - {median:0.4f}, upper - {upper:0.4f}, max - {maximum:0.4f}"
            )

            if upper < 0:
                org.die()
                self._logger.info("Умер...\n")  # noqa: WPS421

                return True

        self._logger.info("Жив...\n")  # noqa: WPS421

        return False


def _check_time_range() -> bool:
    hour = datetime.datetime.today().hour

    if config.START_EVOLVE_HOUR == config.STOP_EVOLVE_HOUR:
        return True

    if config.START_EVOLVE_HOUR < config.STOP_EVOLVE_HOUR:
        return config.START_EVOLVE_HOUR <= hour < config.STOP_EVOLVE_HOUR

    before_midnight = config.START_EVOLVE_HOUR <= hour
    after_midnight = hour < config.STOP_EVOLVE_HOUR

    return before_midnight or after_midnight


def _select_worst_bound(targets: list[dict], candidate: dict, metric: str) -> tuple[float, float, float]:
    """Выбирает минимальное значение верхней границы доверительного интервала.

    Если данный организм не уступает какому либо организму, то верхняя граница будет положительной. В
    то же время сравнение может идти против самого себя, в этом случае граница будет нулевой. Для
    исключения этого случая нулевое значение подменяется на inf.
    """
    bounds = map(functools.partial(_aligned_tests, candidate=candidate, metric=metric), targets)

    median, upper, maximum = min(
        bounds,
        key=lambda bound: bound[1] or np.inf,
    )

    return maximum, median, upper


def _aligned_tests(target: dict, candidate: dict, metric: str) -> tuple[float, float, float]:
    candidate_start = 0
    target_start = 0

    if candidate["date"] > target["date"]:
        candidate_start = 1
    if candidate["date"] < target["date"]:
        target_start = 1

    candidate_data = candidate["ir"][candidate_start:]
    target_data = target["ir"][target_start:]

    if metric == "LLH":
        candidate_data = candidate["llh"][candidate_start:]
        target_data = target["llh"][target_start:]

    return _test_diff(target_data, candidate_data)


def _test_diff(target: list[float], candidate: list[float]) -> tuple[float, float, float]:
    diff = list(map(operator.sub, candidate, target))
    _, upper = seq.median_conf_bound(diff, ALFA)

    return np.median(diff), upper, np.max(diff)
