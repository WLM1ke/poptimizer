import pandas as pd
import pytest
import torch

from poptimizer.data import div
from poptimizer.dl.features import prices, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "forecast_days": 4,
    "features": {"Label": {"div_share": 0.9}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.TestParams(("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS)
    yield prices.Prices("CNTLP", params)

    div.STATS_START = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[0][0])
        assert torch.tensor(-0.0740740740740742).allclose(feature[0][5])
        assert torch.tensor(-0.0824915824915825).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[49][0])
        assert torch.tensor(0.176863181312569).allclose(feature[49][3])
        assert torch.tensor(0.153503893214683).allclose(feature[49][7])

        assert feature[236].shape == torch.Size([8])
        assert torch.tensor(0.0).allclose(feature[236][0])
        assert torch.tensor(0.0112079701120797).allclose(feature[236][4])
        assert torch.tensor(-0.0921544209215441).allclose(feature[236][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
