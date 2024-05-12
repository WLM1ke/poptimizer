from poptimizer.domain import consts
from poptimizer.domain.entity import entity


class Table(entity.Entity):
    last: entity.Day = consts.START_DAY
