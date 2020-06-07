from poptimizer.evolve.chromosomes import scheduler


def test_init_no_data():
    chromo = scheduler.Scheduler({})
    assert len(chromo.data) == 8
    assert 0.001 < chromo.data["max_lr"] < 0.01
    assert 0.999 < chromo.data["epochs"] < 1.001
    assert 0.299 < chromo.data["pct_start"] < 0.301
    assert 0.0 < chromo.data["anneal_strategy"] < 1.0
    assert 0.849 < chromo.data["base_momentum"] < 0.851
    assert 0.949 < chromo.data["max_momentum"] < 0.951
    assert 24.9 < chromo.data["div_factor"] < 25.1
    assert 0.999e4 < chromo.data["final_div_factor"] < 1.01e4


def test_setup_phenotype():
    chromosome_data = dict(
        max_lr=0.2,
        epochs=10.1,
        pct_start=0.4,
        anneal_strategy=-1.5,
        base_momentum=0.6,
        max_momentum=0.7,
        div_factor=1.8,
        final_div_factor=9.9,
    )
    chromo = scheduler.Scheduler(chromosome_data)
    base_phenotype = dict(type="Test_Model")
    phenotype_data = dict(type="Test_Model", scheduler=chromosome_data)
    # noinspection PyTypeChecker
    phenotype_data["scheduler"]["anneal_strategy"] = "linear"
    chromo.change_phenotype(base_phenotype)
    assert base_phenotype == phenotype_data
