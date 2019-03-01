import pandas as pd
import pytest
from hyperopt.pyll import Apply

from poptimizer.config import AFTER_TAX
from poptimizer.ml.feature import divyield


@pytest.fixture(scope="module", name="feat")
def test_divyield_feature():
    return divyield.DivYield(
        ("PHOR", "TATN", "DSKY"), pd.Timestamp("2018-12-12"), {"days": 47}
    )


def test_is_categorical(feat):
    assert not feat.is_categorical()


def test_get_params_space(feat):
    space = feat.get_params_space()
    assert isinstance(space, dict)
    assert len(space) == 1
    assert isinstance(space["days"], Apply)


def test_get(feat):
    df = feat.get({"days": 13})
    assert isinstance(df, pd.Series)

    assert pd.Timestamp("2018-12-12") in df.index
    assert pd.Timestamp("2018-12-13") not in df.index
    assert pd.Timestamp("2010-01-26") not in df.index

    df = feat.get(dict(days=9))
    assert df[(pd.Timestamp("2018-06-22"), "PHOR")] == pytest.approx(
        AFTER_TAX * 15 / 2291
    )
    assert df[(pd.Timestamp("2018-06-25"), "PHOR")] == pytest.approx(0)

    df = feat.get(dict(days=20))
    assert df[(pd.Timestamp("2018-06-11"), "PHOR")] == pytest.approx(
        AFTER_TAX * 15 / 2315
    )

    df = feat.get(dict(days=30))
    assert df[(pd.Timestamp("2018-10-11"), "TATN")] == pytest.approx(
        30.27 * AFTER_TAX / 778.3
    )
    assert df[(pd.Timestamp("2018-10-10"), "TATN")] == pytest.approx(0)
