import pandas as pd
import pytest

from poptimizer.ml import label
from poptimizer.ml.label import LABELS


def test_make_labels():
    # noinspection PyTypeChecker
    df = label.make_labels(
        ("AKRN", "SNGSP", "MSTT"),
        pd.Timestamp("2018-12-11"),
        days=21,
        normalize=12 * 21,
    )

    assert isinstance(df, pd.DataFrame)
    assert isinstance(df.index, pd.MultiIndex)

    assert df.index[0] == (pd.Timestamp("2003-09-25"), "SNGSP")
    assert df.index[-1] == (pd.Timestamp("2018-12-11"), "MSTT")

    assert len(df) == 423
    assert df.shape[1] == 3

    assert df.at[("2018-12-11", "SNGSP"), "MEAN"] == pytest.approx(0.0995856337763434)
    assert df.at[("2018-06-15", "AKRN"), "MEAN"] == pytest.approx(0.114643927228733)

    assert df.at[("2018-11-12", "MSTT"), "STD"] == pytest.approx(0.224696005113617)

    assert df.at[("2018-10-11", "AKRN"), LABELS] == pytest.approx(0.181224685163257)
