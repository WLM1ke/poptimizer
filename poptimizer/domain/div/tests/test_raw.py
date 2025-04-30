from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.div import raw


def test_row_positive_dividend():
    d = date(2020, 1, 1)
    r = raw.Row(day=d, dividend=1.23)
    assert r.day == d
    assert r.dividend == 1.23


def test_row_invalid_dividend():
    d = date(2020, 1, 1)

    with pytest.raises(ValidationError):
        raw.Row(day=d, dividend=0)

    with pytest.raises(ValidationError):
        raw.Row(day=d, dividend=-1)


def test_row_to_tuple():
    d = date(2020, 1, 1)
    r = raw.Row(day=d, dividend=2.5)

    assert r.to_tuple() == (d, 2.5)


def test_div_raw_validator_sorted():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = consts.START_DAY
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d1, dividend=2.0)
    r3 = raw.Row(day=d2, dividend=2.0)
    r4 = raw.Row(day=d2, dividend=2.0)

    raw.DivRaw(rev=rev, day=d2, df=[r1, r2, r3, r4])


def test_div_raw_validator_unsorted_day():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d2, dividend=2.0)
    r2 = raw.Row(day=d1, dividend=1.0)

    with pytest.raises(ValidationError, match="not sorted"):
        raw.DivRaw(rev=rev, day=d2, df=[r1, r2])


def test_div_raw_validator_unsorted_div():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    r1 = raw.Row(day=d1, dividend=2.0)
    r2 = raw.Row(day=d1, dividend=1.0)

    with pytest.raises(ValidationError, match="not sorted"):
        raw.DivRaw(rev=rev, day=d1, df=[r1, r2])


def test_div_raw_after_start_date_validator_error():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = consts.START_DAY - timedelta(days=1)
    r1 = raw.Row(day=d1, dividend=2.0)

    with pytest.raises(ValidationError, match="day before start day"):
        raw.DivRaw(rev=rev, day=d1, df=[r1])


def test_div_raw_update_sorts_and_sets_day():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d2, dividend=2.0)
    r2 = raw.Row(day=d1, dividend=1.0)
    r3 = raw.Row(day=d2, dividend=1.0)
    dr = raw.DivRaw(rev=rev, day=d1, df=[])
    new_day = date(2020, 1, 3)
    new_rows = [r1, r2, r3]

    dr.update(new_day, new_rows)

    assert dr.day == new_day
    assert dr.df == [r2, r3, r1]


def test_div_raw_has_day():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d2, dividend=2.0)
    dr = raw.DivRaw(rev=rev, day=d2, df=[r1, r2])

    assert dr.has_day(d1)
    assert dr.has_day(d2)
    assert not dr.has_day(date(2020, 1, 3))


def test_div_raw_has_row():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d2, dividend=2.0)
    dr = raw.DivRaw(rev=rev, day=d2, df=[r1, r2])

    assert dr.has_row(r1)
    assert dr.has_row(r2)

    r3 = raw.Row(day=date(2020, 1, 3), dividend=3.0)
    assert not dr.has_row(r3)


def test_div_raw_empty_df():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    dr = raw.DivRaw(rev=rev, day=date(2020, 1, 1), df=[])

    assert not dr.has_day(date(2020, 1, 1))
    assert not dr.has_row(raw.Row(day=date(2020, 1, 1), dividend=1.0))


def test_div_raw_same_day_different_dividends():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d = date(2020, 1, 1)
    r1 = raw.Row(day=d, dividend=1.0)
    r2 = raw.Row(day=d, dividend=2.0)
    dr = raw.DivRaw(rev=rev, day=d, df=[r1, r2])

    assert dr.has_row(r1)
    assert dr.has_row(r2)


def test_div_raw_has_day_and_row_edge_cases():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    d3 = date(2020, 1, 3)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d2, dividend=2.0)
    dr = raw.DivRaw(rev=rev, day=d2, df=[r1, r2])

    assert dr.has_day(d1)

    assert dr.has_day(d2)

    assert not dr.has_day(d3)

    assert not dr.has_row(raw.Row(day=d1, dividend=2.0))


def test_div_raw_validator_duplicate_days():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d = date(2020, 1, 1)
    r1 = raw.Row(day=d, dividend=1.0)
    r2 = raw.Row(day=d, dividend=2.0)

    raw.DivRaw(rev=rev, day=d, df=[r1, r2])

    with pytest.raises(ValidationError, match="not sorted"):
        raw.DivRaw(rev=rev, day=d, df=[r2, r1])


def test_div_raw_update_sorted_input():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d2, dividend=2.0)
    dr = raw.DivRaw(rev=rev, day=d1, df=[])
    dr.update(d2, [r1, r2])
    assert dr.df == [r1, r2]


def test_div_raw_update_with_duplicates():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d = date(2020, 1, 1)
    r1 = raw.Row(day=d, dividend=1.0)
    r2 = raw.Row(day=d, dividend=1.0)
    dr = raw.DivRaw(rev=rev, day=d, df=[])
    dr.update(d, [r2, r1])

    assert dr.df == [r1, r2]
