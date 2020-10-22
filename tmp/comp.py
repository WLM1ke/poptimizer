import pandas as pd

from poptimizer.data.views.crop import div
from poptimizer.data.views.div_status import _compare
from poptimizer.portfolio import portfolio

DATE = "2020-10-21"


def comp(ticker):
    df_div = div.dividends(ticker).loc[:DATE]

    df_dohod = div.dohod(ticker)
    df_bcs = div.bcs(ticker)
    df_conomy = div.conomy(ticker)

    df = pd.concat([df_dohod, df_bcs, df_conomy], axis=1).median(axis=1).loc[:DATE]

    return _compare(ticker, df_div, df)


if __name__ == "__main__":
    port = portfolio.load_from_yaml(DATE)
    count = 0
    err = 0

    for ticker in port.index[:-2]:
        df = comp(ticker)
        count += len(df)
        err += (df["STATUS"] == "ERROR").sum()

    print(f"\nДоля ошибок - {err/count:.1%}")
