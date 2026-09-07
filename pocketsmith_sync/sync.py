"""Pull PocketSmith transactions into a Google Sheet, and push recategorisations back."""
import datetime as dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import gspread

from .categories import CategoryIndex
from .config import Config
from .pocketsmith_client import PocketSmithClient
from . import sheets_client
from .sheets_client import HEADERS

CHUNK_SIZE = 2000  # rows per Sheets API write, to stay under request size limits


def _transaction_row(txn: Dict[str, Any], preserved: Dict[str, str]) -> List[Any]:
    account = txn.get("transaction_account") or {}
    institution = account.get("institution") or {}
    category = txn.get("category") or {}
    return [
        txn["id"],
        txn.get("date", ""),
        txn.get("payee", ""),
        txn.get("amount", ""),
        account.get("name", ""),
        institution.get("title", ""),
        category.get("title", ""),
        preserved.get("New Category", ""),
        "TRUE" if txn.get("needs_review") else "FALSE",
        txn.get("note") or "",
        ", ".join(txn.get("labels") or []),
        preserved.get("Last Synced", ""),
    ]


@dataclass
class PullResult:
    transactions_fetched: int = 0
    rows_written: int = 0


def pull(
    config: Config,
    client: PocketSmithClient,
    worksheet: gspread.Worksheet,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> PullResult:
    user = client.get_current_user()
    user_id = user["id"]

    existing_rows = sheets_client.read_rows(worksheet)
    preserved_by_id = {
        row["Transaction ID"]: {
            "New Category": row.get("New Category", ""),
            "Last Synced": row.get("Last Synced", ""),
        }
        for row in existing_rows
        if row.get("Transaction ID")
    }

    transactions = list(
        client.iter_transactions(
            user_id,
            start_date=start_date or config.sync_start_date,
            end_date=end_date or config.sync_end_date,
        )
    )
    transactions.sort(key=lambda t: (t.get("date") or "", t["id"]), reverse=True)

    result = PullResult(transactions_fetched=len(transactions))
    rows = [
        _transaction_row(txn, preserved_by_id.get(str(txn["id"]), {}))
        for txn in transactions
    ]

    # Make sure the sheet is big enough, then wipe old data rows before writing fresh ones.
    required_rows = len(rows) + 1
    if worksheet.row_count < required_rows:
        worksheet.resize(rows=required_rows)
    last_col_letter = gspread.utils.rowcol_to_a1(1, len(HEADERS)).rstrip("0123456789")
    worksheet.batch_clear([f"A2:{last_col_letter}{worksheet.row_count}"])

    for start in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[start : start + CHUNK_SIZE]
        first_row = start + 2
        last_row = first_row + len(chunk) - 1
        cell_range = f"A{first_row}:{gspread.utils.rowcol_to_a1(last_row, len(HEADERS))}"
        worksheet.update(cell_range, chunk, value_input_option="USER_ENTERED")
        result.rows_written += len(chunk)

    return result


@dataclass
class PushResult:
    updated: int = 0
    skipped: int = 0
    errors: List[str] = field(default_factory=list)


def push(
    config: Config,
    client: PocketSmithClient,
    worksheet: gspread.Worksheet,
    dry_run: bool = False,
) -> PushResult:
    user = client.get_current_user()
    user_id = user["id"]

    categories = client.list_categories(user_id)
    index = CategoryIndex(categories)

    rows = sheets_client.read_rows(worksheet)
    result = PushResult()
    cell_updates: List[Dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    for row in rows:
        txn_id_raw = row.get("Transaction ID", "").strip()
        new_category = row.get("New Category", "").strip()
        current_category = row.get("Category", "").strip()

        if not txn_id_raw or not new_category:
            result.skipped += 1
            continue
        if new_category.lower() == current_category.lower():
            result.skipped += 1
            continue

        try:
            txn_id = int(txn_id_raw)
        except ValueError:
            result.errors.append(f"row {row['_row_number']}: invalid Transaction ID {txn_id_raw!r}")
            continue

        try:
            category_id = index.resolve(new_category)
        except ValueError as exc:
            result.errors.append(f"row {row['_row_number']} (txn {txn_id}): {exc}")
            continue

        if dry_run:
            result.updated += 1
            continue

        fields: Dict[str, Any] = {"category_id": category_id}
        if config.auto_mark_reviewed:
            fields["needs_review"] = False

        try:
            client.update_transaction(txn_id, **fields)
        except Exception as exc:  # noqa: BLE001 - surface any API failure per-row
            result.errors.append(f"row {row['_row_number']} (txn {txn_id}): {exc}")
            continue

        resolved_title = index.path_for_id(category_id).split(" > ")[-1]
        cell_updates.append(
            {"row": row["_row_number"], "col": sheets_client.CATEGORY_COL, "value": resolved_title}
        )
        cell_updates.append(
            {"row": row["_row_number"], "col": sheets_client.LAST_SYNCED_COL, "value": now}
        )
        if config.auto_mark_reviewed:
            cell_updates.append(
                {"row": row["_row_number"], "col": sheets_client.NEEDS_REVIEW_COL, "value": "FALSE"}
            )
        result.updated += 1

    if not dry_run:
        sheets_client.batch_update_cells(worksheet, cell_updates)

    return result
