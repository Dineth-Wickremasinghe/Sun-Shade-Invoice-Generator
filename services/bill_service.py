from database.db_manager import DatabaseManager
from models.bill import Bill, BillItem
from models.item import Item
from services.price_service import PriceService
from typing import List, Optional


class BillService:
    """Handles all database operations related to bills and bill items."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.price_service = PriceService(db)

    # ------------------------------------------------------------------ #
    #  CREATE                                                              #
    # ------------------------------------------------------------------ #

    def save_bill(self, bill: Bill) -> Bill:
        """
        Save a complete Bill (with all its BillItems) to the database.
        Sets bill.id and each bill_item.id after saving.
        Raises ValueError if the bill has no items.
        """
        if not bill.items:
            raise ValueError("Cannot save a bill with no items.")

        cursor = self.db.get_cursor()

        # Insert bill header
        cursor.execute(
            "INSERT INTO bills (customer_name, date, total) VALUES (?, ?, ?)",
            (bill.customer_name, bill.date, bill.total)
        )
        bill.id = cursor.lastrowid

        # Insert each line item
        for bill_item in bill.items:
            cursor.execute(
                """INSERT INTO bill_items (bill_id, item_id, quantity, unit_price)
                   VALUES (?, ?, ?, ?)""",
                (bill.id, bill_item.item_id, bill_item.quantity, bill_item.unit_price)
            )
            bill_item.id = cursor.lastrowid
            bill_item.bill_id = bill.id

        self.db.commit()
        return bill

    def create_bill_item_from_item(self, item: Item, quantity: int) -> BillItem:
        """
        Helper to create a BillItem from an Item object and a quantity.
        Snapshots the current price from the Item.
        """
        return BillItem(
            item_id=item.id,
            item_name=item.name,
            size=item.size,
            quantity=quantity,
            unit_price=item.price
        )

    # ------------------------------------------------------------------ #
    #  READ                                                                #
    # ------------------------------------------------------------------ #

    def get_all_bills(self) -> List[Bill]:
        """Return all bills (headers only, no line items) ordered by most recent."""
        cursor = self.db.get_cursor()
        cursor.execute("SELECT id, customer_name, date, total FROM bills ORDER BY id DESC")
        rows = cursor.fetchall()
        bills = []
        for row in rows:
            bill = Bill(customer_name=row["customer_name"], date=row["date"])
            bill.id = row["id"]
            bills.append(bill)
        return bills

    def get_bill_by_id(self, bill_id: int) -> Optional[Bill]:
        """
        Return a full Bill with all its BillItems by bill ID.
        Returns None if not found.
        """
        cursor = self.db.get_cursor()

        # Fetch bill header
        cursor.execute(
            "SELECT id, customer_name, date, total FROM bills WHERE id = ?",
            (bill_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        bill = Bill(customer_name=row["customer_name"], date=row["date"])
        bill.id = row["id"]

        # Fetch line items with item name and size via JOIN
        cursor.execute(
            """SELECT bi.id, bi.item_id, i.name, i.size, bi.quantity, bi.unit_price
               FROM bill_items bi
               JOIN items i ON bi.item_id = i.id
               WHERE bi.bill_id = ?""",
            (bill_id,)
        )
        for item_row in cursor.fetchall():
            bill_item = BillItem(
                id=item_row["id"],
                bill_id=bill_id,
                item_id=item_row["item_id"],
                item_name=item_row["name"],
                size=item_row["size"],
                quantity=item_row["quantity"],
                unit_price=item_row["unit_price"]
            )
            bill.items.append(bill_item)

        return bill

    def search_bills_by_customer(self, name: str) -> List[Bill]:
        """Search bills by partial customer name match."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """SELECT id, customer_name, date, total FROM bills
               WHERE customer_name LIKE ? ORDER BY id DESC""",
            (f"%{name.strip()}%",)
        )
        rows = cursor.fetchall()
        bills = []
        for row in rows:
            bill = Bill(customer_name=row["customer_name"], date=row["date"])
            bill.id = row["id"]
            bills.append(bill)
        return bills

    # ------------------------------------------------------------------ #
    #  DELETE                                                              #
    # ------------------------------------------------------------------ #

    def delete_bill(self, bill_id: int) -> bool:
        """
        Delete a bill and all its line items (CASCADE handles bill_items).
        Returns True if deleted, False if not found.
        """
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM bills WHERE id = ?", (bill_id,))
        self.db.commit()
        return cursor.rowcount > 0


# ------------------------------------------------------------------ #
#  Quick test when run directly                                        #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    db = DatabaseManager()
    price_service = PriceService(db)
    bill_service = BillService(db)

    # Ensure some items exist (ignore error if already added)
    try:
        price_service.add_item("Cotton Shirt", "M", 15.99)
        price_service.add_item("Linen Trousers", "L", 29.50)
    except ValueError:
        pass  # Already exists from previous test run

    # Fetch items to use in the bill
    items = price_service.get_items_by_name("Cotton Shirt")
    shirt = items[0]
    trousers = price_service.get_items_by_name("Linen Trousers")[0]

    # Build a bill
    bill = Bill(customer_name="Jane Smith")
    bill.add_item(bill_service.create_bill_item_from_item(shirt, quantity=2))
    bill.add_item(bill_service.create_bill_item_from_item(trousers, quantity=1))

    # Save it
    saved_bill = bill_service.save_bill(bill)
    print(f"Saved Bill ID: {saved_bill.id}")
    print(saved_bill.summary())

    # Retrieve it back
    retrieved = bill_service.get_bill_by_id(saved_bill.id)
    print("\nRetrieved from DB:")
    print(retrieved.summary())

    # List all bills
    print("\nAll bills:")
    for b in bill_service.get_all_bills():
        print(f"  Bill #{b.id} — {b.customer_name} on {b.date}")

    db.close()