"""Тесты для эволюционного процесса."""
import pytest

from poptimizer.dl import ModelError
from poptimizer.evolve import evolve


def test_setup_needed(mocker):
    """Создается необходимое количество организмов."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 0

    ev = evolve.Evolution(target_population=4)

    ev._setup()

    fake_population.count.assert_called_once_with()
    assert fake_population.create_new_organism.call_count == 4


def test_setup_not_needed(mocker):
    """Если организмов достаточно, то они не создаются."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 4

    ev = evolve.Evolution(target_population=4)

    ev._setup()

    fake_population.count.assert_called_once_with()
    assert not fake_population.create_new_organism.called


def test_eval_and_print(mocker):
    """Вызывает оценку и не меняет шкалу разброса."""
    org = mocker.Mock()
    org.evaluate_fitness.return_value = 4
    org.ir = [i for i in range(9)]
    org.timer = 6

    evolution = evolve.Evolution()
    evolution._eval_organism(org)

    org.evaluate_fitness.assert_called_once()


def test_eval_and_print_err(mocker):
    """При ошибке меняет шкалу разброса."""
    org = mocker.Mock()
    org.evaluate_fitness.side_effect = ModelError

    evolution = evolve.Evolution()

    assert evolution._eval_organism(org) is None

    org.evaluate_fitness.assert_called_once()
