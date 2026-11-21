import pickle
from typing import cast

import pytest

from poptimizer.core import domain, errors


def test_too_short_history_pickle_round_trip() -> None:
    err = errors.TooShortHistoryError(domain.Ticker("TEST"), 42)

    restored = cast("errors.TooShortHistoryError", pickle.loads(pickle.dumps(err)))  # noqa: S301

    assert type(restored) is errors.TooShortHistoryError
    assert restored.args == err.args
    assert restored.minimal_returns_days == 42


@pytest.mark.parametrize(
    "err",
    [
        errors.DomainError("message"),
        errors.UseCasesError("message"),
        errors.AdapterError("message"),
        errors.ControllersError("message"),
    ],
)
def test_library_errors_pickle_round_trip(err: errors.POError) -> None:
    restored = cast("errors.POError", pickle.loads(pickle.dumps(err)))  # noqa: S301

    assert type(restored) is type(err)
    assert restored.args == err.args
