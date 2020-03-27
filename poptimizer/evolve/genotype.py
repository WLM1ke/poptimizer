"""Класс генотипа и операций с ним."""
import copy
from typing import List, Dict, Union, Type, Any

from poptimizer.evolve.genes.chromosome import ParamsType, Chromosome


class Genotype:
    """Класс генотипа и операций с ним."""

    def __init__(
        self,
        chromosome_params: ParamsType,
        base_phenotype: ParamsType,
        all_chromosome_types: List[Type[Chromosome]],
    ):
        self._all_chromosome = [
            gen_type(chromosome_params) for gen_type in all_chromosome_types
        ]
        self._base_phenotype = base_phenotype

    @property
    def chromosome(self):
        """Возвращает все гены."""
        return self._all_chromosome

    @property
    def phenotype(self) -> Dict[str, Union[str, Dict[str, Any]]]:
        """Возвращает фенотип - параметры модели соответствующие набору генов."""
        phenotype = copy.deepcopy(self._base_phenotype)
        for chromosome in self._all_chromosome:
            chromosome.set_phenotype(phenotype)
        return phenotype

    def diff_mutation(
        self,
        base: "Genotype",
        diff1: "Genotype",
        diff2: "Genotype",
        factor: float,
        probability: float,
    ) -> Dict[str, Any]:
        """Реализует мутацию в рамках дифференциальной эволюции."""
        gens_params = dict()
        for main, base, diff1, diff2 in zip(
            self.chromosome, base.chromosome, diff1.chromosome, diff2.chromosome
        ):
            gens_params[main.name()] = main.mutate(
                base, diff1, diff2, factor, probability
            )
        return gens_params
