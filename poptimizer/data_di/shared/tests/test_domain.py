"""Тесты базовых классов доменной модели."""
import pytest

from poptimizer.data_di.shared import domain


class Entity(domain.BaseEntity):
    """Тестовая реализация сущности доменной области."""

    def __init__(self, id_, attr_value):
        """Хранит один атрибут, создающийся при инициализации."""
        super().__init__(id_)
        self.test_attr = attr_value


@pytest.fixture(scope="module", name="entity")
def create_entity():
    """Создает доменный объект для тестов."""
    id_ = domain.ID("a", "b", "c")
    return Entity(id_, 42)


def test_new_entity(entity):
    """Только созданный доменный объект имеет пустое изменное состояние."""
    assert entity.id_ == domain.ID("a", "b", "c")
    assert entity.test_attr == 42
    assert isinstance(entity.changed_state(), dict)
    assert not entity.changed_state()


def test_changed_entity(entity):
    """Проверка отслеживания изменения состояния."""
    entity.test_attr = 44

    assert entity.id_ == domain.ID("a", "b", "c")
    assert entity.test_attr == 44
    assert entity.changed_state() == {"test_attr": 44}


def test_cleared_entity(entity):
    """Проверка пустого измененного состояния после очистки."""
    entity.clear()

    assert entity.id_ == domain.ID("a", "b", "c")
    assert entity.test_attr == 44
    assert isinstance(entity.changed_state(), dict)
    assert not entity.changed_state()
