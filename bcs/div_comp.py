"""Сравнение дивидендов с BCS."""
import pandas as pd


df = pd.read_excel("bcs.xlsx", sheet_name="dividends")
df = df[["TICKER", "close_date", "value"]]
print(df[df.TICKER == "AKRN"].set_index("close_date"))
