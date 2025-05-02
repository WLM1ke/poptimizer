from datetime import date

import pytest
from pydantic import ValidationError

from poptimizer.domain import domain
from poptimizer.domain.div import raw, status


def test_row_valid():
    d = date(2023, 1, 1)
    r = status.Row(
        ticker="TICK",
        ticker_base="BASE",
        preferred=True,
        day=d,
    )
    assert r.ticker == "TICK"
    assert r.ticker_base == "BASE"
    assert r.preferred is True
    assert r.day == d


def test_row_missing_fields():
    d = date(2023, 1, 1)

    with pytest.raises(ValidationError):
        status.Row(ticker="TICK", ticker_base="BASE", preferred=True)

    with pytest.raises(ValidationError):
        status.Row(ticker="TICK", ticker_base="BASE", day=d)

    with pytest.raises(ValidationError):
        status.Row(ticker="TICK", preferred=True, day=d)

    with pytest.raises(ValidationError):
        status.Row(ticker_base="BASE", preferred=True, day=d)


def test_validator_sorted():
    d1 = date(2023, 1, 1)
    d2 = date(2023, 1, 2)
    r1 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d1)
    r2 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d2)
    r3 = status.Row(ticker="B", ticker_base="BASE", preferred=False, day=d1)
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    status.DivStatus(rev=rev, day=d2, df=[r1, r2, r3])


def test_validator_unsorted():
    d1 = date(2023, 1, 1)
    d2 = date(2023, 1, 2)
    r1 = status.Row(ticker="B", ticker_base="BASE", preferred=False, day=d1)
    r2 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d2)
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))

    with pytest.raises(ValidationError, match="not sorted"):
        status.DivStatus(rev=rev, day=d2, df=[r1, r2])


def test_update_sorts_and_sets_day():
    d1 = date(2023, 1, 1)
    d2 = date(2023, 1, 2)
    d3 = date(2023, 1, 3)
    r1 = status.Row(ticker="B", ticker_base="BASE", preferred=False, day=d2)
    r2 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d3)
    r3 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d1)
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    s = status.DivStatus(rev=rev, day=d1, df=[])
    s.update(d3, [r1, r2, r3])

    assert s.day == d3
    assert s.df == [r3, r2, r1]


def test_filter_removes_rows():
    d1 = date(2023, 1, 1)
    d2 = date(2023, 1, 2)
    r1 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d1)
    r2 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d2)
    r3 = status.Row(ticker="B", ticker_base="BASE", preferred=False, day=d1)
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    s = status.DivStatus(rev=rev, day=d2, df=[r1, r2, r3])
    raw_rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    raw_row = raw.Row(day=d1, dividend=1.0)
    raw_table = raw.DivRaw(rev=raw_rev, day=d2, df=[raw_row])
    s.filter(raw_table)

    assert s.df == [r2, r3]


def test_filter_no_removal():
    d1 = date(2023, 1, 1)
    d2 = date(2023, 1, 2)
    r1 = status.Row(ticker="A", ticker_base="BASE", preferred=False, day=d1)
    r2 = status.Row(ticker="B", ticker_base="BASE", preferred=False, day=d2)
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    s = status.DivStatus(rev=rev, day=d2, df=[r1, r2])
    raw_rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    raw_row = raw.Row(day=d2, dividend=1.0)
    raw_table = raw.DivRaw(rev=raw_rev, day=d2, df=[raw_row])
    s.filter(raw_table)

    assert s.df == [r1, r2]
