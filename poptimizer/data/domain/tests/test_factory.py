"""Тесты для фабрики таблиц."""
import pytest

from poptimizer.data.domain import factory
from poptimizer.data.domain.tables import base


@pytest.fixture(scope="function", name="table_factory")
def create_table_factory(mocker):
    """Создать фабрику таблиц для тестов."""
    table_factory = factory.TablesFactory()
    table_factory._types_mapping = {"group1": mocker.Mock()}
    return table_factory


def test_wrong_id(table_factory):
    """Исключение при неправильной группе в ID."""
    id_ = base.create_id("group2")
    with pytest.raises(base.TableWrongIDError):
        table_factory(id_, {})


def test_table_creation(table_factory, mocker):
    """Создание таблицы."""
    fake_df = mocker.Mock()
    fake_timestamp = mocker.Mock()
    mongo_dict = {"df": fake_df, "timestamp": fake_timestamp}
    id_ = base.create_id("group1")

    table_factory(id_, mongo_dict)

    table_factory._types_mapping["group1"].assert_called_once_with(id_, fake_df, fake_timestamp)
