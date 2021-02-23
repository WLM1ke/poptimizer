"""Тесты для загрузки данных о предстоящих иностранных дивидендам."""
import pandas as pd
import pytest

from poptimizer.data.adapters.gateways import moex_status


def test_ticker_parser():
    """Парсер для тикеров."""
    assert moex_status._ticker_parser('ПАО "Северсталь"') is None
    assert (
        moex_status._ticker_parser(
            "Walmart Inc. (Уолмарт, Инк.) - US9311421039, WMT-RM [Акции иностранного эмитента]",
        )
        == "WMT-RM"
    )


@pytest.mark.asyncio
async def test_moex_status_gateway(mocker):
    """Проверка отбрасывания пустых значений в индексе."""
    df_fake = pd.DataFrame(index=["AKRN", None, "CHMF", None, "AKRN"])
    mocker.patch.object(moex_status.parser, "get_df_from_url", return_value=df_fake)
    gw = moex_status.MOEXStatusGateway()
    df_rez = await gw()
    assert df_rez.index.tolist() == ["AKRN", "CHMF", "AKRN"]
