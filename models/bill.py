from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class BillItem:
    """
    Represents a single line item within a bill.

    Attributes:
        item_id    : References the items table
        item_name  : Snapshot of item name at time of billing
        size       : Snapshot of item size at time of billing
        quantity   : Number of units
        unit_price : Price per unit at time of billing (snapshot, not live)
        id         : Auto-assigned by the database
        bill_id    : Set when the parent bill is saved
    """
    item_id: int
    item_name: str
    size: str
    quantity: int
    unit_price: float
    id: Optional[int] = None
    bill_id: Optional[int] = None

    def __post_init__(self):
        if self.quantity <= 0:
            raise ValueError("Quantity must be at least 1.")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

    @property
    def subtotal(self) -> float:
        """Calculate the subtotal for this line item."""
        return round(self.quantity * self.unit_price, 2)

    def __str__(self):
        return (f"{self.item_name} [{self.size}] "
                f"x{self.quantity} @ ${self.unit_price:.2f} = ${self.subtotal:.2f}")


@dataclass
class Bill:
    """
    Represents a complete bill/invoice.

    Attributes:
        customer_name : Name of the customer
        items         : List of BillItem line items
        date          : Date of the bill (defaults to today)
        id            : Auto-assigned by the database
    """
    customer_name: str
    items: List[BillItem] = field(default_factory=list)
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    id: Optional[int] = None

    def __post_init__(self):
        self.customer_name = self.customer_name.strip()


    def add_item(self, bill_item: BillItem):
        """Add a line item to this bill."""
        self.items.append(bill_item)

    def remove_item(self, index: int):
        """Remove a line item by its index in the list."""
        if 0 <= index < len(self.items):
            self.items.pop(index)

    @property
    def total(self) -> float:
        """Calculate the grand total of the bill."""
        return round(sum(item.subtotal for item in self.items), 2)

    def summary(self) -> str:
        """Return a formatted text summary of the bill."""
        lines = [
            f"{'=' * 40}",
            f"  INVOICE",
            f"{'=' * 40}",
            f"  Customer : {self.customer_name}",
            f"  Date     : {self.date}",
            f"  Bill ID  : {self.id or 'Not saved yet'}",
            f"{'-' * 40}",
        ]
        for bill_item in self.items:
            lines.append(f"  {bill_item}")
        lines += [
            f"{'-' * 40}",
            f"  TOTAL    : ${self.total:.2f}",
            f"{'=' * 40}",
        ]
        return "\n".join(lines)


# Quick test when run directly
if __name__ == "__main__":
    bill = Bill(customer_name="John Doe")
    bill.add_item(BillItem(item_id=1, item_name="Cotton Shirt", size="M", quantity=3, unit_price=15.99))
    bill.add_item(BillItem(item_id=2, item_name="Linen Trousers", size="L", quantity=1, unit_price=29.50))
    print(bill.summary())
    print(f"Total items: {len(bill.items)}")