import pandas as pd
import pytest
import torch

from poptimizer.dl.features import FeatureType, data_params, ticker_type

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {},
}


@pytest.fixture(scope="module", name="features")
def make_feature():
    params = data_params.TestParams(
        ("FXKZ", "CNTLP", "LKOH", "MU-RM"), pd.Timestamp("2021-01-26"), PARAMS
    )
    yield (
        ticker_type.TickerType("CNTLP", params),
        ticker_type.TickerType("LKOH", params),
        ticker_type.TickerType("FXKZ", params),
        ticker_type.TickerType("MU-RM", params),
    )


class TestTickerType:
    def test_getitem(self, features):
        cntlp, lkoh, fxkz, mu_rm = features

        assert cntlp[0].shape == torch.Size([])
        assert cntlp[0] == torch.tensor(1, dtype=torch.long)

        assert lkoh[49].shape == torch.Size([])
        assert lkoh[49] == torch.tensor(0, dtype=torch.long)

        assert fxkz[236].shape == torch.Size([])
        assert fxkz[236] == torch.tensor(3, dtype=torch.long)

        assert mu_rm[246].shape == torch.Size([])
        assert mu_rm[246] == torch.tensor(2, dtype=torch.long)

    def test_type_and_size(self, features):
        for ticker in features:
            assert ticker.type_and_size == (FeatureType.EMBEDDING, 4)
