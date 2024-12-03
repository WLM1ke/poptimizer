import statistics
from enum import StrEnum
from typing import Final, Self

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt, model_validator

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
    llh: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    t_critical: float = 0
    adj_count: NonNegativeInt = 0
    minimal_returns_days: int = _INITIAL_MINIMAL_RETURNS_DAYS

    @model_validator(mode="after")
    def _match_length(self) -> Self:
        if len(self.alfas) != len(self.llh):
            raise ValueError("different alfas and llh length")

        return self

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
        llh: list[float],
        duration: float,
    ) -> None:
        if self.state not in (State.INIT, State.INIT_DAY):
            raise errors.DomainError("incorrect state for day initialization")

        self.tickers = tickers
        self.org_uid = org_uid
        self.alfas = alfas
        self.llh = llh
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
        llh: list[float],
        duration: float,
    ) -> None:
        if self.state is not State.NEW_BASE_ORG:
            raise errors.DomainError("incorrect state for new base organism")

        self.org_uid = org_uid
        self.alfas = alfas
        self.llh = llh
        self.duration = duration

        self.state = State.CREATE_ORG

    def eval_org_is_dead(
        self,
        org_uid: domain.UID,
        alfas: list[float],
        llh: list[float],
        duration: float,
    ) -> tuple[bool, str, str]:
        if self.state not in (State.EVAL_ORG, State.CREATE_ORG):
            raise errors.DomainError("incorrect state for organism evaluation")

        if org_uid == self.org_uid:
            return False, *self._update_stats(alfas, llh, duration)

        t_value_alfas = self._t_values(alfas, self.alfas)
        t_value_llh = self._t_values(llh, self.llh)
        adj_t_critical = self._adj_t_critical(duration)

        sign_alfa = ">"
        sign_llh = ">"
        dead = True

        match t_value_alfas < adj_t_critical or t_value_llh < adj_t_critical:
            case True:
                if t_value_alfas < adj_t_critical:
                    sign_alfa = "<"

                if t_value_llh < adj_t_critical:
                    sign_llh = "<"

                self.state = State.EVAL_ORG
            case False:
                dead = False
                self.org_uid = org_uid
                self.alfas = alfas
                self.llh = llh
                self.duration = duration
                self.state = State.CREATE_ORG

        return (
            dead,
            f"Evaluating alfa's t-value({t_value_alfas:.2f}) {sign_alfa} adj-t-critical({adj_t_critical:.2f})",
            f"Evaluating llh's t-value({t_value_llh:.2f}) {sign_llh} adj-t-critical({adj_t_critical:.2f})"
            f", t-critical({self.t_critical:.2f})",
        )

    def _adj_t_critical(self, duration: NonNegativeFloat) -> float:
        return self.t_critical * min(1, self.duration / duration)

    def _t_values(self, target: list[float], base: list[float]) -> float:
        deltas = [target_value - base_value for target_value, base_value in zip(target, base, strict=False)]

        return statistics.mean(deltas) * len(deltas) ** 0.5 / statistics.stdev(deltas)

    def _update_stats(self, alfas: list[float], llh: list[float], duration: float) -> tuple[str, str]:
        if self.state is not State.EVAL_ORG:
            raise errors.DomainError("incorrect state for base returns update")

        t_value_alfas = self._t_values(alfas, self.alfas)
        t_value_llh = self._t_values(llh, self.llh)

        self.alfas = alfas
        self.llh = llh
        self.adj_count += 1
        self.state = State.CREATE_ORG

        old_t_critical = self.t_critical
        adj_t_critical = self._adj_t_critical(duration)

        sign_alfa = ">"
        sign_llh = ">"

        match t_value_alfas < adj_t_critical or t_value_llh < adj_t_critical:
            case True:
                if t_value_alfas < adj_t_critical:
                    sign_alfa = "<"

                if t_value_llh < adj_t_critical:
                    sign_llh = "<"
                self.t_critical -= (1 - consts.P_VALUE) / self.adj_count**0.5
            case False:
                self.t_critical += consts.P_VALUE / self.adj_count**0.5

        return (
            f"Reevaluating alfa's t-value({t_value_alfas:.2f}) {sign_alfa} adj-t-critical({adj_t_critical:.2f}), "
            f"llh's t-value({t_value_llh:.2f}) {sign_llh} adj-t-critical({adj_t_critical:.2f})",
            f"Changing t-critical({old_t_critical:.2f}) -> t-critical({self.t_critical:.2f})",
        )
