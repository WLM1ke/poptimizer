from datetime import date

import pytest
from pydantic import ValidationError

from poptimizer.domain import domain
from poptimizer.domain.moex import securities


def test_row_parse():
    row = securities.Row.model_validate(
        {
            "SECID": "SBERP",
            "LOTSIZE": 10,
            "ISIN": "RU0009029557",
            "BOARDID": "TQBR",
            "SECTYPE": "2",
            "INSTRID": "EQIN",
        }
    )
    assert row.ticker == "SBERP"
    assert row.lot == 10
    assert row.isin == "RU0009029557"
    assert row.board == "TQBR"
    assert row.type == "2"
    assert row.instrument == "EQIN"


def test_row_missing_fields():
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"SECID": "SBERP", "LOTSIZE": 10, "ISIN": "RU0009029557", "BOARDID": "TQBR", "SECTYPE": "2"}
        )
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"LOTSIZE": 10, "ISIN": "RU0009029557", "BOARDID": "TQBR", "SECTYPE": "2", "INSTRID": "EQIN"}
        )
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"SECID": "SBERP", "ISIN": "RU0009029557", "BOARDID": "TQBR", "SECTYPE": "2", "INSTRID": "EQIN"}
        )
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"SECID": "SBERP", "LOTSIZE": 10, "BOARDID": "TQBR", "SECTYPE": "2", "INSTRID": "EQIN"}
        )
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"SECID": "SBERP", "LOTSIZE": 10, "ISIN": "RU0009029557", "SECTYPE": "2", "INSTRID": "EQIN"}
        )
    with pytest.raises(ValidationError):
        securities.Row.model_validate(
            {"SECID": "SBERP", "LOTSIZE": 10, "ISIN": "RU0009029557", "BOARDID": "TQBR", "INSTRID": "EQIN"}
        )


def test_row_is_share():
    row = securities.Row.model_validate(
        {
            "SECID": "GAZP",
            "LOTSIZE": 10,
            "ISIN": "RU0007661625",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    assert row.is_share is True
    row2 = securities.Row.model_validate(
        {
            "SECID": "GAZP",
            "LOTSIZE": 10,
            "ISIN": "RU0007661625",
            "BOARDID": "TQTF",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    assert row2.is_share is False


def test_row_is_preferred():
    row = securities.Row.model_validate(
        {
            "SECID": "SBERP",
            "LOTSIZE": 10,
            "ISIN": "RU0009029557",
            "BOARDID": "TQBR",
            "SECTYPE": "2",
            "INSTRID": "EQIN",
        }
    )
    assert row.is_preferred is True
    row2 = securities.Row.model_validate(
        {
            "SECID": "SBER",
            "LOTSIZE": 10,
            "ISIN": "RU0009029540",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    assert row2.is_preferred is False
    row3 = securities.Row.model_validate(
        {
            "SECID": "SBERP",
            "LOTSIZE": 10,
            "ISIN": "RU0009029557",
            "BOARDID": "TQTF",
            "SECTYPE": "2",
            "INSTRID": "EQIN",
        }
    )
    assert row3.is_preferred is False


def test_row_ticker_base():
    row = securities.Row.model_validate(
        {
            "SECID": "SBERP",
            "LOTSIZE": 10,
            "ISIN": "RU0009029557",
            "BOARDID": "TQBR",
            "SECTYPE": "2",
            "INSTRID": "EQIN",
        }
    )
    assert row.ticker_base == "SBER"
    row2 = securities.Row.model_validate(
        {
            "SECID": "SBER",
            "LOTSIZE": 10,
            "ISIN": "RU0009029540",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    assert row2.ticker_base == "SBER"


def test_securities_validator_sorted():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    r1 = securities.Row.model_validate(
        {
            "SECID": "A",
            "LOTSIZE": 1,
            "ISIN": "RU000A",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    r2 = securities.Row.model_validate(
        {
            "SECID": "B",
            "LOTSIZE": 2,
            "ISIN": "RU000B",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    securities.Securities(rev=rev, day=date(2023, 1, 1), df=[r1, r2])


def test_securities_validator_unsorted():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    r1 = securities.Row.model_validate(
        {
            "SECID": "B",
            "LOTSIZE": 2,
            "ISIN": "RU000B",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    r2 = securities.Row.model_validate(
        {
            "SECID": "A",
            "LOTSIZE": 1,
            "ISIN": "RU000A",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    with pytest.raises(ValidationError, match="not sorted"):
        securities.Securities(rev=rev, day=date(2023, 1, 1), df=[r1, r2])


def test_securities_update_sorts_and_sets_day():
    rev = domain.Revision(uid=domain.UID("A"), ver=domain.Version(1))
    r1 = securities.Row.model_validate(
        {
            "SECID": "B",
            "LOTSIZE": 2,
            "ISIN": "RU000B",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    r2 = securities.Row.model_validate(
        {
            "SECID": "A",
            "LOTSIZE": 1,
            "ISIN": "RU000A",
            "BOARDID": "TQBR",
            "SECTYPE": "1",
            "INSTRID": "EQIN",
        }
    )
    s = securities.Securities(rev=rev, day=date(2023, 1, 1), df=[])
    s.update(date(2023, 1, 2), [r1, r2])
    assert s.day == date(2023, 1, 2)
    assert s.df == [r2, r1]
