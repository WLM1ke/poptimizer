from poptimizer.evolve.chromosomes import chromosome, data


def test_init_no_data():
    chromo = data.Data({})
    assert len(chromo.data) == 17
    assert 128 < chromo.data["batch_size"] < 512
    assert 37 < chromo.data["history_days"] < 74
    assert -1.0 < chromo.data["ticker_on"] < 1.0
    assert -1.0 < chromo.data["day_of_year_on"] < 1.0
    assert -1.0 < chromo.data["day_of_period_on"] < 1.0
    assert -1.0 < chromo.data["prices_on"] < 1.0
    assert -1.0 < chromo.data["dividends_on"] < 1.0
    assert -1.0 < chromo.data["average_turnover_on"] < 1.0
    assert -1.0 < chromo.data["turnover_on"] < 1.0
    assert -1.0 < chromo.data["rvi_on"] < 1.0
    assert -1.0 < chromo.data["mcftrr_on"] < 1.0
    assert -1.0 < chromo.data["imoex_on"] < 1.0
    assert -1.0 < chromo.data["ticker_type_on"] < 1.0
    assert -1.0 < chromo.data["usd_on"] < 1.0
    assert -1.0 < chromo.data["open_on"] < 1.0


def test_init_some_data():
    chromo = data.Data(dict(history_days=40))
    assert len(chromo.data) == 17
    assert 128 < chromo.data["batch_size"] < 512
    assert chromo.data["history_days"] == 40
    assert -1.0 < chromo.data["ticker_on"] < 1.0
    assert -1.0 < chromo.data["day_of_year_on"] < 1.0
    assert -1.0 < chromo.data["day_of_period_on"] < 1.0
    assert -1.0 < chromo.data["prices_on"] < 1.0
    assert -1.0 < chromo.data["dividends_on"] < 1.0
    assert -1.0 < chromo.data["average_turnover_on"] < 1.0
    assert -1.0 < chromo.data["turnover_on"] < 1.0
    assert -1.0 < chromo.data["rvi_on"] < 1.0
    assert -1.0 < chromo.data["mcftrr_on"] < 1.0
    assert -1.0 < chromo.data["imoex_on"] < 1.0
    assert -1.0 < chromo.data["ticker_type_on"] < 1.0


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
            ticker_type_on=5,
        )
    )
    assert len(chromo.data) == 17
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
    assert chromo.data["ticker_type_on"] == 5


def test_make_child(monkeypatch):
    base = data.Data(
        dict(
            batch_size=40,
            history_days=60,
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
    parent = data.Data(
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

    child = base.make_child(parent, 0)

    assert isinstance(child, data.Data)
    assert base.data == child.data
