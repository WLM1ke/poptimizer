"""Кросс-валидация и оптимизация гиперпараметров ML-модели."""
import catboost
import functools
import hyperopt
import numpy as np
from catboost import CatboostError
from hyperopt import hp

from poptimizer import config, portfolio
from poptimizer.config import POptimizerError
from poptimizer.ml.examples import Examples

# Базовые настройки catboost
MAX_ITERATIONS = 300
SEED = 284_704
FOLDS_COUNT = 20
TECH_PARAMS = dict(
    iterations=MAX_ITERATIONS,
    random_state=SEED,
    od_type="Iter",
    verbose=False,
    allow_writing_files=False,
)

# Настройки hyperopt
MAX_SEARCHES = 100

# Диапазоны поиска ключевых гиперпараметров относительно базового значения параметров
# Рекомендации Яндекс - https://tech.yandex.com/catboost/doc/dg/concepts/parameter-tuning-docpage/

# OneHot кодировка - учитывая количество акций в портфеле используется cat-кодировка или OneHot-кодировка
ONE_HOT_SIZE = [2, 100]

# Диапазон поиска скорости обучения
LEARNING_RATE = [4.5e-02, 0.10]

# Диапазон поиска глубины деревьев
DEPTH = [1, 7]
DEPTH[1] += 1

# Диапазон поиска параметра L2-регуляризации
L2_LEAF_REG = [8.2e-01, 4.0]

# Диапазон поиска случайности разбиений
RANDOM_STRENGTH = [0.63, 1.8e00]

# Диапазон поиска интенсивности бэггинга
BAGGING_TEMPERATURE = [0.58, 1.4e00]


def log_space(space_name: str, interval):
    """Создает логарифмическое вероятностное пространство"""
    lower, upper = interval
    lower, upper = np.log(lower), np.log(upper)
    return hp.loguniform(space_name, lower, upper)


def get_model_space():
    """Создает вероятностное пространство для параметров регрессии."""
    space = {
        "one_hot_max_size": hp.choice("one_hot_max_size", ONE_HOT_SIZE),
        "learning_rate": log_space("learning_rate", LEARNING_RATE),
        "depth": hp.choice("depth", list(range(*DEPTH))),
        "l2_leaf_reg": log_space("l2_leaf_reg", L2_LEAF_REG),
        "random_strength": log_space("rand_strength", RANDOM_STRENGTH),
        "bagging_temperature": log_space("bagging_temperature", BAGGING_TEMPERATURE),
    }
    return space


def float_bounds_check(
    name, value, interval, bound: float = 0.1, increase: float = 0.2
):
    """Анализирует близость к границам интервала и предлагает расширить."""
    lower, upper = interval
    if value * (1 + bound) > upper:
        print(
            f"\nНеобходимо расширить {name} до [{lower}, {value * (1 + increase):0.1e}]"
        )
    elif value / (1 + bound) < lower:
        print(
            f"\nНеобходимо расширить {name} до [{value / (1 + increase):0.1e}, {upper}]"
        )


def check_model_bounds(params: dict, bound: float = 0.1, increase: float = 0.2):
    """Проверяет и дает рекомендации о расширении границ пространства поиска параметров.

    Для целочисленных параметров - предупреждение выдается на границе диапазона и рекомендуется
    расширить диапазон на 1.
    Для реальных параметров - предупреждение выдается в 10% от границе и рекомендуется расширить границы
    поиска на 10%, 20%.
    """
    names = ["learning_rate", "l2_leaf_reg", "random_strength", "bagging_temperature"]
    intervals = [LEARNING_RATE, L2_LEAF_REG, RANDOM_STRENGTH, BAGGING_TEMPERATURE]
    for name, interval in zip(names, intervals):
        value = params[name]
        float_bounds_check(name, value, interval, bound, increase)

    if params["depth"] == DEPTH[0]:
        print(f"\nНеобходимо расширить DEPTH до [{DEPTH[0] - 1}, {DEPTH[1] - 1}]")
    if params["depth"] == DEPTH[1] - 1:
        print(f"\nНеобходимо расширить DEPTH до [{DEPTH[0]}, {DEPTH[1]}]")


def make_model_params(data_params, model_params):
    """Формирует параметры модели:

    Вставляет корректные данные по отключенным признакам и добавляет общие технические параметры.
    """
    model_params["ignored_features"] = []
    for num, feat in enumerate(data_params[1:]):
        if feat[0] is False:
            model_params["ignored_features"].append(num)
    model_params = dict(**TECH_PARAMS, **model_params)
    return model_params


def cv_model(params: tuple, examples: Examples) -> dict:
    """Осуществляет кросс-валидацию модели по RMSE, нормированному на СКО набора данных.

    Осуществляется проверка, что не достигнут максимум итераций, возвращается RMSE, R2 и параметры модели
    с оптимальным количеством итераций в формате целевой функции hyperopt.

    :param params:
        Словарь с параметрами модели и данных.
    :param examples:
        Класс создания обучающих примеров.
    :return:
        Словарь с результатом в формате hyperopt:

        * ключ 'loss' - нормированная RMSE на кросс-валидации (для hyperopt),
        * ключ 'status' - успешного прохождения (для hyperopt),
        * ключ 'std' - RMSE на кросс-валидации,
        * ключ 'r2' - 1- нормированная RMSE на кросс-валидации в квадрате,
        * ключ 'params' - параметры модели и данных, в которые добавлено оптимальное количество итераций
        градиентного бустинга на кросс-валидации и общие настройки.
    """
    data_params, model_params = params
    pool_params = examples.learn_pool_params(data_params)
    labels_std = pool_params["label"].std()
    pool = catboost.Pool(**pool_params)
    model_params = make_model_params(data_params, model_params)
    try:
        scores = catboost.cv(pool=pool, params=model_params, fold_count=FOLDS_COUNT)
    except CatboostError:
        return dict(
            loss=None, status=hyperopt.STATUS_FAIL, std=None, r2=None, params=None
        )
    else:
        if len(scores) == MAX_ITERATIONS:
            raise POptimizerError(
                f"Необходимо увеличить MAX_ITERATIONS = {MAX_ITERATIONS}"
            )
        index = scores["test-RMSE-mean"].idxmin()
        model_params["iterations"] = index + 1
        cv_std = scores.loc[index, "test-RMSE-mean"]
        r2 = 1 - (cv_std / labels_std) ** 2
        return dict(
            loss=-r2,
            status=hyperopt.STATUS_OK,
            std=cv_std,
            r2=r2,
            params=(data_params, model_params),
        )


def optimize_hyper(examples: Examples) -> tuple:
    """Ищет и  возвращает лучший набор гиперпараметров без количества итераций.

    :param examples:
        Класс генератора примеров для модели.
    :return:
        Оптимальные параметры модели.
    """
    objective = functools.partial(cv_model, examples=examples)
    param_space = (examples.get_params_space(), get_model_space())
    best = hyperopt.fmin(
        objective,
        space=param_space,
        algo=hyperopt.tpe.suggest,
        max_evals=MAX_SEARCHES,
        rstate=np.random.RandomState(SEED),
    )
    # Преобразование из внутреннего представление в исходное пространство
    best_params = hyperopt.space_eval(param_space, best)
    examples.check_bounds(best_params[0])
    check_model_bounds(best_params[1])
    return best_params


def print_result(name, params, examples: Examples):
    """Проводит кросс-валидацию, выводит ее основные метрики и возвращает R2."""
    cv_results = cv_model(params, examples)
    print(
        f"\n{name}"
        f"\nR2 - {cv_results['r2']:0.4%}"
        f"\nКоличество итераций - {cv_results['params'][1]['iterations']}"
        f"\n{cv_results['params']}"
    )
    return cv_results["r2"]


def find_better_model(port: portfolio.Portfolio):
    """Ищет оптимальную модель и сравнивает с базовой - результаты сравнения распечатываются."""
    examples = Examples(tuple(port.index[:-2]), port.date)
    print("\nИдет поиск новой модели")
    new_params = optimize_hyper(examples)
    base_params = config.ML_PARAMS
    base_name = "Базовая модель"
    base_r2 = print_result(base_name, base_params, examples)
    new_name = "Найденная модель"
    new_r2 = print_result("Найденная модель", new_params, examples)

    if base_r2 > new_r2:
        print(f"\nЛУЧШАЯ МОДЕЛЬ - {base_name}" f"\n{base_params}")
    else:
        print(f"\nЛУЧШАЯ МОДЕЛЬ - {new_name}" f"\n{new_params}")
