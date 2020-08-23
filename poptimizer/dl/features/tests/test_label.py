import pandas as pd
import pytest
import torch

from poptimizer.data_old import div
from poptimizer.dl.features import label, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="feature")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")
    saved_test_days = data_params.TEST_DAYS
    data_params.TEST_DAYS = 240

    params = data_params.TestParams(("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS)
    yield label.Label("CNTLP", params)

    data_params.TEST_DAYS = saved_test_days
    div.STATS_START = saved_start_date


class TestLabel:
    def test_getitem(self, feature):
        assert torch.tensor([-0.012843981385231018]).allclose(feature[0])
        assert torch.tensor([-0.03611114248633385]).allclose(feature[47])
        assert torch.tensor([0.006858736742287874]).allclose(feature[236])

    def test_type_and_size(self, feature):
        assert feature.type_and_size == (FeatureType.LABEL, 1)
