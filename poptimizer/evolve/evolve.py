"""Эволюция параметров модели."""
import datetime
import functools
import logging
import operator
from typing import Optional

import numpy as np

from poptimizer import config
from poptimizer.data.views import indexes, listing
from poptimizer.dl import ModelError
from poptimizer.evolve import population, seq
from poptimizer.portfolio.portfolio import load_tickers


class Evolution:  # noqa: WPS214
    """Эволюция параметров модели.

    Эволюция состоит из бесконечного создания организмов и сравнения их с базовой популяцией по качеству прогноза.
    Сравнение осуществляется с помощью последовательного теста для медиан, который учитывает изменение значимости тестов
    при множественном тестировании в течении по мери появления данных за очередной период времени. Дополнительно
    осуществляется коррекция на множественное тестирования с учетом размера базовой популяции.

    За основу выбора следующего организма взяты подходы из алгоритма имитации отжига:
    - Текущий организм порождает потомка в некой окрестности пространства генов.
    - Производится сравнение с базовой популяцией. Если новый организм оказывается лучше родителя, то он становится
    текущим. Если новый организм оказывается хуже родителя, то он становится текущим, если ухудшение не очень большое.
    Иначе сохраняется прежний родитель и увеличивается допустимое снижение качество, чтобы эволюция не залипала на
    необычно хорошем родителе для сохранения генетического разнообразия, но в среднем дрейфовала в сторону более
    удачных потомков.
    - Организмы, уступающие базовой популяции погибают, при этом сужается окрестность порождения потомков, чтобы новые
    потомки были ближе к родителю по характеристикам, что повышает вероятность создания новых организмов минимально
    приемлемого качества.
    """

    def __init__(self):
        """Инициализирует необходимые параметры."""
        self._scale = 1
        self._jump = 1
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
            jump = self._jump
            self._logger.info(f"Scale - {scale:.2%} / Jump - {jump:.2%}\n")  # noqa: WPS221

            current = self._step(current)

    def _step_setup(
        self,
        step: int,
        org: Optional[population.Organism],
    ) -> tuple[int, population.Organism]:
        self._setup()

        d_min, d_max = population.min_max_date()
        if org is None:
            self._end = d_max or listing.last_history_date()
            self._tickers = load_tickers()
            org = self._next_org()

        dates = indexes.mcftrr(listing.last_history_date()).loc[self._end :].index
        if (d_min != d_max) or (len(dates) == 1):
            return step + 1, org

        self._scale = 1
        self._jump = 1
        self._tickers = load_tickers()
        self._end = dates[1]

        return 1, org

    def _setup(self) -> None:
        if population.count() == 0:
            self._logger.info("Создается базовый организм")
            org = population.create_new_organism()
            self._logger.info(f"{org}\n")

    def _next_org(
        self,
        current: Optional[population.Organism] = None,
    ) -> population.Organism:
        """Возвращает следующий организм и информацию новый ли он.

        В первую очередь берутся не переоцененные существующие организмы. При их отсутствии создается
        потомок текущего в окрестности. При отсутствии текущего (обычно после возобновления прерванной
        эволюции) берется самый старый организм.
        """
        if (org := population.get_next_one(self._end)) is not None:
            return org

        if current is not None:
            return current.make_child(1 / self._scale)

        return population.get_next_one(None)

    def _step(self, hunter: population.Organism) -> population.Organism:
        """Один шаг эволюции."""
        self._logger.info("Родитель:")
        if (hunter_margin := self._eval_organism(hunter)) is None:
            return self._next_org(None)

        prey = self._next_org(hunter)
        label = ""
        if not prey.llh:
            label = " - новый организм"
        self._logger.info(f"Претендент{label}:")
        if (prey_margin := self._eval_organism(prey)) is None:
            return hunter

        delta = prey_margin - hunter_margin

        label = "Старый"
        sign = "<"
        if (min_margin := -self._jump) < delta:
            self._jump = 0
            hunter = prey
            label = "Новый"
            sign = ">"

        if prey_margin < 0:
            self._scale += 1

        self._jump += 1 / self._scale

        self._logger.info(f"{label} родитель - delta={delta:.2%} {sign} {min_margin:.2%}\n")  # noqa: WPS221

        return hunter

    def _eval_organism(self, organism: population.Organism) -> Optional[float]:
        """Оценка организмов.

        Если организм уже оценен для данной даты, то он не оценивается.
        Если организм старый, то оценивается один раз.
        Если организм новый, то он оценивается для минимального количества дат из истории, необходимых
        для последовательного тестирования.
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
            # Тестирование одностороннее, поэтому p-value нужно умножить на 2, но проводится 2 *
            # generations_count тестов, поэтому 2 сокращается.
            alfa = config.P_VALUE / population.generations_count()
            bounding_n = seq.minimum_bounding_n(alfa)
            dates = indexes.mcftrr(listing.last_history_date()).loc[: self._end]
            dates = dates.index[-bounding_n:].tolist()

        for date in dates:
            try:
                organism.evaluate_fitness(self._tickers, date)
            except (ModelError, AttributeError) as error:
                organism.die()
                self._logger.error(f"Удаляю - {error}\n")

                return None

        return self._get_margin(organism)

    def _get_margin(self, org: population.Organism) -> float:
        """Используется тестирование разницы llh и ret против всех организмов базовой популяции.

        Используются тесты для связанных выборок, поэтому предварительно происходит выравнивание по
        датам и отбрасывание значений не имеющих пары (возможно первое значение и хвост из старых
        значений более старого организма).
        """
        margin = np.inf

        for metric in ("LLH", "RET"):
            maximum, median, upper = _select_worst_bound(
                targets=list(population.base_pop_metrics()),
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

            valid = upper not in {np.inf, median}
            margin = min(margin, valid and (upper / (upper - median)))

        time_delta = _time_delta(org)

        self._logger.info(f"Margin - {margin:.2%}, Time excess - {time_delta:.2%}\n")  # noqa: WPS221

        if margin < 0:
            org.die()
            self._logger.info("Исключен из популяции...\n")

        return margin - time_delta


def _time_delta(org):
    """Штраф за время, если организм медленнее самого медленного в популяции."""
    max_timer = max(doc["timer"] for doc in population.base_pop_metrics())

    return max((org.timer / max_timer - 1), 0)


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

    Если данный организм не уступает какому-либо организму, то верхняя граница будет положительной. В
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
    """Последовательный тест на медианную разницу с учетом множественного тестирования.

    Тестирование одностороннее, поэтому p-value нужно умножить на 2, но проводится 2 * generations_count тестов,
    поэтому 2 сокращается.
    """
    diff = list(map(operator.sub, candidate, target))
    _, upper = seq.median_conf_bound(diff, config.P_VALUE / population.generations_count())

    return float(np.median(diff)), upper, np.max(diff)
