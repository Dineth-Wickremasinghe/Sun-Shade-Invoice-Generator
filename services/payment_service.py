from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from database.db_manager import DatabaseManager


@dataclass
class Payment:
    """Represents a single payment made by a customer."""
    customer_name: str
    amount: float
    date: str
    note: str = ""
    id: Optional[int] = None


@dataclass
class CustomerSummary:
    """Aggregated billing and payment summary for a customer."""
    customer_name: str
    total_billed: float
    total_paid: float

    @property
    def balance_due(self) -> float:
        return round(self.total_billed - self.total_paid, 2)


class PaymentService:
    """Handles all database operations for payments and customer summaries."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    # ── CREATE ──────────────────────────────────────────────────────────── #

    def add_payment(self, customer_name: str, amount: float,
                    note: str = "", date: str = None) -> Payment:
        """Record a new payment from a customer."""
        if amount <= 0:
            raise ValueError("Payment amount must be greater than zero.")
        if not customer_name.strip():
            raise ValueError("Customer name cannot be empty.")
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d %H:%M")

        payment = Payment(customer_name=customer_name.strip(),
                          amount=amount, date=date, note=note.strip())
        cursor = self.db.get_cursor()
        cursor.execute(
            "INSERT INTO payments (customer_name, amount, date, note) VALUES (?, ?, ?, ?)",
            (payment.customer_name, payment.amount, payment.date, payment.note)
        )
        self.db.commit()
        payment.id = cursor.lastrowid
        return payment

    # ── READ ─────────────────────────────────────────────────────────────── #

    def get_payments_by_customer(self, customer_name: str) -> List[Payment]:
        """Return all payments for a given customer, most recent first."""
        cursor = self.db.get_cursor()
        cursor.execute(
            """SELECT id, customer_name, amount, date, note
               FROM payments WHERE LOWER(customer_name) = LOWER(?)
               ORDER BY id DESC""",
            (customer_name.strip(),)
        )
        return [Payment(id=r["id"], customer_name=r["customer_name"],
                        amount=r["amount"], date=r["date"], note=r["note"] or "")
                for r in cursor.fetchall()]

    def get_all_payments(self) -> List[Payment]:
        """Return all payments, most recent first."""
        cursor = self.db.get_cursor()
        cursor.execute(
            "SELECT id, customer_name, amount, date, note FROM payments ORDER BY id DESC"
        )
        return [Payment(id=r["id"], customer_name=r["customer_name"],
                        amount=r["amount"], date=r["date"], note=r["note"] or "")
                for r in cursor.fetchall()]

    def get_customer_summary(self, customer_name: str) -> CustomerSummary:
        """Return billed total, paid total and balance due for a customer."""
        cursor = self.db.get_cursor()

        cursor.execute(
            """SELECT COALESCE(SUM(total), 0) as total_billed
               FROM bills WHERE LOWER(customer_name) = LOWER(?)""",
            (customer_name.strip(),)
        )
        total_billed = cursor.fetchone()["total_billed"]

        cursor.execute(
            """SELECT COALESCE(SUM(amount), 0) as total_paid
               FROM payments WHERE LOWER(customer_name) = LOWER(?)""",
            (customer_name.strip(),)
        )
        total_paid = cursor.fetchone()["total_paid"]

        return CustomerSummary(
            customer_name=customer_name.strip(),
            total_billed=round(total_billed, 2),
            total_paid=round(total_paid, 2)
        )

    def get_all_customer_summaries(self) -> List[CustomerSummary]:
        """
        Return a summary for every customer who has at least one bill or payment,
        sorted by balance due (highest first).
        """
        cursor = self.db.get_cursor()

        # Collect all unique customer names from both tables
        cursor.execute(
            """SELECT DISTINCT LOWER(customer_name) as name FROM bills
               UNION
               SELECT DISTINCT LOWER(customer_name) as name FROM payments"""
        )
        names = [row["name"] for row in cursor.fetchall()]

        # Get the original-case name from bills first, else payments
        summaries = []
        for lower_name in names:
            cursor.execute(
                "SELECT customer_name FROM bills WHERE LOWER(customer_name) = ? LIMIT 1",
                (lower_name,)
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "SELECT customer_name FROM payments WHERE LOWER(customer_name) = ? LIMIT 1",
                    (lower_name,)
                )
                row = cursor.fetchone()
            display_name = row["customer_name"]
            summaries.append(self.get_customer_summary(display_name))

        summaries.sort(key=lambda s: s.balance_due, reverse=True)
        return summaries

    # ── DELETE ───────────────────────────────────────────────────────────── #

    def delete_payment(self, payment_id: int) -> bool:
        """Delete a payment record by ID. Returns True if deleted."""
        cursor = self.db.get_cursor()
        cursor.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
        self.db.commit()
        return cursor.rowcount > 0


# ── Quick test ───────────────────────────────────────────────────────────── #
if __name__ == "__main__":
    from database.db_manager import DatabaseManager

    db = DatabaseManager()
    service = PaymentService(db)

    p1 = service.add_payment("Jane Smith", 1500.00, note="Cash")
    p2 = service.add_payment("Jane Smith", 500.00,  note="Bank transfer")
    print(f"Added: {p1}")
    print(f"Added: {p2}")

    summary = service.get_customer_summary("Jane Smith")
    print(f"\nSummary for {summary.customer_name}:")
    print(f"  Billed : LKR {summary.total_billed:,.2f}")
    print(f"  Paid   : LKR {summary.total_paid:,.2f}")
    print(f"  Balance: LKR {summary.balance_due:,.2f}")

    db.close()