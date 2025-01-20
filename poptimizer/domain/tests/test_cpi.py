from datetime import date

import pytest

from poptimizer import errors
from poptimizer.domain import cpi, domain


@pytest.mark.parametrize(
    ("day", "cpi_value", "match"),
    [
        (date(2025, 1, 31), 0.99, "validation error"),
        (date(2025, 1, 30), 1, "not last day of the month"),
    ],
)
def test_row_invalid(day, cpi_value, match) -> None:
    with pytest.raises(ValueError, match=match):
        cpi.Row(day=day, cpi=cpi_value)


def test_cpi_invalid() -> None:
    with pytest.raises(ValueError, match="validation error"):
        cpi.CPI(
            day=date(2025, 1, 20),
            rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(7)),
            df=[
                cpi.Row(day=date(2025, 1, 31), cpi=1),
                cpi.Row(day=date(2025, 1, 31), cpi=1),
            ],
        )


def test_cpi_update_mismatch() -> None:
    table = cpi.CPI(
        day=date(2025, 1, 20),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(7)),
        df=[
            cpi.Row(day=date(2025, 1, 31), cpi=1),
        ],
    )
    rows = [
        cpi.Row(day=date(2025, 1, 31), cpi=1.1),
    ]

    with pytest.raises(errors.DomainError, match="data mismatch error"):
        table.update(date(2025, 1, 19), rows)


def test_cpi_update() -> None:
    table = cpi.CPI(
        day=date(2025, 1, 20),
        rev=domain.Revision(uid=domain.UID("uid"), ver=domain.Version(7)),
        df=[
            cpi.Row(day=date(2025, 1, 31), cpi=1),
        ],
    )
    rows = [
        cpi.Row(day=date(2025, 1, 31), cpi=1),
        cpi.Row(day=date(2025, 2, 28), cpi=1.1),
    ]

    table.update(date(2025, 1, 19), rows)

    assert table.day == date(2025, 1, 19)
    assert table.df == rows
