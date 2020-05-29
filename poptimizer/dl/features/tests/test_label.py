import pandas as pd
import pytest
import torch

from poptimizer.data import div
from poptimizer.dl.features import label, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "forecast_days": 4,
    "features": {"Label": {}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.ValParams(
        ("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS
    )
    yield label.Label("CNTLP", params)

    div.STATS_START = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert torch.tensor([(10.94 - 10.90) / 10.90]).allclose(feature[0])
        assert torch.tensor([(7.41 * 0.87 + (12.54 - 21.60)) / 21.60]).allclose(
            feature[47]
        )
        assert torch.tensor([(14.06 - 14.58) / 14.58]).allclose(feature[236])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.LABEL, 4)
