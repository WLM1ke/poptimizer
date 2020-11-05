import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, rvi

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"RVI": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2020-10-16"), PARAMS)
    yield rvi.RVI("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestRVI:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(31.49).allclose(feature[0][0])
        assert torch.tensor(32.16).allclose(feature[0][5])
        assert torch.tensor(32.03).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(36.51).allclose(feature[49][0])
        assert torch.tensor(36.59).allclose(feature[49][3])
        assert torch.tensor(33.23).allclose(feature[49][7])

        assert feature[61].shape == torch.Size([8])
        assert torch.tensor(35.95).allclose(feature[61][0])
        assert torch.tensor(38.81).allclose(feature[61][4])
        assert torch.tensor(37.79).allclose(feature[61][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
