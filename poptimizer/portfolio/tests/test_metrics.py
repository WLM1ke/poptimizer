from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from poptimizer.portfolio import metrics, portfolio
from poptimizer.portfolio.portfolio import CASH, PORTFOLIO


@pytest.fixture(scope="module", name="single")
def make_metrics():
    positions = dict(BSPB=4890, FESH=1300, KZOS=5080)
    port = portfolio.Portfolio("2020-05-14", 84449, positions)
    mean = pd.Series([0.09, 0.06, 0.07], index=list(positions))
    cov = np.array(
        [[0.04, 0.005, 0.01], [0.005, 0.0625, 0.00625], [0.01, 0.00625, 0.0625]]
    )
    fake_forecast = SimpleNamespace()
    fake_forecast.mean = mean
    fake_forecast.cov = cov
    # noinspection PyTypeChecker
    yield metrics.MetricsSingle(port, fake_forecast)


class TestMetricsSingle:
    def test_mean(self, single):
        mean = single.mean
        assert isinstance(mean, pd.Series)
        assert mean.name == "MEAN"
        assert len(mean) == 5
        assert mean["BSPB"] == 0.09
        assert mean["FESH"] == 0.06
        assert mean["KZOS"] == 0.07
        assert mean[CASH] == 0.0
        assert mean[PORTFOLIO] == pytest.approx(0.0671295513194378)

    def test_std(self, single):
        std = single.std
        assert isinstance(std, pd.Series)
        assert std.name == "STD"
        assert len(std) == 5
        assert std["BSPB"] == 0.20
        assert std["FESH"] == 0.25
        assert std["KZOS"] == 0.25
        assert std[CASH] == 0.0
        assert std[PORTFOLIO] == pytest.approx(0.171832239704213)

    def test_beta(self, single):
        beta = single.beta
        assert isinstance(beta, pd.Series)
        assert beta.name == "BETA"
        assert len(beta) == 5
        assert beta["BSPB"] == pytest.approx(0.564325931057505)
        assert beta["FESH"] == pytest.approx(0.197707113104551)
        assert beta["KZOS"] == pytest.approx(1.3876207989677)
        assert beta[CASH] == 0.0
        assert beta[PORTFOLIO] == 1.0

    def test_r_geom(self, single):
        r_geom = single.r_geom
        assert isinstance(r_geom, pd.Series)
        assert r_geom.name == "R_GEOM"
        assert len(r_geom) == 5
        assert r_geom["BSPB"] == pytest.approx(0.0881006920652409)
        assert r_geom["FESH"] == pytest.approx(0.0689255960895227)
        assert r_geom["KZOS"] == pytest.approx(0.0437918254921255)
        assert r_geom[CASH] == pytest.approx(0.0147631593008831)
        assert r_geom[PORTFOLIO] == pytest.approx(0.0523663920185547)

        assert r_geom[PORTFOLIO] == (single._portfolio.weight * r_geom).iloc[:-1].sum()

    def test_gradient(self, single):
        gradient = single.gradient
        assert isinstance(gradient, pd.Series)
        assert gradient.name == "GRAD"
        assert len(gradient) == 5
        assert gradient["BSPB"] == pytest.approx(0.0357343000466862)
        assert gradient["FESH"] == pytest.approx(0.016559204070968)
        assert gradient["KZOS"] == pytest.approx(-0.00857456652642924)
        assert gradient[CASH] == pytest.approx(-0.0376032327176716)
        assert gradient[PORTFOLIO] == 0.0

        assert gradient[PORTFOLIO] == pytest.approx(
            (single._portfolio.weight * gradient).iloc[:-1].sum()
        )

    def test_str(self, single):
        assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(single)


@pytest.fixture(scope="module", name="resample")
def make_resample():
    positions = dict(BSPB=4890, FESH=1300)
    port = portfolio.Portfolio("2020-05-14", 84449, positions)

    mean1 = pd.Series([0.09, 0.06], index=list(positions))
    cov1 = np.array([[0.04, 0.005], [0.005, 0.0625]])

    mean2 = pd.Series([0.05, 0.09], index=list(positions))
    cov12 = np.array([[0.0225, 0.0042], [0.0042, 0.0196]])

    def fake_get_forecasts(*_):
        data = [
            SimpleNamespace(
                mean=mean1,
                cov=cov1,
                history_days=1,
                forecast_days=3,
                cor=0.4,
                shrinkage=0.3,
            ),
            SimpleNamespace(
                mean=mean2,
                cov=cov12,
                history_days=2,
                forecast_days=3,
                cor=0.5,
                shrinkage=0.2,
            ),
        ]
        yield from data

    saved_get_forecast = metrics.evolve.get_forecasts
    metrics.evolve.get_forecasts = fake_get_forecasts

    yield metrics.MetricsResample(port)

    metrics.evolve.get_forecasts = saved_get_forecast


class TestMetricsResample:
    def test_count(self, resample):
        assert resample.count == 2

    def test_mean(self, resample):
        mean = resample.mean
        assert isinstance(mean, pd.Series)
        assert mean.name == "MEAN"
        assert len(mean) == 4
        assert mean["BSPB"] == 0.07
        assert mean["FESH"] == 0.075
        assert mean[CASH] == 0.0
        assert mean[PORTFOLIO] == pytest.approx(0.0495010842956967)

    def test_std(self, resample):
        std = resample.std
        assert isinstance(std, pd.Series)
        assert std.name == "STD"
        assert len(std) == 4
        assert std["BSPB"] == 0.175
        assert std["FESH"] == 0.195
        assert std[CASH] == 0.0
        assert std[PORTFOLIO] == pytest.approx(0.119237329326756)

    def test_beta(self, resample):
        beta = resample.beta
        assert isinstance(beta, pd.Series)
        assert beta.name == "BETA"
        assert len(beta) == 4
        assert beta["BSPB"] == pytest.approx(1.46588406985897)
        assert beta["FESH"] == pytest.approx(0.302533282078987)
        assert beta[CASH] == 0.0
        assert beta[PORTFOLIO] == 1.0

    def test_r_geom(self, resample):
        r_geom = resample.r_geom
        assert isinstance(r_geom, pd.Series)
        assert r_geom.name == "R_GEOM"
        assert len(r_geom) == 4
        assert r_geom["BSPB"] == pytest.approx(0.0559870972984637)
        assert r_geom["FESH"] == pytest.approx(0.0779560420919237)
        assert r_geom[CASH] == pytest.approx(0.00725189173625379)
        assert r_geom[PORTFOLIO] == pytest.approx(0.0422491925594429)

        assert r_geom[PORTFOLIO] == pytest.approx(
            (resample._portfolio.weight * r_geom).iloc[:-1].sum()
        )

    def test_gradient(self, resample):
        gradient = resample.gradient
        assert isinstance(gradient, pd.Series)
        assert gradient.name == "GRAD"
        assert len(gradient) == 4
        assert gradient["BSPB"] == pytest.approx(0.0137379047390208)
        assert gradient["FESH"] == pytest.approx(0.0357068495324808)
        assert gradient[CASH] == pytest.approx(-0.0349973008231891)
        assert gradient[PORTFOLIO] == 0.0

        assert gradient[PORTFOLIO] == pytest.approx(
            (resample._portfolio.weight * gradient).iloc[:-1].sum()
        )

    def test_error(self, resample):
        gradient = resample.error
        assert isinstance(gradient, pd.Series)
        assert gradient.name == "ERROR"
        assert len(gradient) == 4
        assert gradient["BSPB"] == pytest.approx(0.00501480253039284)
        assert gradient["FESH"] == pytest.approx(0.0249465015578035)
        assert gradient[CASH] == pytest.approx(0.00905669393735241)
        assert gradient[PORTFOLIO] == 0.0

    def test_str(self, resample):
        assert "КЛЮЧЕВЫЕ МЕТРИКИ ПОРТФЕЛЯ" in str(resample)
