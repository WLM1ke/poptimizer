"""Основные функции по агрегации данных из локального хранилища.

На уровне данного модуля запросы к асинхронному хранилищу преобразуются в синхронные функции.
"""
from poptimizer.data.cpi import monthly_cpi
from poptimizer.data.dividends import *
from poptimizer.data.moex import *
