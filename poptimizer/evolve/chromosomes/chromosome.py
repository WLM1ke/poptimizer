"""Базовый класс хромосомы и описание гена."""
import copy
from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Any, List, Callable, Optional, Tuple

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

    Набор генов может расширяться, поэтому у гена должно быть интервал значений по умолчанию -
    будет подставляться случайное значение из этого интервала вместо отсутствующих генов для
    обеспечения генетического разнообразия.

    :param path:
        Список ключей во вложенных словарях соответствующий значению данного гена в фенотипе.
        Последний ключ будет использоваться для хранения значения в словаре хромосомы.
    :param default_value:
        Интервал значений по умолчанию.
    :param phenotype_function:
        Функция для преобразования значения гена (float) в представление, необходимое для фенотипа.
    :param lower_bound:
        Минимальное значение гена - служит ограничением диапазона мутаций.
    :param upper_bound:
        Максимальное значение гена - служит ограничением диапазона мутаций.
    """

    path: List[str]
    default_value: Tuple[float, float]
    phenotype_function: Callable[[float], Any]
    lower_bound: Optional[float]
    upper_bound: Optional[float]


class Chromosome(UserDict):
    """Абстрактный класс хромосомы.

    Хранит значения логически связанных генов, обновлять фенотип с учетом значений генов и
    осуществляет их дифференциальную эволюцию.
    """

    _GENES: List[GeneParams]

    def __init__(self, chromosome_data: Dict[str, float]):
        """Формирует полное описании хромосомы.

        В старых версиях генотипа может отсутствовать хромосома или некоторые гены в ней. В место них
        подставляются значения по умолчанию с небольшой случайной составляющей для создания
        генетического разнообразия.

        :param chromosome_data:
            Словарь с описание хромосомы.
        """
        super().__init__(self._default_chromosome_data(), **chromosome_data)

    @classmethod
    def _default_chromosome_data(cls) -> Dict[str, float]:
        """Значение хромосомы по умолчанию.

        Используется в случае расширения генотипа - организмы с более узким генотипом получат
        значения генов по умолчанию с небольшой случайной компонентой для генетического разнообразия и с
        учетом верхней и нижней границы значения гена.
        """
        chromosome_data = dict()
        for gene in cls._GENES:
            chromosome_data[gene.path[-1]] = np.random.uniform(*gene.default_value)
        return chromosome_data

    def setup_phenotype(self, phenotype: dl.PhenotypeType) -> None:
        """Устанавливает значения фенотипа в соответствии значениями генов хромосомы.

        Значение гена (float) преобразуется в представление необходимое для фенотипа.
        """
        chromosome = self.data
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
    ) -> "Chromosome":
        """Мутация в соответствии с алгоритмом дифференциальной эволюции.

        Если мутировавшее значение выходит за границы допустимых значений - берется среднее значение
        между текущим  и границей.

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
        child = copy.deepcopy(self)
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

    def to_dict(self):
        """Словарь с описанием """
        return self.data
