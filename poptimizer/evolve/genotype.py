"""Класс генотипа и операций с ним."""
import copy
from collections import UserDict
from typing import List, Dict, Union, Type, Any, Optional

from poptimizer import dl
from poptimizer.evolve import chromosomes

# База для формирования фенотипа
BASE_PHENOTYPE = {
    "type": "WaveNet",
    "data": {
        "features": {
            "Label": {"div_share": 0.0},
            "Prices": {},
            "Dividends": {},
            "Weight": {},
        }
    },
}
# Все используемые хромосомы
ALL_CHROMOSOMES_TYPES = [
    chromosomes.Data,
    chromosomes.Model,
    chromosomes.Optimizer,
    chromosomes.Scheduler,
]


class Genotype(UserDict):
    """Класс генотипа и операций с ним."""

    def __init__(
            self,
            genotype_data: Dict[str, Dict[str, float]] = None,
            base_phenotype: Optional[dl.PhenotypeType] = None,
            all_chromosome_types: Optional[List[Type[chromosomes.Chromosome]]] = None,
    ):
        super().__init__()

        genotype_data = genotype_data or {}
        all_chromosome_types = all_chromosome_types or ALL_CHROMOSOMES_TYPES

        for gen_type in all_chromosome_types:
            key = gen_type.__name__
            chromosome_data = genotype_data.get(key, dict())
            self.data[key] = gen_type(chromosome_data)

        self._base_phenotype = base_phenotype or BASE_PHENOTYPE

    def __str__(self):
        return "\n".join(
            f"{key}: {chromosome}" for key, chromosome in self.data.items()
        )

    @property
    def phenotype(self) -> Dict[str, Union[str, Dict[str, Any]]]:
        """Возвращает фенотип - параметры модели соответствующие набору генов."""
        phenotype = copy.deepcopy(self._base_phenotype)
        for chromosome in self.data.values():
            chromosome.setup_phenotype(phenotype)
        return phenotype

    def make_child(
        self,
        base: "Genotype",
        diff1: "Genotype",
        diff2: "Genotype",
        factor: float = 0.8,
        probability: float = 0.9,
    ) -> "Genotype":
        """Реализует мутацию в рамках дифференциальной эволюции.


        If you are going to optimize your own objective function with DE, you may try the following
        classical settings for the input file first: Choose method e.g. DE/rand/1/bin, set the number of
        parents NP to 10 times the number of parameters, select weighting factor F=0.8, and crossover
        constant CR=0.9. It has been found recently that selecting F from the interval [0.5, 1.0]
        randomly for each generation or for each difference vector, a technique called dither, improves
        convergence behaviour significantly, especially for noisy objective functions. It has also been
        found that setting CR to a low value, e.g. CR=0.2 helps optimizing separable functions since it
        fosters the search along the coordinate axes. On the contrary this choice is not effective if
        parameter dependence is encountered, something which is frequently occuring in real-world
        optimization problems rather than artificial test functions. So for parameter dependence the
        choice of CR=0.9 is more appropriate. Another interesting empirical finding is that rasing NP
        above, say, 40 does not substantially improve the convergence, independent of the number of
        parameters. It is worthwhile to experiment with these suggestions. Make sure that you initialize
        your parameter vectors by exploiting their full numerical range, i.e. if a parameter is allowed
        to exhibit values in the range [-100, 100] it's a good idea to pick the initial values from this
        range instead of unnecessarily restricting diversity.
        """
        child = copy.deepcopy(self)
        for key in child:
            child[key] = self[key].make_child(
                base[key], diff1[key], diff2[key], factor, probability
            )
        return child

    def to_dict(self):
        """Словарь с описанием """
        genotype = {key: chromosome.to_dict() for key, chromosome in self.data.items()}
        return genotype
