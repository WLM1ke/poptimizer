import pickle

import pytest

from poptimizer.core import errors


def test_too_short_history_pickle_round_trip():
    err = errors.TooShortHistoryError("TEST", 42)

    restored = pickle.loads(pickle.dumps(err))

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
def test_library_errors_pickle_round_trip(err):
    restored = pickle.loads(pickle.dumps(err))

    assert type(restored) is type(err)
    assert restored.args == err.args
