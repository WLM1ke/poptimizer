import asyncio

from poptimizer.handlers import handler


class EvolutionHandler:
    def __init__(self, msg_bus: handler.Bus) -> None:
        self._msg_bus = msg_bus

    async def __call__(self, msg: handler.DataUpdateFinished) -> None:
        await asyncio.sleep(3)

        self._msg_bus.publish(handler.TradingDayCheckRequired())
