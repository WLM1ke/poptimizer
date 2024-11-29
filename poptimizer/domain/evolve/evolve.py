import statistics
from enum import StrEnum
from typing import Final

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from poptimizer import consts, errors
from poptimizer.domain import domain

_adj_delta_step: Final = 0.1


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
    delta_critical: float = 0
    adj_count: NonNegativeInt = 0

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
            return False, self._update_alfas(alfas, duration)

        delta = self._delta(alfas)
        adj_delta_critical = self._adj_delta_critical(duration)

        match delta < adj_delta_critical:
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
            f"Evaluating organism delta({delta:.2%}) {sign} adj-delta-critical({adj_delta_critical:.2%})"
            f", delta-critical({self.delta_critical:.2%})",
        )

    def _adj_delta_critical(self, duration: NonNegativeFloat) -> float:
        return self.delta_critical * min(1, self.duration / duration)

    def _delta(self, alfas: list[float]) -> float:
        return statistics.mean(alfa - alfa_prev for alfa, alfa_prev in zip(alfas, self.alfas, strict=False))

    def _update_alfas(self, alfas: list[float], duration: float) -> str:
        if self.state is not State.EVAL_ORG:
            raise errors.DomainError("incorrect state for base returns update")

        delta = self._delta(alfas)

        self.alfas = alfas
        self.state = State.CREATE_ORG

        old_delta_critical = self.delta_critical
        adj_delta_critical = self._adj_delta_critical(duration)

        match delta < adj_delta_critical:
            case True:
                sign = "<"
                self.delta_critical -= _adj_delta_step * (1 - consts.P_VALUE) / (self.adj_count + 1)

                if delta > self._adj_delta_critical(duration):
                    self.adj_count += 1
            case False:
                sign = ">"
                self.delta_critical += _adj_delta_step * consts.P_VALUE / (self.adj_count + 1)

                if delta < self._adj_delta_critical(duration):
                    self.adj_count += 1
        return (
            f"Changing adjustment delta({delta:.2%}) {sign} adj-delta-critical({adj_delta_critical:.2%})"
            f", delta-critical({old_delta_critical:.2%}) -> delta-critical({self.delta_critical:.2%})"
        )
