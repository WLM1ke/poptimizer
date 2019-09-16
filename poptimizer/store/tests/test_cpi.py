import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import cpi
from poptimizer.store.cpi import CPI
from poptimizer.store.mongo import MONGO_CLIENT

CHECK_POINTS = [
    ("1991-01-31", 1.0620),
    ("2018-01-31", 1.0031),
    ("2018-11-30", 1.005),
    ("2018-12-31", 1.0084),
]


@pytest.fixture("module", name="manager")
def manager_in_clean_test_db():
    MONGO_CLIENT.drop_database("test")
    yield cpi.Macro(db="test")
    MONGO_CLIENT.drop_database("test")


def test_not_cpi_error(manager):
    with pytest.raises(POptimizerError) as error:
        # noinspection PyStatementEffect
        manager["QQQ"]
    assert "Отсутствуют данные test.misc.QQQ" == str(error.value)


@pytest.mark.parametrize("date, value", CHECK_POINTS)
def test_cpi(date, value, manager):
    df = manager[CPI]
    assert isinstance(df, pd.DataFrame)
    assert df.loc[pd.Timestamp(date), CPI] == value


def test_not_12_months(manager):
    df = pd.DataFrame(0, index=[i for i in range(13)], columns=[1])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        manager._validate(df)
    assert "Таблица должна содержать 12 строк с месяцами" == str(error.value)


def test_bad_first_year(manager):
    df = pd.DataFrame(0, index=[i for i in range(12)], columns=[1992])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        manager._validate(df)
    assert "Первый год должен быть 1991" == str(error.value)


def test_bad_first_month(manager):
    df = pd.DataFrame(0, index=[i for i in range(12)], columns=[1991])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        manager._validate(df)
    assert "Первый месяц должен быть январь" == str(error.value)
