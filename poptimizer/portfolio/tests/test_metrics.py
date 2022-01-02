"""Тестирование метрик."""
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from poptimizer.portfolio import metrics, portfolio


@pytest.fixture(scope="module", name="single")
def make_metrics():
    """Подготовка тестовых данных."""
    positions = {"BSPB": 4890, "FESH": 1300, "KZOS": 5080}
    port = portfolio.Portfolio(["test"], "2020-05-14", 84449, positions)
    mean = pd.Series([0.09, 0.06, 0.07], index=list(positions))
    cov = np.array(
        [
            [0.04, 0.005, 0.01],
            [0.005, 0.0625, 0.00625],
            [0.01, 0.00625, 0.0625],
        ],
    )
    fake_forecast = SimpleNamespace()
    fake_forecast.mean = mean
    fake_forecast.cov = cov
    fake_forecast.risk_aversion = 1
    fake_forecast.error_tolerance = 0
    # noinspection PyTypeChecker
    yield metrics.MetricsSingle(port, fake_forecast)


class TestMetricsSingle:
    """Проверка метрик одного прогноза."""

    def test_mean(self, single):
        """Проверка среднего значения."""
        mean = single.mean
        assert isinstance(mean, pd.Series)
        assert mean.name == "MEAN"
        assert len(mean) == 5
        assert mean["BSPB"] == pytest.approx(0.09)
        assert mean["FESH"] == pytest.approx(0.06)
        assert mean["KZOS"] == pytest.approx(0.07)
        assert mean[portfolio.CASH] == pytest.approx(0)
        assert mean[portfolio.PORTFOLIO] == pytest.approx(0.0671295513194378)

    def test_std(self, single):
        """Проверка СКО."""
        std = single.std
        assert isinstance(std, pd.Series)
        assert std.name == "STD"
        assert len(std) == 5
        assert std["BSPB"] == pytest.approx(0.2)
        assert std["FESH"] == pytest.approx(0.25)
        assert std["KZOS"] == pytest.approx(0.25)
        assert std[portfolio.CASH] == pytest.approx(0)
        assert std[portfolio.PORTFOLIO] == pytest.approx(0.171832239704213)

    def test_beta(self, single):
        """Проверка бет."""
        beta = single.beta
        assert isinstance(beta, pd.Series)
        assert beta.name == "BETA"
        assert len(beta) == 5
        assert beta["BSPB"] == pytest.approx(0.564325931057505)
        assert beta["FESH"] == pytest.approx(0.197707113104551)
        assert beta["KZOS"] == pytest.approx(1.3876207989677)
        assert beta[portfolio.CASH] == pytest.approx(0)
        assert beta[portfolio.PORTFOLIO] == pytest.approx(1)

    def test_metrics(self, single):
        """Проверка значений метрики."""
        sharpe = single.r_adj
        assert isinstance(sharpe, pd.Series)
        assert sharpe.name == "R_ADJ"
        assert len(sharpe) == 5
        assert sharpe["BSPB"] == pytest.approx(0.08810069206524088)
        assert sharpe["FESH"] == pytest.approx(0.0689255960895227)
        assert sharpe["KZOS"] == pytest.approx(0.043791825492125444)
        assert sharpe[portfolio.CASH] == pytest.approx(0.014763159300883089)
        assert sharpe[portfolio.PORTFOLIO] == pytest.approx(0.05236639201855469)

        assert sharpe[portfolio.PORTFOLIO] == pytest.approx(
            (single._portfolio.weight * sharpe).iloc[:-1].sum(),
        )

    def test_gradient(self, single):
        """Проверка градиентов, в том числе тождества для портфеля."""
        gradient = single.gradient
        assert isinstance(gradient, pd.Series)
        assert gradient.name == "GRAD"
        assert len(gradient) == 5
        assert gradient["BSPB"] == pytest.approx(0.035734300046686186)
        assert gradient["FESH"] == pytest.approx(0.01655920407096801)
        assert gradient["KZOS"] == pytest.approx(-0.008574566526429241)
        assert gradient[portfolio.CASH] == pytest.approx(-0.0376032327176716)
        assert gradient[portfolio.PORTFOLIO] == pytest.approx(0)

        assert gradient[portfolio.PORTFOLIO] == pytest.approx(
            (single._portfolio.weight * gradient).iloc[:-1].sum(),
        )

    def test_str(self, single):
        """Прогон распечатки данных."""
        assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(single)


@pytest.fixture(scope="module", name="resample")
def make_resample():
    """Данне для тестов."""
    positions = {"BSPB": 4890, "FESH": 1300}
    port = portfolio.Portfolio("test", "2020-05-14", 84449, positions)

    mean1 = pd.Series([0.09, 0.06], index=list(positions))
    cov1 = np.array([[0.04, 0.005], [0.005, 0.0625]])

    mean2 = pd.Series([0.05, 0.09], index=list(positions))
    cov12 = np.array([[0.0225, 0.0042], [0.0042, 0.0196]])

    def fake_get_forecasts(*_):
        yield from (
            SimpleNamespace(
                mean=mean1,
                cov=cov1,
                history_days=1,
                cor=0.4,
                shrinkage=0.3,
                risk_aversion=1,
                error_tolerance=0,
            ),
            SimpleNamespace(
                mean=mean2,
                cov=cov12,
                history_days=2,
                cor=0.5,
                shrinkage=0.2,
                risk_aversion=1,
                error_tolerance=0,
            ),
        )

    saved_get_forecast = metrics.evolve.get_forecasts
    metrics.evolve.get_forecasts = fake_get_forecasts

    yield metrics.MetricsResample(port)

    metrics.evolve.get_forecasts = saved_get_forecast


class TestMetricsResample:
    """Тестирование метрик для нескольких прогнозов."""

    def test_count(self, resample):
        """Проверка количества прогнозов."""
        assert resample.count == 2

    def test_mean(self, resample):
        """Проверка ожидаемой доходности."""
        mean = resample.mean
        assert isinstance(mean, pd.Series)
        assert mean.name == "MEAN"
        assert len(mean) == 4
        assert mean["BSPB"] == pytest.approx(0.07)
        assert mean["FESH"] == pytest.approx(0.075)
        assert mean[portfolio.CASH] == pytest.approx(0)
        assert mean[portfolio.PORTFOLIO] == pytest.approx(0.0495010842956967)

    def test_std(self, resample):
        """Проверка СКО."""
        std = resample.std
        assert isinstance(std, pd.Series)
        assert std.name == "STD"
        assert len(std) == 4
        assert std["BSPB"] == pytest.approx(0.175)
        assert std["FESH"] == pytest.approx(0.195)
        assert std[portfolio.CASH] == pytest.approx(0)
        assert std[portfolio.PORTFOLIO] == pytest.approx(0.119237329326756)

    def test_beta(self, resample):
        """Проверка значений беты."""
        beta = resample.beta
        assert isinstance(beta, pd.Series)
        assert beta.name == "BETA"
        assert len(beta) == 4
        assert beta["BSPB"] == pytest.approx(1.46588406985897)
        assert beta["FESH"] == pytest.approx(0.302533282078987)
        assert beta[portfolio.CASH] == pytest.approx(0)
        assert beta[portfolio.PORTFOLIO] == pytest.approx(1)

    def test_metrics(self, resample):
        """Проверка метрики, в том числе значения для кэша."""
        sharpe = resample.r_adj
        assert isinstance(sharpe, pd.Series)
        assert sharpe.name == "R_ADJ"
        assert len(sharpe) == 4
        assert sharpe["BSPB"] == pytest.approx(0.055987097298463726)
        assert sharpe["FESH"] == pytest.approx(0.07795604209192372)
        assert sharpe[portfolio.CASH] == pytest.approx(0.007251891736253785)
        assert sharpe[portfolio.PORTFOLIO] == pytest.approx(0.04224919255944291)

    def test_gradient(self, resample):
        """Проверка значений градиента и тождества для портфеля."""
        gradient = resample.gradient
        assert isinstance(gradient, pd.Series)
        assert gradient.name == "GRAD"
        assert len(gradient) == 4
        assert gradient["BSPB"] == pytest.approx(0.013737904739020815)
        assert gradient["FESH"] == pytest.approx(0.035706849532480815)
        assert gradient[portfolio.CASH] == pytest.approx(-0.03499730082318912)
        assert gradient[portfolio.PORTFOLIO] == 0

        assert gradient[portfolio.PORTFOLIO] == pytest.approx(
            (resample._portfolio.weight * gradient).iloc[:-1].sum(),
        )

    def test_str(self, resample):
        """Прогон распечатки метрик."""
        assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(resample)
