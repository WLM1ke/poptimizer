from poptimizer.core import fsm
from poptimizer.portfolio.models import portfolio
from poptimizer.trading.models import trading


class InitTradingStateAction:
    async def __call__(self, ctx: fsm.Ctx) -> None:
        trading_state = await ctx.get_for_update(trading.TradingState)
        port = await ctx.get(portfolio.Portfolio)

        if trading_state.day != port.day:
            trading_state.init_day(port)
