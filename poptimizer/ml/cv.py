"""Кросс-валидация ML-модели."""
import catboost
import hyperopt

from poptimizer import POptimizerError
from poptimizer.ml.examples import Examples

# Базовые настройки catboost
MAX_ITERATIONS = 100
SEED = 284_704
FOLDS_COUNT = 20
TECH_PARAMS = dict(
    iterations=MAX_ITERATIONS,
    random_state=SEED,
    od_type="Iter",
    verbose=False,
    allow_writing_files=False,
)


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
    model_params = dict(**TECH_PARAMS, **model_params)
    scores = catboost.cv(pool=pool, params=model_params, fold_count=FOLDS_COUNT)
    if len(scores) == MAX_ITERATIONS:
        raise POptimizerError(f"Необходимо увеличить MAX_ITERATIONS = {MAX_ITERATIONS}")
    index = scores["test-RMSE-mean"].idxmin()
    model_params["iterations"] = index + 1
    cv_std = scores.loc[index, "test-RMSE-mean"]
    return dict(
        loss=cv_std / labels_std,
        status=hyperopt.STATUS_OK,
        std=cv_std,
        r2=1 - (cv_std / labels_std) ** 2,
        params=(data_params, model_params),
    )
