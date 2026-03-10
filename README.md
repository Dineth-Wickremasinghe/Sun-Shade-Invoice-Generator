# 🧵 Sun & Shade — Textile Invoice Generator

A local desktop application for managing textile item prices, generating customer invoices, tracking bill history, and recording payments. Built with Python and Tkinter, using SQLite for storage.

---

## 📋 Features

- **Price Manager** — Add, edit and delete textile items with size-based pricing. Supports standard sizes (XS, S, M, L, XL, 2XL, 3XL, N/A) and custom sizes.
- **Billing** — Build invoices by selecting items and quantities, save bills to the database, and export as a formatted PDF.
- **Bill History** — Browse all past bills, view line items, edit saved bills, re-export PDFs, and delete records.
- **Accounts** — View per-customer totals (billed, paid, balance due), record payments, and manage payment history.

---

## 🗂 Project Structure

```
Sun-Shade-Invoice-Generator/
│
├── main.py                   # Entry point
├── config.ini                # Company details (not committed to Git)
├── config_loader.py          # Reads config.ini at runtime
├── run.bat                   # Double-click to launch without IDE
├── .gitignore
├── README.md
│
├── database/
│   ├── __init__.py
│   ├── db_manager.py         # SQLite connection and table creation
│   └── textile_billing.db    # Auto-generated database file
│
├── models/
│   ├── __init__.py
│   ├── item.py               # Item data model
│   └── bill.py               # Bill and BillItem data models
│
├── services/
│   ├── __init__.py
│   ├── price_service.py      # CRUD for items and prices
│   ├── bill_service.py       # CRUD for bills
│   └── payment_service.py    # CRUD for payments and customer summaries
│
├── ui/
│   ├── __init__.py
│   ├── app.py                # Main window and tab navigation
│   ├── price_manager.py      # Price Manager tab
│   ├── billing.py            # Billing tab
│   ├── history.py            # Bill History tab
│   └── accounts.py           # Accounts tab
│
└── utils/
    ├── __init__.py
    └── pdf_export.py         # PDF invoice generation using ReportLab
```

---

## 🗄 Database Schema

```sql
-- Textile items with size-based pricing
CREATE TABLE items (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name   TEXT NOT NULL,
    size   TEXT NOT NULL,
    price  REAL NOT NULL,
    UNIQUE(name, size)
);

-- Bill headers
CREATE TABLE bills (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    date          TEXT NOT NULL,
    total         REAL NOT NULL DEFAULT 0
);

-- Line items per bill (prices snapshotted at billing time)
CREATE TABLE bill_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id    INTEGER NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    item_id    INTEGER NOT NULL REFERENCES items(id),
    quantity   INTEGER NOT NULL DEFAULT 1,
    unit_price REAL NOT NULL
);

-- Customer payment records
CREATE TABLE payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    amount        REAL NOT NULL,
    date          TEXT NOT NULL,
    note          TEXT
);
```

---

## ⚙️ Setup

### Requirements
- Python 3.10 or higher
- Windows (for the `.bat` launcher and `os.startfile` PDF opening)

### 1. Clone or download the project

```bash
git clone https://github.com/your-username/Sun-Shade-Invoice-Generator.git
cd Sun-Shade-Invoice-Generator
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install reportlab
```

### 4. Configure company details

Create a `config.ini` file in the project root (this file is excluded from Git):

```ini
[company]
name        = Sun & Shade
tagline     = Textile Invoice Generator
address     = 123 Main Street, Kandy, Sri Lanka
phone       = +94 xx xxx xxxx
email       = info@sunandshade.lk
```

### 5. Run the app

**Option A — Double-click:**
```
run.bat
```

**Option B — Terminal:**
```bash
python main.py
```

The SQLite database (`textile_billing.db`) is created automatically on first run inside the `database/` folder.

---

## 📄 PDF Invoices

Invoices are exported as A4 PDFs using ReportLab. Each invoice includes:
- Company name, tagline, address, phone and email (from `config.ini`)
- Invoice number and date
- Customer name
- Itemised line items with size, quantity, unit price and subtotal
- Grand total
- Thank-you footer

PDFs are saved to a folder of your choice when you click **Export PDF**.

---

## 💰 Accounts & Payments

Payments are matched to bills by **customer name** (case-insensitive). For accurate balances, ensure customer names are spelled consistently when creating bills and recording payments.

Each customer shows:
- 🟠 **Orange** — balance still owed
- ✅ **Green** — fully settled
- 🔴 **Red** — overpaid

---

## 🔒 Privacy

`config.ini` contains your business details and is listed in `.gitignore` so it is never committed to version control. Never remove it from `.gitignore`.

---

## 📦 Dependencies

| Package    | Purpose                        | Install          |
|------------|--------------------------------|------------------|
| reportlab  | PDF invoice generation         | `pip install reportlab` |
| tkinter    | GUI framework (built-in)       | Included with Python |
| sqlite3    | Database (built-in)            | Included with Python |

---

## 🛠 PyCharm Tips

- Mark the project root as **Sources Root** (right-click → Mark Directory as → Sources Root) to resolve imports correctly.
- Set `main.py` as the run configuration entry point.
- The `.venv` folder and `textile_billing.db` are excluded from Git via `.gitignore`.
