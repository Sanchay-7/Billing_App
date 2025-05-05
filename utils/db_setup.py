# db_setup.py
import sqlite3

def init_db():
    conn = sqlite3.connect("db/billing.db")
    c = conn.cursor()

    # Create items table
      c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0
        )
    ''')
    # Create sales table with new columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total REAL NOT NULL,
            invoice_number TEXT NOT NULL,
            table_number INTEGER
        )
    ''')

    # Create sale_items table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    ''')

    # Create settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Initialize settings if empty
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('last_invoice_number', '10000')")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()