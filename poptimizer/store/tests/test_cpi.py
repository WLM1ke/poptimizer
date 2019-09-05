import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.store import client
from poptimizer.store.cpi import CPI, MACRO

CHECK_POINTS = [
    ("1991-01-31", 1.0620),
    ("2018-01-31", 1.0031),
    ("2018-11-30", 1.005),
    ("2018-12-31", 1.0084),
]


@pytest.fixture(autouse=True)
@pytest.mark.asyncio
async def create_client(tmpdir_factory):
    async with client.Client():
        yield


@pytest.mark.parametrize("date, value", CHECK_POINTS)
@pytest.mark.asyncio
async def test_cpi(date, value):
    await CPI().update(MACRO)
    df = await CPI().get()
    assert isinstance(df, pd.Series)
    assert df[pd.Timestamp(date)] == value


def test_not_12_months():
    mng = CPI()
    df = pd.DataFrame(0, index=[i for i in range(13)], columns=[1])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        mng._validate(df)
    assert "Таблица должна содержать 12 строк с месяцами" == str(error.value)


def test_bad_first_year():
    mng = CPI()
    df = pd.DataFrame(0, index=[i for i in range(12)], columns=[1992])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        mng._validate(df)
    assert "Первый год должен быть 1991" == str(error.value)


def test_bad_first_month():
    mng = CPI()
    df = pd.DataFrame(0, index=[i for i in range(12)], columns=[1991])
    with pytest.raises(POptimizerError) as error:
        # noinspection PyProtectedMember
        mng._validate(df)
    assert "Первый месяц должен быть январь" == str(error.value)
