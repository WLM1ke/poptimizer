import pytest
import torch

from poptimizer import errors
from poptimizer.domain.dl import data_loaders, datasets, features


@pytest.fixture(name="days")
def make_days():
    return datasets.Days(
        history=4,
        forecast=2,
        test=3,
    )


def test_no_features_error(days) -> None:
    with pytest.raises(errors.DomainError, match="no features"):
        datasets.TickerData(days, [], [], [], lag_feat=False)


def test_short_history_error(days) -> None:
    with pytest.raises(errors.TooShortHistoryError):
        datasets.TickerData(
            days,
            [
                {
                    features.NumFeat.RETURNS: i,
                    features.NumFeat.OPEN: i + 1,
                    features.NumFeat.CLOSE: i + 2,
                }
                for i in range(9)
            ],
            [features.NumFeat.OPEN, features.NumFeat.CLOSE],
            [],
            lag_feat=False,
        )


@pytest.fixture(name="one_ticker_data")
def make_one_ticker_data(days):
    return datasets.TickerData(
        days,
        [
            {
                features.NumFeat.RETURNS: float(i),
                features.NumFeat.OPEN: float(i + 1),
                features.NumFeat.CLOSE: float(i + 2),
            }
            for i in range(11)
        ],
        [features.NumFeat.OPEN, features.NumFeat.CLOSE],
        [],
        lag_feat=False,
    )


class TestOneTickerData:
    def test_train_dataset_size(self, one_ticker_data) -> None:
        train_dataset = one_ticker_data.train_dataset()

        assert len(train_dataset) == 2

    def test_train_dataset_first(self, one_ticker_data) -> None:
        case_first = one_ticker_data.train_dataset()[0]

        assert torch.allclose(
            case_first.labels,
            torch.tensor(9, dtype=torch.float32).exp(),
        )
        assert torch.allclose(
            case_first.num_feat,
            torch.tensor(
                [
                    [1, 2, 3, 4],
                    [2, 3, 4, 5],
                ],
                dtype=torch.float32,
            ),
        )

    def test_train_dataset_last(self, one_ticker_data) -> None:
        case_last = one_ticker_data.train_dataset()[1]

        assert torch.allclose(
            case_last.labels,
            torch.tensor(11, dtype=torch.float32).exp(),
        )
        assert torch.allclose(
            case_last.num_feat,
            torch.tensor(
                [
                    [2, 3, 4, 5],
                    [3, 4, 5, 6],
                ],
                dtype=torch.float,
            ),
        )

    def test_test_dataset_size(self, one_ticker_data) -> None:
        test_dataset = one_ticker_data.test_dataset()

        assert len(test_dataset) == 3

    def test_test_dataset_first(self, one_ticker_data) -> None:
        case_first = one_ticker_data.test_dataset()[0]

        assert torch.allclose(
            case_first.labels,
            torch.tensor(15, dtype=torch.float32).exp(),
        )
        assert torch.allclose(
            case_first.returns,
            torch.tensor([3, 4, 5, 6], dtype=torch.float32).exp().sub(1),
        )
        assert torch.allclose(
            case_first.num_feat,
            torch.tensor(
                [
                    [4, 5, 6, 7],
                    [5, 6, 7, 8],
                ],
                dtype=torch.float32,
            ),
        )

    def test_test_dataset_last(self, one_ticker_data) -> None:
        case_last = one_ticker_data.test_dataset()[2]

        assert torch.allclose(
            case_last.labels,
            torch.tensor(19, dtype=torch.float32).exp(),
        )
        assert torch.allclose(
            case_last.returns,
            torch.tensor([5, 6, 7, 8], dtype=torch.float32).exp().sub(1),
        )
        assert torch.allclose(
            case_last.num_feat,
            torch.tensor(
                [
                    [6, 7, 8, 9],
                    [7, 8, 9, 10],
                ],
                dtype=torch.float32,
            ),
        )

    def test_forecast_dataset(self, one_ticker_data) -> None:
        forecast_dataset = one_ticker_data.forecast_dataset()

        assert len(forecast_dataset) == 1

        case = forecast_dataset[0]

        assert torch.allclose(
            case.returns,
            torch.tensor([7, 8, 9, 10], dtype=torch.float32).exp().sub(1),
        )
        assert torch.allclose(
            case.num_feat,
            torch.tensor(
                [[8, 9, 10, 11], [9, 10, 11, 12]],
                dtype=torch.float32,
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

    assert batch.labels.shape == (batch_size, 1)
    assert batch.num_feat.shape == (batch_size, 2, 4)


@pytest.fixture(name="second_ticker_data")
def make_second_ticker_data(days):
    return datasets.TickerData(
        days,
        [
            {
                features.NumFeat.RETURNS: float(i),
                features.NumFeat.OPEN: float(i + 1),
                features.NumFeat.CLOSE: float(i + 2),
            }
            for i in range(12)
        ],
        [features.NumFeat.CLOSE, features.NumFeat.OPEN],
        [],
        lag_feat=False,
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
        ret = batch.labels
        assert ret.shape == (2, 1)
        assert torch.allclose(
            ret,
            torch.tensor(
                [[19], [21]],
                dtype=torch.float32,
            ).exp(),
        )

        ret = batch.returns
        assert ret.shape == (2, 4)
        assert torch.allclose(
            ret,
            torch.tensor(
                [range(5, 9), range(6, 10)],
                dtype=torch.float32,
            )
            .exp()
            .sub(1),
        )

        num = batch.num_feat
        assert num.shape == (2, 2, 4)
        assert torch.allclose(
            num[0],
            torch.tensor(
                [range(6, 10), range(7, 11)],
                dtype=torch.float32,
            ),
        )

    def test_last_batch(self, test_data_loader) -> None:
        loader_iter = iter(test_data_loader)
        next(loader_iter)
        next(loader_iter)

        batch = next(loader_iter)

        ret = batch.labels
        assert ret.shape == (2, 1)
        assert torch.allclose(
            ret,
            torch.tensor(
                [[15], [17]],
                dtype=torch.float32,
            ).exp(),
        )

        ret = batch.returns
        assert ret.shape == (2, 4)

        num = batch.num_feat
        assert num.shape == (2, 2, 4)


def test_forecast_data_loader(one_ticker_data, second_ticker_data) -> None:
    loader = data_loaders.forecast(
        [one_ticker_data, second_ticker_data, one_ticker_data],
    )

    assert len(loader) == 1

    batch = next(iter(loader))

    ret = batch.returns
    assert ret.shape == (3, 4)
    assert torch.allclose(
        ret,
        torch.tensor(
            [
                range(7, 11),
                range(8, 12),
                range(7, 11),
            ],
            dtype=torch.float32,
        )
        .exp()
        .sub(1),
    )

    num = batch.num_feat
    assert num.shape == (3, 2, 4)
    assert torch.allclose(
        num[0],
        torch.tensor(
            [
                range(8, 12),
                range(9, 13),
            ],
            dtype=torch.float32,
        ),
    )
