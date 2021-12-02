import logging

import pandas as pd


def dfs_dict_to_excel(filename: str, dfs: dict[str, pd.DataFrame]):
    """Сохраняет словарь таблиц в excel файл.

    :param filename:
        Путь для сохранения нового файла
    :param dfs:
        Словарь pandas.DataFrame, ключи которого - названия страниц в создаваемом файле. Например:
        dfs = {'gadgets': df_gadgets, 'widgets': df_widgets}
    """
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    logger = logging.getLogger()
    for sheetname, df in dfs.items():  # loop through `dict` of dataframes
        logger.info(sheetname)
        df.to_excel(writer, sheet_name=sheetname)  # send df to writer
        worksheet = writer.sheets[sheetname]  # pull worksheet object
        for idx, col in enumerate(df.columns):  # loop through all columns
            series = df[col]
            max_len = max(len(col), series.astype(str).map(len).max()) + 1
            worksheet.set_column(idx + 1, idx + 1, max_len)  # set column width
    writer.save()
