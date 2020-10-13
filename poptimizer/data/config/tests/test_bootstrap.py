"""Конфигурация запуска приложения."""
import datetime

import pytest

from poptimizer.data.app import handlers
from poptimizer.data.config import bootstrap


def test_get_handler():
    """Проверка, что возвращается обработчик."""
    assert isinstance(bootstrap.get_handler(), handlers.Handler)


def test_get_start_date():
    """Проверка, что начальная дата с 20015 года."""
    assert bootstrap.get_start_date() == datetime.date(2015, 1, 1)


def test_get_after_tax_rate():
    """Проверка, что посленалоговая ставка 0.87."""
    assert bootstrap.get_after_tax_rate() == pytest.approx(0.87)
