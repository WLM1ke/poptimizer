"""Тестирование хромосомы модели."""
from poptimizer.evolve.chromosomes import model


def test_init_no_data():
    """Тестирование значение хромосомы по умолчанию."""
    chromo = model.Model({})

    assert len(chromo.data) == len(model.Model._genes)

    for gene in model.Model._genes:
        if (lower_bound := gene.lower_bound) is not None:
            assert lower_bound < chromo.data[gene.name]
        if (upper_bound := gene.upper_bound) is not None:
            assert chromo.data[gene.name] < upper_bound


def test_setup_phenotype():
    """Проверка генерации фенотипа."""
    chromosome_data = {
        "start_bn": -0.2,
        "kernels": 10,
        "sub_blocks": 270,
        "gate_channels": 2,
        "residual_channels": 3,
        "skip_channels": 4,
        "end_channels": 5,
        "mixture_size": 4,
    }
    chromo = model.Model(chromosome_data)
    base_phenotype = {"type": "Test_Model"}
    phenotype_data = {"type": "Test_Model", "model": chromosome_data}
    phenotype_data["model"]["start_bn"] = False
    chromo.change_phenotype(base_phenotype)
    assert base_phenotype == phenotype_data
