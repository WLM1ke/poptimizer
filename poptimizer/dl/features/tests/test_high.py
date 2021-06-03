import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, high

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Open": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2020-11-03"), PARAMS)
    yield high.High("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestHigh:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(34.1 / 28.49 - 1).allclose(feature[0][0])
        assert torch.tensor(23.85 / 28.49 - 1).allclose(feature[0][5])
        assert torch.tensor(23.515 / 28.49 - 1).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(36.425 / 35.1 - 1).allclose(feature[49][0])
        assert torch.tensor(36.0 / 35.1 - 1).allclose(feature[49][3])
        assert torch.tensor(37.495 / 35.1 - 1).allclose(feature[49][7])

        assert feature[73].shape == torch.Size([8])
        assert torch.tensor(33.455 / 33.05 - 1).allclose(feature[73][0])
        assert torch.tensor(31.4 / 33.05 - 1).allclose(feature[73][5])
        assert torch.tensor(30.45 / 33.05 - 1).allclose(feature[73][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
