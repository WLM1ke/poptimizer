"""Фабрика для асинхронного http-соединения."""
import asyncio
import atexit

import aiohttp


def _clean_up(session: aiohttp.ClientSession) -> None:
    """Закрывает клиентскую сессию aiohttp."""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(session.close())


def session_factory(pool_size: int) -> aiohttp.ClientSession:
    """Клиентская сессия aiohttp."""
    connector = aiohttp.TCPConnector(limit=pool_size)
    session = aiohttp.ClientSession(connector=connector)
    atexit.register(_clean_up, session)
    return session
