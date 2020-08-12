import pandas as pd
import pytest
import torch

from poptimizer.data_old import div
from poptimizer.dl.features import turnover, data_params, FeatureType

PARAMS = {
    "batch_size": 100,
    "history_days": 8,
    "features": {"Turnover": {}},
}


@pytest.fixture(scope="module", name="params")
def make_params():
    saved_start_date = div.STATS_START
    div.STATS_START = pd.Timestamp("2010-09-01")

    params = data_params.TestParams(("CNTLP", "LKOH"), pd.Timestamp("2020-03-18"), PARAMS)
    yield params

    div.STATS_START = saved_start_date


@pytest.fixture(scope="function", name="turnover_cntlp")
def make_turnover_cntlp(params):
    yield turnover.Turnover("CNTLP", params)


class TestTurnover:
    def test_getitem(self, turnover_cntlp):
        assert turnover_cntlp[0].shape == torch.Size([8])
        assert torch.tensor(10.1297063703673).allclose(turnover_cntlp[0][0])
        assert torch.tensor(11.4684405200307).allclose(turnover_cntlp[0][5])
        assert torch.tensor(12.6732942836246).allclose(turnover_cntlp[0][7])

        assert turnover_cntlp[49].shape == torch.Size([8])
        assert torch.tensor(15.7650180858293).allclose(turnover_cntlp[49][0])
        assert torch.tensor(18.3151484913264).allclose(turnover_cntlp[49][3])
        assert torch.tensor(17.3864105164998).allclose(turnover_cntlp[49][7])

        assert turnover_cntlp[236].shape == torch.Size([8])
        assert torch.tensor(15.3231453973094).allclose(turnover_cntlp[236][0])
        assert torch.tensor(15.5651014667367).allclose(turnover_cntlp[236][4])
        assert torch.tensor(15.6629672351018).allclose(turnover_cntlp[236][7])

    def test_type_and_size(self, turnover_cntlp):
        assert turnover_cntlp.type_and_size == (FeatureType.SEQUENCE, 8)


@pytest.fixture(scope="class")
def clean_cache(params):
    del params.cache[turnover.TURNOVER]
    del params.cache[turnover.AVERAGE_TURNOVER]


@pytest.fixture(scope="function", name="avr_lkoh")
def make_turnover_lkoh(params):
    yield turnover.AverageTurnover("LKOH", params)


class TestAverageTurnover:
    def test_getitem(self, avr_lkoh):
        assert avr_lkoh[0].shape == torch.Size([8])
        assert torch.tensor(21.4069205180786).allclose(avr_lkoh[0][0])
        assert torch.tensor(20.9764804037646).allclose(avr_lkoh[0][5])
        assert torch.tensor(21.2972159559927).allclose(avr_lkoh[0][7])

        assert avr_lkoh[49].shape == torch.Size([8])
        assert torch.tensor(21.7906959945983).allclose(avr_lkoh[49][0])
        assert torch.tensor(21.9321645581981).allclose(avr_lkoh[49][3])
        assert torch.tensor(21.3933199370821).allclose(avr_lkoh[49][7])

        assert avr_lkoh[236].shape == torch.Size([8])
        assert torch.tensor(22.8339303916294).allclose(avr_lkoh[236][0])
        assert torch.tensor(22.5762276038492).allclose(avr_lkoh[236][4])
        assert torch.tensor(22.8645569305271).allclose(avr_lkoh[236][7])

    # noinspection DuplicatedCode
    @pytest.mark.usefixtures("clean_cache")
    def test_getitem_no_cache(self, avr_lkoh):
        assert avr_lkoh[0].shape == torch.Size([8])
        assert torch.tensor(21.4069205180786).allclose(avr_lkoh[0][0])
        assert torch.tensor(20.9764804037646).allclose(avr_lkoh[0][5])
        assert torch.tensor(21.2972159559927).allclose(avr_lkoh[0][7])

        assert avr_lkoh[49].shape == torch.Size([8])
        assert torch.tensor(21.7906959945983).allclose(avr_lkoh[49][0])
        assert torch.tensor(21.9321645581981).allclose(avr_lkoh[49][3])
        assert torch.tensor(21.3933199370821).allclose(avr_lkoh[49][7])

        assert avr_lkoh[236].shape == torch.Size([8])
        assert torch.tensor(22.8339303916294).allclose(avr_lkoh[236][0])
        assert torch.tensor(22.5762276038492).allclose(avr_lkoh[236][4])
        assert torch.tensor(22.8645569305271).allclose(avr_lkoh[236][7])

    def test_type_and_size(self, avr_lkoh):
        assert avr_lkoh.type_and_size == (FeatureType.SEQUENCE, 8)
