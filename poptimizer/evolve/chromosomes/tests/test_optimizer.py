from poptimizer.evolve.chromosomes import optimizer


def test_init_no_data():
    chromo = optimizer.Optimizer({})
    assert len(chromo.data) == 3
    assert 0.99899 < chromo.data["betas"] < 0.99901
    assert 0.999e-8 < chromo.data["eps"] < 1.001e-8
    assert 0.999e-2 < chromo.data["weight_decay"] < 1.01e-2


def test_setup_phenotype():
    chromosome_data = dict(betas=0.2, eps=10.0, weight_decay=270.0)
    chromo = optimizer.Optimizer(chromosome_data)
    base_phenotype = dict(type="Test_Model")
    phenotype_data = dict(type="Test_Model", optimizer=chromosome_data)
    # noinspection PyTypeChecker
    phenotype_data["optimizer"]["betas"] = (0.9, 0.2)
    chromo.change_phenotype(base_phenotype)
    assert base_phenotype == phenotype_data
