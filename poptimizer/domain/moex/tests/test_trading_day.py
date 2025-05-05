from datetime import date

from poptimizer import consts
from poptimizer.domain import domain
from poptimizer.domain.moex.trading_day import TradingDay


def test_trading_day_init():
    rev = domain.Revision(uid=domain.UID("uid"), ver=domain.Version(1))
    day = date(2025, 1, 1)
    t = TradingDay(rev=rev, day=day)

    assert t.rev == rev
    assert t.day == day
    assert t.last_check == consts.START_DAY
    assert t.poptimizer_ver == ""


def test_update_last_check():
    rev = domain.Revision(uid=domain.UID("uid"), ver=domain.Version(1))
    t = TradingDay(rev=rev, day=date(2025, 1, 1))
    new_day = date(2025, 2, 2)
    t.update_last_check(new_day)

    assert t.last_check == new_day


def test_update_last_trading_day():
    rev = domain.Revision(uid=domain.UID("uid"), ver=domain.Version(1))
    t = TradingDay(rev=rev, day=date(2025, 1, 1))
    new_day = date(2025, 3, 3)
    ver = "3.0.0b2"
    t.update_last_trading_day(new_day, ver)

    assert t.day == new_day
    assert t.last_check == new_day
    assert t.poptimizer_ver == ver
