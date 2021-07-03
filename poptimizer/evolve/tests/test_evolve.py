"""Тесты для эволюционного процесса."""
import pytest

from poptimizer.dl import ModelError
from poptimizer.evolve import evolve


def test_setup_needed(mocker):
    """Создается необходимое количество организмов."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 1

    ev = evolve.Evolution(max_population=4)

    ev._setup()

    fake_population.count.assert_called_once_with()
    assert fake_population.create_new_organism.call_count == 3


def test_setup_not_needed(mocker):
    """Если организмов достаточно, то они не создаются."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 4

    ev = evolve.Evolution(max_population=4)

    ev._setup()

    fake_population.count.assert_called_once_with()
    assert not fake_population.create_new_organism.called


def test_eval_and_print(mocker):
    """Вызывает оценку и не меняет шкалу разброса."""
    org = mocker.Mock()
    org.evaluate_fitness.return_value = 4
    org.ir = 3
    org.timer = 6

    evolution = evolve.Evolution()
    evolution._eval_organism("name", org)

    assert evolution._scale == pytest.approx(1)

    org.evaluate_fitness.assert_called_once()


def test_eval_and_print_err(mocker):
    """При ошибке меняет шкалу разброса."""
    org = mocker.Mock(side_effect=ModelError)
    org.evaluate_fitness.side_effect = ModelError

    evolution = evolve.Evolution()
    evolution._eval_organism("name", org)

    assert evolution._scale == pytest.approx(evolve.SCALE_DOWN)

    org.evaluate_fitness.assert_called_once()


def test_eval_and_print_low_ir(mocker):
    """При отрицательном IR меняет шкалу разброса."""
    org = mocker.Mock()
    org.evaluate_fitness.return_value = 4
    org.ir = -3

    evolution = evolve.Evolution()
    evolution._eval_organism("name", org)

    assert evolution._scale == pytest.approx(evolve.SCALE_DOWN)

    org.evaluate_fitness.assert_called_once()
