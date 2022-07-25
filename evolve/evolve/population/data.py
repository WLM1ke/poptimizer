"""Хромосома данных."""
import types

import numpy as np

from evolve.population import gene


def chromosome() -> gene.Chromosome:
    """Хромосома данных."""
    return types.MappingProxyType(
        {
            "batch_size": gene.Gene(
                lower_default=128,  # noqa: WPS432
                upper_default=128 * 4,  # noqa: WPS432
                lower_bound=1.0,
                upper_bound=np.inf,
                phenotype=int,
            ),
        },
    )
