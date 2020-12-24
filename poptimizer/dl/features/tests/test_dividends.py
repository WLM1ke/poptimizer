import pandas as pd
import pytest
import torch

import poptimizer.data.app.bootstrap
from poptimizer.dl.features import dividends, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {"div_share": 0.9}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = poptimizer.data.app.bootstrap.START_DATE
    poptimizer.data.app.bootstrap.START_DATE = pd.Timestamp("2010-09-01")
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 240

    params = data_params.TestParams(("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS)
    yield dividends.Dividends("CNTLP", params)

    data_params.FORECAST_DAYS = saved_test_days
    poptimizer.data.app.bootstrap.START_DATE = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor(0.0).allclose(feature[0][5])
        assert torch.tensor(0.0).allclose(feature[0][7])

        assert feature[53].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[53][0])
        assert torch.tensor(0.0).allclose(feature[53][4])
        assert torch.tensor(0.296263787).allclose(feature[53][5])
        assert torch.tensor(0.296263787).allclose(feature[53][7])

        assert feature[236].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[236][0])
        assert torch.tensor(0.0).allclose(feature[236][4])
        assert torch.tensor(0.0).allclose(feature[236][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
