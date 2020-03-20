import pandas as pd
import pytest
import torch

from poptimizer.dl import data_params
from poptimizer.dl.features import weight
from poptimizer.dl.features.feature import FeatureTypes

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
    params = data_params.ValParams(
        ("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS
    )
    return weight.Weight("CNTLP", params)


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

    def test_name(self, feature):
        assert feature.name == "Weight"

    def test_type(self, feature):
        assert feature.type is FeatureTypes.WEIGHT
