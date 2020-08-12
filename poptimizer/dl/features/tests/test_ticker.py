import pandas as pd
import pytest
import torch

from poptimizer.data_old import div
from poptimizer.dl.features import data_params, FeatureType, ticker

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Label": {"div_share": 0.9}, "Prices": {}, "Dividends": {}, "Weight": {}},
}


@pytest.fixture(scope="module", name="features")
def make_feature():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.TestParams(("LKOH", "CNTLP"), pd.Timestamp("2020-03-18"), PARAMS)
    yield ticker.Ticker("CNTLP", params), ticker.Ticker("LKOH", params)

    div.STATS_START = saved_start_date


class TestTicker:
    def test_getitem(self, features):
        ticker1, ticker2 = features
        assert ticker1[0].shape == torch.Size([])
        assert ticker1[0] == torch.tensor(1, dtype=torch.long)

        assert ticker2[49].shape == torch.Size([])
        assert ticker2[49] == torch.tensor(0, dtype=torch.long)

        assert ticker2[236].shape == torch.Size([])
        assert ticker2[236] == torch.tensor(0, dtype=torch.long)

    def test_type_and_size(self, features):
        ticker1, ticker2 = features
        assert ticker1.type_and_size == (FeatureType.EMBEDDING, 2)
        assert ticker2.type_and_size == (FeatureType.EMBEDDING, 2)
