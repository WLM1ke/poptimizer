"""Оптимизация долгосрочного портфеля акций."""
from poptimizer.data import smart_lab_status, dividends_status
from poptimizer.ml import (
    find_better_model,
    learning_curve,
    partial_dependence_curve,
    cross_val_predict_plot,
)
from poptimizer.portfolio import *
from poptimizer.reports import income, report

__version__ = "0.2.0"
