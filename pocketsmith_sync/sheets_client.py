"""Thin wrapper around gspread for reading/writing the transactions worksheet."""
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2.service_account import Credentials

from .config import Config

# Column order in the worksheet. "New Category" is the only column a human is
# expected to edit; everything else is written by `pull` / `push`.
HEADERS = [
    "Transaction ID",
    "Date",
    "Payee",
    "Amount",
    "Account",
    "Institution",
    "Category",
    "New Category",
    "Needs Review",
    "Note",
    "Labels",
    "Last Synced",
]

TXN_ID_COL = 1  # 1-indexed column A
NEW_CATEGORY_COL = HEADERS.index("New Category") + 1
CATEGORY_COL = HEADERS.index("Category") + 1
NEEDS_REVIEW_COL = HEADERS.index("Needs Review") + 1
LAST_SYNCED_COL = HEADERS.index("Last Synced") + 1

_SCOPES_KEY_ONLY = ["https://www.googleapis.com/auth/spreadsheets"]
_SCOPES_WITH_DRIVE = _SCOPES_KEY_ONLY + ["https://www.googleapis.com/auth/drive.readonly"]


def open_worksheet(config: Config) -> gspread.Worksheet:
    scopes = _SCOPES_KEY_ONLY if config.google_sheet_id else _SCOPES_WITH_DRIVE
    creds = Credentials.from_service_account_file(
        config.google_service_account_file, scopes=scopes
    )
    client = gspread.authorize(creds)

    if config.google_sheet_id:
        spreadsheet = client.open_by_key(config.google_sheet_id)
    else:
        spreadsheet = client.open(config.google_sheet_name)

    try:
        worksheet = spreadsheet.worksheet(config.sheet_tab_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=config.sheet_tab_name, rows=1000, cols=len(HEADERS)
        )

    if worksheet.row_values(1) != HEADERS:
        worksheet.update("A1", [HEADERS])
        worksheet.freeze(rows=1)

    return worksheet


def read_rows(worksheet: gspread.Worksheet) -> List[Dict[str, Any]]:
    """Return every data row as a dict keyed by header name (row 2 onward)."""
    values = worksheet.get_all_values()
    if len(values) <= 1:
        return []
    header = values[0]
    rows = []
    for row_number, raw_row in enumerate(values[1:], start=2):
        padded = raw_row + [""] * (len(header) - len(raw_row))
        row = dict(zip(header, padded))
        row["_row_number"] = row_number
        rows.append(row)
    return rows


def append_rows(worksheet: gspread.Worksheet, rows: List[List[Any]]) -> None:
    if rows:
        worksheet.append_rows(rows, value_input_option="USER_ENTERED")


def batch_update_cells(
    worksheet: gspread.Worksheet, updates: List[Dict[str, Any]]
) -> None:
    """updates: list of {"row": int, "col": int, "value": Any}."""
    if not updates:
        return
    body = [
        {
            "range": gspread.utils.rowcol_to_a1(u["row"], u["col"]),
            "values": [[u["value"]]],
        }
        for u in updates
    ]
    worksheet.batch_update(body, value_input_option="USER_ENTERED")
