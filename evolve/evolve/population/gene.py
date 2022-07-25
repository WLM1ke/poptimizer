"""Ген и генофонд."""
import types
from dataclasses import dataclass
from typing import Callable

from numpy import random
from scipy import stats


@dataclass(frozen=True)
class Gene:
    """Описание гена.

    Значение гена представлено в виде float - необходимо для реализации дифференциальной эволюции.

    Набор генов может расширяться, поэтому у гена должен быть интервал значений по умолчанию —
    будет подставляться случайное значение из этого интервала вместо отсутствующих генов для
    обеспечения генетического разнообразия.

    Значение гена может иметь верхнюю и нижнюю границу, которые будут ограничивать мутацию во время
    дифференциальной эволюции.

    В фенотипе значение гена может быть любым типом — для преобразования из float используется
    соответствующая функция.
    """

    lower_default: float
    upper_default: float
    lower_bound: float
    upper_bound: float
    phenotype: Callable[[float], bool | str | float | int]

    def default(self) -> float:
        """Случайное значение гена по умолчанию."""
        return random.uniform(self.lower_bound, self.upper_default)

    def make_child(self, parent: float, parent1: float, parent2: float, scale: float) -> float:
        """Значение гена ребенка."""
        raw = parent + (parent2 - parent1) * scale * stats.cauchy.rvs()

        return self._to_bounds(raw)

    def _to_bounds(self, raw_value: float) -> float:
        while True:
            if raw_value < self.lower_bound:
                raw_value = self.lower_bound + (self.lower_bound - raw_value)
            elif raw_value > self.upper_bound:
                raw_value = self.upper_bound - (raw_value - self.upper_bound)
            else:
                return raw_value


Chromosome = types.MappingProxyType[str, Gene]

GenoPool = types.MappingProxyType[str, Chromosome]
