import pandas as pd
import pytest
import torch

from poptimizer.dl import data_params, data_loader

PARAMS = {
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
TICKERS = ("NMTP", "BANEP")
DATE = pd.Timestamp("2020-03-20")


@pytest.fixture(scope="class", name="dataset_params")
def make_dataset():
    params = data_params.TrainParams(TICKERS, DATE, PARAMS)
    return data_loader.OneTickerDataset("NMTP", params), params


class TestOneTickerDataset:
    def test_getitem(self, dataset_params):
        dataset, _ = dataset_params
        example = dataset[22]
        assert isinstance(example, dict)
        assert len(example) == 3
        assert set(example) == {"Label", "Weight", "Sequence"}
        assert isinstance(example["Label"], torch.Tensor)
        assert isinstance(example["Weight"], torch.Tensor)
        assert isinstance(example["Sequence"], list)
        assert len(example["Sequence"]) == 2
        assert isinstance(example["Sequence"][0], torch.Tensor)
        assert isinstance(example["Sequence"][1], torch.Tensor)

    def test_len(self, dataset_params):
        dataset, params = dataset_params
        assert len(dataset) == params.len("NMTP")


def test_get_data_loader():
    loader = data_loader.get_data_loader(
        TICKERS, DATE, PARAMS, data_params.ForecastParams
    )
    # noinspection PyUnresolvedReferences
    assert isinstance(loader, torch.utils.data.DataLoader)
    assert len(loader.dataset) == 2

    example = next(iter(loader))
    assert isinstance(example, dict)
    assert len(example) == 1
    assert set(example) == {"Sequence"}
    assert isinstance(example["Sequence"], list)
    assert len(example["Sequence"]) == 2
    assert isinstance(example["Sequence"][0], torch.Tensor)
    assert isinstance(example["Sequence"][1], torch.Tensor)
