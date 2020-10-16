"""Тесты асинхронного логирования."""
import asyncio
import logging

import pytest

from poptimizer.data.adapters import logger
from poptimizer.data.ports import outer


@pytest.mark.asyncio
async def test_async_logger(caplog):
    """Работа асинхронного логгера."""
    caplog.set_level(logging.INFO)

    async_logger = logger.AsyncLogger("test_name")
    async_logger.log("test_message")

    await asyncio.sleep(0.01)

    assert caplog.record_tuples == [("test_name", 20, "test_message")]


@pytest.mark.asyncio
async def test_loader_logger_mixin(caplog):
    """Логирование загрузки."""
    caplog.set_level(logging.INFO)
    mixin = logger.LoaderLoggerMixin()
    table_name = outer.TableName(outer.QUOTES, "YAKG")

    assert mixin._log_and_validate_group(table_name, outer.QUOTES) == "YAKG"

    await asyncio.sleep(0.01)

    assert caplog.record_tuples == [
        (
            "LoaderLoggerMixin",
            20,
            "Загрузка TableName(group='quotes', name='YAKG')",
        ),
    ]


@pytest.mark.asyncio
async def test_loader_logger_mixin_raises(caplog):
    """Исключение в случае не совпадения названия таблицы и группы."""
    caplog.set_level(logging.INFO)
    mixin = logger.LoaderLoggerMixin()
    table_name = outer.TableName(outer.QUOTES, "YAKG")

    with pytest.raises(outer.DataError, match="Некорректное имя таблицы для обновления"):
        mixin._log_and_validate_group(table_name, outer.SECURITIES)
