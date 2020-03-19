import pandas as pd
import pytest
import torch

from poptimizer.dl import data_params
from poptimizer.dl.features import label
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
    return label.Label("CNTLP", params)


class TestLabel:
    def test_getitem(self, feature):
        assert torch.tensor([0.1 * (10.94 - 10.90) / 10.90]).allclose(feature[0])
        assert torch.tensor([(7.41 * 0.87 + 0.1 * (12.54 - 21.60)) / 21.60]).allclose(
            feature[47]
        )
        assert torch.tensor([0.1 * (14.06 - 14.58) / 14.58]).allclose(feature[236])

    def test_name(self, feature):
        assert feature.name == "Label"

    def test_type(self, feature):
        assert feature.type is FeatureTypes.LABEL
