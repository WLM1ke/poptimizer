"""Тесты для эволюционного процесса."""
from poptimizer.dl import ModelError
from poptimizer.evolve import evolve


def test_setup_needed(mocker):
    """Создается необходимое количество организмов."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 0

    ev = evolve.Evolution(initial_population=4)

    ev._setup()

    assert fake_population.create_new_organism.call_count == 4


def test_setup_not_needed(mocker):
    """Если организмов достаточно, то они не создаются."""
    fake_population = mocker.patch.object(evolve, "population")
    fake_population.count.return_value = 4

    ev = evolve.Evolution(initial_population=4)

    ev._setup()

    assert not fake_population.create_new_organism.called


def test_eval_and_print_err(mocker):
    """При ошибке меняет шкалу разброса."""
    org = mocker.Mock()
    org.evaluate_fitness.side_effect = ModelError

    evolution = evolve.Evolution()

    assert evolution._eval_organism(org) is None

    org.evaluate_fitness.assert_called_once()
