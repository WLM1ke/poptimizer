"""Абстрактный класс хромосомы."""
import abc
import copy
from dataclasses import dataclass
from typing import Dict, Any, List, Callable, Optional

import numpy as np

from poptimizer import dl


# noinspection PyUnresolvedReferences
@dataclass(frozen=True)
class GeneParams:
    """Описание гена.

    Используется для описания размещения значения гена в фенотипе (система вложенных словарей
    используемых для генерирования данных, построения модели и ее обучения) и хромосоме (вложенный
    словарь используемый для хранения связанных генов в словаре генотипа).

    В хромосоме все гены представлены в виде float - необходимо для реализации дифференциальной эволюции.
    Значение гена может иметь верхнюю и нижнюю границу. В фенотипе значение гена может быть любым типом -
    для преобразования из float используется соответствующая функция.

    Набор генов может расширяться, поэтому у гена должно быть значение по умолчанию. В старых версиях
    генотипа данное значение будет подставляться в случая его отсутствия (с небольшой случайной
    компонентой).

    :param path:
        Список ключей во вложенных словарях соответствующий значению данного гена в фенотипе.
        Последний ключ будет использоваться для хранения значения в словаре хромосомы.
    :param default_value:
        Значение по умолчанию.
    :param phenotype_function:
        Функция для преобразования значения гена (float) в представление, необходимое для фенотипа.
    :param lower_bound:
        Минимальное значение гена - служит ограничением диапазона мутаций.
    :param upper_bound:
        Максимальное значение гена - служит ограничением диапазона мутаций.
    """

    path: List[str]
    default_value: float
    phenotype_function: Callable[[float], Any]
    lower_bound: Optional[float]
    upper_bound: Optional[float]


class Chromosome(abc.ABC):
    """Абстрактный класс хромосомы.

    Хранит значения логически связанных генов. Обновлять фенотип с учетом значений генов и
    осуществляет их дифференциальную эволюцию.
    """

    _GENES: List[GeneParams]

    def __init__(self, genotype: Dict[str, Dict[str, float]]):
        """Формирует полное описании хромосомы.

        В старых версиях генотипа может отсутствовать хромосома или некоторые гены в ней. В место них
        подставляются значения по умолчанию с небольшой случайной составляющей для создания
        генетического разнообразия.

        :param genotype:
            Словарь с описание генотипа - содержит словари описанием хромосом.
        """
        self._chromosome = self._default_chromosome()
        self._chromosome.update(genotype.get(self.name(), dict()))

    def __str__(self) -> str:
        return f"{self.name()}: {self._chromosome}"

    @classmethod
    def name(cls) -> str:
        """Название класса хромосомы.

        Используется в качестве ключа для хранения хромосомы внутри словаря генотипа.
        """
        return cls.__name__

    @classmethod
    def _default_chromosome(
        cls, relative_range: float = 0.1, cape: float = 2.0
    ) -> Dict[str, float]:
        """Значение хромосомы по умолчанию.

        Используется в случае расширения генотипа - организмы с более узким генотипом получат
        значения генов по умолчанию с небольшой случайной компонентой для генетического разнообразия и с
        учетом верхней и нижней границы значения гена.
        """
        chromosome = dict()
        for gene in cls._GENES:
            caped_range = relative_range
            default_value = gene.default_value

            if gene.lower_bound is not None:
                caped_range = min(
                    caped_range,
                    (default_value - gene.lower_bound) / default_value / cape,
                )
            if gene.upper_bound is not None:
                caped_range = min(
                    caped_range,
                    (gene.upper_bound - default_value) / default_value / cape,
                )

            min_ = default_value * (1 - caped_range)
            max_ = default_value * (1 + caped_range)

            chromosome[gene.path[-1]] = np.random.uniform(min_, max_)
        return chromosome

    @property
    def as_dict(self) -> Dict[str, float]:
        """Словарь с описание хромосомы."""
        return self._chromosome

    def set_phenotype(self, phenotype: dl.PhenotypeType) -> None:
        """Устанавливает значения фенотипа в соответствии значениями генов хромосомы.

        Значение гена (float) преобразуется в представление необходимое для фенотипа.
        """
        chromosome = self._chromosome
        for gene in self._GENES:
            node = phenotype
            for key in gene.path[:-1]:
                node = phenotype.setdefault(key, {})
            key = gene.path[-1]
            node[key] = gene.phenotype_function(chromosome[key])

    def make_child(
        self,
        base: "Chromosome",
        diff1: "Chromosome",
        diff2: "Chromosome",
        factor: float,
        probability: float,
    ) -> Dict[str, float]:
        """Мутация в соответствии с алгоритмом дифференциальной эволюции.

        :param base:
            Базовая хромосома для мутации.
        :param diff1:
            Первая хромосома для расчета размера мутации.
        :param diff2:
            Вторая хромосома для расчета размера мутации.
        :param factor:
            Понижающий коэффициент мутации.
        :param probability:
            Вероятность мутации.
        :return:
            Представление хромосомы потомка в виде словаря.
        """
        child = copy.deepcopy(self._chromosome)
        base, diff1, diff2 = base.as_dict, diff1.as_dict, diff2.as_dict
        gens = self._GENES

        flags = np.random.rand(len(gens))
        flags = map(lambda x: x < probability, flags)
        for flag, gene in zip(flags, gens):
            if flag:
                key = gene.path[-1]
                value = base[key] + (diff1[key] - diff2[key]) * factor
                if gene.lower_bound is not None and value < gene.lower_bound:
                    value = (base[key] + gene.lower_bound) / 2
                if gene.upper_bound is not None and value > gene.upper_bound:
                    value = (base[key] + gene.upper_bound) / 2
                child[key] = value
        return child
