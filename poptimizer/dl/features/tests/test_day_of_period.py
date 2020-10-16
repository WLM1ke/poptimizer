import pandas as pd
import pytest
import torch

from poptimizer.data.config import bootstrap
from poptimizer.dl.features import data_params, FeatureType, day_of_period

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {"div_share": 0.7}, "Prices": {}, "Dividends": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = bootstrap.START_DATE
    bootstrap.START_DATE = pd.Timestamp("2010-09-01")
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 243

    params = data_params.TestParams(("PLZL", "KRKNP"), pd.Timestamp("2020-04-29"), PARAMS)
    yield day_of_period.DayOfPeriod("PLZL", params)

    data_params.FORECAST_DAYS = saved_test_days
    bootstrap.START_DATE = saved_start_date


class TestDayOfPeriod:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0) == feature[0][0]
        assert torch.tensor(5) == feature[0][5]
        assert torch.tensor(7) == feature[0][7]

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.EMBEDDING_SEQUENCE, 8)
