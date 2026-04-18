from poptimizer.evolve.dl import trainer
from poptimizer.evolve.evolution import genotype


def _check_keys(phenotype, cfg) -> None:
    for k, v in phenotype.items():
        assert k in cfg

        if isinstance(v, dict):
            _check_keys(v, cfg[k])


def test_cfg_match_phenotype():
    phenotype = genotype.Genotype().phenotype
    cfg = trainer.Cfg.model_validate(phenotype).model_dump()
    _check_keys(phenotype, cfg)
