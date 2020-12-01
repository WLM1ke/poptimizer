import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, imoex

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"IMOEX": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2020-11-30"), PARAMS)
    yield imoex.IMOEX("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestIMOEX:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor((2801.66 - 2760.75) / 2760.75).allclose(feature[0][5])
        assert torch.tensor((2825.21 - 2760.75) / 2760.75).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[49][0])
        assert torch.tensor((2888.79 - 2931.92) / 2931.92).allclose(feature[49][3])
        assert torch.tensor((2928.38 - 2931.92) / 2931.92).allclose(feature[49][7])

        assert feature[97].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[97][0])
        assert torch.tensor((3080.68 - 3015.03) / 3015.03).allclose(feature[97][5])
        assert torch.tensor((3051.04 - 3015.03) / 3015.03).allclose(feature[97][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
