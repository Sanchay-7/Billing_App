import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

DB_PATH = "db/billing.db"

class InventoryEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Editor")
        self.root.geometry("800x400")
        
        # Initialize UI elements
        self.setup_ui()
        # Load initial data
        self.load_inventory()
        
    def setup_ui(self):
        # Treeview with scrollbar
        tree_frame = tk.Frame(self.root)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(tree_frame, columns=("ID", "Barcode", "Name", "Price", "Qty"), show="headings")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        for col in ("ID", "Barcode", "Name", "Price", "Qty"):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor=tk.CENTER)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)

        # Entry Form
        form_frame = tk.Frame(self.root)
        form_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(form_frame, text="ID:").grid(row=0, column=0, padx=5)
        self.entry_id = tk.Entry(form_frame, state="readonly")
        self.entry_id.grid(row=0, column=1, padx=5)

        tk.Label(form_frame, text="Barcode:").grid(row=0, column=2, padx=5)
        self.entry_barcode = tk.Entry(form_frame)
        self.entry_barcode.grid(row=0, column=3, padx=5)

        tk.Label(form_frame, text="Name:").grid(row=0, column=4, padx=5)
        self.entry_name = tk.Entry(form_frame)
        self.entry_name.grid(row=0, column=5, padx=5)

        tk.Label(form_frame, text="Price:").grid(row=0, column=6, padx=5)
        self.entry_price = tk.Entry(form_frame)
        self.entry_price.grid(row=0, column=7, padx=5)

        tk.Label(form_frame, text="Qty:").grid(row=0, column=8, padx=5)
        self.entry_qty = tk.Entry(form_frame)
        self.entry_qty.grid(row=0, column=9, padx=5)

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="Update Item", command=self.update_item, width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Delete Item", command=self.delete_item, width=15).pack(side=tk.LEFT, padx=5)

    def load_inventory(self):
        # Clear existing items
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Connect to database and load items
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, barcode, name, price, quantity FROM items")
            for row in cursor.fetchall():
                self.tree.insert("", tk.END, values=row)
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to load inventory: {str(e)}")
        finally:
            if conn:
                conn.close()

    def on_item_select(self, event):
        selected = self.tree.focus()
        if not selected:
            return
        values = self.tree.item(selected, 'values')
        
        self.entry_id.config(state="normal")
        self.entry_id.delete(0, tk.END)
        self.entry_id.insert(0, values[0])
        self.entry_id.config(state="readonly")
    
        self.entry_barcode.delete(0, tk.END)
        self.entry_barcode.insert(0, values[1])
        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, values[2])
        self.entry_price.delete(0, tk.END)
        self.entry_price.insert(0, values[3])
        self.entry_qty.delete(0, tk.END)
        self.entry_qty.insert(0, values[4])

    def update_item(self):
        try:
            item_id = int(self.entry_id.get())
            price = float(self.entry_price.get())
            qty = int(self.entry_qty.get())
            if qty < 0:
                raise ValueError("Quantity cannot be negative")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
            return

        name = self.entry_name.get().strip()
        barcode = self.entry_barcode.get().strip()

        if not name or not barcode:
            messagebox.showerror("Input Error", "Name and Barcode cannot be empty")
            return

        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items 
                SET barcode = ?, name = ?, price = ?, quantity = ?
                WHERE id = ?
            """, (barcode, name, price, qty, item_id))
            conn.commit()
            messagebox.showinfo("Success", "Item updated successfully")
            self.load_inventory()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to update item: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def delete_item(self):
        item_id = self.entry_id.get()
        if not item_id:
            return
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this item?")
        if not confirm:
            return
            
        conn = None
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
            conn.commit()
            messagebox.showinfo("Success", "Item deleted successfully")
            self.load_inventory()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Failed to delete item: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()


# Main application entry point
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryEditor(root)
    root.mainloop()