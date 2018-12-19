import pandas as pd

from poptimizer import portfolio
from poptimizer.finder.momentum import find_momentum


def test_find_momentum(capsys):
    date = pd.Timestamp("2018-12-18")
    positions = dict(TATN=1, KZOS=1, LKOH=1)
    port = portfolio.Portfolio(date, 0, positions)
    find_momentum(port, 0.02)
    captured = capsys.readouterr()
    assert "Выведены 2% - 5 акций" in captured.out
    assert "TATN   0.509073  0.244496  1.000000  2.082128     " in captured.out
    assert "BANEP  0.412600  0.205033  1.000000  2.012363  ADD" in captured.out
    assert "NVTK   0.536663  0.275343  1.000000  1.949073  ADD" in captured.out
    assert "KZOS   0.385195  0.199113  0.999934  1.934423     " in captured.out
    assert "SIBN   0.418839  0.240944  1.000000  1.738324  ADD" in captured.out
    assert "LKOH" not in captured.out
