"""Тесты для эволюционного процесса."""
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
    """Возвращает фитнес организма."""
    org = mocker.Mock()
    org.evaluate_fitness.return_value = 4
    org.timer = 6

    assert evolve._eval_and_print(org, "aaa", "bbb") == 4

    org.evaluate_fitness.assert_called_once_with("aaa", "bbb")


def test_eval_and_print_err(mocker):
    """Возвращает None при ошибке во время оценки организма."""
    org = mocker.Mock(side_effect=ModelError)
    org.evaluate_fitness.side_effect = ModelError

    assert evolve._eval_and_print(org, "aaa", "bbb") is None


def test_kill_weakest(mocker):
    """Находится и убивается слабый."""
    org = mocker.Mock()
    weaker = org.find_weaker.return_value
    weaker.llh = 2.11
    weaker.timer = 3

    evolve._kill_weakest(org)

    org.find_weaker.assert_called_once_with()
    weaker.die.assert_called_once_with()
