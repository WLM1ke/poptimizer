import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, usd

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"USD": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2021-02-12"), PARAMS)
    yield usd.USD("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestUSD:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor(71.37 / 69.02 - 1).allclose(feature[0][5])
        assert torch.tensor(71.4725 / 69.02 - 1).allclose(feature[0][7])

        assert feature[50].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[50][0])
        assert torch.tensor(76.28 / 75.4325 - 1).allclose(feature[50][2])
        assert torch.tensor(74.99 / 75.4325 - 1).allclose(feature[50][7])

        assert feature[148].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[148][0])
        assert torch.tensor(76.1475 / 75.085 - 1).allclose(feature[148][4])
        assert torch.tensor(75.505 / 75.085 - 1).allclose(feature[148][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
