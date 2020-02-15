import pandas as pd
import pytest
import torch
from torch.utils.data import Dataset

import poptimizer
from poptimizer.dl import datasets_old

DIV, PRICE = poptimizer.data.div_ex_date_prices(
    ("KRKNP", "CHMF", "MRKC"), pd.Timestamp("2019-01-10")
)
DATA_PARAMS = (PRICE, DIV, {"history_days": 5, "forecast_days": 3, "div_share": 0.6})
TEST_DATA = [
    dict(
        params=DATA_PARAMS,
        len=1783 + 2124 * 2 - 4 * 3,
        keys=3,
        shapes=((4,), (4,), torch.Size([])),
    ),
    dict(
        params=(*DATA_PARAMS, pd.Timestamp("2018-10-31")),
        len=144 - 4 * 3,
        keys=3,
        shapes=((4,), (4,), torch.Size([])),
    ),
    dict(
        params=(*DATA_PARAMS, None, pd.Timestamp("2018-11-21")),
        len=1783 + 2124 * 2 - 4 * 3 - 99,
        keys=4,
        shapes=((4,), (4,), torch.Size([]), torch.Size([])),
    ),
    dict(
        params=(*DATA_PARAMS, pd.Timestamp("2018-10-31"), pd.Timestamp("2018-11-21")),
        len=45 - 4 * 3,
        keys=4,
        shapes=((4,), (4,), torch.Size([]), torch.Size([])),
    ),
]


@pytest.mark.parametrize("data", TEST_DATA)
def test_get_dataset_len_and_shape(data):
    rez = datasets_old.get_dataset(*data["params"])
    assert isinstance(rez, Dataset)
    assert len(rez) == data["len"]
    assert len(rez[0]) == data["keys"]
    for value, shape in zip(rez[0].values(), data["shapes"]):
        assert isinstance(value, torch.Tensor)
        assert value.shape == shape


@pytest.fixture(name="dataset")
def make_dataset():
    return datasets_old.get_dataset(*TEST_DATA[2]["params"])


def test_get_dataset_price_values(dataset):
    value = dataset[0]
    assert torch.allclose(
        value["price"], torch.tensor([0, 0, -0.264558823529412, -0.264558823529412])
    )
    value = dataset[1750 - 4 - 1]
    assert torch.allclose(
        value["price"],
        torch.tensor(
            [
                0.0183150183150182,
                0.0164835164835164,
                0.0073260073260073,
                0.00549450549450547,
            ]
        ),
    )
    value = dataset[1750 - 4]
    assert torch.allclose(
        value["price"],
        torch.tensor(
            [
                -0.0210545732430367,
                -0.00231890168383886,
                -0.0158106932989012,
                -0.0161532583203773,
            ]
        ),
    )
    value = dataset[len(dataset) - 1]
    assert torch.allclose(
        value["price"],
        torch.tensor(
            [
                -0.00207900207900225,
                -0.00762300762300772,
                -0.0131670131670133,
                -0.00900900900900914,
            ]
        ),
    )


def test_get_dataset_label_values(dataset):
    value = dataset[0]
    assert value["label"] == torch.tensor(0.257748450309938 * 0.4)
    value = dataset[1750 - 4 - 1]
    assert value["label"] == torch.tensor(-0.0127504553734062 * 0.4)
    value = dataset[1750 - 4]
    assert value["label"] == torch.tensor(-0.0415684593957576 * 0.4)

    # Учет дивидендов
    value = dataset[1750 - 4 + 2041]
    assert value["label"] == torch.tensor(0.0136523836023001)
    value = dataset[1750 - 4 + 2042]
    assert value["label"] == torch.tensor(0.0330818551367331)
    value = dataset[1750 - 4 + 2043]
    assert value["label"] == torch.tensor(0.0271714155666819)
    value = dataset[1750 - 4 + 2044]
    assert value["label"] == torch.tensor(0.017549596412556)
    value = dataset[1750 - 4 + 2045]
    assert value["label"] == torch.tensor(0.00727611940298508)

    value = dataset[len(dataset) - 1]
    assert value["label"] == torch.tensor(0.00139860139860137 * 0.4)


def test_get_dataset_weight_values(dataset):
    value = dataset[0]
    assert value["weight"] == torch.tensor(57.1499020053445)
    value = dataset[9]
    # Обрезка низкой волатильности
    assert value["weight"] == torch.tensor(10 ** 6)
    value = dataset[1750 - 4 - 1]
    assert value["weight"] == torch.tensor(7228.03073085306)
    value = dataset[1750 - 4]
    assert value["weight"] == torch.tensor(3224.8694622829)
    # Учет дивидендов
    value = dataset[1750 - 4 + 2046]
    assert value["weight"] == torch.tensor(11748.064354186)
    value = dataset[len(dataset) - 1]
    assert value["weight"] == torch.tensor(46973.8028823736)


def test_get_dataset_div_values(dataset):
    value = dataset[0]
    assert torch.allclose(value["div"], torch.tensor([0.0, 0.0, 0.0, 0.0]))
    value = dataset[1750 - 4 + 2044]
    assert torch.allclose(value["div"], torch.tensor([0.0, 0.0, 0.0, 0.0]))
    value = dataset[1750 - 4 + 2045]
    assert torch.allclose(value["div"], torch.tensor([0, 0, 0, 0.0370690038953812]))
    value = dataset[1750 - 4 + 2046]
    assert torch.allclose(
        value["div"], torch.tensor([0, 0, 0.0369251662971175, 0.0369251662971175])
    )
    value = dataset[1750 - 4 + 2047]
    assert torch.allclose(
        value["div"],
        torch.tensor([0, 0.0363839781520255, 0.0363839781520255, 0.0363839781520255]),
    )
    value = dataset[1750 - 4 + 2048]
    assert torch.allclose(
        value["div"],
        torch.tensor(
            [
                0.0358455605381166,
                0.0358455605381166,
                0.0358455605381166,
                0.0358455605381166,
            ]
        ),
    )
    value = dataset[1750 - 4 + 2049]
    assert torch.allclose(value["div"], torch.tensor([0.0, 0.0, 0.0, 0.0]))
