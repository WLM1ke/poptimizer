"""HTTP-соединение и загрузка страницы по url."""
import requests
from requests import adapters

from poptimizer.data import ports

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


def get_html(url: str) -> str:
    """Получает необходимую html-страницу."""
    session = get_http_session()
    with session.get(url) as respond:
        try:
            respond.raise_for_status()
        except requests.HTTPError:
            raise ports.DataError(f"Данные {url} не загружены")
        else:
            html = respond.text
    return html
