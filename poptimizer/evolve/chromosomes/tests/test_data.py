from poptimizer.evolve.chromosomes import data, chromosome


def test_init_no_data():
    chromo = data.Data({})
    assert len(chromo.data) == 3
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert 252.1 < chromo.data["history_days"] < 252.9
    assert 196.1 < chromo.data["forecast_days"] < 196.9


def test_init_some_data():
    chromo = data.Data(dict(history_days=40))
    assert len(chromo.data) == 3
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert chromo.data["history_days"] == 40
    assert 196.1 < chromo.data["forecast_days"] < 196.9


def test_init_all_data():
    chromo = data.Data(dict(history_days=40, batch_size=10, forecast_days=270))
    assert len(chromo.data) == 3
    assert chromo.data["batch_size"] == 10
    assert chromo.data["history_days"] == 40
    assert chromo.data["forecast_days"] == 270


def test_setup_phenotype():
    chromosome_data = dict(history_days=40, batch_size=10, forecast_days=270)
    chromo = data.Data(chromosome_data)
    base_phenotype = dict(model="Test_Model")
    phenotype_data = dict(model="Test_Model", data=chromosome_data)
    chromo.change_phenotype(base_phenotype)
    assert base_phenotype == phenotype_data


def test_make_child(monkeypatch):
    monkeypatch.setattr(chromosome.random, "rand", lambda _: (0.89, 0.91, 0.89))

    parent = data.Data(dict(batch_size=40, history_days=20, forecast_days=300))
    base = data.Data(dict(batch_size=30, history_days=50, forecast_days=270))
    diff1 = data.Data(dict(batch_size=20, history_days=60, forecast_days=280))
    diff2 = data.Data(dict(batch_size=10, history_days=70, forecast_days=260))

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, data.Data)
    assert len(child.data) == 3

    assert child.data["batch_size"] == 30 + 0.8 * (20 - 10)
    assert child.data["history_days"] == 20
    assert child.data["forecast_days"] == 270 + 0.8 * (280 - 260)
