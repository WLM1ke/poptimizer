from poptimizer.domain.evolve import genotype
from poptimizer.use_cases.dl import trainer


def _check_keys(phenotype, cfg) -> None:
    for k, v in phenotype.items():
        assert k in cfg

        if isinstance(v, dict):
            _check_keys(v, cfg[k])


def test_cfg_match_phenotype():
    phenotype = genotype.Genotype().phenotype
    cfg = trainer.Cfg.model_validate(phenotype).model_dump()
    _check_keys(phenotype, cfg)
