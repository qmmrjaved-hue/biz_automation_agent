"""
excel_adapter.py — default, zero-credential sink: append/read rows in a
local .xlsx workbook, one sheet per record type.

Public functions:
  - append_row(sheet_name, row, workbook_path=None) -> str
  - read_sheet(sheet_name, workbook_path=None) -> pandas.DataFrame
"""

import os

import pandas as pd

from config import settings


def _resolve_path(workbook_path: str = None) -> str:
    return workbook_path or settings.excel_path


def append_row(sheet_name: str, row: dict, workbook_path: str = None) -> str:
    """
    Append a single row (dict of column -> value) to a sheet in the workbook,
    creating the workbook and/or sheet if they don't exist yet.

    Args:
        sheet_name:     Name of the worksheet to append to.
        row:            Mapping of column name to value.
        workbook_path:  Optional override of the default workbook path.

    Returns:
        The absolute path to the workbook that was written.
    """
    path = _resolve_path(workbook_path)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

    new_row_df = pd.DataFrame([row])

    if os.path.exists(path):
        try:
            existing = pd.read_excel(path, sheet_name=sheet_name)
            combined = pd.concat([existing, new_row_df], ignore_index=True)
        except ValueError:
            combined = new_row_df  # sheet didn't exist yet
        sheets = pd.read_excel(path, sheet_name=None)
        sheets[sheet_name] = combined
    else:
        sheets = {sheet_name: new_row_df}

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)

    print(f"[excel_adapter] Appended 1 row to '{sheet_name}' in '{path}'.")
    return os.path.abspath(path)


def read_sheet(sheet_name: str, workbook_path: str = None) -> pd.DataFrame:
    """
    Read a sheet from the workbook as a DataFrame. Returns an empty
    DataFrame if the workbook or sheet doesn't exist yet.
    """
    path = _resolve_path(workbook_path)
    if not os.path.exists(path):
        return pd.DataFrame()
    try:
        return pd.read_excel(path, sheet_name=sheet_name)
    except ValueError:
        return pd.DataFrame()
