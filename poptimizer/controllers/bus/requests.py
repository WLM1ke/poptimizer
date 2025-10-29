from poptimizer.controllers.bus import msg
from poptimizer.use_cases.requests import portfolio, raw, settings


def register_handlers(bus: msg.Bus) -> None:
    port_handler = portfolio.Handler()
    bus.register_request_handler(port_handler.get_portfolio)
    bus.register_request_handler(port_handler.create_account)
    bus.register_request_handler(port_handler.remove_acount)
    bus.register_request_handler(port_handler.update_position)
    bus.register_request_handler(port_handler.exclude_ticker)
    bus.register_request_handler(port_handler.not_exclude_ticker)
    bus.register_request_handler(port_handler.get_forecast)

    div_handler = raw.Handler()
    bus.register_request_handler(div_handler.get_div_tickers)
    bus.register_request_handler(div_handler.get_dividends)
    bus.register_request_handler(div_handler.update_dividends)

    settings_handler = settings.Handler()
    bus.register_request_handler(settings_handler.get_theme)
    bus.register_request_handler(settings_handler.update_theme)
