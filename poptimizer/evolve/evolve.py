"""Эволюция параметров модели."""
import datetime
import logging
import operator
from typing import Optional

import numpy as np

from poptimizer import config
from poptimizer.data.views import listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers


class Evolution:  # noqa: WPS214
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного создания организмов и сравнения их с базовой популяцией по качеству прогноза.
    Сравнение осуществляется с помощью последовательного теста для медиан, который учитывает изменение значимости тестов
    при множественном тестировании по мере появления данных за очередной период времени. Дополнительно осуществляется
    коррекция на множественное тестирование на разницу llh и доходности.

    За основу выбора следующего организма взяты подходы из алгоритма имитации отжига:
    - Текущий организм порождает потомка в некой окрестности пространства генов.
    - Производится сравнение с самым старым в популяции, а для самого старого со вторым. Если новый организм оказывается
    лучше родителя, то он становится текущим. Если новый организм оказывается хуже родителя, то он сохраняется в
    популяции, если ухудшение не очень большое.
    - Организмы тестируются для истории равной размеру популяции, но не меньше минимального размера дней, необходимого
    для проведения теста.
    """

    def __init__(self):
        """Инициализирует необходимые параметры."""
        self._scale = 1
        self._count = seq.minimum_bounding_n(config.P_VALUE)
        self._tickers = None
        self._end = None
        self._logger = logging.getLogger()

    def evolve(self) -> None:
        """Осуществляет эволюции.

        При необходимости создается начальная популяция из случайных организмов по умолчанию.
        """
        step = 0
        current = None

        while _check_time_range():
            step, current = self._step_setup(step, current)

            date = self._end.date()
            self._logger.info(f"***{date}: Шаг эволюции — {step}***")
            population.print_stat()

            scale = 1 / self._scale
            self._logger.info(f"Scale - {scale:.2%}\n")  # noqa: WPS221

            current = self._maybe_clear(current)
            current = self._step(current)

    def _step_setup(
        self,
        step: int,
        org: Optional[population.Organism],
    ) -> tuple[int, population.Organism]:
        self._setup()

        d_min, d_max = population.min_max_date()
        if org is None:
            self._tickers = load_tickers()
            self._end = d_max or listing.all_history_date(self._tickers)[-1]
            org = self._next_org()

        dates = listing.all_history_date(self._tickers, start=self._end)
        if (d_min != self._end) or (len(dates) == 1):
            return step + 1, org

        self._scale = 1
        self._tickers = load_tickers()
        self._end = dates[1]

        return 1, org

    def _setup(self) -> None:
        if population.count() == 0:
            while population.count() < seq.minimum_bounding_n(config.P_VALUE):
                self._logger.info("Создается базовый организм:")
                org = population.create_new_organism()
                self._logger.info(f"{org}\n")

    def _next_org(
        self,
        current: Optional[population.Organism] = None,
    ) -> population.Organism:
        """Возвращает следующий организм.

        В первую проверяется, что первые два организма имеют достаточно оценок. Потом берутся не переоцененные для
        последней даты существующие организмы. При их отсутствии создается потомок текущего в окрестности. При
        отсутствии текущего (обычно после возобновления прерванной эволюции) берется самый старый организм.

        Если организмы имеют мало оценок для текущего размера популяции, их оценки сбрасываются для проведения оценки
        для более длинного периода времени.
        """
        return self._select_next(current)

    def _maybe_clear(self, org: population.Organism) -> population.Organism:
        if (org.date == self._end) and (0 < org.scores < self._n_test()):
            org.clear()

        if (org.date != self._end) and (0 < org.scores < self._n_test() - 1):
            org.clear()

        return org

    def _select_next(
        self,
        current: Optional[population.Organism] = None,
    ) -> population.Organism:
        for _, org in zip(range(2), population.get_all()):
            if (current is None) or (org.scores < self._n_test()):
                return self._maybe_clear(org)

        return population.get_next_one(self._end) or current.make_child(1 / self._scale)

    def _step(self, hunter: population.Organism) -> Optional[population.Organism]:
        """Один шаг эволюции."""
        label = ""
        if not hunter.llh:
            label = " - новый организм"
            if hunter.scores > 0:
                label = " - повторное обучение"
        self._logger.info(f"Родитель{label}:")
        if (hunter_margin := self._eval_organism(hunter)) is None:
            return None
        if hunter_margin[0] < 0:
            return None

        hunter_margin = hunter_margin[0] - hunter_margin[1]

        prey = self._next_org(hunter)

        label = ""
        if not prey.llh:
            label = " - новый организм"
            if prey.scores > 0:
                label = " - повторное обучение"

        self._logger.info(f"Претендент{label}:")
        if (prey_margin := self._eval_organism(prey)) is None:
            return hunter

        prey_margin = prey_margin[0] - prey_margin[1]

        delta = prey_margin - hunter_margin

        label = "Старый"
        sign = "<"
        if delta > 0:
            hunter = prey
            label = "Новый"
            sign = ">"

        self._scale += (prey_margin < 0) * 2 - 1
        self._scale = max(1, self._scale)

        self._logger.info(f"{label} родитель - delta={delta:.2%} {sign} 0\n")  # noqa: WPS221

        return hunter

    def _eval_organism(self, organism: population.Organism) -> Optional[tuple[float, float]]:
        """Оценка организмов.

        - Если организм уже оценен для данной даты, то он не оценивается.
        - Если организм старый, то оценивается один раз.
        - Если организм новый, то он оценивается для минимального количества дат из истории, необходимых для
          последовательного тестирования.
        """
        try:
            self._logger.info(f"{organism}\n")
        except AttributeError as err:
            organism.die()
            self._logger.error(f"Удаляю - {err}\n")

            return None

        if organism.date == self._end:
            return self._get_margin(organism)

        dates = [self._end]
        if not organism.llh:
            dates = listing.all_history_date(self._tickers, end=self._end)
            dates = dates[-self._n_test() :].tolist()

        for date in dates:
            try:
                organism.evaluate_fitness(self._tickers, date)
            except (ModelError, AttributeError) as error:
                organism.die()
                self._logger.error(f"Удаляю - {error}\n")

                return None

        return self._get_margin(organism)

    def _get_margin(self, org: population.Organism) -> tuple[float, float]:
        """Используется тестирование разницы llh и ret против самого старого организма.

        Используются тесты для связанных выборок, поэтому предварительно происходит выравнивание по
        датам и отбрасывание значений не имеющих пары (возможно первое значение и хвост из старых
        значений более старого организма).
        """
        margin = np.inf

        pop = list(population.get_metrics())
        oldest = pop[0]
        if (len(pop) > 1) and (oldest["_id"] == org.id):
            oldest = pop[1]

        for metric in ("LLH", "RET"):
            median, upper, maximum = _select_worst_bound(
                targets=oldest,
                candidate={"date": org.date, "llh": org.llh, "ir": org.ir},
                metric=metric,
            )

            self._logger.info(
                " ".join(
                    [
                        f"{metric} worst difference:",
                        f"median - {median:0.4f},",
                        f"upper - {upper:0.4f},",
                        f"max - {maximum:0.4f}",
                    ],
                ),
            )

            valid = upper != median
            margin = min(margin, valid and (upper / (upper - median)))

        if margin == np.inf:
            margin = 0

        time_delta = _time_delta(org)

        self._logger.info(f"Margin - {margin:.2%}, Time excess - {time_delta:.2%}\n")  # noqa: WPS221

        if margin < 0:
            org.die()
            self._logger.info("Исключен из популяции...\n")

        return margin, time_delta

    def _n_test(self) -> int:
        return max(population.count(), seq.minimum_bounding_n(config.P_VALUE), self._scale)


def _time_delta(org):
    """Штраф за время, если организм медленнее медианного в популяции."""
    median = np.median([doc["timer"] for doc in population.get_metrics()])

    return max((org.timer / median - 1), 0)


def _check_time_range() -> bool:
    hour = datetime.datetime.today().hour

    if config.START_EVOLVE_HOUR == config.STOP_EVOLVE_HOUR:
        return True

    if config.START_EVOLVE_HOUR < config.STOP_EVOLVE_HOUR:
        return config.START_EVOLVE_HOUR <= hour < config.STOP_EVOLVE_HOUR

    before_midnight = config.START_EVOLVE_HOUR <= hour
    after_midnight = hour < config.STOP_EVOLVE_HOUR

    return before_midnight or after_midnight


def _select_worst_bound(targets: dict, candidate: dict, metric: str) -> tuple[float, float, float]:
    """Выбирает минимальное значение верхней границы доверительного интервала.

    Если данный организм не уступает целевому организму, то верхняя граница будет положительной.
    """
    diff = _aligned_diff(targets, candidate, metric)
    bounds = map(
        lambda size: _test_diff(diff[:size]),
        range(1, len(diff) + 1),
    )

    return min(
        bounds,
        key=lambda bound: bound[1] or np.inf,
    )


def _aligned_diff(target: dict, candidate: dict, metric: str) -> list[float]:
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

    return list(map(operator.sub, candidate_data, target_data))[::-1]


def _test_diff(diff: list[float]) -> tuple[float, float, float]:
    """Последовательный тест на медианную разницу с учетом множественного тестирования.

    Тестирование одностороннее, поэтому p-value нужно умножить на 2, но проводится 2 раза.
    """
    _, upper = seq.median_conf_bound(diff, config.P_VALUE)

    return float(np.median(diff)), upper, np.max(diff)
