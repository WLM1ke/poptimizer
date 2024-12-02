import statistics
from enum import StrEnum
from typing import Final

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from poptimizer import consts, errors
from poptimizer.domain import domain
from poptimizer.domain.dl import datasets

_INITIAL_MINIMAL_RETURNS_DAYS: Final = datasets.minimal_returns_days(
    history_days=consts.INITIAL_HISTORY_DAYS_END,
    forecast_days=consts.FORECAST_DAYS,
    test_days=consts.INITIAL_TEST_DAYS,
)


def _extract_minimal_returns_days(err_group: BaseExceptionGroup[errors.DomainError]) -> int | None:
    if (subgroup := err_group.subgroup(errors.TooShortHistoryError)) is None:
        return None

    while True:
        if isinstance(subgroup.exceptions[0], errors.TooShortHistoryError):
            return subgroup.exceptions[0].minimal_returns_days

        subgroup = subgroup.exceptions[0]


class State(StrEnum):
    INIT = "initializing new evolution"
    INIT_DAY = "initializing new day"
    NEW_BASE_ORG = "evaluating new base organism"
    EVAL_ORG = "evaluating organism"
    CREATE_ORG = "creating new organism"


class Evolution(domain.Entity):
    state: State = State.INIT
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    org_uid: domain.UID = domain.UID("")
    alfas: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    t_critical: float = 0
    adj_count: NonNegativeInt = 0
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    def __str__(self) -> str:
        return f"Evolution day {self.day} step {self.step} - {self.state}"

    def start_step(self, day: domain.Day) -> State:
        if self.state == State.INIT:
            self.day = day

            return self.state

        if self.day != day:
            self.state = State.INIT_DAY
            self.day = day
            self.step = 1

            return self.state

        self.step += 1

        return self.state

    def init_new_day(
        self,
        tickers: tuple[domain.Ticker, ...],
        org_uid: domain.UID,
        alfas: list[float],
        duration: float,
    ) -> None:
        if self.state not in (State.INIT, State.INIT_DAY):
            raise errors.DomainError("incorrect state for day initialization")

        self.tickers = tickers
        self.org_uid = org_uid
        self.alfas = alfas
        self.duration = duration

        self.state = State.CREATE_ORG

    def org_failed(self, org_uid: domain.UID, err: BaseExceptionGroup[errors.DomainError]) -> int | None:
        match self.state:
            case State.CREATE_ORG:
                self.state = State.EVAL_ORG
            case State.EVAL_ORG if self.org_uid == org_uid:
                self.state = State.NEW_BASE_ORG
            case _:
                ...

        minimal_returns_days = _extract_minimal_returns_days(err)
        if minimal_returns_days is not None and minimal_returns_days > self.minimal_returns_days:
            self.minimal_returns_days += 1

            return self.minimal_returns_days

        return None

    def new_base_org(
        self,
        org_uid: domain.UID,
        alfas: list[float],
        duration: float,
    ) -> None:
        if self.state is not State.NEW_BASE_ORG:
            raise errors.DomainError("incorrect state for new base organism")

        self.org_uid = org_uid
        self.alfas = alfas
        self.duration = duration

        self.state = State.CREATE_ORG

    def eval_org_is_dead(
        self,
        org_uid: domain.UID,
        alfas: list[float],
        duration: float,
    ) -> tuple[bool, str]:
        if self.state not in (State.EVAL_ORG, State.CREATE_ORG):
            raise errors.DomainError("incorrect state for organism evaluation")

        if org_uid == self.org_uid:
            return False, self._update_alfas(alfas, duration)

        t_value = self._t_values(alfas)
        adj_t_critical = self._adj_t_critical(duration)

        match t_value < adj_t_critical:
            case True:
                sign = "<"

                self.state = State.EVAL_ORG
            case False:
                sign = ">"

                self.org_uid = org_uid
                self.alfas = alfas
                self.duration = duration
                self.state = State.CREATE_ORG

        return (
            sign == "<",
            f"Evaluating organism t-value({t_value:.2f}) {sign} adj-t-critical({adj_t_critical:.2f})"
            f", t-critical({self.t_critical:.2f})",
        )

    def _adj_t_critical(self, duration: NonNegativeFloat) -> float:
        return self.t_critical * min(1, self.duration / duration)

    def _t_values(self, alfas: list[float]) -> float:
        deltas = [org_ret - prev_ret for org_ret, prev_ret in zip(alfas, self.alfas, strict=False)]

        return statistics.mean(deltas) * len(deltas) ** 0.5 / statistics.stdev(deltas)

    def _update_alfas(self, alfas: list[float], duration: float) -> str:
        if self.state is not State.EVAL_ORG:
            raise errors.DomainError("incorrect state for base returns update")

        t_value = self._t_values(alfas)

        self.alfas = alfas
        self.adj_count += 1
        self.state = State.CREATE_ORG

        old_t_critical = self.t_critical
        adj_t_critical = self._adj_t_critical(duration)

        match t_value < adj_t_critical:
            case True:
                sign = "<"
                self.t_critical -= (1 - consts.P_VALUE) / self.adj_count**0.5
            case False:
                sign = ">"
                self.t_critical += consts.P_VALUE / self.adj_count**0.5

        return (
            f"Changing adjustment t-value({t_value:.2f}) {sign} adj-t-critical({adj_t_critical:.2f})"
            f", t-critical({old_t_critical:.2f}) -> t-critical({self.t_critical:.2f})"
        )
