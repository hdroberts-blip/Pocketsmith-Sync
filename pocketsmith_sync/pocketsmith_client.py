"""Thin client around the PocketSmith Developer API (https://developers.pocketsmith.com)."""
import time
from typing import Any, Dict, Iterator, List, Optional

import requests

BASE_URL = "https://api.pocketsmith.com/v2"


class PocketSmithError(RuntimeError):
    pass


class PocketSmithClient:
    def __init__(self, api_key: str, session: Optional[requests.Session] = None):
        self._session = session or requests.Session()
        self._session.headers.update(
            {
                "X-Developer-Key": api_key,
                "Accept": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{BASE_URL}{path}"
        for attempt in range(5):
            response = self._session.request(method, url, timeout=30, **kwargs)
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 2 ** attempt))
                time.sleep(retry_after)
                continue
            if response.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            if not response.ok:
                raise PocketSmithError(
                    f"PocketSmith API {method} {path} failed: "
                    f"{response.status_code} {response.text}"
                )
            return response
        raise PocketSmithError(f"PocketSmith API {method} {path} failed after retries")

    def get_current_user(self) -> Dict[str, Any]:
        return self._request("GET", "/me").json()

    def list_categories(self, user_id: int) -> List[Dict[str, Any]]:
        return self._request("GET", f"/users/{user_id}/categories").json()

    def iter_transactions(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        per_page: int = 100,
    ) -> Iterator[Dict[str, Any]]:
        """Yield every transaction for the user, transparently paginating."""
        page = 1
        while True:
            params: Dict[str, Any] = {"page": page, "per_page": per_page}
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            response = self._request(
                "GET", f"/users/{user_id}/transactions", params=params
            )
            batch = response.json()
            if not batch:
                return
            yield from batch
            total_pages = response.headers.get("X-Total-Pages")
            if total_pages is not None and page >= int(total_pages):
                return
            page += 1

    def update_transaction(self, transaction_id: int, **fields: Any) -> Dict[str, Any]:
        """Update a transaction. Pass category_id="" to uncategorise."""
        return self._request(
            "PUT", f"/transactions/{transaction_id}", json=fields
        ).json()
