import pandas as pd
import pytest
import torch

import poptimizer.data.app.bootstrap
from poptimizer.dl.features import FeatureType, data_params, label

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = poptimizer.data.app.bootstrap.START_DATE
    poptimizer.data.app.bootstrap.START_DATE = pd.Timestamp("2010-09-01")
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 4

    params = data_params.TestParams(("CNTLP", "LKOH"), pd.Timestamp("2020-08-07"), PARAMS)
    yield label.Label("CNTLP", params)

    data_params.FORECAST_DAYS = saved_test_days
    poptimizer.data.app.bootstrap.START_DATE = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert torch.tensor([(17.86 - 29.8 + 11.83 * 0.87) / 29.8]).allclose(feature[0])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.LABEL, 4)
