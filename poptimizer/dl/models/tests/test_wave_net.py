import copy

import pandas as pd
import pytest
import torch

from poptimizer.dl import data_loader
from poptimizer.dl.features import data_params
from poptimizer.dl.models import wave_net

DATA_PARAMS = {
    "batch_size": 100,
    "history_days": 245,
    "forecast_days": 194,
    "features": {
        "Label": {"div_share": 0.9},
        "Prices": {},
        "Dividends": {},
        "Ticker": {},
        "DayOfYear": {},
    },
}
NET_PARAMS = {
    "start_bn": True,
    "embedding_dim": 5,
    "kernels": 3,
    "sub_blocks": 1,
    "gate_channels": 16,
    "residual_channels": 16,
    "skip_channels": 16,
    "end_channels": 16,
}


def test_sub_block():
    residual_channels = 4
    net = wave_net.SubBlock(
        kernels=2, gate_channels=3, residual_channels=residual_channels
    )
    shape = (100, residual_channels, 58)
    input_tensor = torch.rand(*shape)
    input_tensor = net(input_tensor)
    assert net(input_tensor).shape == shape


def test_block():
    residual_channels = 4
    skip_channels = 3
    net = wave_net.Block(
        sub_blocks=2,
        kernels=3,
        gate_channels=9,
        residual_channels=residual_channels,
        skip_channels=skip_channels,
    )
    shape = (101, residual_channels, 59)
    input_tensor = torch.rand(*shape)
    output_tensor, skip = net(input_tensor)
    assert output_tensor.shape == (*shape[:2], (shape[2] + 1) // 2)
    assert skip.shape == (shape[0], skip_channels, 1)


@pytest.fixture(scope="module", name="loader")
def make_data_loader():
    return data_loader.DescribedDataLoader(
        ("MTSS", "BANE"),
        pd.Timestamp("2020-03-20"),
        DATA_PARAMS,
        data_params.TrainParams,
    )


def test_wave_net_bn(loader):
    batch = next(iter(loader))
    batch2 = copy.deepcopy(batch)
    batch2["Prices"] = batch2["Prices"][50:, :]
    batch2["Dividends"] = batch2["Dividends"][50:, :]
    batch2["DayOfYear"] = batch2["DayOfYear"][50:, :]
    batch2["Ticker"] = batch2["Ticker"][50:]

    net = wave_net.WaveNet(loader.features_description, **NET_PARAMS)
    net.eval()
    m1, s1 = net(batch)
    m2, s2 = net(batch2)

    assert m1.shape == (100, 1)
    assert s1.shape == (100, 1)

    assert m2.shape == (50, 1)
    assert s2.shape == (50, 1)

    assert m2.allclose(m1[50:, :])
    assert s2.allclose(s1[50:, :])


def test_wave_net_no_bn(loader):
    batch = next(iter(loader))
    batch2 = copy.deepcopy(batch)
    batch2["Prices"] = batch2["Prices"][:40, :]
    batch2["Dividends"] = batch2["Dividends"][:40, :]
    batch2["DayOfYear"] = batch2["DayOfYear"][:40, :]
    batch2["Ticker"] = batch2["Ticker"][:40]

    NET_PARAMS["start_bn"] = False
    net = wave_net.WaveNet(loader.features_description, **NET_PARAMS)
    m1, s1 = net(batch)
    m2, s2 = net(batch2)

    assert m1.shape == (100, 1)
    assert s1.shape == (100, 1)

    assert m2.shape == (40, 1)
    assert s2.shape == (40, 1)

    assert m2.allclose(m1[:40, :])
    assert s2.allclose(s1[:40, :])
