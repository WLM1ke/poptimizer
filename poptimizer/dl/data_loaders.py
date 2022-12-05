from typing import Iterator

from torch.utils import data

from poptimizer.dl import datasets, exceptions

AllTickersData = list[datasets.OneTickerData]
DataLoader = data.DataLoader[datasets.Batch]


def train(
    all_data: AllTickersData,
    batch_size: int,
    num_workers: int = 0,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
) -> DataLoader:
    """Загрузчик данных для тренировки модели.

    Обучающие примеры выдаются батчами заданного размера в случайном порядке.
    """
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.train_dataset() for ticker in all_data),
        batch_size=batch_size,
        shuffle=True,
        drop_last=False,
        num_workers=num_workers,
    )


class _DaysSampler(data.Sampler[list[int]]):
    def __init__(self, all_data: list[data.Subset[datasets.Batch]]) -> None:
        super().__init__(None)
        self._test_days = len(all_data[0])
        self._tests = self._test_days * len(all_data)

        if any(len(dataset) != self._test_days for dataset in all_data):
            raise exceptions.FeaturesError("test length missmatch")

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
            for day in range(self._test_days)
        )


def test(
    all_data: AllTickersData,
    num_workers: int = 0,  # Загрузка в отдельном потоке - увеличение потоков не докидывает
) -> DataLoader:
    """Загрузчик данных для тестирования модели.

    Обучающие примеры выдаются батчами, равными количеству тикеров с фиксированным порядком.
    """
    test_dataset = [ticker.test_dataset() for ticker in all_data]

    return data.DataLoader(
        dataset=data.ConcatDataset(test_dataset),
        batch_sampler=_DaysSampler(test_dataset),
        drop_last=False,
        num_workers=num_workers,
    )


def forecast(
    all_data: AllTickersData,
) -> DataLoader:
    """Загрузчик данных для построения прогноза.

    Обучающие примеры выдаются одним батчем, равными количеству тикеров с фиксированным порядком.
    """
    return data.DataLoader(
        dataset=data.ConcatDataset(ticker.forecast_dataset() for ticker in all_data),
        batch_size=len(all_data),
        shuffle=False,
        drop_last=False,
    )
