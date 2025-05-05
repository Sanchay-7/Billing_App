import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Additional imports for webcam barcode scanning
import cv2
from pyzbar import pyzbar

# Path to your SQLite database
db_dir = os.path.join(os.path.dirname(__file__), 'db')
DB_PATH = os.path.join(db_dir, 'pos.db')

def ensure_db():
    """Create the items table if it doesn't exist."""
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            barcode   TEXT PRIMARY KEY,
            name      TEXT NOT NULL,
            price     REAL NOT NULL,
            quantity  INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

class AddItems:
    def __init__(self, window):
        """
        window: a tk.Toplevel or tk.Tk instance.
        """
        self.window = window
        self.window.title("Add / Restock Item")
        self.window.geometry("400x300")
        self.window.resizable(False, False)

        ensure_db()
        self._build_ui()

    def _build_ui(self):
        pad = dict(padx=10, pady=8)
        frm = ttk.Frame(self.window)
        frm.pack(fill=tk.BOTH, expand=True)

        # Barcode + Scan
        ttk.Label(frm, text="Barcode:").grid(row=0, column=0, **pad, sticky=tk.E)
        self.entry_barcode = ttk.Entry(frm, width=30)
        self.entry_barcode.grid(row=0, column=1, **pad)
        ttk.Button(frm, text="Scan Barcode", command=self.scan_barcode).grid(
            row=0, column=2, padx=(0,10), pady=8)

        # Name
        ttk.Label(frm, text="Name:").grid(row=1, column=0, **pad, sticky=tk.E)
        self.entry_name = ttk.Entry(frm, width=30)
        self.entry_name.grid(row=1, column=1, **pad)

        # Price
        ttk.Label(frm, text="Price:").grid(row=2, column=0, **pad, sticky=tk.E)
        self.entry_price = ttk.Entry(frm, width=30)
        self.entry_price.grid(row=2, column=1, **pad)

        # Quantity
        ttk.Label(frm, text="Quantity:").grid(row=3, column=0, **pad, sticky=tk.E)
        self.entry_qty = ttk.Entry(frm, width=30)
        self.entry_qty.grid(row=3, column=1, **pad)

        # Buttons
        btns = ttk.Frame(frm)
        btns.grid(row=4, column=0, columnspan=3, pady=20)
        ttk.Button(btns, text="Add / Restock", command=self.add_or_restock).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Clear", command=self.clear_fields).pack(side=tk.LEFT, padx=5)
        ttk.Button(btns, text="Close", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

    def scan_barcode(self):
        """Open webcam and scan for barcodes."""
        cap = cv2.VideoCapture(0)
        barcode_data = None
        messagebox.showinfo("Info", "Press 'q' to quit scanning.", parent=self.window)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            barcodes = pyzbar.decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, barcode_data, (x, y - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                break

            cv2.imshow('Scan Barcode - Press q to quit', frame)
            if barcode_data or cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if barcode_data:
            self.entry_barcode.delete(0, tk.END)
            self.entry_barcode.insert(0, barcode_data)
        else:
            messagebox.showwarning("Warning", "No barcode detected.", parent=self.window)

    def clear_fields(self):
        """Clear all entries."""
        for e in (self.entry_barcode, self.entry_name, self.entry_price, self.entry_qty):
            e.delete(0, tk.END)

    def add_or_restock(self):
        bc    = self.entry_barcode.get().strip()
        name  = self.entry_name.get().strip()
        price = self.entry_price.get().strip()
        qty   = self.entry_qty.get().strip()

        # Validation
        if not bc or not name or not price or not qty:
            messagebox.showerror("Error", "All fields are required.", parent=self.window)
            return
        try:
            price_f = float(price)
            qty_i   = int(qty)
        except ValueError:
            messagebox.showerror("Error", "Price must be a number, Quantity an integer.", parent=self.window)
            return
        if price_f < 0 or qty_i < 0:
            messagebox.showerror("Error", "Price and Quantity must be ≥ 0.", parent=self.window)
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO items (barcode, name, price, quantity)
                VALUES (?, ?, ?, ?)
            """, (bc, name, price_f, qty_i))
            conn.commit()
            messagebox.showinfo("Added", f"Item '{name}' added with {qty_i} units.", parent=self.window)
        except sqlite3.IntegrityError:
            c.execute("SELECT quantity FROM items WHERE barcode = ?", (bc,))
            old_qty = c.fetchone()[0]
            new_qty = old_qty + qty_i
            c.execute("""
                UPDATE items
                   SET name=?, price=?, quantity=?
                 WHERE barcode=?
            """, (name, price_f, new_qty, bc))
            conn.commit()
            messagebox.showinfo("Restocked",
                f"'{name}' existed: quantity {old_qty} → {new_qty} units.", parent=self.window)
        finally:
            conn.close()
            self.clear_fields()
