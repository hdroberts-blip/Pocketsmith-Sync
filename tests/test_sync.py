from unittest.mock import MagicMock

from pocketsmith_sync.config import Config
from pocketsmith_sync.sheets_client import HEADERS
from pocketsmith_sync.sync import push

CATEGORIES = [
    {
        "id": 1,
        "title": "Eating and Drinking",
        "children": [
            {"id": 2, "title": "Groceries", "children": []},
            {"id": 3, "title": "Eating Out", "children": []},
        ],
    },
]


class FakeWorksheet:
    def __init__(self, rows):
        self._values = [HEADERS] + rows
        self.batch_update_calls = []

    def get_all_values(self):
        return self._values

    def batch_update(self, body, value_input_option=None):
        self.batch_update_calls.append(body)


def _row(txn_id, category, new_category):
    row = {h: "" for h in HEADERS}
    row["Transaction ID"] = str(txn_id)
    row["Category"] = category
    row["New Category"] = new_category
    return [row[h] for h in HEADERS]


def _config(**overrides):
    defaults = dict(
        pocketsmith_api_key="key",
        google_service_account_file="sa.json",
        google_sheet_id="sheet",
        google_sheet_name=None,
        sheet_tab_name="Transactions",
        sync_start_date=None,
        sync_end_date=None,
        auto_mark_reviewed=True,
    )
    defaults.update(overrides)
    return Config(**defaults)


def test_push_updates_changed_category_and_marks_reviewed():
    client = MagicMock()
    client.get_current_user.return_value = {"id": 1}
    client.list_categories.return_value = CATEGORIES

    worksheet = FakeWorksheet([_row(100, "Groceries", "Eating Out")])
    result = push(_config(), client, worksheet)

    assert result.updated == 1
    assert result.skipped == 0
    assert result.errors == []
    client.update_transaction.assert_called_once_with(100, category_id=3, needs_review=False)
    assert worksheet.batch_update_calls  # cell updates were written back


def test_push_skips_unchanged_rows():
    client = MagicMock()
    client.get_current_user.return_value = {"id": 1}
    client.list_categories.return_value = CATEGORIES

    worksheet = FakeWorksheet(
        [
            _row(100, "Groceries", ""),  # nothing entered
            _row(101, "Groceries", "Groceries"),  # same as current
        ]
    )
    result = push(_config(), client, worksheet)

    assert result.updated == 0
    assert result.skipped == 2
    client.update_transaction.assert_not_called()


def test_push_reports_unresolvable_category():
    client = MagicMock()
    client.get_current_user.return_value = {"id": 1}
    client.list_categories.return_value = CATEGORIES

    worksheet = FakeWorksheet([_row(100, "Groceries", "Not A Real Category")])
    result = push(_config(), client, worksheet)

    assert result.updated == 0
    assert len(result.errors) == 1
    assert "no category named" in result.errors[0]
    client.update_transaction.assert_not_called()


def test_push_dry_run_makes_no_api_calls():
    client = MagicMock()
    client.get_current_user.return_value = {"id": 1}
    client.list_categories.return_value = CATEGORIES

    worksheet = FakeWorksheet([_row(100, "Groceries", "Eating Out")])
    result = push(_config(), client, worksheet, dry_run=True)

    assert result.updated == 1
    client.update_transaction.assert_not_called()
    assert worksheet.batch_update_calls == []
