"""Тест для базового класса сущностей."""
from poptimizer.data.domain import entity


class Entity(entity.BaseEntity):
    """Тестовая реализация сущности доменной области."""

    def __init__(self, attr_value):
        """Хранит один атрибут, создающийся при инициализации."""
        super().__init__()
        self.test_attr = attr_value


def test_entity():
    """Проверка отслеживания изменения состояния.

    - чистый после создания
    - грязный после изменения атрибута
    - чистый после очистки состояния
    """
    test_odj = Entity(4)

    assert not test_odj.is_dirty()

    test_odj.test_attr = 5

    assert test_odj.is_dirty()

    test_odj.clear()

    assert not test_odj.is_dirty()
