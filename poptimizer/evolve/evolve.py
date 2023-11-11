"""Эволюция параметров модели."""
import datetime
import itertools
import logging
import operator
from typing import Optional

import numpy as np
from scipy import stats

from poptimizer import config
from poptimizer.data.views import listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers


class Evolution:  # noqa: WPS214
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного создания организмов и сравнения их характеристик с медианными значениями по
    популяции. Сравнение осуществляется с помощью последовательного теста для медиан, который учитывает изменение
    значимости тестов при множественном тестировании по мере появления данных за очередной период времени. Дополнительно
    осуществляется коррекция на множественное тестирование на разницу llh и доходности.
    """

    def __init__(self):
        """Инициализирует необходимые параметры."""
        self._tickers = None
        self._end = None
        self._logger = logging.getLogger()
        self._tests = 1

    @property
    def _scale(self) -> float:
        return population.count() ** 0.5

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        step = 0
        self._setup()

        while _check_time_range():
            org = population.get_next_one()
            step = self._step_setup(step)

            date = self._end.date()
            self._logger.info(f"***{date}: Шаг эволюции — {step}***")
            population.print_stat()
            count = population.count()
            self._logger.info(
                f"Тестов - {self.tests} / "
                f"Организмов - {count} / "
                f"Оценок - {population.min_scores()}-{population.max_scores()}\n"
            )

            self._step(org)

            delta = population.count() - count

            if delta > 0 and (count + delta) > config.TARGET_POPULATION:
                self._tests += 1

    @property
    def tests(self):
        count = population.count()
        min_tests = seq.minimum_bounding_n(config.P_VALUE / (count + 1))
        self._tests = max(min_tests, self._tests)

        return self._tests

    def _step_setup(
        self,
        step: int,
    ) -> int:
        d_min, d_max = population.min_max_date()

        if self._tickers is None:
            self._tickers = load_tickers()
            self._end = d_max or listing.all_history_date(self._tickers)[-1]

        dates = listing.all_history_date(self._tickers, start=self._end)

        if (d_min != self._end) or (len(dates) == 1):
            return step + 1

        self._end = dates[1]

        return 1

    def _setup(self) -> None:
        if population.count() == 0:
            for i in range(1, config.TARGET_POPULATION + 1):
                self._logger.info(f"Создается базовый организм {i}:")
                org = population.create_new_organism()
                self._logger.info(f"{org}\n")

        self._tests = max(population.min_scores(), seq.minimum_bounding_n(config.P_VALUE / (population.count() + 1)))

    def _step(self, hunter: population.Organism) -> Optional[population.Organism]:
        """Один шаг эволюции."""
        have_more_dates = hunter.date and self._end > hunter.date

        label = ""
        if not hunter.scores:
            label = " - новый организм"

        self._logger.info(f"Родитель{label}:")
        if self._eval_organism(hunter) is None:
            return None

        if have_more_dates and (population.count() > config.TARGET_POPULATION):
            self._logger.info("Появились новые данные - не размножается...\n")

            return None

        for n_child in itertools.count(1):
            self._logger.info(f"Потомок {n_child}:")

            hunter = hunter.make_child(1 / hunter.scores)
            if (margin := self._eval_organism(hunter)) is None:
                return None

            if (rnd := np.random.random()) < (slowness := margin[1]):
                self._logger.info(f"Медленный не размножается {rnd=:.2%} < {slowness=:.2%}...\n")

                return None

    def _eval_organism(self, organism: population.Organism) -> tuple[float, float] | None:
        try:
            self._logger.info(f"{organism}\n")
        except AttributeError as err:
            organism.die()
            self._logger.error(f"Удаляю - {err}\n")

            return None

        all_dates = listing.all_history_date(self._tickers, end=self._end)

        try:
            if organism.date == self._end:
                prob = 1 - _time_delta(organism)
                retry = max(population.count() - config.TARGET_POPULATION, stats.geom.rvs(prob))
                dates = all_dates[-max(self.tests, (organism.scores + retry)): -organism.scores].tolist()
                organism.retrain(self._tickers, dates[0])
            elif organism.scores:
                if self._tickers != tuple(organism.tickers):
                    organism.retrain(self._tickers, self._end)
                dates = [self._end]
            else:
                dates = all_dates[-self.tests:].tolist()
                organism.retrain(self._tickers, dates[0])
        except (ModelError, AttributeError) as error:
            organism.die()
            self._logger.error(f"Удаляю - {error}\n")

            return None

        for date in reversed(dates):
            try:
                organism.evaluate_fitness(self._tickers, date)
            except (ModelError, AttributeError) as error:
                organism.die()
                self._logger.error(f"Удаляю - {error}\n")

                return None

        return self._get_margin(organism)

    def _get_margin(self, org: population.Organism) -> tuple[float, float] | None:
        """Используется тестирование разницы llh и ret против самого старого организма.

        Используются тесты для связанных выборок, поэтому предварительно происходит выравнивание по
        датам и отбрасывание значений не имеющих пары (возможно первое значение и хвост из старых
        значений более старого организма).
        """
        names = {"llh": "LLH", "ir": "RET"}
        upper_bound = -np.inf

        for metric in ("ir", "llh"):
            median, upper, maximum = _select_worst_bound(
                candidate={"date": org.date, "llh": org.llh, "ir": org.ir},
                metric=metric,
            )

            self._logger.info(
                " ".join(
                    [
                        f"{names[metric]} worst difference:",
                        f"median - {median:0.4f},",
                        f"upper - {upper:0.4f},",
                        f"max - {maximum:0.4f}",
                    ],
                ),
            )

            if upper < 0:
                org.die()
                self._logger.info("Исключен из популяции...\n")

                return None

            upper_bound = max(upper_bound, upper)

        org.upper_bound = upper_bound
        time_score = _time_delta(org)

        self._logger.info(f"Upper bound - {upper_bound:.4f}, Slowness - {time_score:.2%}\n")  # noqa: WPS221

        return upper_bound, time_score


def _time_delta(org):
    times = [doc["timer"] for doc in population.get_metrics() if "timer" in doc]

    return stats.percentileofscore(times, org.timer, kind="mean") / 100


def _check_time_range() -> bool:
    hour = datetime.datetime.today().hour

    if config.START_EVOLVE_HOUR == config.STOP_EVOLVE_HOUR:
        return True

    if config.START_EVOLVE_HOUR < config.STOP_EVOLVE_HOUR:
        return config.START_EVOLVE_HOUR <= hour < config.STOP_EVOLVE_HOUR

    before_midnight = config.START_EVOLVE_HOUR <= hour
    after_midnight = hour < config.STOP_EVOLVE_HOUR

    return before_midnight or after_midnight


def _select_worst_bound(candidate: dict, metric: str) -> tuple[float, float, float]:
    """Выбирает минимальное значение верхней границы доверительного интервала.

    Если данный организм не уступает целевому организму, то верхняя граница будет положительной.
    """

    diff = _aligned_diff(candidate, metric)

    bounds = map(
        lambda size: _test_diff(diff[:size]),
        range(1, len(diff) + 1),
    )

    return min(
        bounds,
        key=lambda bound: bound[1],
    )


def _aligned_diff(candidate: dict, metric: str) -> list[float]:
    comp = []

    for base in population.get_metrics():
        metrics = base[metric]

        if base["date"] < candidate["date"]:
            metrics = [np.nan] + metrics

        scores = len(candidate[metric])

        metrics = metrics[:scores]
        metrics = metrics + [np.nan] * (scores - len(metrics))

        comp.append(metrics)

    comp = np.nanmedian(np.array(comp), axis=0)

    return list(map(operator.sub, candidate[metric], comp))


def _test_diff(diff: list[float]) -> tuple[float, float, float]:
    """Последовательный тест на медианную разницу с учетом множественного тестирования.

    Тестирование одностороннее, поэтому p-value нужно умножить на 2, но проводится 2 раза.
    """
    _, upper = seq.median_conf_bound(diff, config.P_VALUE / population.count())

    return float(np.median(diff)), upper, np.max(diff)
