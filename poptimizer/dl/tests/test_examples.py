import pandas as pd
import pytest
import torch
from torch.utils import data

from poptimizer.dl import examples


@pytest.fixture(scope="module", name="example")
def make_examples():
    return examples.Examples(
        ("PMSBP", "UNAC"),
        pd.Timestamp("2019-01-14"),
        {"history_days": 6, "forecast_days": 4, "div_share": 0.6},
    )


def test_train_val_dataset(example):
    train, val = example.train_val_dataset()

    assert isinstance(train, data.Dataset)
    assert isinstance(val, data.Dataset)

    rez = train[0]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0781565217391305)
    rez = train[len(train) - 1]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(-0.0103151862464183)

    rez = val[0]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.017)
    rez = val[len(val) - 1]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0110552763819095)


# noinspection DuplicatedCode
def test_train_val_dataset_non_default(example):
    train, val = example.train_val_dataset(
        {"history_days": 6, "forecast_days": 4, "div_share": 0.4}
    )

    assert isinstance(train, data.Dataset)
    assert isinstance(val, data.Dataset)

    rez = train[0]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0781565217391305 * 1.5)
    rez = train[len(train) - 1]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(-0.0103151862464183 * 1.5)

    rez = val[0]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.017 * 1.5)
    rez = val[len(val) - 1]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0110552763819095 * 1.5)


# noinspection DuplicatedCode
def test_train_predict_dataset(example):
    train, predict = example.train_predict_dataset()

    assert isinstance(train, data.Dataset)
    assert isinstance(predict, data.Dataset)

    rez = train[0]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0781565217391305)
    rez = train[len(train) - 1]
    assert len(rez) == 4
    assert rez["label"] == torch.tensor(0.0110552763819095)

    assert len(predict) == 2
    rez = predict[0]
    assert len(rez) == 3
    assert rez["weight"] == torch.tensor(37825.5795674102)
    rez = predict[1]
    assert len(rez) == 3
    assert rez["weight"] == torch.tensor(13000.4268995439)
