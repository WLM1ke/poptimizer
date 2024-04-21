from aiohttp import web


class Handlers:
    def __init__(self, app: web.Application) -> None:
        self._app = app
