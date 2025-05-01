from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.div import raw, reestry


def test_reestry_instantiate_and_fields():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d = date(2020, 1, 1)
    r = raw.Row(day=d, dividend=1.23)
    dr = reestry.DivReestry(rev=rev, day=d, df=[r])

    assert dr.rev == rev
    assert dr.day == d
    assert dr.df == [r]


def test_reestry_update_and_sorting():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d2, dividend=2.0)
    r2 = raw.Row(day=d1, dividend=1.0)
    dr = reestry.DivReestry(rev=rev, day=d1, df=[])
    new_day = date(2020, 1, 3)
    dr.update(new_day, [r1, r2])

    assert dr.day == new_day
    assert dr.df == [r2, r1]


def test_reestry_has_day_and_row():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 1)
    d2 = date(2020, 1, 2)
    r1 = raw.Row(day=d1, dividend=1.0)
    r2 = raw.Row(day=d2, dividend=2.0)
    dr = reestry.DivReestry(rev=rev, day=d2, df=[r1, r2])

    assert dr.has_day(d1)
    assert dr.has_day(d2)
    assert not dr.has_day(date(2020, 1, 3))
    assert dr.has_row(r1)
    assert dr.has_row(r2)

    r3 = raw.Row(day=date(2020, 1, 3), dividend=3.0)
    assert not dr.has_row(r3)


def test_reestry_validators_and_errors():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    d1 = date(2020, 1, 2)
    d2 = date(2020, 1, 1)
    r1 = raw.Row(day=d1, dividend=2.0)
    r2 = raw.Row(day=d2, dividend=1.0)

    with pytest.raises(ValidationError):
        reestry.DivReestry(rev=rev, day=d1, df=[r1, r2])

    d3 = consts.START_DAY - timedelta(days=1)
    r3 = raw.Row(day=d3, dividend=2.0)

    with pytest.raises(ValidationError):
        reestry.DivReestry(rev=rev, day=d3, df=[r3])


def test_reestry_empty_df():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    dr = reestry.DivReestry(rev=rev, day=date(2020, 1, 1), df=[])

    assert not dr.has_day(date(2020, 1, 1))
    assert not dr.has_row(raw.Row(day=date(2020, 1, 1), dividend=1.0))
