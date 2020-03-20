from poptimizer.ml.feature import feature


def test_feature():
    res = feature.days_choice_list(11)
    assert isinstance(res, list)
    assert len(res) == 5
    assert res[0] == 9
    assert res[-1] == 13

    res = feature.days_choice_list(5)
    assert isinstance(res, list)
    assert len(res) == 3
    assert res[0] == 4
    assert res[-1] == 6


def test_period_choice():
    res = feature.periods_choice_list(1)
    assert isinstance(res, list)
    assert len(res) == 2
    assert res[0] == 1
    assert res[1] == 2

    res = feature.periods_choice_list(4)
    assert isinstance(res, list)
    assert len(res) == 5
    assert res == list(range(1, 6))
