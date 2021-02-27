"""Тесты для описания колонок."""

import pandas as pd
import pytest

from poptimizer.data.adapters.html import description
from poptimizer.shared import col

TICKER_CASES = (
    ("GAZP", True),
    ("SNGSP", False),
    ("WRONG", None),
    ("AAPL-RM", None),
)


@pytest.mark.parametrize("ticker, answer", TICKER_CASES)
def test_is_common(ticker, answer):
    """Проверка, что тикер соответствует обыкновенной акции."""
    if answer is None:
        with pytest.raises(description.ParserError, match="Некорректный тикер"):
            description.is_common(ticker)
    else:
        assert description.is_common(ticker) is answer


def test_reformat_df():
    """Данные разносятся на два столбца."""
    div = pd.DataFrame(["2027.5RUR", "2.1USD", "27 RUR"], columns=["SOME"])
    div_reformatted = pd.DataFrame(
        [[2027.5, "RUR"], [2.1, "USD"], [27, "RUR"]],
        columns=["SOME", col.CURRENCY],
    )

    pd.testing.assert_frame_equal(description.reformat_df_with_cur(div, "SOME"), div_reformatted)
