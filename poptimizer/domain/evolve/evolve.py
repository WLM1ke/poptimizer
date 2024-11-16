import statistics
from enum import StrEnum
from typing import cast

import numpy as np
from pydantic import Field, PositiveInt
from scipy import stats  # type: ignore[reportMissingTypeStubs]

from poptimizer import consts
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

    def __str__(self) -> str:
        return f"Evolution day {self.day} step {self.step} - {self.state}"

    def start_step(self, day: domain.Day) -> State:
        if self.state == State.INIT:
            self.day = day

            return State.INIT

        if self.day != day:
            self.day = day
            self.step = 1

            return State.INIT_DAY

        self.step += 1

        return self.state

    def init_new_day(
        self,
        tickers: tuple[domain.Ticker, ...],
        org_uid: domain.UID,
        ret_deltas: list[float],
    ) -> None:
        self.tickers = tickers
        self.org_uid = org_uid
        self.ret_deltas = ret_deltas

        self.state = State.CREATE_ORG

    def eval_org_is_dead(
        self,
        org_uid: domain.UID,
        ret_deltas: list[float],
    ) -> bool:
        if self.org_uid == org_uid:
            self.ret_deltas = ret_deltas

            self.state = State.CREATE_ORG

            return False

        deltas = [org_ret - prev_ret for org_ret, prev_ret in zip(ret_deltas, self.ret_deltas, strict=False)]
        if statistics.mean(deltas) > 0:
            self.org_uid = org_uid
            self.ret_deltas = ret_deltas

            self.state = State.CREATE_ORG

            return False

        upper_bound = stats.bootstrap(  # type: ignore[reportUnknownMemberType]
            (deltas,),
            np.mean,
            confidence_level=(1 - consts.P_VALUE),
            alternative="less",
        ).confidence_interval.high

        self.state = State.EVAL_ORG

        return cast(float, upper_bound) < 0
