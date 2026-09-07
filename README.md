# Pocketsmith-Sync

Round-trip your PocketSmith transactions through a Google Sheet:

1. **`pull`** — download transactions from PocketSmith into a sheet.
2. Recategorise transactions by typing a category name into the **New Category**
   column (leave it blank for anything you don't want to touch).
3. **`push`** — apply every changed **New Category** back to PocketSmith, and
   (optionally) mark those transactions as reviewed.

Only categorisation is synced back to PocketSmith. All other columns are
informational, refreshed on every `pull`.

## Setup

### 1. PocketSmith API key

Create a Developer Key at https://my.pocketsmith.com/security and put it in
`.env` as `POCKETSMITH_API_KEY`.

### 2. Google Sheets service account

1. In Google Cloud Console, create (or reuse) a project and enable the
   **Google Sheets API** (and **Google Drive API** if you plan to reference
   your sheet by name rather than ID).
2. Create a **Service Account**, then create a JSON key for it and save it
   as `service-account.json` in the project root (or point
   `GOOGLE_SERVICE_ACCOUNT_FILE` at wherever you saved it).
3. Create a Google Sheet (any name), then **share it** with the service
   account's `client_email` (found in the JSON key file) as an **Editor**.
4. Copy the sheet ID from its URL
   (`https://docs.google.com/spreadsheets/d/<THIS_PART>/edit`) into
   `GOOGLE_SHEET_ID` in `.env`.

### 3. Install and configure

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# then edit .env with your API key, sheet ID, and service account path
```

## Usage

```bash
# Download all transactions into the sheet (creates the "Transactions" tab if needed)
python -m pocketsmith_sync pull

# Only pull a date range
python -m pocketsmith_sync pull --start-date 2026-01-01 --end-date 2026-09-01

# ... go recategorise rows in the "New Category" column in Google Sheets ...

# Preview what would change without touching PocketSmith
python -m pocketsmith_sync push --dry-run

# Apply the recategorisations
python -m pocketsmith_sync push
```

Re-running `pull` refreshes every read-only column (date, payee, amount,
current category, etc.) from PocketSmith while **preserving** anything you've
typed into `New Category` that hasn't been pushed yet, so it's safe to pull
again mid-recategorisation to pick up new transactions.

### Sheet columns

| Column | Written by | Meaning |
|---|---|---|
| Transaction ID | pull | PocketSmith transaction ID. Don't edit. |
| Date, Payee, Amount, Account, Institution | pull | Read-only transaction details. |
| Category | pull, push | Current category in PocketSmith. |
| New Category | you | Type a category name here to recategorise. Leave blank to skip. |
| Needs Review, Note, Labels | pull | Read-only, from PocketSmith. |
| Last Synced | push | Timestamp of the last successful push for that row. |

### Category names

Type either a category's own name (e.g. `Groceries`) or, if that name exists
under more than one parent, `Parent > Child` (e.g.
`Eating and Drinking > Groceries`) to disambiguate. Matching is
case-insensitive. `push` reports any row whose category name can't be
resolved without changing anything for that row.

### Config reference (`.env`)

See `.env.example` for the full list. Key options:

- `SYNC_START_DATE` / `SYNC_END_DATE` — limit what `pull` fetches (useful
  given large transaction histories); omit for everything.
- `AUTO_MARK_REVIEWED` — when `true` (default), a successful category push
  also clears PocketSmith's "needs review" flag on that transaction.
- `SHEET_TAB_NAME` — worksheet/tab name to use (default `Transactions`).

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests cover the category name resolver and the push sync logic against fake
PocketSmith/Sheets clients — no live credentials required.

## Limitations

- Split transactions and transfers are synced like any other transaction
  (their top-level category can be changed), but this tool doesn't create or
  edit splits.
- `push` overwrites PocketSmith's category with whatever is in `New
  Category`; if the same transaction was also recategorised directly in
  PocketSmith since your last `pull`, the sheet's value wins.
