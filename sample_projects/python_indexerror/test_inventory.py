"""
Test cases for inventory management system.
"""

import pytest
from inventory import Inventory


def test_add_item():
    """Test adding items to inventory."""
    inv = Inventory()
    inv.add_item("apple", 10)
    assert inv.get_total_items() == 1


def test_get_first_item_empty():
    """Test getting first item from empty inventory - TRIGGERS BUG."""
    inv = Inventory()
    # This should raise IndexError because inventory is empty
    result = inv.get_first_item()
    assert result is not None


def test_get_first_item_with_items():
    """Test getting first item when inventory has items."""
    inv = Inventory()
    inv.add_item("banana", 5)
    item = inv.get_first_item()
    assert item["name"] == "banana"
    assert item["quantity"] == 5


def test_find_item():
    """Test finding items by name."""
    inv = Inventory()
    inv.add_item("orange", 15)
    item = inv.find_item("orange")
    assert item is not None
    assert item["quantity"] == 15


def test_find_item_not_found():
    """Test finding non-existent item."""
    inv = Inventory()
    inv.add_item("grape", 8)
    item = inv.find_item("watermelon")
    assert item is None
