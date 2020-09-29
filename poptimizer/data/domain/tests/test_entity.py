"""Тест для базового класса сущностей."""
from poptimizer.data.domain import entity


class Entity(entity.BaseEntity):
    def __init__(self, x):
        super().__init__()
        self.x = x


def test_entity():
    obj = Entity(4)

    assert not obj.is_dirty()

    obj.x = 5

    assert obj.is_dirty()

    obj.clear()

    assert not obj.is_dirty()
