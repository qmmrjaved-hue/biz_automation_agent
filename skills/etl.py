"""
etl.py — clean a raw CSV/Excel file and load it into a sink. The cleaning
pass is a generalized port of Voice2Query's db_cleaner.py, applied to a
pandas.DataFrame directly (so it works before data ever lands in a database):
  1. Drop fully empty rows (every column NULL/blank).
  2. Strip leading/trailing whitespace from text columns.
  3. Standardize column names to lowercase snake_case (collision-safe).

Public functions:
  - clean_dataframe(df) -> tuple[pandas.DataFrame, dict]
  - clean_and_load(file_path, sink=None, table_name=None) -> dict
"""

import os
import re
import sqlite3

import pandas as pd

from adapters import excel_adapter, postgres_adapter, sheets_adapter
from config import settings


def _standardise(name: str) -> str:
    """Convert a column name to lowercase snake_case."""
    name = str(name).strip().lower()
    name = re.sub(r"[\s\-]+", "_", name)
    name = re.sub(r"[^\w]", "", name)
    return name or "col"


def clean_dataframe(df: pd.DataFrame) -> tuple:
    """
    Clean a DataFrame in place-equivalent fashion (returns a new DataFrame).

    Args:
        df: The raw DataFrame to clean.

    Returns:
        (cleaned_df, report) where report is:
        {
            "empty_rows_removed": int,
            "cells_stripped": int,
            "columns_renamed": list[str],   # "old -> new"
        }
    """
    report = {"empty_rows_removed": 0, "cells_stripped": 0, "columns_renamed": []}

    before = len(df)
    is_blank = df.map(lambda v: pd.isna(v) or str(v).strip() == "")
    df = df.loc[~is_blank.all(axis=1)].reset_index(drop=True)
    report["empty_rows_removed"] = before - len(df)

    for col in df.select_dtypes(include=["object", "str"]).columns:
        stripped = df[col].astype(str).str.strip()
        changed = (df[col].astype(str) != stripped).sum()
        if changed:
            report["cells_stripped"] += int(changed)
            df[col] = stripped

    new_names = [_standardise(c) for c in df.columns]
    seen = {}
    resolved = []
    for name in new_names:
        if name in seen:
            seen[name] += 1
            resolved.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            resolved.append(name)

    for old, new in zip(df.columns, resolved):
        if old != new:
            report["columns_renamed"].append(f"{old} -> {new}")
    df.columns = resolved

    print(f"[etl] Cleaned — {report['empty_rows_removed']} empty rows removed, "
          f"{report['cells_stripped']} cells stripped, "
          f"{len(report['columns_renamed'])} columns renamed.")
    return df, report


def _load_dataframe(file_path: str) -> pd.DataFrame:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(file_path)
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path)
    raise ValueError(f"[etl] Unsupported file type: '{ext}'. Use .csv or .xlsx.")


def _load_to_sink(df: pd.DataFrame, sink: str, table_name: str) -> str:
    if sink == "excel":
        path = settings.excel_path
        with pd.ExcelWriter(path, engine="openpyxl",
                             mode="a" if os.path.exists(path) else "w",
                             if_sheet_exists="replace" if os.path.exists(path) else None) as writer:
            df.to_excel(writer, sheet_name=table_name[:31], index=False)
        return os.path.abspath(path)

    if sink == "sqlite":
        os.makedirs(os.path.dirname(os.path.abspath(settings.warehouse_db_path)), exist_ok=True)
        conn = sqlite3.connect(settings.warehouse_db_path)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        conn.close()
        return f"sqlite:{settings.warehouse_db_path}#{table_name}"

    if sink == "postgres":
        engine = postgres_adapter.get_engine()
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        return f"postgres:{table_name}"

    if sink == "sheets":
        for _, row in df.iterrows():
            sheets_adapter.append_row(table_name, row.to_dict())
        return f"google_sheets:{settings.sheets_spreadsheet_id}/{table_name}"

    raise ValueError(f"[etl] Unknown sink: '{sink}'")


def clean_and_load(file_path: str, sink: str = None, table_name: str = None) -> dict:
    """
    Read a CSV/Excel file, clean it, and load it into the chosen sink.

    Args:
        file_path:  Path to a .csv or .xlsx source file.
        sink:       "excel" | "sheets" | "postgres" | "sqlite". Defaults to config.settings.default_sink.
        table_name: Destination table/sheet name. Defaults to the file's basename.

    Returns:
        The clean_dataframe() report dict, plus "rows_loaded" and "saved_to".

    Raises:
        FileNotFoundError: if file_path does not exist.
        ValueError: if the file type or sink is unsupported.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"[etl] File not found: '{file_path}'")

    sink = sink or settings.default_sink
    table_name = table_name or _standardise(os.path.splitext(os.path.basename(file_path))[0])

    raw_df = _load_dataframe(file_path)
    clean_df, report = clean_dataframe(raw_df)
    saved_to = _load_to_sink(clean_df, sink, table_name)

    report["rows_loaded"] = len(clean_df)
    report["saved_to"] = saved_to
    print(f"[etl] Loaded {len(clean_df)} row(s) into {saved_to}.")
    return report
