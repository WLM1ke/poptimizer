import asyncio
import bisect
import statistics
from typing import Annotated, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PlainSerializer,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from poptimizer.core import consts, domain, errors, fsms
from poptimizer.data.moex import quotes, securities

type AccountData = dict[domain.AccName, NonNegativeInt]


class Position(BaseModel):
    ticker: domain.Ticker
    lot: PositiveInt
    price: PositiveFloat
    turnover: NonNegativeFloat
    accounts: AccountData = Field(default_factory=dict[domain.AccName, int])

    def quantity(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(self.accounts.values())

        return self.accounts.get(account, 0)

    def value(self, account: domain.AccName | None = None) -> float:
        return self.price * self.quantity(account)


class NormalizedPosition(BaseModel):
    ticker: domain.Ticker
    weight: float = Field(ge=0, le=1)
    norm_turnover: NonNegativeFloat
    accounts: list[domain.AccName]


class Portfolio(domain.Entity):
    day: domain.Day = consts.START_DAY
    holding_period: NonNegativeFloat = Field(0, ge=1)
    account_names: Annotated[
        set[domain.AccName],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.AccName])
    cash: AccountData = Field(default_factory=dict[domain.AccName, int])
    positions: Annotated[
        list[Position],
        AfterValidator(domain.sorted_with_ticker_field_validator),
    ] = Field(default_factory=list[Position])
    exclude: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])
    illiquid: Annotated[
        set[domain.Ticker],
        PlainSerializer(
            list,
            return_type=list,
        ),
    ] = Field(default_factory=set[domain.Ticker])

    @model_validator(mode="after")
    def _positions_have_know_accounts(self) -> Self:
        for position in self.positions:
            if unknown_accounts := position.accounts.keys() - self.account_names:
                raise ValueError(f"{position.ticker} has unknown accounts {unknown_accounts}")

        return self

    @field_validator("positions")
    def _positions_are_multiple_of_lots(cls, positions: list[Position]) -> list[Position]:
        for position in positions:
            for acc, shares in position.accounts.items():
                ticker = position.ticker

                if shares % position.lot:
                    raise ValueError(f"{acc} has {shares} {ticker} - not multiple of lot of {position.lot} shares")

                if not shares:
                    raise ValueError(f"{acc} has zero {ticker} shares")

        return positions

    @property
    def forecast_days(self) -> int:
        return int(self.holding_period)

    def create_acount(self, name: domain.AccName) -> None:
        if name in self.account_names:
            raise errors.DomainError(f"account {name} already exists")

        if not name:
            raise errors.DomainError("account name is empty")

        self.account_names.add(name)

    def remove_acount(self, name: domain.AccName) -> None:
        if name not in self.account_names:
            raise errors.DomainError(f"account {name} doesn't exist")

        if name in self.cash:
            raise errors.DomainError(f"account {name} has not zero cash")

        for position in self.positions:
            if name in position.accounts:
                raise errors.DomainError(f"account {name} has not zero {position.ticker}")

        self.account_names.remove(name)

    def find_position(self, ticker: domain.Ticker) -> tuple[int, Position | None]:
        n = bisect.bisect_left(self.positions, ticker, key=lambda pos: pos.ticker)
        if n == len(self.positions) or self.positions[n].ticker != ticker:
            return n, None

        return n, self.positions[n]

    def _try_remove_ticket(self, ticker: domain.Ticker) -> bool:
        match self.find_position(ticker):
            case (n, None):
                return False
            case (n, position):
                if position.accounts:
                    return False

                self.positions = self.positions[:n] + self.positions[n + 1 :]

                return True

    def update_position(self, acc_name: domain.AccName, ticker: domain.Ticker, quantity: NonNegativeInt) -> None:
        if acc_name not in self.account_names:
            raise errors.DomainError(f"account {acc_name} doesn't exist")

        if ticker == domain.CashTicker:
            self.cash[acc_name] = quantity

            if not quantity:
                self.cash.pop(acc_name)

            return

        match self.find_position(ticker):
            case (_, None):
                raise errors.DomainError(f"{ticker} not in portfolio")
            case (_, position):
                if quantity % (lot := position.lot):
                    raise errors.DomainError(f"quantity {quantity} must be multiple of {lot}")

                if not position.accounts and quantity:
                    self.holding_period *= 1 - 1 / (self.open_positions() + 1)

                position.accounts[acc_name] = quantity

                if not quantity:
                    position.accounts.pop(acc_name)

    def normalized_turnover(self) -> list[float]:
        values = self.value()

        return [position.turnover / values for position in self.positions]

    @property
    def normalized_positions(self) -> list[NormalizedPosition]:
        port_value = self.value()

        if not port_value:
            port_value = 1

        return [
            NormalizedPosition(
                ticker=pos.ticker,
                weight=pos.value() / port_value,
                norm_turnover=pos.turnover / port_value,
                accounts=sorted(pos.accounts),
            )
            for pos in self.positions
        ]

    def cash_value(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(self.cash.values())

        return self.cash.get(account, 0)

    def value(self, account: domain.AccName | None = None) -> float:
        if account is None:
            return sum(pos.price * sum(pos.accounts.values()) for pos in self.positions) + self.cash_value()

        return sum(pos.price * pos.accounts.get(account, 0) for pos in self.positions) + self.cash_value(account)

    def open_positions(self, account: domain.AccName | None = None) -> int:
        if account is None:
            return sum(bool(pos.accounts) for pos in self.positions)

        return sum(account in pos.accounts for pos in self.positions)

    @property
    def effective_positions(self) -> float:
        positions_value = sum(pos.value() for pos in self.positions)

        if not positions_value:
            return 0

        return positions_value**2 / sum(pos.value() ** 2 for pos in self.positions)

    def exclude_ticker(self, ticker: domain.Ticker) -> None:
        _, pos = self.find_position(ticker)
        if pos is None:
            raise errors.DomainError(f"ticker {ticker} is not in portfolio")

        self.exclude.add(ticker)
        self.illiquid.add(ticker)

    def not_exclude_ticker(self, ticker: domain.Ticker) -> None:
        if ticker not in self.exclude:
            raise errors.DomainError(f"ticker {ticker} is not excluded")

        self.exclude.remove(ticker)


async def update(
    ctx: fsms.CoreCtx,
    minimal_candles: PositiveInt,
) -> None:
    port = await ctx.get_for_update(Portfolio)

    if not await _update_holding_period(ctx, port):
        return

    port.illiquid.clear()
    sec_cache = await _prepare_sec_cache(ctx, port.forecast_days, minimal_candles)
    min_turnover = _calc_min_turnover(port, sec_cache)

    old_value = port.value()
    _update_existing_positions(ctx, port, sec_cache, min_turnover)
    _add_new_liquid(ctx, port, sec_cache, min_turnover)

    if old_value:
        new_value = port.value()
        change = new_value / old_value - 1
        ctx.warning(f"Portfolio value changed {change:.2%} - {old_value:_.0f} -> {new_value:_.0f}")


async def _update_holding_period(ctx: fsms.CoreCtx, port: Portfolio) -> bool:
    sec_table = await ctx.get(securities.Securities)

    if port.day >= sec_table.trading_days[-1]:
        return False

    for day in reversed(sec_table.trading_days):
        if day <= port.day:
            break

        port.holding_period += 1

    if port.day == consts.START_DAY:
        port.holding_period = 1

    port.day = sec_table.trading_days[-1]

    return True


async def _prepare_sec_cache(
    ctx: fsms.CoreCtx,
    forecast_days: PositiveInt,
    minimal_candles: PositiveInt,
) -> dict[domain.Ticker, Position]:
    sec_table = await ctx.get(securities.Securities)

    async with asyncio.TaskGroup() as tg:
        quotes_tasks = [tg.create_task(ctx.get(quotes.Quotes, domain.UID(sec.ticker))) for sec in sec_table.df]

    cache: dict[domain.Ticker, Position] = {}

    turnover_days = set(sec_table.trading_days[-forecast_days:])

    for sec, quotes_task in zip(sec_table.df, quotes_tasks, strict=True):
        df = quotes_task.result().df

        if not df:
            continue

        turnover = 0
        if len(df) >= minimal_candles:
            turnover_data = [row.turnover for row in df[-forecast_days:] if row.day in turnover_days]
            if turnover_data:
                turnover = statistics.median(turnover_data)

        cache[sec.ticker] = Position(
            ticker=sec.ticker,
            lot=sec.lot,
            price=df[-1].close,
            turnover=turnover,
        )

    return cache


def _calc_min_turnover(
    port: Portfolio,
    sec_cache: dict[domain.Ticker, Position],
) -> float:
    min_turnover = port.cash_value()

    for position in port.positions:
        if new_position := sec_cache.get(position.ticker):
            min_turnover = max(min_turnover, new_position.value())

    return min_turnover


def _update_existing_positions(
    ctx: fsms.CoreCtx,
    port: Portfolio,
    sec_cache: dict[domain.Ticker, Position],
    min_turnover: float,
) -> None:
    updated_positions: list[Position] = []

    for position in port.positions:
        match sec_cache.pop(position.ticker, None):
            case None if not position.accounts:
                ctx.info("Not traded %s is removed from portfolio", position.ticker)
            case None:
                position.turnover = min_turnover
                updated_positions.append(position)
                port.illiquid.add(position.ticker)
                ctx.warning("Not traded %s is not removed from portfolio", position.ticker)
            case new_position if new_position.turnover < min_turnover and not position.accounts:
                ctx.info("Not liquid %s is removed from portfolio", position.ticker)
            case new_position if new_position.turnover < min_turnover:
                new_position.accounts = position.accounts
                new_position.turnover = min_turnover
                updated_positions.append(new_position)
                port.illiquid.add(position.ticker)
                ctx.warning("Not liquid %s is not removed from portfolio", position.ticker)
            case new_position if new_position.ticker in port.exclude and not position.accounts:
                ctx.info("%s from exclude list is removed from portfolio", new_position.ticker)
            case new_position if new_position.ticker in port.exclude:
                new_position.accounts = position.accounts
                updated_positions.append(new_position)
                port.illiquid.add(position.ticker)
                ctx.warning("%s from exclude list is not removed from portfolio", position.ticker)
            case new_position:
                new_position.accounts = position.accounts
                updated_positions.append(new_position)

    port.positions = updated_positions


def _add_new_liquid(
    ctx: fsms.CoreCtx,
    port: Portfolio,
    sec_cache: dict[domain.Ticker, Position],
    min_turnover: float,
) -> None:
    for ticker, position in sec_cache.items():
        if position.turnover > min_turnover and ticker not in port.exclude:
            n, _ = port.find_position(position.ticker)
            port.positions.insert(n, position)

            ctx.info("%s is added to portfolio", ticker)
