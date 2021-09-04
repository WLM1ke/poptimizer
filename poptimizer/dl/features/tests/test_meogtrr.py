import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, meogtrr

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"MEOGTRR": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_test_days = data_params.FORECAST_DAYS
    data_params.FORECAST_DAYS = 6

    params = data_params.TrainParams(("POGR", "LKOH"), pd.Timestamp("2020-11-03"), PARAMS)
    yield meogtrr.MEOGTRR("POGR", params)

    data_params.FORECAST_DAYS = saved_test_days


class TestMEOGTRR:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor((9401.39 - 9404.93) / 9404.93).allclose(feature[0][4])
        assert torch.tensor((9485.31 - 9404.93) / 9404.93).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[49][0])
        assert torch.tensor((9119.57 - 9256.56) / 9256.56).allclose(feature[49][3])
        assert torch.tensor((9110.93 - 9256.56) / 9256.56).allclose(feature[49][5])

        assert feature[73].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[73][0])
        assert torch.tensor((8863.58 - 8961.23) / 8961.23).allclose(feature[73][5])
        assert torch.tensor((8713.12 - 8961.23) / 8961.23).allclose(feature[73][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
