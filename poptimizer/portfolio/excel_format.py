import pandas as pd


def save_to_excel(filename, dfs):
    # Given a dict of dataframes, for example:
    # dfs = {'gadgets': df_gadgets, 'widgets': df_widgets}
    writer = pd.ExcelWriter(filename, engine='xlsxwriter')
    for sheetname, df in dfs.items():  # loop through `dict` of dataframes
        print(sheetname)
        df.to_excel(writer, sheet_name=sheetname)  # send df to writer
        worksheet = writer.sheets[sheetname]  # pull worksheet object
        for idx, col in enumerate(df.columns):  # loop through all columns
            series = df[col]
            max_len = max(len(col), series.astype(str).map(len).max()) + 1
            worksheet.set_column(idx + 1, idx + 1, max_len)  # set column width
    writer.save()