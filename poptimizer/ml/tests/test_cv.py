import pandas as pd
import pytest

from poptimizer.config import POptimizerError
from poptimizer.ml import cv, examples
from poptimizer.ml.feature import YEAR_IN_TRADING_DAYS

PARAMS = (
    (
        (True, {"days": 21}),
        (True, {"days": 252}),
        (True, {}),
        (True, {"days": 252}),
        (True, {"days": 252}),
    ),
    {
        "bagging_temperature": 1,
        "depth": 6,
        "ignored_features": (),
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
    },
)


def test_cv_model():
    data = examples.Examples(("LSNGP", "LKOH", "GMKN"), pd.Timestamp("2018-12-14"))
    result = cv.cv_model(PARAMS, data)

    assert isinstance(result, dict)
    assert len(result) == 5
    assert result["loss"] == pytest.approx(0.9593482060259035)
    assert result["status"] == "ok"
    assert result["std"] == pytest.approx(
        3.251270743258923 / YEAR_IN_TRADING_DAYS ** 0.5
    )
    assert result["r2"] == pytest.approx(0.07965101959488052)
    data_params, model_params = result["params"]
    assert data_params == PARAMS[0]
    for key, value in PARAMS[1].items():
        assert model_params[key] == value
    for key, value in cv.TECH_PARAMS.items():
        if key == "iterations":
            assert model_params[key] < value
        else:
            assert model_params[key] == value


def test_cv_model_raise_max_iter():
    PARAMS[1]["learning_rate"] = 0.001
    data = examples.Examples(("LSNGP", "LKOH", "GMKN"), pd.Timestamp("2018-12-14"))
    with pytest.raises(POptimizerError) as error:
        cv.cv_model(PARAMS, data)
    assert "Необходимо увеличить MAX_ITERATIONS =" in str(error.value)
