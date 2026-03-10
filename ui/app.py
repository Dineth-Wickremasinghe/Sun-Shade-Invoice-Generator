import tkinter as tk
from tkinter import ttk
from database.db_manager import DatabaseManager
from ui.price_manager import PriceManagerFrame
from ui.billing import BillingFrame
from ui.history import HistoryFrame
from ui.accounts import AccountsFrame
from config_loader import load_company_config

BG     = "#F7F3EE"
ACCENT = "#2C5F2E"
PANEL  = "#FFFFFF"
BORDER = "#D9D0C5"


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.company = load_company_config()
        self.title(f"{self.company['name']} — {self.company['tagline']}")
        self.geometry("980x700")
        self.minsize(820, 560)
        self.configure(bg=BG)

        try:
            self.iconbitmap("assets/icon.ico")
        except Exception:
            pass

        self.db = DatabaseManager()
        self._build_titlebar()
        self._build_tabs()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=ACCENT, height=48)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"🧵  {self.company['name']}",
                 font=("Georgia", 14, "bold"),
                 fg="white", bg=ACCENT).pack(side="left", padx=20)
        tk.Label(bar, text=self.company["tagline"],
                 font=("Georgia", 9, "italic"),
                 fg="#A8C8AA", bg=ACCENT).pack(side="left")

    def _build_tabs(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("App.TNotebook",
                        background=BG, borderwidth=0, tabmargins=[0, 0, 0, 0])
        style.configure("App.TNotebook.Tab",
                        background="#D9D0C5", foreground="#5A5550",
                        font=("Helvetica", 9, "bold"), padding=[18, 8])
        style.map("App.TNotebook.Tab",
                  background=[("selected", ACCENT), ("active", "#3A7A3C")],
                  foreground=[("selected", "white"), ("active", "white")])

        self.notebook = ttk.Notebook(self, style="App.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.price_frame   = PriceManagerFrame(self.notebook, self.db)
        self.notebook.add(self.price_frame,   text="  📋  Price Manager  ")

        self.billing_frame = BillingFrame(self.notebook, self.db)
        self.notebook.add(self.billing_frame, text="  🧾  Billing  ")

        self.history_frame = HistoryFrame(self.notebook, self.db)
        self.notebook.add(self.history_frame, text="  🗂  Bill History  ")

        self.accounts_frame = AccountsFrame(self.notebook, self.db)
        self.notebook.add(self.accounts_frame, text="  💰  Accounts  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        selected = self.notebook.index(self.notebook.select())
        if selected == 1:
            self.billing_frame.on_tab_focus()
        elif selected == 2:
            self.history_frame.on_tab_focus()
        elif selected == 3:
            self.accounts_frame.on_tab_focus()

    def _on_close(self):
        self.db.close()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()