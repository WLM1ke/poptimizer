from datetime import timedelta

import pytest
from pydantic import ValidationError

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.div import div


def make_revision():
    return domain.Revision(uid=domain.UID("TEST"), ver=domain.Version(0))


def make_dividends(day, df):
    return div.Dividends(rev=make_revision(), day=day, df=df)


def test_row_invalid_dividend():
    with pytest.raises(ValidationError, match="greater than 0"):
        div.Row(day=consts.START_DAY, dividend=0)

    with pytest.raises(ValidationError, match="greater than 0"):
        div.Row(day=consts.START_DAY, dividend=-1)


def test_dividends_not_sorted():
    rows = [
        div.Row(day=consts.START_DAY + timedelta(days=1), dividend=1),
        div.Row(day=consts.START_DAY, dividend=1),
    ]

    with pytest.raises(ValidationError, match="df not sorted by day"):
        make_dividends(consts.START_DAY, rows)


def test_dividends_before_start():
    rows = [div.Row(day=consts.START_DAY - timedelta(days=1), dividend=1)]

    with pytest.raises(ValidationError, match="day before start day"):
        make_dividends(consts.START_DAY, df=rows)


def test_update():
    d = make_dividends(consts.START_DAY, [])

    new_day = consts.START_DAY + timedelta(days=10)
    rows = [div.Row(day=new_day, dividend=2.0)]
    d.update(new_day, rows)

    assert d.day == new_day
    assert d.df == rows
