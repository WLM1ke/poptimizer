import pandas as pd
import pytest
import torch

from poptimizer.data import div
from poptimizer.dl.features import turnover, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "forecast_days": 4,
    "features": {"Turnover": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.ValParams(
        ("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS
    )
    yield turnover.Turnover("CNTLP", params)

    div.STATS_START = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert feature[0].shape == torch.Size([8])
        assert torch.tensor(10.1297063703673).allclose(feature[0][0])
        assert torch.tensor(11.4684405200307).allclose(feature[0][5])
        assert torch.tensor(12.6732942836246).allclose(feature[0][7])

        assert feature[49].shape == torch.Size([8])
        assert torch.tensor(15.7650180858293).allclose(feature[49][0])
        assert torch.tensor(18.3151484913264).allclose(feature[49][3])
        assert torch.tensor(17.3864105164998).allclose(feature[49][7])

        assert feature[236].shape == torch.Size([8])
        assert torch.tensor(15.3231453973094).allclose(feature[236][0])
        assert torch.tensor(15.5651014667367).allclose(feature[236][4])
        assert torch.tensor(15.6629672351018).allclose(feature[236][7])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.SEQUENCE, 8)
