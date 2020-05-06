"""Оптимизатор портфеля."""
import pandas as pd

from poptimizer.config import MAX_TRADE
from poptimizer.portfolio import metrics
from poptimizer.portfolio.portfolio import Portfolio, CASH, PORTFOLIO

# На сколько сделок разбивается операция по покупке/продаже акций
TRADES = 5
T_SCORE = 3.6


class Optimizer:
    """Предлагает сделки для улучшения метрик портфеля."""

    def __init__(self, portfolio: Portfolio):
        """Учитывается градиент, его ошибку и ликвидность бумаг - градиент корректирует на фактор
        оборота.

        :param portfolio:
            Оптимизируемый портфель."""
        self._portfolio = portfolio
        self._metrics = metrics.MetricsResample(portfolio)

    def __str__(self) -> str:
        return f"\nОПТИМИЗАЦИЯ ПОРТФЕЛЯ\n\n{self.gradient}"

    @property
    def portfolio(self):
        """Оптимизируемый портфель."""
        return self._portfolio

    @property
    def metrics(self):
        """Метрики портфеля."""
        return self._metrics

    @property
    def gradient(self) -> pd.DataFrame:
        """Анализирует градиент позиций с учетом ликвидности и ошибки прогноза."""
        portfolio = self._portfolio
        gradient = self._metrics.gradient
        turnover = self._portfolio.turnover_factor
        error = self._metrics.error
        mean = gradient.where(gradient < 0, gradient * turnover)
        lower = mean - T_SCORE * error
        upper = mean + T_SCORE * error
        buy_sell = pd.Series("", index=gradient.index)
        buy_size = (
            portfolio.value[CASH] / TRADES / portfolio.price / portfolio.lot_size
        ).apply(int)
        buy_sell = buy_sell.mask(lower > 0, buy_size)

        value = portfolio.value
        max_trade = value[PORTFOLIO] * MAX_TRADE
        sell_size = value.mask(max_trade > value, max_trade)
        sell_size = max_trade / TRADES / portfolio.price / portfolio.lot_size
        sell_size = sell_size.apply(lambda x: int(x) + 1)

        buy_sell = buy_sell.mask((upper < 0) & (portfolio.weight > 0), -sell_size)
        buy_sell[CASH] = ""
        df = pd.concat([gradient, turnover, lower, mean, upper, buy_sell], axis=1)
        df.columns = ["GRADIENT", "TURNOVER", "LOWER", "MEAN", "UPPER", "BUY_SELL"]
        return df.sort_values(by="GRADIENT", axis=0, ascending=False)


if __name__ == "__main__":
    CASH_ = 2143 + 501_091 + 2049 + 1607 + (994 + 2333) - 500_000
    POSITIONS = dict(
        AKRN=152 + 716 + 91 + 7 + (542 + 0),
        ALRS=2690,
        BANEP=741 + 13 + 107 + 235,
        BSPB=4890 + 0 + 3600 + 150,
        CBOM=0 + 4400 + 71000 + (197_200 + 0),
        CHMF=114 + 1029 + 170,
        GCHE=0 + 0 + 24,
        GMKN=0 + 58,
        KRKNP=66 + 0 + 43,
        KZOS=490 + 5080 + 2090,
        LNZL=(66 + 0),
        LSNGP=2280 + 670 + 2410,
        MGTSP=485 + 0 + 9 + (151 + 0),
        MOEX=2110 + 200 + 290 + (6730 + 0),
        MSTT=720 + 0 + 100 + 320 + (840 + 0),
        MTSS=2340 + 4800 + 1500 + 2120 + (3540 + 0),
        MVID=90 + 0 + 800 + (6060 + 0),
        NMTP=29000 + 74000 + 13000 + 67000,
        PHOR=497 + 271 + 248 + 405 + (1039 + 374),
        PIKK=0 + 3090 + 0 + 90 + (4050 + 0),
        PLZL=86 + 21 + 23,
        PMSBP=0 + 0 + 1160,
        PRTK=0 + 6980 + (2420 + 0),
        RTKM=(13150 + 0),
        RTKMP=0 + 29400,
        SELG=0 + 7300 + 1000,
        SFIN=(1190 + 0),
        SNGSP=72000 + 12200 + 22400 + 5100 + (46200 + 0),
        TRCN=41 + 0 + 4 + 3 + (68 + 0),
        TRNFP=7 + (13 + 0),
        UPRO=345_000 + 451_000 + 283_000 + 85000,
        VSMO=39 + 161 + 3,
        # Бумаги с нулевым весом
        RNFT=0,
        LSRG=0,
        DSKY=0,
        CNTLP=0,
        BANE=0,
        IRKT=0,
        MRKV=0,
        TATNP=0,
        SIBN=0,
        UNAC=0,
        MRKC=0,
        LSNG=0,
        MSRS=0,
        SVAV=0,
        TGKA=0,
        NKNC=0,
        NVTK=0,
        LKOH=0,
        OGKB=0,
        AFLT=0,
        SNGS=0,
        MRKZ=0,
        ROSN=0,
        SBERP=0,
        VTBR=0,
        ENRU=0,
        TATN=0,
        RASP=0,
        NLMK=0,
        NKNCP=0,
        FEES=0,
        HYDR=0,
        MRKP=0,
        MTLRP=0,
        MAGN=0,
        GAZP=0,
        SBER=0,
        MGNT=0,
        RSTI=0,
        MSNG=0,
        AFKS=0,
        MTLR=0,
        ISKJ=0,
        RSTIP=0,
        OBUV=0,
        APTK=0,
        GTRK=0,
        ROLO=0,
        FESH=0,
        IRAO=0,
        AMEZ=0,
        YAKG=0,
        AQUA=0,
        RGSS=0,
        LIFE=0,
        KBTK=0,
        KMAZ=0,
        TTLK=0,
        TGKD=0,
        TGKB=0,
        RBCM=0,
        KZOSP=0,
        RUGR=0,
        CHEP=0,
        TRMK=0,
        TGKN=0,
        IRGZ=0,
        LNZLP=0,
        BRZL=0,
    )
    POSITIONS.pop("OBUV")
    POSITIONS.pop("GTRK")
    DATE = "2020-05-05"

    opt = Optimizer(Portfolio(DATE, CASH_, POSITIONS))
    print(opt.portfolio)
    print(opt.metrics)
    print(opt)
