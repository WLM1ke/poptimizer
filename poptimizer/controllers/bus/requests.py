from poptimizer.controllers.bus import msg
from poptimizer.use_cases.requests import portfolio, raw


def register_handlers(bus: msg.Bus) -> None:
    port_handler = portfolio.PortfolioHandler()
    bus.register_request_handler(port_handler.get_portfolio)
    bus.register_request_handler(port_handler.create_account)
    bus.register_request_handler(port_handler.remove_acount)
    bus.register_request_handler(port_handler.update_position)
    bus.register_request_handler(port_handler.get_forecast)

    div_handler = raw.DividendsHandler()
    bus.register_request_handler(div_handler.get_div_tickers)
    bus.register_request_handler(div_handler.get_dividends)
    bus.register_request_handler(div_handler.update_dividends)
