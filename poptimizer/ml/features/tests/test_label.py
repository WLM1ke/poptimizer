import pandas as pd
import pytest

from poptimizer.ml.features import label


def test_make_labels():
    # noinspection PyTypeChecker
    labels = label.Label(("AKRN", "SNGSP", "MSTT"), pd.Timestamp("2018-12-11"))

    assert not labels.is_categorical()
    assert labels.get_params_space() == dict(days=21)

    df = labels.get(pd.Timestamp("2018-11-12"), days=21)
    assert isinstance(df, pd.Series)
    assert df.size == 3
    assert df.at["SNGSP"] == pytest.approx(0.0995856337763434)

    df = labels.get(pd.Timestamp("2018-05-17"), days=21)
    assert df.at["AKRN"] == pytest.approx(0.114643927228733)
