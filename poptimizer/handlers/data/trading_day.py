import asyncio

from poptimizer.handlers import handler


class TradingDayHandler:
    def __init__(self, msg_bus: handler.Bus) -> None:
        self._msg_bus = msg_bus

    async def __call__(self, msg: handler.TradingDayCheckRequired) -> None:
        await asyncio.sleep(3)

        self._msg_bus.publish(handler.DataUpdateFinished())
