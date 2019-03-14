import pandas as pd
import pytest
from hyperopt import hp
from hyperopt.pyll import Apply

from poptimizer.config import POptimizerError
from poptimizer.ml import cv, examples
from poptimizer.portfolio import portfolio

PARAMS = {
    "data": (
        ("Label", {"days": 21}),
        ("STD", {"days": 252}),
        ("Ticker", {}),
        ("Mom12m", {"days": 252}),
        ("DivYield", {"days": 252}),
    ),
    "model": {
        "bagging_temperature": 1,
        "depth": 6,
        "ignored_features": [],
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
    },
}


def test_log_space():
    space = cv.log_space("test1", [2, 8])
    assert isinstance(space, Apply)
    assert "test1" in str(space)
    assert "loguniform" in str(space)
    assert "0.693147" in str(space)
    assert "2.079441" in str(space)


def test_get_model_space():
    space = cv.get_model_space()
    assert isinstance(space, dict)
    assert len(space) == 6

    assert isinstance(space["one_hot_max_size"], Apply)
    assert "switch" in str(space["one_hot_max_size"])
    assert "Literal{2}" in str(space["one_hot_max_size"])
    assert "Literal{100}" in str(space["one_hot_max_size"])

    assert isinstance(space["learning_rate"], Apply)
    assert "loguniform" in str(space["learning_rate"])

    assert isinstance(space["depth"], Apply)
    assert "switch" in str(space["depth"])
    assert f"{{{cv.MAX_DEPTH}}}" in str(space["depth"])

    assert isinstance(space["l2_leaf_reg"], Apply)
    assert "loguniform" in str(space["l2_leaf_reg"])

    assert isinstance(space["random_strength"], Apply)
    assert "loguniform" in str(space["random_strength"])

    assert isinstance(space["bagging_temperature"], Apply)
    assert "loguniform" in str(space["bagging_temperature"])


def test_float_bounds_check_middle(capsys):
    cv.float_bounds_check("qwerty", 15, [10, 20])
    captured = capsys.readouterr()
    assert captured.out == ""


def test_float_bounds_check_lower(capsys):
    cv.float_bounds_check("qwerty", 10.5, [10, 20])
    captured = capsys.readouterr()
    assert "qwerty" in captured.out
    assert "20" in captured.out
    assert "8.8e+00" in captured.out


def test_float_bounds_check_upper(capsys):
    cv.float_bounds_check("qwerty", 19.5, [10, 20])
    captured = capsys.readouterr()
    assert "qwerty" in captured.out
    assert "10" in captured.out
    assert "2.3e+01" in captured.out


def test_check_model_bounds_middle(capsys):
    params = dict(
        learning_rate=sum(cv.LEARNING_RATE) / 2,
        l2_leaf_reg=sum(cv.L2_LEAF_REG) / 2,
        random_strength=sum(cv.RANDOM_STRENGTH) / 2,
        bagging_temperature=sum(cv.BAGGING_TEMPERATURE) / 2,
        depth=int(cv.MAX_DEPTH / 2),
    )
    cv.check_model_bounds(params)
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_model_bounds_lower(capsys):
    params = dict(
        learning_rate=min(cv.LEARNING_RATE) * 1.05,
        l2_leaf_reg=min(cv.L2_LEAF_REG) * 1.05,
        random_strength=min(cv.RANDOM_STRENGTH) * 1.05,
        bagging_temperature=min(cv.BAGGING_TEMPERATURE) * 1.05,
        depth=0,
    )
    cv.check_model_bounds(params)
    captured = capsys.readouterr()
    assert "learning_rate" in captured.out
    assert "l2_leaf_reg" in captured.out
    assert "random_strength" in captured.out
    assert "bagging_temperature" in captured.out


def test_check_model_bounds_upper(capsys):
    params = dict(
        learning_rate=max(cv.LEARNING_RATE) / 1.05,
        l2_leaf_reg=max(cv.L2_LEAF_REG) / 1.05,
        random_strength=max(cv.RANDOM_STRENGTH) / 1.05,
        bagging_temperature=max(cv.BAGGING_TEMPERATURE) / 1.05,
        depth=cv.MAX_DEPTH,
    )
    cv.check_model_bounds(params)
    captured = capsys.readouterr()
    assert "learning_rate" in captured.out
    assert "l2_leaf_reg" in captured.out
    assert "random_strength" in captured.out
    assert "bagging_temperature" in captured.out

    assert "MAX_DEPTH" in captured.out
    assert str(cv.MAX_DEPTH + 1) in captured.out


def test_make_model_params():
    data_params = (
        ("Label", {"days": 49}),
        ("STD", {"on_off": False, "days": 235}),
        ("Ticker", {}),
        ("Mom12m", {"on_off": False, "days": 252}),
        ("DivYield", {"days": 252}),
    )
    model_params = {
        "bagging_temperature": 1,
        "depth": 6,
        "l2_leaf_reg": 3,
        "learning_rate": 4,
        "one_hot_max_size": 2,
        "random_strength": 5,
        "ignored_features": [2, 4],
    }
    result = cv.make_model_params(data_params, model_params)
    assert isinstance(result, dict)
    print(result)
    assert len(result) == 15
    assert result["bagging_temperature"] == 1
    assert result["depth"] == 6
    assert result["l2_leaf_reg"] == 3
    assert result["learning_rate"] == 4
    assert result["one_hot_max_size"] == 2
    assert result["random_strength"] == 5
    assert result["ignored_features"] == [0, 2]

    assert result["loss_function"] == "RMSE"
    assert result["custom_metric"] == "R2"
    assert result["iterations"] == cv.MAX_ITERATIONS
    assert result["random_state"] == cv.SEED
    assert result["od_type"] == "Iter"
    assert result["od_wait"] == cv.MAX_ITERATIONS // 10
    assert result["verbose"] is False
    assert result["allow_writing_files"] is False


def test_valid_model():
    data = examples.Examples(
        ("LSNGP", "LKOH", "GMKN"), pd.Timestamp("2018-12-14"), PARAMS["data"]
    )
    result = cv.valid_model(PARAMS, data)

    assert isinstance(result, dict)
    assert len(result) == 6
    assert result["loss"] == pytest.approx(0.014_495_100_438_051_8)
    assert result["status"] == "ok"
    assert result["std"] == pytest.approx(0.163_971_874_342_929_92)
    assert result["r2"] == pytest.approx(-0.014_495_100_438_051_8)
    assert result["data"] == PARAMS["data"]
    for key, value in PARAMS["model"].items():
        assert result["model"][key] == value
    for key, value in cv.TECH_PARAMS.items():
        if key == "iterations":
            assert result["model"][key] < value
        else:
            assert result["model"][key] == value


def test_cv_model_raise_max_iter(monkeypatch):
    fake_tech_params = dict(**cv.TECH_PARAMS)
    fake_max_iter = 3
    fake_tech_params["iterations"] = fake_max_iter
    monkeypatch.setattr(cv, "TECH_PARAMS", fake_tech_params)
    monkeypatch.setattr(cv, "MAX_ITERATIONS", fake_max_iter)
    data = examples.Examples(
        ("LSNGP", "LKOH", "GMKN"), pd.Timestamp("2018-12-14"), PARAMS["data"]
    )
    with pytest.raises(POptimizerError) as error:
        cv.valid_model(PARAMS, data)
    assert "Необходимо увеличить MAX_ITERATIONS =" in str(error.value)


def test_optimize_hyper(monkeypatch, capsys):
    space = {
        "data": (
            ("Label", {"days": hp.choice("label", list(range(21, 31)))}),
            ("STD", {"days": 186}),
            ("Ticker", {"on_off": False}),
            ("Mom12m", {"days": 279}),
            ("DivYield", {"days": 252}),
        ),
        "model": {
            "bagging_temperature": 1,
            "depth": 6,
            "l2_leaf_reg": 3,
            "learning_rate": 0.1,
            "one_hot_max_size": 2,
            "random_strength": 1,
            "ignored_features": [],
        },
    }
    cases = examples.Examples(
        ("LSNGP", "LKOH", "GMKN"), pd.Timestamp("2018-12-14"), PARAMS["data"]
    )
    monkeypatch.setattr(cv, "MAX_SEARCHES", 10)
    monkeypatch.setattr(cases, "get_params_space", lambda: space["data"])
    monkeypatch.setattr(cv, "get_model_space", lambda: space["model"])

    result = cv.optimize_hyper(cases)

    captured = capsys.readouterr()
    assert "Необходимо расширить" in captured.out

    assert isinstance(result, dict)
    assert len(result) == 2
    assert result["data"] == (
        ("Label", {"days": 29}),
        ("STD", {"days": 186}),
        ("Ticker", {"on_off": False}),
        ("Mom12m", {"days": 279}),
        ("DivYield", {"days": 252}),
    )
    model_params = {
        "bagging_temperature": 1,
        "depth": 6,
        "l2_leaf_reg": 3,
        "learning_rate": 0.1,
        "one_hot_max_size": 2,
        "random_strength": 1,
    }
    for k, v in model_params.items():
        assert result["model"][k] == pytest.approx(v)


def test_find_better_model(monkeypatch, capsys):
    monkeypatch.setattr(cv, "MAX_SEARCHES", 10)
    monkeypatch.setattr(cv, "MAX_DEPTH", 7)
    pos = dict(LSNGP=10, KZOS=20, GMKN=30)
    port = portfolio.Portfolio(pd.Timestamp("2018-12-19"), 100, pos)
    cv.find_better_model(port, PARAMS)
    captured = capsys.readouterr()
    assert "Базовая модель" in captured.out
    assert "Найденная модель" in captured.out
    assert "ЛУЧШАЯ МОДЕЛЬ - Найденная модель" in captured.out


def test_find_better_model_fake_base(monkeypatch, capsys):
    monkeypatch.setattr(cv, "MAX_SEARCHES", 10)
    monkeypatch.setattr(
        cv, "print_result", lambda x, y, z: 1 if x == "Базовая модель" else 0
    )
    pos = dict(LSNGP=10, KZOS=20, GMKN=30)
    port = portfolio.Portfolio(pd.Timestamp("2018-12-19"), 100, pos)
    cv.find_better_model(port)
    captured = capsys.readouterr()
    assert "ЛУЧШАЯ МОДЕЛЬ - Базовая модель" in captured.out
