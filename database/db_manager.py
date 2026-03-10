import sqlite3
import os


class DatabaseManager:
    """Handles SQLite connection and table creation."""

    DB_PATH = os.path.join(os.path.dirname(__file__), "textile_billing.db")

    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Open a connection to the SQLite database."""
        self.connection = sqlite3.connect(self.DB_PATH)
        self.connection.row_factory = sqlite3.Row  # Allows dict-like row access
        self.connection.execute("PRAGMA foreign_keys = ON")  # Enforce FK constraints

    def get_cursor(self):
        """Return a cursor for executing queries."""
        return self.connection.cursor()

    def commit(self):
        """Commit the current transaction."""
        self.connection.commit()

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()

    def create_tables(self):
        """Create all required tables if they don't already exist."""
        cursor = self.get_cursor()

        # Items table: stores item name, size, and price
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL,
                size    TEXT NOT NULL,
                price   REAL NOT NULL,
                UNIQUE(name, size)
            )
        """)

        # Bills table: stores bill header info
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                date          TEXT NOT NULL,
                total         REAL NOT NULL DEFAULT 0
            )
        """)

        # Bill items table: line items linked to a bill
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bill_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id    INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
                item_id    INTEGER NOT NULL REFERENCES items(id),
                quantity   INTEGER NOT NULL DEFAULT 1,
                unit_price REAL NOT NULL
            )
        """)

        self.commit()
        print("Database tables created/verified successfully.")


# Quick test when run directly
if __name__ == "__main__":
    db = DatabaseManager()
    print(f"Database created at: {DatabaseManager.DB_PATH}")
    db.close()