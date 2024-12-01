import statistics
from enum import StrEnum
from typing import Final

from pydantic import Field, NonNegativeFloat, PositiveInt
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer import consts, errors
from poptimizer.domain import domain

_adj_delta_step: Final = 0.01


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

    def org_failed(self, org_uid: domain.UID) -> None:
        match self.state:
            case State.CREATE_ORG:
                self.state = State.EVAL_ORG
            case State.EVAL_ORG if self.org_uid == org_uid:
                self.state = State.NEW_BASE_ORG
            case _:
                return

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
            self.alfas = alfas
            self.duration = duration

            self.state = State.CREATE_ORG

            return False, "Reevaluating base org"

        t_value, t_critical = self._t_values(alfas)
        adj_t_critical = self._adj_t_critical(t_critical, duration)

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
            f"Evaluating organism t_value({t_value:.2f}) {sign} adj_t_critical({adj_t_critical:.2f})"
            f", t_critical({t_critical:.2f})",
        )

    def _adj_t_critical(self, t_critical: float, duration: NonNegativeFloat) -> float:
        return t_critical * min(1, self.duration / duration)

    def _t_values(self, alfas: list[float]) -> tuple[float, float]:
        deltas = [alfa - alfa_prev for alfa, alfa_prev in zip(alfas, self.alfas, strict=False)]
        t_value = statistics.mean(deltas) * len(deltas) ** 0.5 / statistics.stdev(deltas)
        t_critical = stats.t.ppf(consts.P_VALUE, len(deltas) - 1)  # type: ignore[reportUnknownMemberType]

        return t_value, float(t_critical)
