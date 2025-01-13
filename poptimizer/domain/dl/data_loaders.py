from collections.abc import Iterator

from torch.utils import data

from poptimizer import errors
from poptimizer.domain.dl import datasets

AllTickersData = list[datasets.TickerData]


def train(all_data: AllTickersData, batch_size: int) -> data.DataLoader[datasets.TrainBatch]:
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.train_dataset() for ticker in all_data),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,
    )


class _DaysSampler(data.Sampler[list[int]]):
    def __init__(self, all_data: list[datasets.TickerTestDataSet]) -> None:
        super().__init__()
        self._test_days = len(all_data[0])
        self._tests = self._test_days * len(all_data)

        if any(len(dataset) != self._test_days for dataset in all_data):
            raise errors.DomainError("test length mismatch")

    def __len__(self) -> int:
        return self._test_days

    def __iter__(self) -> Iterator[list[int]]:
        yield from (
            list(
                range(
                    day,
                    self._tests,
                    self._test_days,
                ),
            )
            for day in reversed(range(self._test_days))
        )


def test(all_data: AllTickersData) -> data.DataLoader[datasets.TestBatch]:
    test_dataset = [ticker.test_dataset() for ticker in all_data]

    return data.DataLoader(
        dataset=data.ConcatDataset(test_dataset),
        batch_sampler=_DaysSampler(test_dataset),
        drop_last=False,
    )


def forecast(all_data: AllTickersData) -> data.DataLoader[datasets.ForecastBatch]:
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.forecast_dataset() for ticker in all_data),
        batch_size=len(all_data),
        shuffle=False,
        drop_last=False,
    )
