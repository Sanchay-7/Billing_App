import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import pandas as pd
import os

class LedgerView:
    def __init__(self, window):
        self.window = window
        self.window.title("Transaction Ledger")
        self.window.geometry("1200x800")
        self.window.configure(bg="#f5f5f5")
        
        # Set theme
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", 
                        background="#f0f0f0",
                        foreground="black",
                        rowheight=25,
                        fieldbackground="#f0f0f0")
        style.configure("Treeview.Heading", 
                        background="#4a7abc", 
                        foreground="white", 
                        relief="flat", 
                        font=('Arial', 10, 'bold'))
        style.map("Treeview", background=[("selected", "#4a7abc")])

        # Filter variables
        self.type_filter = tk.StringVar(value="All")
        
        # Build UI
        self.create_widgets()

        # Status bar (must exist before loading data)
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.window, textvariable=self.status_var,
                                    relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_status("Ready")

        # Initial load (no filters)
        self.load_ledger()

    def create_widgets(self):
        main = ttk.Frame(self.window)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        ttk.Label(main, text="Transaction Ledger", font=("Arial", 16, "bold"))\
            .pack(pady=(0,20))

        # Filter frame
        filt = ttk.LabelFrame(main, text="Filter Options")
        filt.pack(fill=tk.X, pady=(0,10))
        df = ttk.Frame(filt)
        df.pack(fill=tk.X, padx=10, pady=10)

        # Date from
        ttk.Label(df, text="From (YYYY-MM-DD):").grid(row=0, column=0, padx=(0,5))
        self.start_date_var = tk.StringVar()
        ttk.Entry(df, width=12, textvariable=self.start_date_var).grid(row=0, column=1, padx=5)

        # Date to
        ttk.Label(df, text="To (YYYY-MM-DD):").grid(row=0, column=2, padx=(10,5))
        self.end_date_var = tk.StringVar()
        ttk.Entry(df, width=12, textvariable=self.end_date_var).grid(row=0, column=3, padx=5)

        # Type
        ttk.Label(df, text="Type:").grid(row=0, column=4, padx=(10,5))
        self.type_combo = ttk.Combobox(df, textvariable=self.type_filter,
                                       values=["All","Purchase","Sale"], width=10)
        self.type_combo.grid(row=0, column=5, padx=5)
        self.type_combo.current(0)

        # Buttons
        btns = ttk.Frame(df)
        btns.grid(row=0, column=6, padx=(20,0))
        ttk.Button(btns, text="Apply Filter",   command=self.apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Reset",          command=self.reset_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Export to Excel",command=self.export_to_excel).pack(side=tk.LEFT, padx=5)

        # Treeview
        treef = ttk.Frame(main)
        treef.pack(fill=tk.BOTH, expand=True)
        cols  = ("ID","Date","Type","Item","Qty","Price","Total")
        widths = [50,150,100,300,80,100,120]
        self.tree = ttk.Treeview(treef, columns=cols, show="headings")
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col, command=lambda _c=col: self.sort_treeview(_c))
            self.tree.column(col, width=w, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(treef, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(treef, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind("<Double-1>", self.on_item_double_click)

    def load_ledger(self, start_date=None, end_date=None, transaction_type=None):
        # Treat empty strings as None
        if start_date == "": start_date = None
        if end_date   == "": end_date   = None

        # Clear existing rows
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        try:
            conn = sqlite3.connect('db/billing.db')
            c    = conn.cursor()

            query  = "SELECT id, date, type, item_name, quantity, price FROM ledger"
            params = []
            conds  = []

            if start_date:
                conds.append("date(date) >= date(?)")
                params.append(start_date)
            if end_date:
                conds.append("date(date) <= date(?)")
                params.append(end_date)
            if transaction_type and transaction_type != "All":
                conds.append("type = ?")
                params.append(transaction_type)

            if conds:
                query += " WHERE " + " AND ".join(conds)
            query += " ORDER BY date DESC"

            c.execute(query, params)
            rows = c.fetchall()
            conn.close()

            for row in rows:
                id_, date_, typ, item, qty, price = row

                # Guard against NULL in DB
                qty   = qty   if qty   is not None else 0
                price = price if price is not None else 0.0
                total = qty * price

                self.tree.insert("", "end", values=(
                    id_, date_, typ, item, qty,
                    f"₹{price:.2f}", f"₹{total:.2f}"
                ))

            self.update_status(f"Showing {len(rows)} transactions")

        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error: {e}")
            self.update_status("Error loading data")

    def apply_filter(self):
        sd = self.start_date_var.get()
        ed = self.end_date_var.get()

        # Validate
        if sd:
            try: datetime.strptime(sd, '%Y-%m-%d')
            except ValueError:
                messagebox.showwarning("Invalid Date", "From must be YYYY-MM-DD")
                return
        if ed:
            try: datetime.strptime(ed, '%Y-%m-%d')
            except ValueError:
                messagebox.showwarning("Invalid Date", "To must be YYYY-MM-DD")
                return
        if sd and ed and sd > ed:
            messagebox.showwarning("Invalid Range", "From date ≤ To date")
            return

        t = self.type_filter.get()
        self.load_ledger(sd, ed, t)
        self.update_status(f"Filtered: {sd or '–'} → {ed or '–'}, Type={t}")

    def reset_filter(self):
        # Clear date fields and reset type
        self.start_date_var.set("")
        self.end_date_var.set("")
        self.type_combo.current(0)

        # Reload all data
        self.load_ledger(start_date=None, end_date=None, transaction_type="All")
        self.update_status("Filters reset – showing all transactions")

    def on_item_double_click(self, _event):
        sel = self.tree.selection()
        if not sel: return
        tid = self.tree.item(sel[0])['values'][0]
        self.show_transaction_details(tid)

    def show_transaction_details(self, transaction_id):
        win = tk.Toplevel(self.window)
        win.title(f"Transaction #{transaction_id}")
        win.geometry("600x400")
        win.grab_set()

        try:
            conn = sqlite3.connect('db/billing.db')
            c    = conn.cursor()
            c.execute("SELECT * FROM ledger WHERE id = ?", (transaction_id,))
            txn = c.fetchone()
            conn.close()

            if not txn:
                ttk.Label(win, text="Not found").pack(pady=20)
                return

            cols = ["ID","Date","Type","Item Name","Quantity","Price","Notes"]
            frm  = ttk.Frame(win, padding=20)
            frm.pack(fill=tk.BOTH, expand=True)

            for i, (col, val) in enumerate(zip(cols, txn)):
                ttk.Label(frm, text=f"{col}:", font=("Arial",10,"bold"))\
                   .grid(row=i, column=0, sticky=tk.W, pady=5)
                ttk.Label(frm, text=val).grid(row=i, column=1, sticky=tk.W, padx=10)

            ttk.Button(frm, text="Close", command=win.destroy)\
               .grid(row=len(cols)+1, column=0, columnspan=2, pady=20)

        except sqlite3.Error as e:
            ttk.Label(win, text=f"Error: {e}").pack(pady=20)

    def export_to_excel(self):
    # Gather data
        data = [self.tree.item(i)['values'] for i in self.tree.get_children()]
        df   = pd.DataFrame(data, columns=["ID","Date","Type","Item","Quantity","Price","Total"])

    # Build a cross-platform Downloads path
        user_home = os.path.expanduser("~")
        downloads = os.path.join(user_home, "Downloads")
        os.makedirs(downloads, exist_ok=True)

        filename = os.path.join(
            downloads,
            f"ledger_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        )

        try:
            # Try Excel first
            df.to_excel(filename, index=False, engine='xlsxwriter')
            messagebox.showinfo("Exported", f"Ledger saved to:\n{filename}")
            self.update_status(f"Exported to {filename}")
        except ImportError:
            # Fallback to CSV
            csv_name = filename.replace('.xlsx', '.csv')
            df.to_csv(csv_name, index=False)
            messagebox.showinfo("Exported as CSV", f"Ledger saved to:\n{csv_name}")
            self.update_status(f"Exported to {csv_name}")

    def sort_treeview(self, col):
        data    = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children('')]
        reverse = self.tree.heading(col, "text").startswith("▲")
        data.sort(reverse=reverse)
        for idx, (_v, iid) in enumerate(data):
            self.tree.move(iid, '', idx)
        arrow = "▼" if reverse else "▲"
        self.tree.heading(col, text=f"{arrow} {col}")

    def update_status(self, message):
        self.status_var.set(message)


if __name__ == "__main__":
    # Ensure database/table exists
    conn = sqlite3.connect('db/billing.db')
    c    = conn.cursor()
    c.execute('''
      CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT    NOT NULL,
        type TEXT    NOT NULL,
        item_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        price    REAL NOT NULL,
        notes    TEXT
      )
    ''')
    c.execute("SELECT COUNT(*) FROM ledger")
    if c.fetchone()[0] == 0:
        sample_data = [
            ('2025-05-01','Purchase','Laptop',2,45000.00,'HP ProBook'),
            ('2025-05-01','Sale','Monitor',3,12000.00,'LG 24-inch'),
            ('2025-05-02','Purchase','Keyboard',5,1500.00,'Logitech'),
            ('2025-05-03','Sale','Mouse',10,600.00,'Wireless'),
            ('2025-05-04','Purchase','Headphones',4,2000.00,'Sony'),
            ('2025-05-05','Sale','Printer',1,18000.00,'HP LaserJet'),
        ]
        c.executemany('''
          INSERT INTO ledger (date,type,item_name,quantity,price,notes)
          VALUES (?,?,?,?,?,?)
        ''', sample_data)
    conn.commit()
    conn.close()

    root = tk.Tk()
    app  = LedgerView(root)
    root.mainloop()
