import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from database.db_manager import DatabaseManager
from services.bill_service import BillService
from services.price_service import PriceService
from models.bill import Bill, BillItem
from utils.pdf_export import export_bill_to_pdf

# ── Palette ────────────────────────────────────────────────────────────────
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


def _entry(parent, textvariable, width=22):
    return tk.Entry(parent, textvariable=textvariable, width=width,
                    font=FONT_ENTRY, relief="flat",
                    bg="#F0EBE3", fg=TXT_DARK,
                    insertbackground=TXT_DARK,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    highlightcolor=ACCENT)


class HistoryFrame(tk.Frame):
    """
    Bills history screen.
    Browse past bills, view line items, edit customer name,
    add/remove items, re-export as PDF, or delete a bill.
    """

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG)
        self.db            = db
        self.bill_service  = BillService(db)
        self.price_service = PriceService(db)
        self._selected_bill: Bill | None = None
        self._edit_mode    = False

        self._build_header()
        self._build_body()
        self.refresh_bills()

    # ── Layout ────────────────────────────────────────────────────────── #

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Bill History",
                 font=FONT_HEAD, fg="white", bg=ACCENT).pack(side="left", padx=22)
        tk.Label(hdr, text="Browse, edit and re-export past invoices",
                 font=FONT_SUB, fg="#A8C8AA", bg=ACCENT).pack(side="left", padx=4)

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Left: bill list
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 14))
        self._build_bill_list(left)

        # Right: detail / edit panel
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_detail_panel(right)

    def _build_bill_list(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="both", expand=True, ipadx=8, ipady=8)

        # Search
        tk.Label(card, text="PAST BILLS", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=10, pady=(10, 6))

        search_row = tk.Frame(card, bg=PANEL)
        search_row.pack(fill="x", padx=10, pady=(0, 8))
        _label(search_row, "🔍", fg=TXT_MID).pack(side="left")
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *_: self._on_search())
        _entry(search_row, self.var_search, width=20).pack(side="left", padx=4)

        # Bills treeview
        cols = ("ID", "Customer", "Date", "Total")
        self.bills_tree = ttk.Treeview(card, columns=cols,
                                       show="headings", height=20,
                                       selectmode="browse")

        style = ttk.Style()
        style.configure("Hist.Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=TXT_DARK, font=FONT_TABLE, rowheight=26)
        style.configure("Hist.Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Helvetica", 9, "bold"), relief="flat")
        style.map("Hist.Treeview", background=[("selected", "#D4E8D4")])
        self.bills_tree.configure(style="Hist.Treeview")

        widths = {"ID": 40, "Customer": 150, "Date": 130, "Total": 90}
        for col in cols:
            self.bills_tree.heading(col, text=col)
            self.bills_tree.column(col, width=widths[col],
                                   anchor="center" if col in ("ID", "Total") else "w")

        self.bills_tree.tag_configure("odd",  background="#F7F3EE")
        self.bills_tree.tag_configure("even", background=PANEL)

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.bills_tree.yview)
        self.bills_tree.configure(yscrollcommand=vsb.set)
        self.bills_tree.pack(side="left", fill="both", expand=True,
                             padx=(10, 0), pady=(0, 10))
        vsb.pack(side="left", fill="y", pady=(0, 10), padx=(0, 6))
        self.bills_tree.bind("<<TreeviewSelect>>", self._on_bill_select)

        self.lbl_count = tk.Label(card, text="", font=("Helvetica", 8),
                                  fg=TXT_LIGHT, bg=PANEL)
        self.lbl_count.pack(anchor="e", padx=10, pady=(0, 4))

    def _build_detail_panel(self, parent):
        # ── Top: customer + meta ──
        meta_card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                             highlightbackground=BORDER)
        meta_card.pack(fill="x", ipadx=12, ipady=10, pady=(0, 10))

        tk.Label(meta_card, text="BILL DETAILS", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).grid(row=0, column=0, columnspan=4,
                                               sticky="w", padx=12, pady=(10, 8))

        # Bill ID (read-only)
        _label(meta_card, "Bill ID").grid(row=1, column=0, sticky="w", padx=12)
        self.lbl_bill_id = tk.Label(meta_card, text="—",
                                    font=FONT_ENTRY, fg=ACCENT, bg=PANEL)
        self.lbl_bill_id.grid(row=1, column=1, sticky="w", padx=8)

        # Date (read-only)
        _label(meta_card, "Date").grid(row=1, column=2, sticky="w", padx=12)
        self.lbl_bill_date = tk.Label(meta_card, text="—",
                                      font=FONT_ENTRY, fg=TXT_DARK, bg=PANEL)
        self.lbl_bill_date.grid(row=1, column=3, sticky="w", padx=8)

        # Customer name (editable when in edit mode)
        _label(meta_card, "Customer").grid(row=2, column=0, sticky="w",
                                           padx=12, pady=(8, 0))
        self.var_customer = tk.StringVar()
        self.ent_customer = _entry(meta_card, self.var_customer, width=28)
        self.ent_customer.grid(row=2, column=1, columnspan=3, sticky="w",
                               padx=8, pady=(8, 10))
        self.ent_customer.config(state="disabled")

        # ── Middle: items table ──
        items_card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                              highlightbackground=BORDER)
        items_card.pack(fill="both", expand=True, pady=(0, 10))

        tk.Label(items_card, text="LINE ITEMS", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("#", "Item", "Size", "Qty", "Unit Price", "Subtotal")
        self.items_tree = ttk.Treeview(items_card, columns=cols,
                                       show="headings", height=9,
                                       selectmode="browse")
        self.items_tree.configure(style="Hist.Treeview")

        widths = {"#": 30, "Item": 160, "Size": 60,
                  "Qty": 45, "Unit Price": 95, "Subtotal": 95}
        for col in cols:
            self.items_tree.heading(col, text=col)
            self.items_tree.column(col, width=widths[col],
                                   anchor="w" if col == "Item" else "center")

        self.items_tree.tag_configure("odd",  background="#F7F3EE")
        self.items_tree.tag_configure("even", background=PANEL)

        ivsb = ttk.Scrollbar(items_card, orient="vertical",
                              command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=ivsb.set)
        self.items_tree.pack(side="left", fill="both", expand=True,
                             padx=(12, 0), pady=(0, 8))
        ivsb.pack(side="left", fill="y", pady=(0, 8), padx=(0, 8))

        # ── Edit mode: add item row ──
        self.add_item_frame = tk.Frame(items_card, bg=PANEL)
        # (packed/hidden dynamically in _toggle_edit)
        _label(self.add_item_frame, "Add Item:").pack(side="left", padx=(12, 4))

        self.var_add_name = tk.StringVar()
        self.cmb_add_name = ttk.Combobox(self.add_item_frame,
                                         textvariable=self.var_add_name,
                                         width=16, state="readonly",
                                         font=FONT_ENTRY)
        self.cmb_add_name.pack(side="left", padx=4)
        self.cmb_add_name.bind("<<ComboboxSelected>>", self._on_edit_name_selected)

        self.var_add_size = tk.StringVar()
        self.cmb_add_size = ttk.Combobox(self.add_item_frame,
                                         textvariable=self.var_add_size,
                                         width=7, state="readonly",
                                         font=FONT_ENTRY)
        self.cmb_add_size.pack(side="left", padx=4)

        _label(self.add_item_frame, "Qty:").pack(side="left", padx=(8, 2))
        self.var_add_qty = tk.StringVar(value="1")
        tk.Spinbox(self.add_item_frame, from_=1, to=9999,
                   textvariable=self.var_add_qty,
                   width=5, font=FONT_ENTRY,
                   bg="#F0EBE3", relief="flat").pack(side="left", padx=4)

        _btn(self.add_item_frame, "＋ Add", self._add_item_to_bill,
             width=8).pack(side="left", padx=8)
        _btn(self.add_item_frame, "✕ Remove Row", self._remove_item_from_bill,
             color=DANGER, width=12).pack(side="left", padx=4)

        # ── Bottom: total + action buttons ──
        bottom = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                          highlightbackground=BORDER)
        bottom.pack(fill="x", ipadx=12, ipady=10)

        total_row = tk.Frame(bottom, bg=PANEL)
        total_row.pack(fill="x", padx=12)
        _label(total_row, "TOTAL").pack(side="left")
        self.lbl_total = tk.Label(total_row, text="—",
                                  font=FONT_TOTAL, fg=ACCENT, bg=PANEL)
        self.lbl_total.pack(side="right")

        tk.Frame(bottom, bg=BORDER, height=1).pack(fill="x", padx=12, pady=8)

        btn_row = tk.Frame(bottom, bg=PANEL)
        btn_row.pack(fill="x", padx=12)

        _btn(btn_row, "🗑  Delete Bill", self._delete_bill,
             color=DANGER, width=14).pack(side="left")

        self.btn_edit = _btn(btn_row, "✎  Edit Bill", self._toggle_edit, width=13)
        self.btn_edit.pack(side="right", padx=(6, 0))

        self.btn_save_edit = _btn(btn_row, "💾  Save Changes",
                                  self._save_edits, width=15)
        self.btn_save_edit.pack(side="right", padx=(6, 0))
        self.btn_save_edit.pack_forget()  # hidden until edit mode

        _btn(btn_row, "📄  Export PDF", self._export_pdf,
             color="#5A5550", width=14).pack(side="right", padx=(0, 6))

    # ── Data helpers ──────────────────────────────────────────────────── #

    def refresh_bills(self, bills=None):
        """Reload the bills list."""
        self.bills_tree.delete(*self.bills_tree.get_children())
        if bills is None:
            bills = self.bill_service.get_all_bills()
        for i, bill in enumerate(bills):
            tag = "even" if i % 2 == 0 else "odd"
            # Fetch total by loading full bill
            full = self.bill_service.get_bill_by_id(bill.id)
            total = full.total if full else 0
            self.bills_tree.insert("", "end", iid=str(bill.id),
                                   values=(bill.id, bill.customer_name,
                                           bill.date, f"LKR {total:,.2f}"),
                                   tags=(tag,))
        self.lbl_count.config(text=f"{len(bills)} bill(s)")

    def _refresh_items_tree(self):
        """Reload line items for the currently selected bill."""
        self.items_tree.delete(*self.items_tree.get_children())
        if not self._selected_bill:
            return
        for i, bi in enumerate(self._selected_bill.items):
            tag = "even" if i % 2 == 0 else "odd"
            self.items_tree.insert("", "end",
                                   values=(i + 1, bi.item_name, bi.size,
                                           bi.quantity,
                                           f"{bi.unit_price:,.2f}",
                                           f"{bi.subtotal:,.2f}"),
                                   tags=(tag,))
        self.lbl_total.config(
            text=f"LKR {self._selected_bill.total:,.2f}")

    def _load_bill(self, bill_id: int):
        """Load a full bill and display it in the detail panel."""
        self._selected_bill = self.bill_service.get_bill_by_id(bill_id)
        if not self._selected_bill:
            return
        self.lbl_bill_id.config(text=f"#{self._selected_bill.id}")
        self.lbl_bill_date.config(text=self._selected_bill.date)
        self.var_customer.set(self._selected_bill.customer_name)
        self._refresh_items_tree()

    def _on_bill_select(self, _=None):
        sel = self.bills_tree.selection()
        if not sel:
            return
        bill_id = int(sel[0])
        if self._edit_mode:
            self._cancel_edit()
        self._load_bill(bill_id)

    def _on_search(self):
        kw = self.var_search.get().strip()
        if kw:
            self.refresh_bills(self.bill_service.search_bills_by_customer(kw))
        else:
            self.refresh_bills()

    # ── Edit mode ─────────────────────────────────────────────────────── #

    def _toggle_edit(self):
        if not self._selected_bill:
            messagebox.showwarning("No Bill Selected", "Select a bill to edit.")
            return
        self._edit_mode = True
        self.ent_customer.config(state="normal")
        self.btn_edit.pack_forget()
        self.btn_save_edit.pack(side="right", padx=(6, 0))
        self.add_item_frame.pack(fill="x", padx=8, pady=(0, 8))
        # Populate item dropdowns
        names = self.price_service.get_unique_item_names()
        self.cmb_add_name["values"] = names

    def _cancel_edit(self):
        self._edit_mode = False
        self.ent_customer.config(state="disabled")
        self.btn_save_edit.pack_forget()
        self.btn_edit.pack(side="right", padx=(6, 0))
        self.add_item_frame.pack_forget()
        # Reload original bill data
        if self._selected_bill:
            self._load_bill(self._selected_bill.id)

    def _on_edit_name_selected(self, _=None):
        name = self.var_add_name.get()
        variants = self.price_service.get_items_by_name(name)
        self.cmb_add_size["values"] = [v.size for v in variants]
        self.var_add_size.set(variants[0].size if variants else "")

    def _add_item_to_bill(self):
        name = self.var_add_name.get()
        size = self.var_add_size.get()
        if not name or not size:
            messagebox.showwarning("Incomplete", "Select an item and size.")
            return
        try:
            qty = int(self.var_add_qty.get())
            if qty < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Qty", "Quantity must be a whole number ≥ 1.")
            return

        variants = self.price_service.get_items_by_name(name)
        item = next((v for v in variants if v.size == size), None)
        if not item:
            messagebox.showerror("Not Found", "Item not found.")
            return

        new_bi = BillItem(item_id=item.id, item_name=item.name,
                          size=item.size, quantity=qty,
                          unit_price=item.price)
        self._selected_bill.add_item(new_bi)
        self._refresh_items_tree()

    def _remove_item_from_bill(self):
        sel = self.items_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a row to remove.")
            return
        idx = self.items_tree.index(sel[0])
        self._selected_bill.remove_item(idx)
        self._refresh_items_tree()

    def _save_edits(self):
        """
        Save edits: delete the old bill and re-insert with the same ID approach.
        Since SQLite doesn't support partial updates easily for related rows,
        we delete and re-save, then fix the ID back.
        """
        if not self._selected_bill:
            return
        customer = self.var_customer.get().strip()
        if not customer:
            messagebox.showwarning("Customer Required", "Customer name cannot be empty.")
            return
        if not self._selected_bill.items:
            messagebox.showwarning("Empty Bill", "A bill must have at least one item.")
            return

        old_id = self._selected_bill.id
        self._selected_bill.customer_name = customer

        try:
            # Delete old bill (CASCADE removes bill_items too)
            self.bill_service.delete_bill(old_id)
            # Re-save — this gets a new auto-increment ID
            saved = self.bill_service.save_bill(self._selected_bill)
            self._selected_bill = saved
            messagebox.showinfo("Saved", f"Bill updated successfully (now Bill #{saved.id}).")
        except Exception as e:
            messagebox.showerror("Save Failed", str(e))
            return

        self._cancel_edit()
        self.refresh_bills()
        # Re-select the updated bill
        try:
            self.bills_tree.selection_set(str(saved.id))
            self._load_bill(saved.id)
        except Exception:
            pass

    # ── Actions ───────────────────────────────────────────────────────── #

    def _delete_bill(self):
        if not self._selected_bill:
            messagebox.showwarning("No Bill Selected", "Select a bill to delete.")
            return
        if not messagebox.askyesno(
                "Confirm Delete",
                f"Delete Bill #{self._selected_bill.id} "
                f"for {self._selected_bill.customer_name}?\nThis cannot be undone."):
            return
        self.bill_service.delete_bill(self._selected_bill.id)
        self._selected_bill = None
        self._edit_mode = False
        self.lbl_bill_id.config(text="—")
        self.lbl_bill_date.config(text="—")
        self.var_customer.set("")
        self.items_tree.delete(*self.items_tree.get_children())
        self.lbl_total.config(text="—")
        self.refresh_bills()

    def _export_pdf(self):
        if not self._selected_bill:
            messagebox.showwarning("No Bill Selected", "Select a bill to export.")
            return
        output_dir = filedialog.askdirectory(title="Select folder to save PDF")
        if not output_dir:
            return
        try:
            path = export_bill_to_pdf(self._selected_bill, output_dir=output_dir)
            if messagebox.askyesno("PDF Exported",
                                   f"Invoice saved to:\n{path}\n\nOpen the file now?"):
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("Export Failed", str(e))

    def on_tab_focus(self):
        """Call this when the tab becomes active to refresh the bill list."""
        self.refresh_bills()


# ── Standalone test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Bill History — Test")
    root.geometry("980x660")
    root.configure(bg=BG)
    db = DatabaseManager()
    HistoryFrame(root, db).pack(fill="both", expand=True)
    root.mainloop()
    db.close()