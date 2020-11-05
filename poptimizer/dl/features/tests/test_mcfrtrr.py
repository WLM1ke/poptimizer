import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, mcftrr

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"MCFTRR": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2020-11-03"), PARAMS)
    yield mcftrr.MCFTRR("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestMCFTRR:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor((4553.91 - 4486.54) / 4486.54).allclose(feature[0][5])
        assert torch.tensor((4592.19 - 4486.54) / 4486.54).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[49][0])
        assert torch.tensor((4797.29 - 4868.04) / 4868.04).allclose(feature[49][3])
        assert torch.tensor((4863.04 - 4868.04) / 4868.04).allclose(feature[49][7])

        assert feature[73].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[73][0])
        assert torch.tensor((4809.03 - 4775.88) / 4775.88).allclose(feature[73][5])
        assert torch.tensor((4713.83 - 4775.88) / 4775.88).allclose(feature[73][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
