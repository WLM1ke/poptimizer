"""Класс генотипа и операций с ним."""
import copy
from typing import List, Dict, Union, Type, Any

from poptimizer.evolve.chromosomes.chromosome import ParamsType, Chromosome


class Genotype:
    """Класс генотипа и операций с ним."""

    def __init__(
        self,
        genotype: ParamsType,
        base_phenotype: ParamsType,
        all_chromosome_types: List[Type[Chromosome]],
    ):
        self._genotype = [gen_type(genotype) for gen_type in all_chromosome_types]
        self._base_phenotype = base_phenotype

    @property
    def chromosome(self) -> List[Chromosome]:
        """Возвращает все гены."""
        return self._genotype

    @property
    def phenotype(self) -> Dict[str, Union[str, Dict[str, Any]]]:
        """Возвращает фенотип - параметры модели соответствующие набору генов."""
        phenotype = copy.deepcopy(self._base_phenotype)
        for chromosome in self._genotype:
            chromosome.set_phenotype(phenotype)
        return phenotype

    def mutate(
        self,
        base: "Genotype",
        diff1: "Genotype",
        diff2: "Genotype",
        factor: float = 0.8,
        probability: float = 0.9,
    ) -> Dict[str, Any]:
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
        gens_params = dict()
        for main, base, diff1, diff2 in zip(
            self.chromosome, base.chromosome, diff1.chromosome, diff2.chromosome
        ):
            gens_params[main.name()] = main.mutate(
                base, diff1, diff2, factor, probability
            )
        return gens_params
