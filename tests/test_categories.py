import pytest

from pocketsmith_sync.categories import CategoryIndex

CATEGORIES = [
    {
        "id": 1,
        "title": "Eating and Drinking",
        "children": [
            {"id": 2, "title": "Groceries", "children": []},
            {"id": 3, "title": "Eating Out", "children": []},
        ],
    },
    {
        "id": 4,
        "title": "Transport",
        "children": [
            {"id": 5, "title": "Fuel", "children": []},
        ],
    },
    {
        "id": 6,
        "title": "Groceries",  # duplicate leaf title, different parent (none here, but top-level)
        "children": [],
    },
]


def test_resolve_unambiguous_leaf():
    index = CategoryIndex(CATEGORIES)
    assert index.resolve("Eating Out") == 3


def test_resolve_top_level():
    index = CategoryIndex(CATEGORIES)
    assert index.resolve("Transport") == 4


def test_resolve_is_case_insensitive():
    index = CategoryIndex(CATEGORIES)
    assert index.resolve("eating out") == 3


def test_resolve_ambiguous_requires_path():
    index = CategoryIndex(CATEGORIES)
    with pytest.raises(ValueError, match="ambiguous"):
        index.resolve("Groceries")


def test_resolve_with_explicit_path():
    index = CategoryIndex(CATEGORIES)
    assert index.resolve("Eating and Drinking > Groceries") == 2


def test_resolve_not_found():
    index = CategoryIndex(CATEGORIES)
    with pytest.raises(ValueError, match="no category named"):
        index.resolve("Nonexistent")


def test_path_for_id():
    index = CategoryIndex(CATEGORIES)
    assert index.path_for_id(3) == "Eating and Drinking > Eating Out"
    assert index.path_for_id(4) == "Transport"
