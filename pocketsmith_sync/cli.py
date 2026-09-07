"""Command-line entry point: `python -m pocketsmith_sync pull|push`."""
import argparse
import sys

from .config import Config
from .pocketsmith_client import PocketSmithClient
from .sheets_client import open_worksheet
from .sync import pull, push


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pocketsmith_sync",
        description="Sync PocketSmith transactions with a Google Sheet.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    pull_parser = subparsers.add_parser(
        "pull", help="Download PocketSmith transactions into the Google Sheet."
    )
    pull_parser.add_argument("--start-date", help="YYYY-MM-DD, overrides SYNC_START_DATE")
    pull_parser.add_argument("--end-date", help="YYYY-MM-DD, overrides SYNC_END_DATE")

    push_parser = subparsers.add_parser(
        "push", help="Apply recategorisations from the Google Sheet back to PocketSmith."
    )
    push_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without calling the PocketSmith API.",
    )

    return parser


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    config = Config.load()
    client = PocketSmithClient(config.pocketsmith_api_key)
    worksheet = open_worksheet(config)

    if args.command == "pull":
        result = pull(config, client, worksheet, start_date=args.start_date, end_date=args.end_date)
        print(f"Fetched {result.transactions_fetched} transactions, wrote {result.rows_written} rows.")
        return 0

    if args.command == "push":
        result = push(config, client, worksheet, dry_run=args.dry_run)
        label = "Would update" if args.dry_run else "Updated"
        print(f"{label} {result.updated} transaction(s); skipped {result.skipped} unchanged row(s).")
        if result.errors:
            print(f"\n{len(result.errors)} error(s):", file=sys.stderr)
            for error in result.errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
