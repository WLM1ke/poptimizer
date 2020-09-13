import pandas as pd
import pytest
import torch

from poptimizer.dl import data_loader
from poptimizer.dl.features import data_params, FeatureType
from poptimizer.dl.features.data_params import FORECAST_DAYS

PARAMS = {
    "batch_size": 100,
    "history_days": 245,
    "features": {"Label": {"on": True}, "Prices": {"on": True}, "Dividends": {"on": True}},
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
        keys = {"Label", "Prices", "Dividends"}
        assert set(example) == keys
        for key in keys:
            assert isinstance(example[key], torch.Tensor)

    def test_len(self, dataset_params):
        dataset, params = dataset_params
        assert len(dataset) == params.len("NMTP")

    def test_features_description(self, dataset_params):
        dataset, _ = dataset_params
        description = dataset.features_description
        assert isinstance(description, dict)
        assert len(description) == 3
        assert description == dict(
            Label=(FeatureType.LABEL, FORECAST_DAYS),
            Prices=(FeatureType.SEQUENCE, 245),
            Dividends=(FeatureType.SEQUENCE, 245),
        )


@pytest.fixture(scope="class", name="loader")
def make_data_loader():
    return data_loader.DescribedDataLoader(TICKERS, DATE, PARAMS, data_params.ForecastParams)


class TestDescribedDataLoader:
    def test_data_loader(self, loader):
        assert len(loader.dataset) == 2

        example = next(iter(loader))
        assert isinstance(example, dict)
        assert len(example) == 2
        keys = {"Prices", "Dividends"}
        assert set(example) == keys
        for key in keys:
            assert isinstance(example[key], torch.Tensor)

    def test_features_description(self, loader):
        description = loader.features_description
        assert isinstance(description, dict)
        assert len(description) == 2
        assert description == dict(
            Prices=(FeatureType.SEQUENCE, 245), Dividends=(FeatureType.SEQUENCE, 245)
        )
