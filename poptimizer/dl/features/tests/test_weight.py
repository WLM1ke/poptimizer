import pandas as pd
import pytest
import torch

from poptimizer.data import div
from poptimizer.dl.features import weight, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "forecast_days": 4,
    "features": {
        "Label": {"div_share": 0.9},
        "Prices": {},
        "Dividends": {},
        "Weight": {},
    },
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.ValParams(
        ("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS
    )
    yield weight.Weight("CNTLP", params)

    div.STATS_START = saved_start_date


class TestWeight:
    def test_getitem(self, feature):
        assert torch.tensor([860.552688692118]).allclose(feature[0])
        assert torch.tensor([454.104107146875]).allclose(feature[48])
        assert torch.tensor([1136.24243770129]).allclose(feature[236])

    def test_getitem_low_std(self, feature, monkeypatch):
        monkeypatch.setattr(weight, "LOW_STD", 1 / 25)
        assert torch.tensor([25.0 * 25.0]).allclose(feature[0])
        assert torch.tensor([454.104107146875]).allclose(feature[48])
        assert torch.tensor([25.0 * 25.0]).allclose(feature[236])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.WEIGHT, 8)
