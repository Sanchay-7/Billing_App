import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import cv2
from pyzbar.pyzbar import decode
import threading
from datetime import datetime

class RestockManager:
    def __init__(self, window):
        self.window = window
        self.window.title("Restock Items")
        self.window.geometry("800x600")
        self.scanner_active = False
        self.cap = None

        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.window)
        main_frame.pack(padx=30, pady=30)

        # Barcode Scanner Section
        scan_frame = ttk.Frame(main_frame)
        scan_frame.pack(pady=20)

        ttk.Button(scan_frame, text="📷 Scan Barcode", 
                   command=self.start_scan, padding=10).pack(side=tk.LEFT)
        self.barcode_entry = ttk.Entry(scan_frame, width=25)
        self.barcode_entry.pack(side=tk.LEFT, padx=10)

        # Item Details
        details_frame = ttk.Frame(main_frame)
        details_frame.pack(pady=20)

        ttk.Label(details_frame, text="Item Name:").grid(row=0, column=0, sticky=tk.E)
        self.name_label = ttk.Label(details_frame, text="-")
        self.name_label.grid(row=0, column=1, sticky=tk.W)

        ttk.Label(details_frame, text="Current Price:").grid(row=1, column=0, sticky=tk.E)
        self.price_label = ttk.Label(details_frame, text="-")
        self.price_label.grid(row=1, column=1, sticky=tk.W)

        # Restock Controls
        ttk.Label(main_frame, text="Quantity to Add:").pack(pady=10)
        self.qty_entry = ttk.Entry(main_frame)
        self.qty_entry.pack()

        ttk.Button(main_frame, text="Restock", 
                   command=self.process_restock, padding=10).pack(pady=20)

    def start_scan(self):
        if self.scanner_active:
            return
        self.scanner_active = True
        threading.Thread(target=self.scan_barcode, daemon=True).start()

    def scan_barcode(self):
        """Open webcam feed and scan for barcode."""
        self.cap = cv2.VideoCapture(0)
        barcode_data = None

        while self.scanner_active:
            ret, frame = self.cap.read()
            if not ret:
                break
            # Decode barcodes
            for barcode in decode(frame):
                barcode_data = barcode.data.decode('utf-8')
                self.scanner_active = False
                break

            # Show feed
            cv2.imshow('Scanning - Press q to cancel', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                barcode_data = None
                self.scanner_active = False
                break

        # Cleanup
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

        # Populate entry and details
        if barcode_data:
            self.window.after(0, self.barcode_entry.delete, 0, tk.END)
            self.window.after(0, self.barcode_entry.insert, 0, barcode_data)
            self.window.after(0, self.load_item_details, barcode_data)
        else:
            messagebox.showwarning("Scan Cancelled", "No barcode detected.", parent=self.window)

    def load_item_details(self, barcode):
        """Fetch existing item details from DB."""
        conn = sqlite3.connect('db/pos.db')
        c = conn.cursor()
        c.execute("SELECT name, price FROM items WHERE barcode = ?", (barcode,))
        row = c.fetchone()
        conn.close()

        if row:
            name, price = row
            self.name_label.config(text=name)
            self.price_label.config(text=f"₹{price:.2f}")
        else:
            self.name_label.config(text="<new item>")
            self.price_label.config(text="-/-")

    def process_restock(self):
        barcode = self.barcode_entry.get().strip()
        qty_text = self.qty_entry.get().strip()
        name = self.name_label.cget('text')
        price_label = self.price_label.cget('text')

        if not barcode:
            messagebox.showerror("Error", "Scan a barcode first.", parent=self.window)
            return
        try:
            qty = int(qty_text)
        except ValueError:
            messagebox.showerror("Error", "Quantity must be an integer.", parent=self.window)
            return
        if qty <= 0:
            messagebox.showerror("Error", "Quantity must be > 0.", parent=self.window)
            return

        conn = sqlite3.connect('db/billing.db')
        c = conn.cursor()
        # Determine item exists
        c.execute("SELECT name, price, quantity FROM items WHERE barcode = ?", (barcode,))
        row = c.fetchone()
        if row:
            old_name, old_price, old_qty = row
            new_qty = old_qty + qty
            c.execute(
                "UPDATE items SET quantity = ?, name = ?, price = ? WHERE barcode = ?",
                (new_qty, old_name if name == '<new item>' else name, old_price if price_label == '-/-' else float(price_label.replace('₹','')), barcode)
            )
            txn_type = 'Purchase'
            item_name = old_name
            price = old_price
        else:
            # New item: insert with placeholder name and price
            new_qty = qty
            placeholder_price = 0.0
            c.execute(
                "INSERT INTO items (barcode, name, price, quantity) VALUES (?, ?, ?, ?)",
                (barcode, '', placeholder_price, new_qty)
            )
            txn_type = 'Purchase'
            item_name = ''
            price = placeholder_price

        # Record in ledger table
        txn_date = datetime.now().strftime('%Y-%m-%d')
        try:
            c.execute(
                "INSERT INTO ledger (date, type, item_name, quantity, price) VALUES (?,?,?,?,?)",
                (txn_date, txn_type, item_name, qty, price)
            )
        except sqlite3.Error as e:
            messagebox.showwarning("Ledger Error", f"Failed to record ledger: {e}", parent=self.window)

        conn.commit()
        conn.close()

        messagebox.showinfo("Success", f"Restocked {qty} units of '{item_name or barcode}'.", parent=self.window)
        # Clear inputs
        self.barcode_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        self.name_label.config(text="-")
        self.price_label.config(text="-")
