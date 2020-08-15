"""Описание класса со спецификаций таблицы данных и вспомогательные функции для загрузки данных."""
import requests
from requests import adapters

# Максимальный пул соединений по HTTPS и повторных загрузок
MAX_POOL_SIZE = 20
MAX_RETRIES = 3


def start_http_session() -> requests.Session:
    """Открытие пула соединений с интернетом."""
    session = requests.Session()
    adapter = adapters.HTTPAdapter(pool_maxsize=MAX_POOL_SIZE, max_retries=MAX_RETRIES, pool_block=True)
    session.mount("https://", adapter)
    return session


SESSION = start_http_session()


def get_http_session() -> requests.Session:
    """Возвращает сессию для http соединений."""
    return SESSION
