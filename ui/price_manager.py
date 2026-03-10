import tkinter as tk
from tkinter import ttk, messagebox
from database.db_manager import DatabaseManager
from services.price_service import PriceService


# ── Palette ────────────────────────────────────────────────────────────────
BG        = "#F7F3EE"        # warm off-white canvas
PANEL     = "#FFFFFF"        # card background
ACCENT    = "#2C5F2E"        # deep forest green  (primary action)
ACCENT_HV = "#1E4220"        # hover / pressed
DANGER    = "#B94040"        # delete / error
BORDER    = "#D9D0C5"        # subtle border
TXT_DARK  = "#1A1A1A"
TXT_MID   = "#5A5550"
TXT_LIGHT = "#9A948E"

FONT_HEAD  = ("Georgia", 15, "bold")
FONT_SUB   = ("Georgia", 10, "italic")
FONT_LABEL = ("Helvetica", 9, "bold")
FONT_ENTRY = ("Helvetica", 10)
FONT_BTN   = ("Helvetica", 9, "bold")
FONT_TABLE = ("Helvetica", 9)


def _btn(parent, text, command, color=ACCENT, fg="white", width=14):
    """Reusable flat button."""
    b = tk.Button(parent, text=text, command=command,
                  bg=color, fg=fg, relief="flat",
                  font=FONT_BTN, cursor="hand2",
                  padx=10, pady=6, width=width)
    b.bind("<Enter>", lambda e: b.config(bg=ACCENT_HV if color == ACCENT else "#8A2020"))
    b.bind("<Leave>", lambda e: b.config(bg=color))
    return b


def _label(parent, text, font=FONT_LABEL, fg=TXT_MID, **kw):
    return tk.Label(parent, text=text, font=font, fg=fg, bg=PANEL, **kw)


def _entry(parent, textvariable, width=24):
    e = tk.Entry(parent, textvariable=textvariable, width=width,
                 font=FONT_ENTRY, relief="flat",
                 bg="#F0EBE3", fg=TXT_DARK,
                 insertbackground=TXT_DARK,
                 highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=ACCENT)
    return e


class PriceManagerFrame(tk.Frame):
    """
    Screen for managing item prices.
    Allows adding, editing, and deleting items with size-based pricing.
    """

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG)
        self.db = db
        self.service = PriceService(db)
        self._selected_id = None

        self._build_header()
        self._build_body()
        self.refresh_table()

    # ── Layout ────────────────────────────────────────────────────────── #

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Price Manager",
                 font=FONT_HEAD, fg="white", bg=ACCENT).pack(side="left", padx=22)
        tk.Label(hdr, text="Add & maintain item prices by size",
                 font=FONT_SUB, fg="#A8C8AA", bg=ACCENT).pack(side="left", padx=4)

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Left: form card
        card = tk.Frame(body, bg=PANEL, bd=0,
                        highlightthickness=1, highlightbackground=BORDER)
        card.pack(side="left", fill="y", padx=(0, 16), pady=0, ipadx=16, ipady=16)
        self._build_form(card)

        # Right: table card
        tbl_card = tk.Frame(body, bg=PANEL, bd=0,
                            highlightthickness=1, highlightbackground=BORDER)
        tbl_card.pack(side="left", fill="both", expand=True, ipady=8)
        self._build_table(tbl_card)

    def _build_form(self, parent):
        tk.Label(parent, text="ITEM DETAILS", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).grid(row=0, column=0, columnspan=2,
                                               sticky="w", pady=(8, 12))

        self.var_name  = tk.StringVar()
        self.var_size  = tk.StringVar()
        self.var_price = tk.StringVar()

        fields = [
            ("Item Name",  self.var_name),
            ("Size",       self.var_size),
            ("Price (LKR)", self.var_price),
        ]
        for i, (label, var) in enumerate(fields, start=1):
            _label(parent, label).grid(row=i*2-1, column=0, columnspan=2,
                                       sticky="w", pady=(6, 1))
            _entry(parent, var).grid(row=i*2, column=0, columnspan=2,
                                     sticky="ew", pady=(0, 2))

        # Size shortcut buttons
        _label(parent, "Quick Sizes").grid(row=7, column=0, columnspan=2,
                                           sticky="w", pady=(10, 4))
        qs = tk.Frame(parent, bg=PANEL)
        qs.grid(row=8, column=0, columnspan=2, sticky="w")
        for size in ["XS", "S", "M", "L", "XL", "2XL","3XL"]:
            tk.Button(qs, text=size, font=("Helvetica", 8),
                      bg="#EDE8E0", fg=TXT_DARK, relief="flat",
                      cursor="hand2", padx=6, pady=3,
                      command=lambda s=size: self.var_size.set(s)
                      ).pack(side="left", padx=2)
        # No-size option for items that do not vary by size
        tk.Button(qs, text="N/A", font=("Helvetica", 8),
                  bg="#D9D0C5", fg=TXT_MID, relief="flat",
                  cursor="hand2", padx=6, pady=3,
                  command=lambda: self.var_size.set("N/A")
                  ).pack(side="left", padx=(6, 2))

        # Separator
        tk.Frame(parent, bg=BORDER, height=1).grid(
            row=9, column=0, columnspan=2, sticky="ew", pady=14)

        # Action buttons
        btn_frame = tk.Frame(parent, bg=PANEL)
        btn_frame.grid(row=10, column=0, columnspan=2, sticky="ew")
        _btn(btn_frame, "＋  Add Item",    self._add_item,    width=16).pack(fill="x", pady=3)
        _btn(btn_frame, "✎  Update",       self._update_item, width=16).pack(fill="x", pady=3)
        _btn(btn_frame, "✕  Delete",       self._delete_item,
             color=DANGER, width=16).pack(fill="x", pady=3)
        _btn(btn_frame, "↺  Clear Form",   self._clear_form,
             color="#8A8480", width=16).pack(fill="x", pady=(10, 3))

        parent.columnconfigure(0, weight=1)

    def _build_table(self, parent):
        # Search bar
        search_bar = tk.Frame(parent, bg=PANEL)
        search_bar.pack(fill="x", padx=12, pady=(12, 6))
        _label(search_bar, "🔍  Search:", fg=TXT_MID).pack(side="left")
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *_: self._on_search())
        se = _entry(search_bar, self.var_search, width=28)
        se.pack(side="left", padx=8)

        # Treeview
        cols = ("ID", "Item Name", "Size", "Price (LKR)")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings",
                                 selectmode="browse", height=18)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=TXT_DARK, font=FONT_TABLE, rowheight=26)
        style.configure("Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Helvetica", 9, "bold"), relief="flat")
        style.map("Treeview", background=[("selected", "#D4E8D4")])
        style.map("Treeview.Heading", background=[("active", ACCENT_HV)])

        widths = {"ID": 40, "Item Name": 200, "Size": 70, "Price (LKR)": 110}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=widths[col],
                             anchor="center" if col in ("ID", "Size", "Price (LKR)") else "w")

        self.tree.tag_configure("odd",  background="#F7F3EE")
        self.tree.tag_configure("even", background=PANEL)

        vsb = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(12, 0), pady=(0, 12))
        vsb.pack(side="left", fill="y", pady=(0, 12), padx=(0, 8))

        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        # Footer count label
        self.lbl_count = tk.Label(parent, text="", font=("Helvetica", 8),
                                  fg=TXT_LIGHT, bg=PANEL)
        self.lbl_count.pack(anchor="e", padx=14, pady=(0, 6))

    # ── Data helpers ──────────────────────────────────────────────────── #

    def refresh_table(self, items=None):
        self.tree.delete(*self.tree.get_children())
        if items is None:
            items = self.service.get_all_items()
        for i, item in enumerate(items):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(item.id),
                             values=(item.id, item.name, item.size,
                                     f"{item.price:,.2f}"),
                             tags=(tag,))
        self.lbl_count.config(text=f"{len(items)} record(s)")

    def _on_search(self):
        kw = self.var_search.get().strip()
        if kw:
            self.refresh_table(self.service.search_items(kw))
        else:
            self.refresh_table()

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel[0], "values")
        self._selected_id = int(values[0])
        self.var_name.set(values[1])
        self.var_size.set(values[2])
        self.var_price.set(values[3].replace(",", ""))

    def _sort_by(self, col):
        rows = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            rows.sort(key=lambda t: float(t[0].replace(",", "")))
        except ValueError:
            rows.sort()
        for i, (_, k) in enumerate(rows):
            self.tree.move(k, "", i)

    # ── Actions ───────────────────────────────────────────────────────── #

    def _get_inputs(self):
        name  = self.var_name.get().strip()
        size  = self.var_size.get().strip()
        price = self.var_price.get().strip()
        if not name or not size or not price:
            messagebox.showwarning("Missing Fields", "Please fill in all fields.")
            return None, None, None
        try:
            price = float(price)
        except ValueError:
            messagebox.showerror("Invalid Price", "Price must be a number.")
            return None, None, None
        return name, size, price

    def _add_item(self):
        name, size, price = self._get_inputs()
        if name is None:
            return
        try:
            self.service.add_item(name, size, price)
            self._clear_form()
            self.refresh_table()
            messagebox.showinfo("Success", f"'{name} [{size}]' added successfully.")
        except ValueError as e:
            messagebox.showerror("Duplicate Entry", str(e))

    def _update_item(self):
        if not self._selected_id:
            messagebox.showwarning("No Selection", "Please select an item to update.")
            return
        name, size, price = self._get_inputs()
        if name is None:
            return
        try:
            self.service.update_item(self._selected_id, name, size, price)
            self._clear_form()
            self.refresh_table()
            messagebox.showinfo("Updated", "Item updated successfully.")
        except ValueError as e:
            messagebox.showerror("Update Failed", str(e))

    def _delete_item(self):
        if not self._selected_id:
            messagebox.showwarning("No Selection", "Please select an item to delete.")
            return
        name = self.var_name.get()
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete '{name}'? This cannot be undone."):
            return
        self.service.delete_item(self._selected_id)
        self._clear_form()
        self.refresh_table()

    def _clear_form(self):
        self.var_name.set("")
        self.var_size.set("")
        self.var_price.set("")
        self._selected_id = None
        self.tree.selection_remove(self.tree.selection())


# ── Standalone test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Price Manager — Test")
    root.geometry("860x580")
    root.configure(bg=BG)
    db = DatabaseManager()
    PriceManagerFrame(root, db).pack(fill="both", expand=True)
    root.mainloop()
    db.close()