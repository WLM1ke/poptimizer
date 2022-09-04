"""Создает сервер со всеми обработчиками."""
import uvicorn
from fastapi import FastAPI

from poptimizer.data.edit import select


def create(host: str, port: int) -> uvicorn.Server:
    """Создает сервер со всеми обработчиками.

    Обнулен конфиг логов для сервера, чтобы использовался единообразный подход с другими сервисами.
    Отключено логирование запросов у сервера, и сделано на уровне FastAPI.
    """
    app = FastAPI()
    app.include_router(select.router)

    u_cfg = uvicorn.Config(
        app,
        host=host,
        port=port,
        use_colors=True,
        log_config=None,
        access_log=False,
    )

    return uvicorn.Server(u_cfg)
