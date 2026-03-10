import tkinter as tk
from tkinter import ttk, messagebox
from database.db_manager import DatabaseManager
from services.payment_service import PaymentService
from services.bill_service import BillService

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
ORANGE    = "#C26A00"   # overdue / balance warning

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


class AccountsFrame(tk.Frame):
    """
    Accounts screen.
    Shows per-customer totals (billed, paid, balance),
    lets you record payments and view payment history.
    """

    def __init__(self, parent, db: DatabaseManager):
        super().__init__(parent, bg=BG)
        self.db              = db
        self.payment_service = PaymentService(db)
        self.bill_service    = BillService(db)
        self._selected_customer: str | None = None

        self._build_header()
        self._build_body()
        self.refresh_summaries()

    # ── Layout ────────────────────────────────────────────────────────── #

    def _build_header(self):
        hdr = tk.Frame(self, bg=ACCENT, pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Accounts",
                 font=FONT_HEAD, fg="white", bg=ACCENT).pack(side="left", padx=22)
        tk.Label(hdr, text="Track customer balances and record payments",
                 font=FONT_SUB, fg="#A8C8AA", bg=ACCENT).pack(side="left", padx=4)

    def _build_body(self):
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        # Left: customer summary list
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="y", padx=(0, 14))
        self._build_summary_list(left)

        # Right: payment form + payment history
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self._build_balance_panel(right)
        self._build_payment_form(right)
        self._build_payment_history(right)

    def _build_summary_list(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="both", expand=True, ipadx=8, ipady=8)

        tk.Label(card, text="ALL CUSTOMERS", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=10, pady=(10, 6))

        # Search
        search_row = tk.Frame(card, bg=PANEL)
        search_row.pack(fill="x", padx=10, pady=(0, 8))
        _label(search_row, "🔍", fg=TXT_MID).pack(side="left")
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *_: self._on_search())
        _entry(search_row, self.var_search, width=18).pack(side="left", padx=4)

        # Summary treeview
        cols = ("Customer", "Billed", "Paid", "Balance")
        self.summary_tree = ttk.Treeview(card, columns=cols,
                                         show="headings", height=20,
                                         selectmode="browse")

        style = ttk.Style()
        style.configure("Acct.Treeview",
                        background=PANEL, fieldbackground=PANEL,
                        foreground=TXT_DARK, font=FONT_TABLE, rowheight=28)
        style.configure("Acct.Treeview.Heading",
                        background=ACCENT, foreground="white",
                        font=("Helvetica", 9, "bold"), relief="flat")
        style.map("Acct.Treeview", background=[("selected", "#D4E8D4")])
        self.summary_tree.configure(style="Acct.Treeview")

        widths = {"Customer": 150, "Billed": 95, "Paid": 95, "Balance": 95}
        for col in cols:
            self.summary_tree.heading(col, text=col)
            self.summary_tree.column(col, width=widths[col],
                                     anchor="w" if col == "Customer" else "e")

        # Colour tags
        self.summary_tree.tag_configure("settled",  foreground="#2C5F2E")  # paid off
        self.summary_tree.tag_configure("owing",    foreground=ORANGE)      # balance > 0
        self.summary_tree.tag_configure("overpaid", foreground=DANGER)      # negative balance

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=vsb.set)
        self.summary_tree.pack(side="left", fill="both", expand=True,
                               padx=(10, 0), pady=(0, 10))
        vsb.pack(side="left", fill="y", pady=(0, 10), padx=(0, 6))
        self.summary_tree.bind("<<TreeviewSelect>>", self._on_customer_select)

    def _build_balance_panel(self, parent):
        """Large balance display for the selected customer."""
        self.balance_card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                                     highlightbackground=BORDER)
        self.balance_card.pack(fill="x", ipadx=16, ipady=12, pady=(0, 10))

        tk.Label(self.balance_card, text="SELECTED CUSTOMER",
                 font=("Helvetica", 8, "bold"), fg=TXT_LIGHT, bg=PANEL
                 ).grid(row=0, column=0, columnspan=6, sticky="w",
                        padx=14, pady=(10, 10))

        # Three summary boxes
        def _stat(parent, label, row, col, var):
            f = tk.Frame(parent, bg="#F7F3EE",
                         highlightthickness=1, highlightbackground=BORDER)
            f.grid(row=row, column=col, padx=10, pady=(0, 12), ipadx=12, ipady=8)
            tk.Label(f, text=label, font=("Helvetica", 8, "bold"),
                     fg=TXT_LIGHT, bg="#F7F3EE").pack()
            tk.Label(f, textvariable=var, font=("Georgia", 12, "bold"),
                     fg=TXT_DARK, bg="#F7F3EE").pack()

        self.var_cust_name    = tk.StringVar(value="—")
        self.var_total_billed = tk.StringVar(value="LKR 0.00")
        self.var_total_paid   = tk.StringVar(value="LKR 0.00")
        self.var_balance      = tk.StringVar(value="LKR 0.00")

        tk.Label(self.balance_card, textvariable=self.var_cust_name,
                 font=("Georgia", 13, "bold"), fg=ACCENT, bg=PANEL
                 ).grid(row=1, column=0, padx=14, sticky="w")

        _stat(self.balance_card, "Total Billed", 1, 1, self.var_total_billed)
        _stat(self.balance_card, "Total Paid",   1, 2, self.var_total_paid)

        # Balance box — larger and coloured
        bal_frame = tk.Frame(self.balance_card, bg=ACCENT,
                             highlightthickness=0)
        bal_frame.grid(row=1, column=3, padx=10, pady=(0, 12), ipadx=16, ipady=8)
        tk.Label(bal_frame, text="Balance Due", font=("Helvetica", 8, "bold"),
                 fg="#A8C8AA", bg=ACCENT).pack()
        self.lbl_balance = tk.Label(bal_frame, textvariable=self.var_balance,
                                    font=("Georgia", 14, "bold"),
                                    fg="white", bg=ACCENT)
        self.lbl_balance.pack()

        self.balance_card.columnconfigure(0, weight=1)

    def _build_payment_form(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="x", ipadx=12, ipady=10, pady=(0, 10))

        tk.Label(card, text="RECORD PAYMENT", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).grid(row=0, column=0, columnspan=6,
                                               sticky="w", padx=12, pady=(10, 8))

        # Customer name (auto-filled from selection, but editable)
        _label(card, "Customer").grid(row=1, column=0, sticky="w", padx=12)
        self.var_pay_customer = tk.StringVar()
        _entry(card, self.var_pay_customer, width=20
               ).grid(row=1, column=1, padx=6, pady=4)

        # Amount
        _label(card, "Amount (LKR)").grid(row=1, column=2, sticky="w", padx=8)
        self.var_pay_amount = tk.StringVar()
        _entry(card, self.var_pay_amount, width=12
               ).grid(row=1, column=3, padx=6)

        # Note
        _label(card, "Note (optional)").grid(row=1, column=4, sticky="w", padx=8)
        self.var_pay_note = tk.StringVar()
        _entry(card, self.var_pay_note, width=16
               ).grid(row=1, column=5, padx=(6, 12))

        _btn(card, "＋  Add Payment", self._add_payment, width=16
             ).grid(row=2, column=0, columnspan=6, padx=12, pady=(6, 10), sticky="w")

    def _build_payment_history(self, parent):
        card = tk.Frame(parent, bg=PANEL, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="both", expand=True)

        tk.Label(card, text="PAYMENT HISTORY", font=("Helvetica", 8, "bold"),
                 fg=TXT_LIGHT, bg=PANEL).pack(anchor="w", padx=12, pady=(10, 6))

        cols = ("ID", "Customer", "Amount", "Date", "Note")
        self.pay_tree = ttk.Treeview(card, columns=cols,
                                     show="headings", height=8,
                                     selectmode="browse")
        self.pay_tree.configure(style="Acct.Treeview")

        widths = {"ID": 40, "Customer": 160, "Amount": 110,
                  "Date": 130, "Note": 180}
        for col in cols:
            self.pay_tree.heading(col, text=col)
            self.pay_tree.column(col, width=widths[col],
                                 anchor="w" if col in ("Customer", "Note") else "center")

        self.pay_tree.tag_configure("odd",  background="#F7F3EE")
        self.pay_tree.tag_configure("even", background=PANEL)

        vsb = ttk.Scrollbar(card, orient="vertical", command=self.pay_tree.yview)
        self.pay_tree.configure(yscrollcommand=vsb.set)
        self.pay_tree.pack(side="left", fill="both", expand=True,
                           padx=(12, 0), pady=(0, 8))
        vsb.pack(side="left", fill="y", pady=(0, 8), padx=(0, 8))

        # Delete payment button
        _btn(card, "🗑  Delete Payment", self._delete_payment,
             color=DANGER, width=18).pack(anchor="w", padx=12, pady=(0, 10))

    # ── Data helpers ──────────────────────────────────────────────────── #

    def refresh_summaries(self, summaries=None):
        """Reload the customer summary list."""
        self.summary_tree.delete(*self.summary_tree.get_children())
        if summaries is None:
            summaries = self.payment_service.get_all_customer_summaries()
        for s in summaries:
            if s.balance_due > 0.005:
                tag = "owing"
            elif s.balance_due < -0.005:
                tag = "overpaid"
            else:
                tag = "settled"
            self.summary_tree.insert(
                "", "end", iid=s.customer_name,
                values=(s.customer_name,
                        f"LKR {s.total_billed:,.2f}",
                        f"LKR {s.total_paid:,.2f}",
                        f"LKR {s.balance_due:,.2f}"),
                tags=(tag,)
            )

    def _refresh_payment_history(self, customer_name: str = None):
        """Reload payment history — filtered by customer if given."""
        self.pay_tree.delete(*self.pay_tree.get_children())
        if customer_name:
            payments = self.payment_service.get_payments_by_customer(customer_name)
        else:
            payments = self.payment_service.get_all_payments()
        for i, p in enumerate(payments):
            tag = "even" if i % 2 == 0 else "odd"
            self.pay_tree.insert("", "end", iid=str(p.id),
                                 values=(p.id, p.customer_name,
                                         f"LKR {p.amount:,.2f}",
                                         p.date, p.note),
                                 tags=(tag,))

    def _update_balance_panel(self, customer_name: str):
        """Refresh the balance summary boxes for the selected customer."""
        s = self.payment_service.get_customer_summary(customer_name)
        self.var_cust_name.set(customer_name)
        self.var_total_billed.set(f"LKR {s.total_billed:,.2f}")
        self.var_total_paid.set(f"LKR {s.total_paid:,.2f}")
        self.var_balance.set(f"LKR {s.balance_due:,.2f}")

        # Colour the balance box
        if s.balance_due > 0.005:
            self.balance_card.config(highlightbackground=ORANGE)
        elif s.balance_due < -0.005:
            self.balance_card.config(highlightbackground=DANGER)
        else:
            self.balance_card.config(highlightbackground=ACCENT)

    def _on_customer_select(self, _=None):
        sel = self.summary_tree.selection()
        if not sel:
            return
        self._selected_customer = sel[0]   # iid is customer_name
        self._update_balance_panel(self._selected_customer)
        self._refresh_payment_history(self._selected_customer)
        self.var_pay_customer.set(self._selected_customer)

    def _on_search(self):
        kw = self.var_search.get().strip().lower()
        if not kw:
            self.refresh_summaries()
            return
        all_summaries = self.payment_service.get_all_customer_summaries()
        filtered = [s for s in all_summaries if kw in s.customer_name.lower()]
        self.refresh_summaries(filtered)

    # ── Actions ───────────────────────────────────────────────────────── #

    def _add_payment(self):
        customer = self.var_pay_customer.get().strip()
        note     = self.var_pay_note.get().strip()

        if not customer:
            messagebox.showwarning("Missing Customer",
                                   "Please enter or select a customer name.")
            return
        try:
            amount = float(self.var_pay_amount.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Amount",
                                 "Please enter a valid number for the amount.")
            return

        try:
            self.payment_service.add_payment(customer, amount, note=note)
        except ValueError as e:
            messagebox.showerror("Invalid Payment", str(e))
            return

        # Clear form fields
        self.var_pay_amount.set("")
        self.var_pay_note.set("")

        # Refresh all relevant panels
        self.refresh_summaries()
        self._update_balance_panel(customer)
        self._refresh_payment_history(customer)

        # Re-select the customer in the list
        try:
            self.summary_tree.selection_set(customer)
        except Exception:
            pass

        messagebox.showinfo("Payment Recorded",
                            f"Payment of LKR {amount:,.2f} recorded for {customer}.")

    def _delete_payment(self):
        sel = self.pay_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Select a payment row to delete.")
            return
        payment_id = int(sel[0])
        if not messagebox.askyesno("Confirm Delete",
                                   "Delete this payment record? This cannot be undone."):
            return
        self.payment_service.delete_payment(payment_id)
        self.refresh_summaries()
        if self._selected_customer:
            self._update_balance_panel(self._selected_customer)
            self._refresh_payment_history(self._selected_customer)

    def on_tab_focus(self):
        """Call this when the tab becomes active."""
        self.refresh_summaries()
        if self._selected_customer:
            self._update_balance_panel(self._selected_customer)
            self._refresh_payment_history(self._selected_customer)


# ── Standalone test ────────────────────────────────────────────────────── #
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Accounts — Test")
    root.geometry("1000x680")
    root.configure(bg=BG)
    db = DatabaseManager()
    AccountsFrame(root, db).pack(fill="both", expand=True)
    root.mainloop()
    db.close()