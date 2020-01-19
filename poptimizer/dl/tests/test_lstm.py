import torch

from poptimizer.dl import lstm


def test_lstm_bi():
    model = lstm.LSTM(4, 5, bidirectional=True)
    data = dict(price=torch.rand((6, 7)), div=torch.rand((6, 7)))
    rez = model(data)
    assert rez.shape == (6, 1)

    assert torch.allclose(rez[:3], model({k: v[:3] for k, v in data.items()}))
    assert torch.allclose(rez[3:], model({k: v[3:] for k, v in data.items()}))


def test_lstm():
    model = lstm.LSTM(3, 6, bidirectional=False)
    data = dict(price=torch.rand((7, 4)), div=torch.rand((7, 4)))
    rez = model(data)
    assert rez.shape == (7, 1)

    assert torch.allclose(rez[:4], model({k: v[:4] for k, v in data.items()}))
    assert torch.allclose(rez[4:], model({k: v[4:] for k, v in data.items()}))
