from poptimizer.evolve.chromosomes import data, chromosome


def test_init_no_data():
    chromo = data.Data({})
    assert len(chromo.data) == 6
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert 252.1 < chromo.data["history_days"] < 252.9
    assert 196.1 < chromo.data["forecast_days"] < 196.9
    assert 0.0 < chromo.data["ticker_on"] < 1.0
    assert 0.0 < chromo.data["day_of_year_on"] < 1.0
    assert 0.0 < chromo.data["average_turnover"] < 1.0


def test_init_some_data():
    chromo = data.Data(dict(history_days=40))
    assert len(chromo.data) == 6
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert chromo.data["history_days"] == 40
    assert 196.1 < chromo.data["forecast_days"] < 196.9
    assert 0.0 < chromo.data["ticker_on"] < 1.0
    assert 0.0 < chromo.data["day_of_year_on"] < 1.0
    assert 0.0 < chromo.data["average_turnover"] < 1.0


def test_init_all_data():
    chromo = data.Data(
        dict(
            history_days=40,
            batch_size=10,
            forecast_days=270,
            ticker_on=-1,
            day_of_year_on=-3,
            average_turnover=0,
        )
    )
    assert len(chromo.data) == 6
    assert chromo.data["batch_size"] == 10
    assert chromo.data["history_days"] == 40
    assert chromo.data["forecast_days"] == 270
    assert chromo.data["ticker_on"] == -1
    assert chromo.data["day_of_year_on"] == -3
    assert chromo.data["average_turnover"] == 0


def test_setup_phenotype():
    chromosome_data = dict(
        history_days=40,
        batch_size=10,
        forecast_days=270,
        ticker_on=-1,
        day_of_year_on=2,
        average_turnover=0,
    )
    chromo = data.Data(chromosome_data)
    base_phenotype = dict(model="Test_Model")
    chromo.change_phenotype(base_phenotype)
    phenotype_data = dict(
        model="Test_Model",
        data=dict(
            history_days=40,
            batch_size=10,
            forecast_days=270,
            features=dict(
                Ticker=dict(on=False), DayOfYear=dict(on=True), AverageTurnover=dict(on=False)
            ),
        ),
    )
    assert base_phenotype == phenotype_data


def test_make_child(monkeypatch):
    monkeypatch.setattr(chromosome.random, "rand", lambda _: (0.89, 0.91, 0.89, 0.89, 0.89, 0.91))

    parent = data.Data(
        dict(
            batch_size=40,
            history_days=20,
            forecast_days=300,
            ticker_on=1,
            day_of_year_on=1,
            average_turnover=1,
        )
    )
    base = data.Data(
        dict(
            batch_size=30,
            history_days=50,
            forecast_days=270,
            ticker_on=2,
            day_of_year_on=6,
            average_turnover=4,
        )
    )
    diff1 = data.Data(
        dict(
            batch_size=20,
            history_days=60,
            forecast_days=280,
            ticker_on=1,
            day_of_year_on=1,
            average_turnover=0,
        )
    )
    diff2 = data.Data(
        dict(
            batch_size=10,
            history_days=70,
            forecast_days=260,
            ticker_on=8,
            day_of_year_on=0,
            average_turnover=3,
        )
    )

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, data.Data)
    assert len(child.data) == 6

    assert child.data["batch_size"] == 30 + 0.8 * (20 - 10)
    assert child.data["history_days"] == 20
    assert child.data["forecast_days"] == 270 + 0.8 * (280 - 260)
    assert child.data["ticker_on"] == 2 + 0.8 * (1 - 8)
    assert child.data["day_of_year_on"] == 6 + 0.8 * (1 - 0)
    assert child.data["average_turnover"] == 1
