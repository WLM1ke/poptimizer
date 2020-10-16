import pandas as pd
import pytest
import torch

from poptimizer.data.config import bootstrap
from poptimizer.dl.features import data_params, FeatureType, day_of_year

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {"div_share": 0.7}, "Prices": {}, "Dividends": {}},
}


@pytest.fixture(scope="module", name="features")
def make_feature():
    saved_start_date = bootstrap.START_DATE
    bootstrap.START_DATE = pd.Timestamp("2010-09-01")
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 243

    params = data_params.TestParams(("PLZL", "KRKNP"), pd.Timestamp("2020-04-29"), PARAMS)
    yield day_of_year.DayOfYear("PLZL", params), day_of_year.DayOfYear("KRKNP", params)

    data_params.FORECAST_DAYS = saved_test_days
    bootstrap.START_DATE = saved_start_date


class TestDayOfYear:
    def test_getitem(self, features):
        day1, day2 = features
        assert day1[0].shape == torch.Size([8])
        assert torch.tensor(121) == day1[0][0]
        assert torch.tensor(129) == day1[0][5]
        assert torch.tensor(133) == day1[0][7]

        assert day2[49].shape == torch.Size([8])
        assert torch.tensor(192) == day2[49][0]
        assert torch.tensor(197) == day2[49][3]
        assert torch.tensor(203) == day2[49][7]

        assert day1[239].shape == torch.Size([8])
        assert torch.tensor(104) == day1[239][0]
        assert torch.tensor(110) == day1[239][4]
        assert torch.tensor(113) == day1[239][7]

    def test_type_and_size(self, features):
        day1, day2 = features
        assert day1.type_and_size == (FeatureType.EMBEDDING_SEQUENCE, 366)
        assert day2.type_and_size == (FeatureType.EMBEDDING_SEQUENCE, 366)
