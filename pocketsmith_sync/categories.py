"""Flatten PocketSmith's hierarchical category tree for name <-> id lookups."""
from collections import defaultdict
from typing import Any, Dict, List, NamedTuple


class CategoryEntry(NamedTuple):
    id: int
    title: str
    path: str  # "Title" for top-level, "Parent > Title" for children


class CategoryIndex:
    def __init__(self, categories: List[Dict[str, Any]]):
        self._by_path: Dict[str, CategoryEntry] = {}
        self._by_title: Dict[str, List[CategoryEntry]] = defaultdict(list)
        self._by_id: Dict[int, CategoryEntry] = {}
        for node in categories:
            self._walk(node, parent_path=None)

    def _walk(self, node: Dict[str, Any], parent_path: str) -> None:
        title = node["title"]
        path = f"{parent_path} > {title}" if parent_path else title
        entry = CategoryEntry(id=node["id"], title=title, path=path)
        self._by_path[path.lower()] = entry
        self._by_title[title.lower()].append(entry)
        self._by_id[node["id"]] = entry
        for child in node.get("children") or []:
            self._walk(child, parent_path=path)

    def path_for_id(self, category_id: int) -> str:
        entry = self._by_id.get(category_id)
        return entry.path if entry else ""

    def resolve(self, name: str) -> int:
        """Resolve a user-typed category name to an id.

        Raises ValueError with a human-readable message on failure (not found,
        or ambiguous and needs a "Parent > Child" qualifier).
        """
        name = name.strip()
        if not name:
            raise ValueError("empty category name")

        if ">" in name:
            by_path = self._by_path.get(name.lower())
            if by_path:
                return by_path.id
            raise ValueError(f"no category matches path {name!r}")

        matches = self._by_title.get(name.lower(), [])
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            options = ", ".join(m.path for m in matches)
            raise ValueError(
                f"{name!r} is ambiguous, matches: {options}. "
                f"Use 'Parent > Child' to disambiguate."
            )
        raise ValueError(f"no category named {name!r}")
