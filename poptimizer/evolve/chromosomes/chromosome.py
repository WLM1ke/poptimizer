"""Базовый класс хромосомы и описание гена."""
import copy
from collections import UserDict
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Optional

from numpy import random
from scipy import stats

from poptimizer.dl import PhenotypeData


@dataclass(frozen=True)
class GeneParams:
    """Описание гена.

    Используется для описания размещения значения гена в фенотипе (система вложенных словарей
    используемых для генерирования данных, построения модели и ее обучения) и хромосоме (словарь
    используемый для хранения связанных генов).

    В хромосоме все гены представлены в виде float - необходимо для реализации дифференциальной эволюции.
    Набор генов может расширяться, поэтому у гена должен быть интервал значений по умолчанию —
    будет подставляться случайное значение из этого интервала вместо отсутствующих генов для
    обеспечения генетического разнообразия.

    Значение гена может иметь верхнюю и нижнюю границу, которые будут ограничивать мутацию во время
    дифференциальной эволюции.

    В фенотипе значение гена может быть любым типом — для преобразования из float используется
    соответствующая функция.
    """

    name: str
    default_range: tuple[float, float]
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    path: tuple[str, ...]
    phenotype_function: Callable[[float], Any]


# Представление данных в хромосоме
ChromosomeData = dict[str, float]


class Chromosome(UserDict):
    """Базовый класс хромосомы.

    Хранит значения логически связанных генов, обновлять фенотип с учетом значений генов и
    осуществляет их дифференциальную эволюцию.
    """

    _genes: ClassVar[tuple[GeneParams, ...]] = ()

    def __init__(self, chromosome_data: ChromosomeData) -> None:
        """Формирует полное описание хромосомы.

        В старых версиях генотипа может отсутствовать хромосома или некоторые гены в ней. В место них
        подставляются значения по умолчанию с небольшой случайной составляющей для создания
        генетического разнообразия.

        :param chromosome_data:
            Словарь с описанием хромосомы.
        """
        super().__init__(_default_chromosome_data(self._genes), **chromosome_data)

    def change_phenotype(self, phenotype: PhenotypeData) -> None:
        """Меняет фенотип в соответствии со значениями генов хромосомы.

        Значение гена (float) преобразуется в представление необходимое для фенотипа.
        """
        for gene in self._genes:
            node = phenotype
            for path_key in gene.path[:-1]:
                node = node.setdefault(path_key, {})
            value_key = gene.path[-1]
            node[value_key] = gene.phenotype_function(self[gene.name])

    def make_child(
        self,
        parent1: "Chromosome",
        parent2: "Chromosome",
        scale: float,
    ) -> "Chromosome":
        """Мутация на основе алгоритма дифференциальной эволюции.

        Если мутировавшее значение выходит за границы допустимых значений,
        то значение отражается от границы.

        :param parent1:
            Хромосома первого родителя, которая используется для расчета разницы значений признаков.
        :param parent2:
            Хромосома второго родителя, которая используется для расчета разницы значений признаков.
        :param scale:
            Фактор масштабирования разницы между родителями.
        :return:
            Представление хромосомы потомка в виде словаря.
        """
        child = copy.deepcopy(self)
        for gene in self._genes:
            key = gene.name
            diff = (parent1[key] - parent2[key]) * scale
            raw_value = child[key] + diff * stats.norm.rvs()
            child[key] = _to_bounds(raw_value, gene.lower_bound, gene.upper_bound)

        return child


def _default_chromosome_data(genes: tuple[GeneParams, ...]) -> ChromosomeData:
    """Значение хромосомы по умолчанию.

    Используется в случае расширения генотипа — организмы с более узким генотипом получат
    значения генов по умолчанию с небольшой случайной компонентой для генетического разнообразия и с
    учетом верхней и нижней границы значения гена.
    """
    chromosome_data = {}
    for gene in genes:
        chromosome_data[gene.name] = random.uniform(*gene.default_range)
    return chromosome_data


def _to_bounds(raw_value: float, lower_bound: Optional[float], upper_bound: Optional[float]) -> float:
    while True:
        if lower_bound is not None and raw_value < lower_bound:
            raw_value = lower_bound + (lower_bound - raw_value)
        elif upper_bound is not None and raw_value > upper_bound:
            raw_value = upper_bound - (raw_value - upper_bound)
        else:
            return raw_value
