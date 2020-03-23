import copy

import pandas as pd
import pytest

from poptimizer.dl import data_loader, data_params
from poptimizer.dl.models import wave_net

DATA_PARAMS = {
    "batch_size": 100,
    "history_days": 245,
    "forecast_days": 194,
    "features": {
        "Label": {"div_share": 0.9},
        "Prices": {},
        "Dividends": {},
        "Weight": {},
    },
}
NET_PARAMS = {
    "start_bn": True,
    "kernels": 3,
    "sub_blocks": 1,
    "gate_channels": 16,
    "residual_channels": 16,
    "skip_channels": 16,
    "end_channels": 16,
}


@pytest.fixture(scope="module", name="loader")
def make_data_loader():
    return data_loader.get_data_loader(
        ("MTSS", "BANE"),
        pd.Timestamp("2020-03-20"),
        DATA_PARAMS,
        data_params.TrainParams,
    )


def test_wave_net_bn(loader):
    batch = next(iter(loader))
    batch2 = copy.deepcopy(batch)
    batch2["Sequence"][0] = batch2["Sequence"][0][50:, :]
    batch2["Sequence"][1] = batch2["Sequence"][1][50:, :]

    net = wave_net.WaveNet(loader, **NET_PARAMS)
    net.eval()
    rez = net(batch)
    rez2 = net(batch2)

    assert rez.shape == (100, 1)
    assert rez2.shape == (50, 1)
    assert rez2.allclose(rez[50:, :])


def test_wave_net_no_bn(loader):
    batch = next(iter(loader))
    batch2 = copy.deepcopy(batch)
    batch2["Sequence"][0] = batch2["Sequence"][0][50:, :]
    batch2["Sequence"][1] = batch2["Sequence"][1][50:, :]

    NET_PARAMS["start_bn"] = False
    net = wave_net.WaveNet(loader, **NET_PARAMS)
    rez = net(batch)
    rez2 = net(batch2)

    assert rez.shape == (100, 1)
    assert rez2.shape == (50, 1)
    assert rez2.allclose(rez[50:, :])
