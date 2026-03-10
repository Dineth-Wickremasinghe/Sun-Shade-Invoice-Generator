from database.db_manager import DatabaseManager
from models.item import Item
from typing import List, Optional


class PriceService:
    """Handles all database operations related to items and their prices."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ------------------------------------------------------------------ #
    #  CREATE                                                              #
    # ------------------------------------------------------------------ #

    def add_item(self, name: str, size: str, price: float) -> Item:
        """
        Add a new item+size+price entry.
        Raises ValueError if the name+size combination already exists.
        """
        item = Item(name=name, size=size, price=price)  # Validates input
        cursor = self.db.get_cursor()
        try:
            cursor.execute(
                "INSERT INTO items (name, size, price) VALUES (?, ?, ?)",
                (item.name, item.size, item.price)
            )
            self.db.commit()
            item.id = cursor.lastrowid
            return item
        except Exception as e:
            raise ValueError(f"Item '{item.name}' with size '{item.size}' already exists.") from e

    # ------------------------------------------------------------------ #
    #  READ                                                                #
    # ------------------------------------------------------------------ #

    def get_all_items(self) -> List[Item]:
        """Return all items ordered by name and size."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT id, name, size, price FROM items ORDER BY name, size")
        rows = cursor.fetchall()
        return [Item(id=row["id"], name=row["name"], size=row["size"], price=row["price"])
                for row in rows]

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        """Return a single item by its ID, or None if not found."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT id, name, size, price FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if row:
            return Item(id=row["id"], name=row["name"], size=row["size"], price=row["price"])
        return None

    def get_items_by_name(self, name: str) -> List[Item]:
        """Return all size/price variants for a given item name."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT id, name, size, price FROM items WHERE LOWER(name) = LOWER(?) ORDER BY size",
            (name.strip(),)
        )
        rows = cursor.fetchall()
        return [Item(id=row["id"], name=row["name"], size=row["size"], price=row["price"])
                for row in rows]

    def get_unique_item_names(self) -> List[str]:
        """Return a sorted list of unique item names (useful for dropdowns)."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT DISTINCT name FROM items ORDER BY name")
        return [row["name"] for row in cursor.fetchall()]

    def search_items(self, keyword: str) -> List[Item]:
        """Search items by partial name match."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT id, name, size, price FROM items WHERE name LIKE ? ORDER BY name, size",
            (f"%{keyword.strip()}%",)
        )
        rows = cursor.fetchall()
        return [Item(id=row["id"], name=row["name"], size=row["size"], price=row["price"])
                for row in rows]

    # ------------------------------------------------------------------ #
    #  UPDATE                                                              #
    # ------------------------------------------------------------------ #

    def update_price(self, item_id: int, new_price: float) -> bool:
        """
        Update the price of an existing item by ID.
        Returns True if successful, False if item not found.
        """
        if new_price < 0:
            raise ValueError("Price cannot be negative.")
        cursor = self.db.get_cursor()
        cursor.execute("UPDATE items SET price = ? WHERE id = ?", (new_price, item_id))
        self.db.commit()
        return cursor.rowcount > 0

    def update_item(self, item_id: int, name: str, size: str, price: float) -> bool:
        """
        Update all fields of an existing item by ID.
        Returns True if successful, False if item not found.
        """
        item = Item(name=name, size=size, price=price)  # Validates input
        cursor = self.db.get_cursor()
        try:
            cursor.execute(
                "UPDATE items SET name = ?, size = ?, price = ? WHERE id = ?",
                (item.name, item.size, item.price, item_id)
            )
            self.db.commit()
            return cursor.rowcount > 0
        except Exception as e:
            raise ValueError(f"Update failed: {e}") from e

    # ------------------------------------------------------------------ #
    #  DELETE                                                              #
    # ------------------------------------------------------------------ #

    def delete_item(self, item_id: int) -> bool:
        """
        Delete an item by ID.
        Returns True if deleted, False if not found.
        """
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        self.db.commit()
        return cursor.rowcount > 0


# ------------------------------------------------------------------ #
#  Quick test when run directly                                        #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    db = DatabaseManager()
    service = PriceService(db)

    # Add items
    shirt_m = service.add_item("Cotton Shirt", "M", 15.99)
    shirt_l = service.add_item("Cotton Shirt", "L", 17.99)
    trouser = service.add_item("Linen Trousers", "L", 29.50)
    print(f"Added: {shirt_m}")
    print(f"Added: {shirt_l}")
    print(f"Added: {trouser}")

    # Get all
    print("\nAll items:")
    for item in service.get_all_items():
        print(f"  {item}")

    # Get by name
    print("\nAll 'Cotton Shirt' variants:")
    for item in service.get_items_by_name("Cotton Shirt"):
        print(f"  {item}")

    # Update price
    service.update_price(shirt_m.id, 18.99)
    updated = service.get_item_by_id(shirt_m.id)
    print(f"\nUpdated price: {updated}")

    # Delete
    service.delete_item(trouser.id)
    print(f"\nAfter delete, all items:")
    for item in service.get_all_items():
        print(f"  {item}")

    db.close()