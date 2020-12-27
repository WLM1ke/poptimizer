from poptimizer.evolve.chromosomes import model, chromosome


def test_init_no_data():
    chromo = model.Model({})
    assert len(chromo.data) == 7
    assert 0.0 < chromo.data["start_bn"] < 1.0
    assert 2.1 < chromo.data["kernels"] < 2.9
    assert 1.1 < chromo.data["sub_blocks"] < 1.2
    assert 4.1 < chromo.data["gate_channels"] < 4.9
    assert 4.1 < chromo.data["residual_channels"] < 4.9
    assert 4.1 < chromo.data["skip_channels"] < 4.9
    assert 4.1 < chromo.data["end_channels"] < 4.9


def test_setup_phenotype():
    chromosome_data = dict(
        start_bn=-0.2,
        kernels=10,
        sub_blocks=270,
        gate_channels=2,
        residual_channels=3,
        skip_channels=4,
        end_channels=5,
    )
    chromo = model.Model(chromosome_data)
    base_phenotype = dict(type="Test_Model")
    phenotype_data = dict(type="Test_Model", model=chromosome_data)
    phenotype_data["model"]["start_bn"] = False
    chromo.change_phenotype(base_phenotype)
    assert base_phenotype == phenotype_data


def test_make_child_lower_upper_bound(monkeypatch):
    monkeypatch.setattr(
        chromosome.random,
        "rand",
        lambda _: (0.89, 0.91, 0.89, 0.91, 0.91, 0.91, 0.91),
    )

    parent = model.Model(
        dict(
            start_bn=0.2,
            kernels=10,
            sub_blocks=4,
            gate_channels=2,
            residual_channels=3,
            skip_channels=4,
            end_channels=5,
        )
    )
    base = model.Model(
        dict(
            start_bn=1.9,
            kernels=10,
            sub_blocks=2,
            gate_channels=2,
            residual_channels=3,
            skip_channels=4,
            end_channels=5,
        )
    )
    diff1 = model.Model(
        dict(
            start_bn=0.5,
            kernels=10,
            sub_blocks=1,
            gate_channels=2,
            residual_channels=3,
            skip_channels=4,
            end_channels=5,
        )
    )
    diff2 = model.Model(
        dict(
            start_bn=0.1,
            kernels=10,
            sub_blocks=10,
            gate_channels=2,
            residual_channels=3,
            skip_channels=4,
            end_channels=5,
        )
    )

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, model.Model)
    assert len(child.data) == 7

    assert child.data["start_bn"] == 1.9 + (0.5 - 0.1) * 0.8
    assert child.data["kernels"] == 10
    assert child.data["sub_blocks"] == 1 - (2 + (1 - 10) * 0.8 - 1)
    assert child.data["gate_channels"] == 2
    assert child.data["residual_channels"] == 3
    assert child.data["skip_channels"] == 4
    assert child.data["end_channels"] == 5
