import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from database.db_manager import DatabaseManager
from services.price_service import PriceService
from services.bill_service import BillService
from models.bill import Bill
from utils.pdf_export import export_bill_to_pdf

# ── Palette (shared with price_manager) ────────────────────────────────────
BG        = "#F7F3EE"
PANEL     = "#FFFFFF"
ACCENT    = "#2C5F2E"
ACCENT_HV = "#1E4220"
DANGER    = "#B94040"
BORDER    = "#D9D0C5"
TXT_DARK  = "#1A1A1A"
TXT_MID   = "#5A5550"
TXT_LIGHT = "#9A948E"

FONT_HEAD  = ("Georgia", 15, "bold")
FONT_SUB   = ("Georgia", 10, "italic")
FONT_LABEL = ("Helvetica", 9, "bold")
FONT_ENTRY = ("Helvetica", 10)
FONT_BTN   = ("Helvetica", 9, "bold")
FONT_TABLE = ("Helvetica", 9)
FONT_TOTAL = ("Georgia", 13, "bold")


def _btn(parent, text, command, color=ACCENT, fg="white", width=14):
    b = tk.Button(parent, text=text, command=command,
                  bg=color, fg=fg, relief="flat",
                  font=FONT_BTN, cursor="hand2",
                  padx=10, pady=6, width=width)
    b.bind("<Enter>", lambda e: b.config(bg=ACCENT_HV if color == ACCENT else "#8A2020"))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


def _label(parent, text, font=FONT_LABEL, fg=TXT_MID, bg=PANEL, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, **kw)


def _entry(parent, textvariable, width=22, bg=PANEL):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    font=FONT_ENTRY, relief="flat",
                    bg="#F0EBE3", fg=TXT_DARK,
                    insertbackground=TXT_DARK,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    highlightcolor=ACCENT)


class BillingFrame(tk.Frame):
    """
    Screen for creating bills.
    Select items, set quantities, and generate/save invoices.
    """

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG)
        self.db = db
        self.price_service = PriceService(db)
        self.bill_service  = BillService(db)
        self._current_bill = Bill(customer_name="")
        self._selected_row = None

        self._build_header()
        self._build_body()
        self._refresh_item_list()

    # ── Layout ────────────────────────────────────────────────────────── #

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Billing",
                 font=FONT_HEAD, fg="white", bg=ACCENT).pack(side="left", padx=22)
        tk.Label(hdr, text="Build and save customer invoices",
                 font=FONT_SUB, fg="#A8C8AA", bg=ACCENT).pack(side="left", padx=4)

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Left column: item picker + customer
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 14))
        self._build_item_picker(left)
        self._build_customer_panel(left)

        # Right column: bill table + total + actions
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_bill_table(right)
        self._build_total_panel(right)

    def _build_item_picker(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", ipadx=12, ipady=12, pady=(0, 12))

        tk.Label(card, text="SELECT ITEM", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).grid(row=0, column=0, columnspan=2,
                                               sticky="w", padx=8, pady=(8, 10))

        # Item name dropdown
        _label(card, "Item Name").grid(row=1, column=0, sticky="w", padx=8, pady=(0, 2))
        self.var_item_name = tk.StringVar()
        self.cmb_item = ttk.Combobox(card, textvariable=self.var_item_name,
                                     width=22, state="readonly",
                                     font=FONT_ENTRY)
        self.cmb_item.grid(row=2, column=0, columnspan=2, padx=8, sticky="ew")
        self.cmb_item.bind("<<ComboboxSelected>>", self._on_item_name_selected)

        # Size dropdown
        _label(card, "Size").grid(row=3, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_size = tk.StringVar()
        self.cmb_size = ttk.Combobox(card, textvariable=self.var_size,
                                     width=10, state="readonly",
                                     font=FONT_ENTRY)
        self.cmb_size.grid(row=4, column=0, padx=8, sticky="w")
        self.cmb_size.bind("<<ComboboxSelected>>", self._on_size_selected)

        # Unit price display
        self.lbl_unit = tk.Label(card, text="Price: —",
                                 font=("Helvetica", 9, "italic"),
                                 fg=ACCENT, bg=PANEL)
        self.lbl_unit.grid(row=4, column=1, padx=8, sticky="w")

        # Quantity
        _label(card, "Quantity").grid(row=5, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_qty = tk.StringVar(value="1")
        sp = tk.Spinbox(card, from_=1, to=9999,
                        textvariable=self.var_qty,
                        width=8, font=FONT_ENTRY,
                        bg="#F0EBE3", fg=TXT_DARK,
                        relief="flat",
                        highlightthickness=1,
                        highlightbackground=BORDER)
        sp.grid(row=6, column=0, padx=8, sticky="w")

        _btn(card, "＋  Add to Bill", self._add_to_bill, width=18
             ).grid(row=6, column=1, padx=8, pady=4)

        card.columnconfigure(0, weight=1)

    def _build_customer_panel(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", ipadx=12, ipady=12)

        tk.Label(card, text="CUSTOMER", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=8, pady=(8, 6))

        self.var_customer = tk.StringVar()
        _entry(card, self.var_customer, width=26).pack(padx=8, fill="x")

    # ── Bill Table ────────────────────────────────────────────────────── #

    def _build_bill_table(self, parent):
        hdr = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                       highlightbackground=BORDER)
        hdr.pack(fill="both", expand=True)

        tk.Label(hdr, text="CURRENT BILL", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("#", "Item", "Size", "Qty", "Unit Price", "Subtotal")
        self.bill_tree = ttk.Treeview(hdr, columns=cols,
                                      show="headings", height=12,
                                      selectmode="browse")

        style = ttk.Style()
        style.configure("Bill.Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=TXT_DARK, font=FONT_TABLE, rowheight=26)
        style.configure("Bill.Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Helvetica", 9, "bold"), relief="flat")
        style.map("Bill.Treeview", background=[("selected", "#D4E8D4")])
        self.bill_tree.configure(style="Bill.Treeview")

        widths = {"#": 30, "Item": 160, "Size": 55,
                  "Qty": 45, "Unit Price": 95, "Subtotal": 95}
        for col in cols:
            self.bill_tree.heading(col, text=col)
            self.bill_tree.column(col, width=widths[col],
                                  anchor="center" if col != "Item" else "w")

        self.bill_tree.tag_configure("odd",  background="#F7F3EE")
        self.bill_tree.tag_configure("even", background=PANEL)

        vsb = ttk.Scrollbar(hdr, orient="vertical", command=self.bill_tree.yview)
        self.bill_tree.configure(yscrollcommand=vsb.set)
        self.bill_tree.pack(side="left", fill="both", expand=True,
                            padx=(12, 0), pady=(0, 8))
        vsb.pack(side="left", fill="y", pady=(0, 8), padx=(0, 8))
        self.bill_tree.bind("<<TreeviewSelect>>",
                            lambda e: setattr(self, "_selected_row",
                                              self.bill_tree.selection()))

    def _build_total_panel(self, parent):
        panel = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                         highlightbackground=BORDER)
        panel.pack(fill="x", pady=(12, 0), ipadx=12, ipady=12)

        # Total display
        total_row = tk.Frame(panel, bg=PANEL)
        total_row.pack(fill="x", padx=12)
        tk.Label(total_row, text="TOTAL", font=FONT_LABEL,
                 fg=TXT_MID, bg=PANEL).pack(side="left")
        self.lbl_total = tk.Label(total_row, text="LKR 0.00",
                                  font=FONT_TOTAL, fg=ACCENT, bg=PANEL)
        self.lbl_total.pack(side="right")

        tk.Frame(panel, bg=BORDER, height=1).pack(fill="x", padx=12, pady=8)

        # Action buttons
        btn_row = tk.Frame(panel, bg=PANEL)
        btn_row.pack(fill="x", padx=12)
        _btn(btn_row, "🗑  Remove Row",  self._remove_row,
             color=DANGER, width=16).pack(side="left", padx=(0, 6))
        _btn(btn_row, "↺  Clear Bill",  self._clear_bill,
             color="#8A8480", width=14).pack(side="left", padx=(0, 6))
        _btn(btn_row, "💾  Save Bill",   self._save_bill,
             width=14).pack(side="right")
        _btn(btn_row, "📄  Export PDF",  self._export_pdf,
             color="#5A5550", width=14).pack(side="right", padx=(0, 6))

    # ── Data helpers ──────────────────────────────────────────────────── #

    def _refresh_item_list(self):
        names = self.price_service.get_unique_item_names()
        self.cmb_item["values"] = names
        self.cmb_size["values"] = []
        self.var_size.set("")
        self.lbl_unit.config(text="Price: —")

    def _on_item_name_selected(self, _=None):
        name = self.var_item_name.get()
        variants = self.price_service.get_items_by_name(name)
        sizes = [v.size for v in variants]
        self.cmb_size["values"] = sizes
        self.var_size.set(sizes[0] if sizes else "")
        self._on_size_selected()

    def _on_size_selected(self, _=None):
        name = self.var_item_name.get()
        size = self.var_size.get()
        if not name or not size:
            return
        items = self.price_service.get_items_by_name(name)
        match = next((i for i in items if i.size == size), None)
        if match:
            self.lbl_unit.config(text=f"Price: LKR {match.price:,.2f}")
            self._current_item = match
        else:
            self.lbl_unit.config(text="Price: —")
            self._current_item = None

    def _refresh_bill_tree(self):
        self.bill_tree.delete(*self.bill_tree.get_children())
        for i, bi in enumerate(self._current_bill.items):
            tag = "even" if i % 2 == 0 else "odd"
            self.bill_tree.insert("", "end",
                                  values=(i + 1, bi.item_name, bi.size,
                                          bi.quantity,
                                          f"{bi.unit_price:,.2f}",
                                          f"{bi.subtotal:,.2f}"),
                                  tags=(tag,))
        total = self._current_bill.total
        self.lbl_total.config(text=f"LKR {total:,.2f}")

    # ── Actions ───────────────────────────────────────────────────────── #

    def _add_to_bill(self):
        item = getattr(self, "_current_item", None)
        if not item:
            messagebox.showwarning("No Item", "Please select an item and size.")
            return
        try:
            qty = int(self.var_qty.get())
            if qty < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Qty", "Quantity must be a whole number ≥ 1.")
            return

        bill_item = self.bill_service.create_bill_item_from_item(item, qty)
        self._current_bill.add_item(bill_item)
        self._refresh_bill_tree()
        self.var_qty.set("1")

    def _remove_row(self):
        sel = self.bill_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a row to remove.")
            return
        idx = self.bill_tree.index(sel[0])
        self._current_bill.remove_item(idx)
        self._refresh_bill_tree()

    def _clear_bill(self):
        if self._current_bill.items:
            if not messagebox.askyesno("Clear Bill", "Remove all items from the bill?"):
                return
        self._current_bill = Bill(customer_name="")
        self.var_customer.set("")
        self._refresh_bill_tree()

    def _save_bill(self):
        customer = self.var_customer.get().strip()
        if not customer:
            messagebox.showwarning("Customer Required",
                                   "Please enter a customer name.")
            return
        if not self._current_bill.items:
            messagebox.showwarning("Empty Bill",
                                   "Add at least one item before saving.")
            return

        self._current_bill.customer_name = customer
        try:
            saved = self.bill_service.save_bill(self._current_bill)
            messagebox.showinfo(
                "Bill Saved",
                f"Bill #{saved.id} saved for {customer}.\n"
                f"Total: LKR {saved.total:,.2f}"
            )
            self._current_bill = Bill(customer_name="")
            self.var_customer.set("")
            self._refresh_bill_tree()
        except ValueError as e:
            messagebox.showerror("Save Failed", str(e))

    def _export_pdf(self):
        if not self._current_bill.items:
            messagebox.showwarning("Empty Bill",
                                   "Add at least one item before exporting.")
            return
        customer = self.var_customer.get().strip()
        if not customer:
            messagebox.showwarning("Customer Required",
                                   "Please enter a customer name before exporting.")
            return

        # Ask where to save
        output_dir = filedialog.askdirectory(title="Select folder to save PDF")
        if not output_dir:
            return  # User cancelled

        self._current_bill.customer_name = customer

        # Auto-save if not already saved so the invoice gets a real number
        try:
            if self._current_bill.id is None:
                self._current_bill = self.bill_service.save_bill(self._current_bill)
                self._refresh_bill_tree()
        except ValueError as e:
            messagebox.showerror("Save Failed", str(e))
            return

        try:
            path = export_bill_to_pdf(self._current_bill, output_dir=output_dir)
            if messagebox.askyesno("PDF Exported",
                                   f"Invoice saved to:\n{path}\n\nOpen the file now?"):
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def on_tab_focus(self):
        """Call this when the tab becomes active to refresh item list."""
        self._refresh_item_list()


# ── Standalone test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Billing — Test")
    root.geometry("900x600")
    root.configure(bg=BG)
    db = DatabaseManager()
    BillingFrame(root, db).pack(fill="both", expand=True)
    root.mainloop()
    db.close()