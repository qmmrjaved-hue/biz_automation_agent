"""
sheets_adapter.py — Google Sheets sink via a service account (gspread).

Requires in .env:
  SHEETS_CREDENTIALS_PATH  — path to a service-account JSON key file
  SHEETS_SPREADSHEET_ID    — the target spreadsheet's ID
The service account must be shared as an editor on the target spreadsheet.

Public functions:
  - append_row(sheet_name, row) -> None
  - read_sheet(sheet_name) -> pandas.DataFrame
"""

import pandas as pd

from config import settings

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _client():
    import gspread
    from google.oauth2.service_account import Credentials

    if not settings.sheets_credentials_path or not settings.sheets_spreadsheet_id:
        raise EnvironmentError(
            "[sheets_adapter] SHEETS_CREDENTIALS_PATH and SHEETS_SPREADSHEET_ID "
            "must be set in .env to use Google Sheets."
        )

    creds = Credentials.from_service_account_file(settings.sheets_credentials_path, scopes=_SCOPES)
    return gspread.authorize(creds)


def _worksheet(sheet_name: str):
    gc = _client()
    sh = gc.open_by_key(settings.sheets_spreadsheet_id)
    try:
        return sh.worksheet(sheet_name)
    except Exception:
        return sh.add_worksheet(title=sheet_name, rows=1000, cols=26)


def append_row(sheet_name: str, row: dict) -> None:
    """Append a single row (dict of column -> value) to a worksheet, creating
    a header row from the dict keys if the sheet is currently empty."""
    ws = _worksheet(sheet_name)
    existing = ws.get_all_values()
    if not existing:
        ws.append_row(list(row.keys()))
    ws.append_row([str(v) for v in row.values()])
    print(f"[sheets_adapter] Appended 1 row to '{sheet_name}'.")


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read a worksheet into a DataFrame using its first row as headers."""
    ws = _worksheet(sheet_name)
    records = ws.get_all_records()
    return pd.DataFrame(records)
