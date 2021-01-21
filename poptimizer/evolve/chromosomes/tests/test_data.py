from poptimizer.evolve.chromosomes import data, chromosome


def test_init_no_data():
    chromo = data.Data({})
    assert len(chromo.data) == 12
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert 50.1 < chromo.data["history_days"] < 50.9
    assert 0.0 < chromo.data["ticker_on"] < 1.0
    assert 0.0 < chromo.data["day_of_year_on"] < 1.0
    assert -1.0 < chromo.data["day_of_period_on"] < 0.0
    assert 0.0 < chromo.data["prices_on"] < 1.0
    assert 0.0 < chromo.data["dividends_on"] < 1.0
    assert 0.0 < chromo.data["average_turnover_on"] < 1.0
    assert 0.0 < chromo.data["turnover_on"] < 1.0
    assert -1.0 < chromo.data["rvi_on"] < 0.0
    assert -1.0 < chromo.data["mcftrr_on"] < 0.0
    assert -1.0 < chromo.data["imoex_on"] < 0.0


def test_init_some_data():
    chromo = data.Data(dict(history_days=40))
    assert len(chromo.data) == 12
    assert 128.1 < chromo.data["batch_size"] < 128.9
    assert chromo.data["history_days"] == 40
    assert 0.0 < chromo.data["ticker_on"] < 1.0
    assert 0.0 < chromo.data["day_of_year_on"] < 1.0
    assert -1.0 < chromo.data["day_of_period_on"] < 0.0
    assert 0.0 < chromo.data["prices_on"] < 1.0
    assert 0.0 < chromo.data["dividends_on"] < 1.0
    assert 0.0 < chromo.data["average_turnover_on"] < 1.0
    assert 0.0 < chromo.data["turnover_on"] < 1.0
    assert -1.0 < chromo.data["rvi_on"] < 0.0
    assert -1.0 < chromo.data["mcftrr_on"] < 0.0
    assert -1.0 < chromo.data["imoex_on"] < 0.0


def test_init_all_data():
    chromo = data.Data(
        dict(
            history_days=40,
            batch_size=10,
            ticker_on=-1,
            day_of_year_on=-3,
            day_of_period_on=-7,
            prices_on=-9,
            dividends_on=-2,
            average_turnover_on=0,
            turnover_on=1,
            rvi_on=7,
            mcftrr_on=8,
            imoex_on=9,
        )
    )
    assert len(chromo.data) == 12
    assert chromo.data["batch_size"] == 10
    assert chromo.data["history_days"] == 40
    assert chromo.data["ticker_on"] == -1
    assert chromo.data["day_of_year_on"] == -3
    assert chromo.data["day_of_period_on"] == -7
    assert chromo.data["dividends_on"] == -2
    assert chromo.data["average_turnover_on"] == 0
    assert chromo.data["turnover_on"] == 1
    assert chromo.data["rvi_on"] == 7
    assert chromo.data["mcftrr_on"] == 8
    assert chromo.data["imoex_on"] == 9


def test_setup_phenotype():
    chromosome_data = dict(
        history_days=40,
        batch_size=10,
        ticker_on=-1,
        day_of_year_on=2,
        day_of_period_on=-7,
        prices_on=-9,
        dividends_on=-2,
        average_turnover_on=0,
        turnover_on=-1,
        rvi_on=-8,
    )
    chromo = data.Data(chromosome_data)
    base_phenotype = dict(model="Test_Model")
    chromo.change_phenotype(base_phenotype)
    phenotype_data = dict(
        model="Test_Model",
        data=dict(
            history_days=40,
            batch_size=10,
            features=dict(
                Ticker=dict(on=False),
                DayOfYear=dict(on=True),
                DayOfPeriod=dict(on=False),
                Prices=dict(on=False),
                Dividends=dict(on=False),
                AverageTurnover=dict(on=False),
                Turnover=dict(on=False),
                RVI=dict(on=False),
                MCFTRR=dict(on=False),
                IMOEX=dict(on=False),
            ),
        ),
    )
    assert base_phenotype == phenotype_data


def test_make_child(monkeypatch):
    monkeypatch.setattr(
        chromosome.random, "rand", lambda _: (0.89, 0.91, 0.89, 0.89, 0.89, 0.89, 0.91, 0.89, 0.91, 0.89)
    )

    parent = data.Data(
        dict(
            batch_size=40,
            history_days=20,
            ticker_on=1,
            day_of_year_on=1,
            day_of_period_on=2,
            prices_on=0,
            dividends_on=1,
            average_turnover_on=1,
            turnover_on=1,
            rvi_on=-8,
        )
    )
    base = data.Data(
        dict(
            batch_size=30,
            history_days=50,
            ticker_on=2,
            day_of_year_on=6,
            day_of_period_on=7,
            prices_on=8,
            dividends_on=1,
            average_turnover_on=4,
            turnover_on=6,
            rvi_on=-6,
        )
    )
    diff1 = data.Data(
        dict(
            batch_size=20,
            history_days=60,
            ticker_on=1,
            day_of_year_on=1,
            day_of_period_on=1,
            prices_on=0,
            dividends_on=2,
            average_turnover_on=0,
            turnover_on=0,
            rvi_on=0,
        )
    )
    diff2 = data.Data(
        dict(
            batch_size=10,
            history_days=70,
            ticker_on=8,
            day_of_year_on=0,
            day_of_period_on=7,
            prices_on=1,
            dividends_on=7,
            average_turnover_on=3,
            turnover_on=4,
            rvi_on=1,
        )
    )

    child = parent.make_child(base, diff1, diff2)

    assert isinstance(child, data.Data)
    assert len(child.data) == 12

    assert child.data["batch_size"] == 30 + 0.8 * (20 - 10)
    assert child.data["history_days"] == 20
    assert child.data["ticker_on"] == 2 + 0.8 * (1 - 8)
    assert child.data["day_of_year_on"] == 6 + 0.8 * (1 - 0)
    assert child.data["day_of_period_on"] == 7 + 0.8 * (1 - 7)
    assert child.data["prices_on"] == 8 + 0.8 * (0 - 1)
    assert child.data["dividends_on"] == 1
    assert child.data["turnover_on"] == 6 + 0.8 * (0 - 4)
    assert child.data["average_turnover_on"] == 1
    assert child.data["rvi_on"] == -6 + 0.8 * (0 - 1)
