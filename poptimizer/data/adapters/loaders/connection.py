"""HTTP-соединение и загрузка страницы по url."""
import requests

from poptimizer.data.config import resources
from poptimizer.data.ports import base


def get_html(url: str) -> str:
    """Получает необходимую html-страницу."""
    session = resources.get_http_session()
    with session.get(url) as respond:
        try:
            respond.raise_for_status()
        except requests.HTTPError:
            raise base.DataError(f"Данные {url} не загружены")
        else:
            html = respond.text
    return html
