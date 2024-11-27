import statistics
from enum import StrEnum

from pydantic import Field, NonNegativeFloat, NonNegativeInt, PositiveInt

from poptimizer import consts, errors
from poptimizer.domain import domain


class State(StrEnum):
    INIT = "initializing new evolution"
    INIT_DAY = "initializing new day"
    EVAL_ORG = "evaluating organism"
    CREATE_ORG = "creating new organism"


class Evolution(domain.Entity):
    state: State = State.INIT
    step: PositiveInt = 1
    tickers: tuple[domain.Ticker, ...] = Field(default_factory=tuple)
    org_uid: domain.UID = domain.UID("")
    ret_deltas: list[float] = Field(default_factory=list)
    duration: NonNegativeFloat = 0
    t_critical: float = 0
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
        ret_deltas: list[float],
        duration: float,
    ) -> None:
        if self.state not in (State.INIT, State.INIT_DAY):
            raise errors.DomainError("incorrect state for day initialization")

        self.tickers = tickers
        self.org_uid = org_uid
        self.ret_deltas = ret_deltas
        self.duration = duration

        self.state = State.CREATE_ORG

    def eval_org_is_dead(
        self,
        org_uid: domain.UID,
        ret_deltas: list[float],
        duration: float,
    ) -> tuple[bool, str]:
        if self.state not in (State.EVAL_ORG, State.CREATE_ORG):
            raise errors.DomainError("incorrect state for organism evaluation")

        if org_uid == self.org_uid:
            return False, self._update_deltas(ret_deltas, duration)

        t_value = self._t_values(ret_deltas)
        adj_t_critical = self._adj_t_critical(duration)

        match t_value < adj_t_critical:
            case True:
                sign = "<"

                self.state = State.EVAL_ORG
            case False:
                sign = ">"

                self.org_uid = org_uid
                self.ret_deltas = ret_deltas
                self.duration = duration
                self.state = State.CREATE_ORG

        return (
            sign == "<",
            f"Evaluating organism t-value({t_value:.2f}) {sign} adj-t-critical({adj_t_critical:.2f})"
            f", t-critical({self.t_critical:.2f})",
        )

    def _adj_t_critical(self, duration: NonNegativeFloat) -> float:
        return self.t_critical * min(1, self.duration / duration)

    def _t_values(self, ret_deltas: list[float]) -> float:
        deltas = [org_ret - prev_ret for org_ret, prev_ret in zip(ret_deltas, self.ret_deltas, strict=False)]

        return statistics.mean(deltas) * len(deltas) ** 0.5 / statistics.stdev(deltas)

    def _update_deltas(self, ret_deltas: list[float], duration: float) -> str:
        if self.state is not State.EVAL_ORG:
            raise errors.DomainError("incorrect state for base returns update")

        t_value = self._t_values(ret_deltas)

        self.ret_deltas = ret_deltas
        self.adj_count += 1
        self.state = State.CREATE_ORG

        old_t_critical = self.t_critical
        adj_t_critical = self._adj_t_critical(duration)

        match t_value < adj_t_critical:
            case True:
                sign = "<"
                self.t_critical -= (1 - consts.P_VALUE) / self.adj_count
            case False:
                sign = ">"
                self.t_critical += consts.P_VALUE / self.adj_count

        return (
            f"Changing adjustment t-value({t_value:.2f}) {sign} adj-t-critical({adj_t_critical:.2f})"
            f", t-critical({old_t_critical:.2f}) -> t-critical({self.t_critical:.2f})"
        )
