import tkinter as tk
from tkinter import ttk
from ledger import LedgerView
from restock import RestockManager
from add_items import AddItems
from pos_gui import PosApp
from inventory_editor import InventoryEditor
import sqlite3

class MainApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inventory Management System")
        self.root.geometry("1000x750")
        self.init_db()
        self.create_menu()
    
    def init_db(self):
        conn = sqlite3.connect('db/billing.db')
        c = conn.cursor()
        
        # Create tables if not exists
        c.execute('''CREATE TABLE IF NOT EXISTS items
                    (id INTEGER PRIMARY KEY,
                     barcode TEXT UNIQUE,
                     name TEXT,
                     price REAL,
                     quantity INTEGER)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS ledger
                    (id INTEGER PRIMARY KEY,
                     date TEXT,
                     type TEXT,
                     item_id INTEGER,
                     item_name TEXT,
                     quantity INTEGER,
                     price REAL)''')
        
        conn.commit()
        conn.close()
    
    def create_menu(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(expand=True, fill='both', padx=50, pady=50)
        
        buttons = [
            ("POS System", self.open_pos),
            ("Add Items", self.open_add_items),
            ("Inventory Editor", self.open_inventory_editor),
            ("Ledger", self.open_ledger),
            ("Restock", self.open_restock)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(main_frame, text=text, command=command, 
                            width=25, padding=15)
            btn.pack(pady=15)
    
    def open_ledger(self):
        ledger_window = tk.Toplevel(self.root)
        LedgerView(ledger_window)
    
    def open_restock(self):
        restock_window = tk.Toplevel(self.root)
        RestockManager(restock_window)
    
    def open_add_items(self):
        add_window = tk.Toplevel(self.root)
        AddItems(add_window)
    
    def open_pos(self):
        add_window = tk.Toplevel(self.root)
        PosApp(add_window)
    
    def open_inventory_editor(self):
        add_window = tk.Toplevel(self.root)
        InventoryEditor(add_window)

if __name__ == "__main__":
    root = tk.Tk()
    app = MainApp(root)
    root.mainloop()