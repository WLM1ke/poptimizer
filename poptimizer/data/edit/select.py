"""Сервис выбора тикеров."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/index")
def index() -> dict[str, str]:
    """Заглушка."""
    return {"Hello": "World"}
