"""Базовый класс хромосомы и описание гена."""
import copy
from collections import UserDict
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional, Tuple, NoReturn, ClassVar

from numpy import random

from poptimizer.dl import PhenotypeData

# Параметры по умолчанию для дифференциальной мутации
MUTATION_FACTOR = 0.8
MUTATION_PROBABILITY = 0.9


@dataclass(frozen=True)
class GeneParams:
    """Описание гена.

    Используется для описания размещения значения гена в фенотипе (система вложенных словарей
    используемых для генерирования данных, построения модели и ее обучения) и хромосоме (словарь
    используемый для хранения связанных генов).

    В хромосоме все гены представлены в виде float - необходимо для реализации дифференциальной эволюции.
    Набор генов может расширяться, поэтому у гена должен быть интервал значений по умолчанию -
    будет подставляться случайное значение из этого интервала вместо отсутствующих генов для
    обеспечения генетического разнообразия.

    Значение гена может иметь верхнюю и нижнюю границу, которые будут ограничивать мутацию во время
    дифференциальной эволюции.

    В фенотипе значение гена может быть любым типом - для преобразования из float используется
    соответствующая функция.
    """

    path: Tuple[str, ...]
    default_range: Tuple[float, float]
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    phenotype_function: Callable[[float], Any]


# Представление данных в хромосоме
ChromosomeData = Dict[str, float]


class Chromosome(UserDict):
    """Базовый класс хромосомы.

    Хранит значения логически связанных генов, обновлять фенотип с учетом значений генов и
    осуществляет их дифференциальную эволюцию.
    """

    _GENES: ClassVar[Tuple[GeneParams]] = tuple()

    def __init__(self, chromosome_data: ChromosomeData) -> NoReturn:
        """Формирует полное описании хромосомы.

        В старых версиях генотипа может отсутствовать хромосома или некоторые гены в ней. В место них
        подставляются значения по умолчанию с небольшой случайной составляющей для создания
        генетического разнообразия.

        :param chromosome_data:
            Словарь с описание хромосомы.
        """
        super().__init__(self._default_chromosome_data(), **chromosome_data)

    @classmethod
    def _default_chromosome_data(cls) -> ChromosomeData:
        """Значение хромосомы по умолчанию.

        Используется в случае расширения генотипа - организмы с более узким генотипом получат
        значения генов по умолчанию с небольшой случайной компонентой для генетического разнообразия и с
        учетом верхней и нижней границы значения гена.
        """
        chromosome_data = dict()
        for gene in cls._GENES:
            chromosome_data[gene.path[-1]] = random.uniform(*gene.default_range)
        return chromosome_data

    def change_phenotype(self, phenotype: PhenotypeData) -> NoReturn:
        """Меняет фенотип в соответствии со значениями генов хромосомы.

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
        factor: float = MUTATION_FACTOR,
        probability: float = MUTATION_PROBABILITY,
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

        flags = random.rand(len(gens))
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

    def to_dict(self) -> ChromosomeData:
        """Словарь с описанием данных."""
        return self.data
