"""Configuration loaded from environment variables (optionally via a .env file)."""
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Config:
    pocketsmith_api_key: str
    google_service_account_file: str
    google_sheet_id: Optional[str]
    google_sheet_name: Optional[str]
    sheet_tab_name: str
    sync_start_date: Optional[str]
    sync_end_date: Optional[str]
    auto_mark_reviewed: bool

    @staticmethod
    def load() -> "Config":
        api_key = os.environ.get("POCKETSMITH_API_KEY")
        if not api_key:
            raise RuntimeError(
                "POCKETSMITH_API_KEY is not set. Copy .env.example to .env and fill it in."
            )

        service_account_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")

        sheet_id = os.environ.get("GOOGLE_SHEET_ID") or None
        sheet_name = os.environ.get("GOOGLE_SHEET_NAME") or None
        if not sheet_id and not sheet_name:
            raise RuntimeError(
                "Set either GOOGLE_SHEET_ID or GOOGLE_SHEET_NAME in your .env file."
            )

        return Config(
            pocketsmith_api_key=api_key,
            google_service_account_file=service_account_file,
            google_sheet_id=sheet_id,
            google_sheet_name=sheet_name,
            sheet_tab_name=os.environ.get("SHEET_TAB_NAME", "Transactions"),
            sync_start_date=os.environ.get("SYNC_START_DATE") or None,
            sync_end_date=os.environ.get("SYNC_END_DATE") or None,
            auto_mark_reviewed=_bool_env("AUTO_MARK_REVIEWED", True),
        )
