import pandas as pd
import pytest
import torch

from poptimizer.domain import consts
from poptimizer.domain.entity.dl import data_loaders, datasets


@pytest.fixture(name="days")
def make_days():
    return datasets.Days(
        history=4,
        forecast=2,
        test=3,
    )


def test_short_history_error(days) -> None:
    with pytest.raises(consts.DomainError):
        datasets.OneTickerData(
            days,
            pd.Series(range(9)),
            [
                pd.Series(range(2, 13)),
                pd.Series(range(1, 12)),
            ],
        )


def test_features_mismatch_error(days) -> None:
    with pytest.raises(consts.DomainError):
        datasets.OneTickerData(
            days,
            pd.Series(range(10)),
            [
                pd.Series(range(2, 13)),
                pd.Series(range(1, 12)),
            ],
        )


@pytest.fixture(name="one_ticker_data")
def make_one_ticker_data(days):
    return datasets.OneTickerData(
        days,
        pd.Series(range(11)),
        [
            pd.Series(range(2, 13)),
            pd.Series(range(1, 12)),
        ],
    )


class TestOneTickerData:
    def test_len(self, one_ticker_data) -> None:
        assert len(one_ticker_data) == 8

    def test_getitem_last_with_label(self, one_ticker_data) -> None:
        case = one_ticker_data[5]

        assert len(case) == 3
        assert torch.allclose(
            case[datasets.FeatTypes.LABEL1P],
            torch.tensor(110, dtype=torch.float),
        )
        assert torch.allclose(
            case[datasets.FeatTypes.RETURNS],
            torch.tensor([5, 6, 7, 8], dtype=torch.float),
        )
        assert torch.allclose(
            case[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [7, 8, 9, 10],
                    [6, 7, 8, 9],
                ],
                dtype=torch.float,
            ),
        )

    def test_getitem_first_without_label(self, one_ticker_data) -> None:
        case = one_ticker_data[6]

        assert len(case) == 2

        assert torch.allclose(
            case[datasets.FeatTypes.RETURNS],
            torch.tensor([6, 7, 8, 9], dtype=torch.float),
        )
        assert torch.allclose(
            case[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [8, 9, 10, 11],
                    [7, 8, 9, 10],
                ],
                dtype=torch.float,
            ),
        )

    def test_train_dataset_size(self, one_ticker_data) -> None:
        train_dataset = one_ticker_data.train_dataset()

        assert len(train_dataset) == 2

    def test_train_dataset_first(self, one_ticker_data) -> None:
        case_first = one_ticker_data.train_dataset()[0]

        assert len(case_first) == 3
        assert torch.allclose(
            case_first[datasets.FeatTypes.LABEL1P],
            torch.tensor(30, dtype=torch.float),
        )
        assert torch.allclose(
            case_first[datasets.FeatTypes.RETURNS],
            torch.tensor([0, 1, 2, 3], dtype=torch.float),
        )
        assert torch.allclose(
            case_first[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [2, 3, 4, 5],
                    [1, 2, 3, 4],
                ],
                dtype=torch.float,
            ),
        )

    def test_train_dataset_last(self, one_ticker_data) -> None:
        case_last = one_ticker_data.train_dataset()[1]

        assert len(case_last) == 3
        assert torch.allclose(
            case_last[datasets.FeatTypes.LABEL1P],
            torch.tensor(42, dtype=torch.float),
        )
        assert torch.allclose(
            case_last[datasets.FeatTypes.RETURNS],
            torch.tensor([1, 2, 3, 4], dtype=torch.float),
        )
        assert torch.allclose(
            case_last[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [3, 4, 5, 6],
                    [2, 3, 4, 5],
                ],
                dtype=torch.float,
            ),
        )

    def test_test_dataset_size(self, one_ticker_data) -> None:
        test_dataset = one_ticker_data.test_dataset()

        assert len(test_dataset) == 3

    def test_test_dataset_first(self, one_ticker_data) -> None:
        case_first = one_ticker_data.test_dataset()[0]

        assert len(case_first) == 3
        assert torch.allclose(
            case_first[datasets.FeatTypes.LABEL1P],
            torch.tensor(72, dtype=torch.float),
        )
        assert torch.allclose(
            case_first[datasets.FeatTypes.RETURNS],
            torch.tensor([3, 4, 5, 6], dtype=torch.float),
        )
        assert torch.allclose(
            case_first[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [5, 6, 7, 8],
                    [4, 5, 6, 7],
                ],
                dtype=torch.float,
            ),
        )

    def test_test_dataset_last(self, one_ticker_data) -> None:
        case_last = one_ticker_data.test_dataset()[2]

        assert len(case_last) == 3
        assert torch.allclose(
            case_last[datasets.FeatTypes.LABEL1P],
            torch.tensor(110, dtype=torch.float),
        )
        assert torch.allclose(
            case_last[datasets.FeatTypes.RETURNS],
            torch.tensor([5, 6, 7, 8], dtype=torch.float),
        )
        assert torch.allclose(
            case_last[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [
                    [7, 8, 9, 10],
                    [6, 7, 8, 9],
                ],
                dtype=torch.float,
            ),
        )

    def test_forecast_dataset(self, one_ticker_data) -> None:
        forecast_dataset = one_ticker_data.forecast_dataset()

        assert len(forecast_dataset) == 1

        case = forecast_dataset[0]

        assert len(case) == 2
        assert torch.allclose(
            case[datasets.FeatTypes.RETURNS],
            torch.tensor([7, 8, 9, 10], dtype=torch.float),
        )
        assert torch.allclose(
            case[datasets.FeatTypes.NUMERICAL],
            torch.tensor(
                [[9, 10, 11, 12], [8, 9, 10, 11]],
                dtype=torch.float,
            ),
        )


def test_train_data_loader(one_ticker_data) -> None:
    batch_size = 1024

    loader = data_loaders.train(
        [one_ticker_data for _ in range(batch_size)],
        batch_size,
    )

    assert len(loader) == 2

    batch = next(iter(loader))

    assert len(batch) == 3

    label = batch[datasets.FeatTypes.LABEL1P]
    assert label.shape == (batch_size, 1)
    assert torch.min(label) == 30
    assert torch.max(label) == 42

    assert batch[datasets.FeatTypes.RETURNS].shape == (batch_size, 4)
    assert batch[datasets.FeatTypes.NUMERICAL].shape == (batch_size, 2, 4)


@pytest.fixture(name="bad_second_ticker_data")
def make_bad_second_ticker_data():
    days = datasets.Days(
        history=4,
        forecast=2,
        test=2,
    )
    return datasets.OneTickerData(
        days,
        pd.Series(range(12)),
        [
            pd.Series(range(2, 14)),
            pd.Series(range(1, 13)),
        ],
    )


def test_test_length_mismatch_error(one_ticker_data, bad_second_ticker_data) -> None:
    with pytest.raises(consts.DomainError):
        data_loaders.test(
            [one_ticker_data, bad_second_ticker_data],
        )


@pytest.fixture(name="second_ticker_data")
def make_second_ticker_data(days):
    return datasets.OneTickerData(
        days,
        pd.Series(range(12)),
        [
            pd.Series(range(2, 14)),
            pd.Series(range(1, 13)),
        ],
    )


@pytest.fixture(name="test_data_loader")
def make_test_data_loader(one_ticker_data, second_ticker_data):
    return data_loaders.test(
        [one_ticker_data, second_ticker_data],
    )


class TestTestDataLoader:
    def test_size(self, test_data_loader) -> None:
        assert len(test_data_loader) == 3

    def test_first_batch(self, test_data_loader) -> None:
        loader_iter = iter(test_data_loader)
        batch = next(loader_iter)
        ret = batch[datasets.FeatTypes.LABEL1P]
        assert ret.shape == (2, 1)
        assert torch.allclose(
            ret,
            torch.tensor(
                [[110], [132]],
                dtype=torch.float,
            ),
        )

        ret = batch[datasets.FeatTypes.RETURNS]
        assert ret.shape == (2, 4)

        num = batch[datasets.FeatTypes.NUMERICAL]
        assert num.shape == (2, 2, 4)

    def test_last_batch(self, test_data_loader) -> None:
        loader_iter = iter(test_data_loader)
        next(loader_iter)
        next(loader_iter)

        batch = next(loader_iter)

        assert len(batch) == 3

        ret = batch[datasets.FeatTypes.LABEL1P]
        assert ret.shape == (2, 1)
        assert torch.allclose(
            ret,
            torch.tensor(
                [[72], [90]],
                dtype=torch.float,
            ),
        )

        ret = batch[datasets.FeatTypes.RETURNS]
        assert ret.shape == (2, 4)

        num = batch[datasets.FeatTypes.NUMERICAL]
        assert num.shape == (2, 2, 4)


def test_forecast_data_loader(one_ticker_data, second_ticker_data) -> None:
    loader = data_loaders.forecast(
        [one_ticker_data, second_ticker_data, one_ticker_data],
    )

    assert len(loader) == 1

    batch = next(iter(loader))

    assert len(batch) == 2

    ret = batch[datasets.FeatTypes.RETURNS]
    assert ret.shape == (3, 4)
    assert torch.allclose(
        ret,
        torch.tensor(
            [
                range(7, 11),
                range(8, 12),
                range(7, 11),
            ],
            dtype=torch.float,
        ),
    )

    num = batch[datasets.FeatTypes.NUMERICAL]
    assert num.shape == (3, 2, 4)
