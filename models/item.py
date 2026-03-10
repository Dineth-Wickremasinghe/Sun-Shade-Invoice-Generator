from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    """
    Represents a single item with a specific size and price.

    Attributes:
        name  : Name of the textile item (e.g., "Cotton Shirt")
        size  : Size of the item (e.g., "S", "M", "L", "XL", or custom like "40cm x 60cm")
        price : Price for this specific item + size combination
        id    : Auto-assigned by the database (None before saving)
    """
    name: str
    size: str
    price: float
    id: Optional[int] = None

    def __post_init__(self):
        self.name = self.name.strip()
        self.size = self.size.strip().upper()
        if self.price < 0:
            raise ValueError("Price cannot be negative.")
        if not self.name:
            raise ValueError("Item name cannot be empty.")
        if not self.size:
            raise ValueError("Item size cannot be empty.")

    def __str__(self):
        return f"{self.name} [{self.size}] — ${self.price:.2f}"


# Quick test when run directly
if __name__ == "__main__":
    item = Item(name="Cotton Shirt", size="m", price=15.99)
    print(item)          # Cotton Shirt [M] — $15.99
    print(item.name)     # Cotton Shirt
    print(item.size)     # M (auto-uppercased)
    print(item.price)    # 15.99