import statistics
from enum import StrEnum

from pydantic import Field, PositiveInt
from scipy import stats  # type: ignore[reportMissingTypeStubs]

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
    t_adj: float = 0
    adj_count: int = 0

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
    ) -> None:
        if self.state not in (State.INIT, State.INIT_DAY):
            raise errors.DomainError("incorrect state for day initialization")

        self.tickers = tickers
        self.org_uid = org_uid
        self.ret_deltas = ret_deltas

        self.state = State.CREATE_ORG

    def eval_org_is_dead(
        self,
        org_uid: domain.UID,
        ret_deltas: list[float],
    ) -> tuple[bool, str]:
        if self.state not in (State.EVAL_ORG, State.CREATE_ORG):
            raise errors.DomainError("incorrect state for organism evaluation")

        if org_uid == self.org_uid:
            return False, self._update_deltas(ret_deltas)

        t_value, t_critical = self._t_values(ret_deltas)

        match t_value + self.t_adj < t_critical:
            case True:
                sign = "<"

                self.state = State.EVAL_ORG
            case False:
                sign = ">"

                self.org_uid = org_uid
                self.ret_deltas = ret_deltas
                self.state = State.CREATE_ORG

        return (
            sign == "<",
            f"Evaluating organism t-value({t_value:.2f}) + adj({self.t_adj:.2f}) {sign} t-critical({t_critical:.2f})",
        )

    def _t_values(self, ret_deltas: list[float]) -> tuple[float, float]:
        deltas = [org_ret - prev_ret for org_ret, prev_ret in zip(ret_deltas, self.ret_deltas, strict=False)]
        t_value = statistics.mean(deltas) * len(deltas) ** 0.5 / statistics.stdev(deltas)
        t_critical = stats.t.ppf(consts.P_VALUE, len(deltas) - 1)  # type: ignore[reportUnknownMemberType]

        return t_value, float(t_critical)

    def _update_deltas(self, ret_deltas: list[float]) -> str:
        if self.state is not State.EVAL_ORG:
            raise errors.DomainError("incorrect state for base returns update")

        t_value, t_critical = self._t_values(ret_deltas)

        self.ret_deltas = ret_deltas
        self.adj_count += 1
        self.state = State.CREATE_ORG

        old_t_adj = self.t_adj

        match t_value + self.t_adj < t_critical:
            case True:
                sign = "<"
                self.t_adj += (1 - consts.P_VALUE) / self.adj_count**0.5
            case False:
                sign = ">"
                self.t_adj -= consts.P_VALUE / self.adj_count**0.5

        return (
            f"Changing adjustment t-value({t_value:.2f}) + adj({old_t_adj:.2f}) {sign} "
            f"t-critical({t_critical:.2f}) -> adj({self.t_adj:.2f})"
        )
