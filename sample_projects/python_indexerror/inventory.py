"""
Simple inventory management system with an IndexError bug.
"""

class Inventory:
    def __init__(self):
        self.items = []
    
    def add_item(self, name, quantity):
        """Add an item to inventory."""
        self.items.append({"name": name, "quantity": quantity})
    
    def get_first_item(self):
        """Get the first item in inventory - BUG: no bounds check."""
        return self.items[0]  # Will crash if inventory is empty
    
    def remove_item(self, index):
        """Remove item at index."""
        if index < len(self.items):
            self.items.pop(index)
    
    def get_total_items(self):
        """Get total number of items in inventory."""
        return len(self.items)
    
    def find_item(self, name):
        """Find item by name."""
        for item in self.items:
            if item["name"] == name:
                return item
        return None
