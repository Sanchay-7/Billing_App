import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import datetime
import sqlite3
import os
import subprocess
import cv2
from pyzbar.pyzbar import decode
import threading
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

DB_PATH = "db/billing.db"
cart = []
scanner_active = False

class PosApp:
    def __init__(self, root):
        self.root = root
        self.cart = []
        self.scanner_active = False
        
        # Initialize database
        self.init_db()
        
        # Setup UI
        self.setup_gui()
        
    def init_db(self):
        """Initialize the database and create necessary tables"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create settings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # Create sales table with table_number
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total REAL NOT NULL,
                invoice_number TEXT NOT NULL,
                table_number INTEGER
            )
        """)
        
        # Create sale_items table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES sales(id)
            )
        """)
        
        # Create items table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER DEFAULT 0,
                barcode TEXT
            )
        """)
        
        cursor.execute("SELECT value FROM settings WHERE key = 'last_invoice_number'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO settings (key, value) VALUES ('last_invoice_number', '10000')")
            
        cursor.execute("PRAGMA table_info(sales)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'invoice_number' not in columns:
            cursor.execute("ALTER TABLE sales ADD COLUMN invoice_number TEXT")
            
        conn.commit()
        conn.close()

    def setup_gui(self):
        """Set up the GUI components"""
        self.root.title("Smart Billing POS")
        self.root.geometry("1024x700")
        self.root.configure(bg="#f0f0f0")

        # === HEADER ===
        self.header = tk.Frame(self.root, bg="white", height=100)
        self.header.pack(fill=tk.X, padx=10, pady=5)
        
        self.table_frame = tk.Frame(self.header, bg="white")
        self.table_frame.pack(side=tk.RIGHT, padx=10)
        tk.Label(self.table_frame, text="Table #:", bg="white", font=("Arial", 12)).pack(side=tk.LEFT)
        self.table_entry = tk.Entry(self.table_frame, width=5, font=("Arial", 12))
        self.table_entry.pack(side=tk.LEFT)
        
        # Logo and store info
        try:
            logo_img = Image.open("logo.png").resize((80, 80))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            self.logo_label = tk.Label(self.header, image=self.logo_photo, bg="white")
        except:
            self.logo_label = tk.Label(self.header, text="[LOGO]", bg="white", font=("Arial", 12))
        self.logo_label.pack(side=tk.LEFT, padx=20)

        self.store_info = tk.Frame(self.header, bg="white")
        self.store_info.pack(side=tk.LEFT)
        tk.Label(self.store_info, text="Bakery", font=("Arial", 20, "bold"), bg="white").pack(anchor=tk.W)
        tk.Label(self.store_info, text="12505 Bel Red Road\nBellevue, WA 98005", bg="white").pack(anchor=tk.W)

        # Invoice info
        self.invoice_frame = tk.Frame(self.header, bg="white")
        self.invoice_frame.pack(side=tk.RIGHT, padx=20)
        self.invoice_header_var = tk.StringVar(value=f"Invoice #: {self.get_next_invoice_number()}")
        tk.Label(self.invoice_frame, textvariable=self.invoice_header_var, bg="white", font=("Arial", 12)).pack(anchor=tk.E)

        # === MAIN CONTENT ===
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel with Search and Cart
        self.left_panel = tk.Frame(self.main_frame, bg="white", bd=2, relief=tk.GROOVE)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Search Frame
        self.search_frame = tk.Frame(self.left_panel, bg="white", padx=10, pady=10)
        self.search_frame.pack(fill=tk.X)

        tk.Label(self.search_frame, text="Search Item:", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)
        self.search_entry = tk.Entry(self.search_frame, font=("Arial", 14), width=25, bd=2, relief=tk.GROOVE)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<KeyRelease>", self.search_items)

        self.scan_btn = tk.Button(self.search_frame, text="📷 Scan", font=("Arial", 12), 
                            command=self.start_barcode_scan, bg="#4DB6AC", fg="white")
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        # Search Results
        self.search_results = tk.Listbox(self.left_panel, height=5, font=("Arial", 12))
        self.search_results.pack(fill=tk.X, padx=10, pady=5)
        self.search_results.items = []
        self.search_results.bind("<<ListboxSelect>>", self.select_item)
        
        # Barcode Entry
        self.entry_frame = tk.Frame(self.left_panel, bg="white", padx=10, pady=10)
        self.entry_frame.pack(fill=tk.X)
        tk.Label(self.entry_frame, text="Scan Barcode:", bg="white", font=("Arial", 14)).pack(side=tk.LEFT)
        self.barcode_entry = tk.Entry(self.entry_frame, font=("Arial", 14), width=30, bd=2, relief=tk.GROOVE)
        self.barcode_entry.pack(side=tk.LEFT, padx=10)
        self.barcode_entry.bind("<Return>", self.process_barcode_entry)

        # Cart Display
        self.tree_frame = tk.Frame(self.left_panel, bg="white")
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ("S.No.", "Barcode", "Item Name", "Qty", "Price", "Subtotal")
        self.tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings", height=12)
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.vsb.set)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor=tk.CENTER)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # Right Panel (Controls and Totals)
        self.right_panel = tk.Frame(self.main_frame, bg="#e0e0e0", bd=2, relief=tk.GROOVE, width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        # Control Buttons
        btn_style = {'font': ('Arial', 12), 'bd': 2, 'width': 18}
        tk.Button(self.right_panel, text="🔄 Update Quantity", bg="#81C784", command=self.update_quantity, **btn_style).pack(pady=5)
        tk.Button(self.right_panel, text="❌ Clear Selected", bg="#FF8A65", command=self.clear_selected_items, **btn_style).pack(pady=5)
        tk.Button(self.right_panel, text="💾 Save", bg="#90CAF9", command=self.save_sale, **btn_style).pack(pady=5)
        tk.Button(self.right_panel, text="🖨️ Save & Print", bg="#9575CD", fg="white", command=self.save_and_print, **btn_style).pack(pady=5)
        
        # Totals Display
        self.totals_frame = tk.Frame(self.right_panel, bg="#e0e0e0")
        self.totals_frame.pack(pady=20, padx=10, fill=tk.X)

        tk.Label(self.totals_frame, text="Quantity Total:", bg="#e0e0e0", font=("Arial", 12)).pack(anchor=tk.W)
        self.qty_label = tk.Label(self.totals_frame, text="0", bg="#e0e0e0", font=("Arial", 14, "bold"))
        self.qty_label.pack(anchor=tk.W)

        tk.Label(self.totals_frame, text="Grand Total:", bg="#e0e0e0", font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=10)
        self.total_label = tk.Label(self.totals_frame, text="₹0.00", bg="#e0e0e0", font=("Arial", 18, "bold"), fg="green")
        self.total_label.pack(anchor=tk.W)

    def process_barcode_entry(self, event=None):
        """Process barcode entry when Enter key is pressed"""
        barcode = self.barcode_entry.get().strip()
        if barcode:
            item = self.lookup_item(barcode)
            if item:
                self.add_to_cart(item)
                self.barcode_entry.delete(0, tk.END)
            else:
                messagebox.showinfo("Not Found", f"No item found with barcode: {barcode}")

    def start_barcode_scan(self):
        """Start barcode scanning in a separate thread"""
        self.scanner_active = True
        scan_thread = threading.Thread(target=self.scan_barcode, daemon=True)
        scan_thread.start()

    def scan_barcode(self):
        """Scan barcode using camera"""
        cap = cv2.VideoCapture(0)
        while self.scanner_active:
            ret, frame = cap.read()
            if not ret:
                break
                
            decoded_objects = decode(frame)
            if decoded_objects:
                barcode = decoded_objects[0].data.decode('utf-8')
                item = self.lookup_item(barcode)
                if item:
                    self.add_scanned_item(item)
                    self.scanner_active = False
                    break
                    
            cv2.imshow('Barcode Scanner', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.scanner_active = False
                break
                
        cap.release()
        cv2.destroyAllWindows()

    def add_scanned_item(self, item):
        """Add scanned item to cart"""
        for cart_item in self.cart:
            if cart_item['id'] == item[0]:
                cart_item['qty'] += 1
                cart_item['subtotal'] = cart_item['qty'] * cart_item['price']
                break
        else:
            self.cart.append({
                'id': item[0],
                'name': item[1],
                'price': item[2],
                'qty': 1,
                'subtotal': item[2]
            })
        self.update_cart_display()

    def search_items(self, event=None):
        """Search items by name, id or barcode"""
        search_term = self.search_entry.get().strip()
        self.search_results.delete(0, tk.END)
        self.search_results.items = []  # Reset stored items
        
        if not search_term:
            return
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price FROM items 
            WHERE name LIKE ? OR id LIKE ? OR barcode = ?
        """, (f'%{search_term}%', f'%{search_term}%', search_term))
        
        items = cursor.fetchall()
        conn.close()
        
        for item in items:
            display_text = f"{item[1]} (₹{item[2]:.2f})"
            self.search_results.insert(tk.END, display_text)
            self.search_results.items.append(item)  # Store full item data

    def select_item(self, event):
        """Handle item selection from search results"""
        widget = event.widget
        if not widget.curselection():
            return
        
        index = widget.curselection()[0]
        if index < len(widget.items):
            item = widget.items[index]
            self.add_to_cart(item)

    def add_to_cart(self, item):
        """Add item to cart"""
        for cart_item in self.cart:
            if cart_item['id'] == item[0]:
                cart_item['qty'] += 1
                cart_item['subtotal'] = cart_item['qty'] * item[2]
                break
        else:
            self.cart.append({
                'id': item[0],
                'name': item[1],
                'price': item[2],
                'qty': 1,
                'subtotal': item[2]
            })
        self.update_cart_display()

    def lookup_item(self, search_term):
        """Look up item by id, name or barcode"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, price FROM items 
            WHERE barcode = ? OR name LIKE ? OR id = ?
        """, (search_term, f'%{search_term}%', search_term))
        item = cursor.fetchone()
        conn.close()
        return item

    def update_quantity(self):
        """Update quantity of selected item"""
        selected = self.tree.selection()
        if not selected:
            return
        
        # Get selected item details
        item_values = self.tree.item(selected[0])['values']
        
        # Convert ID to integer
        try:
            item_id = int(item_values[1])
        except ValueError:
            messagebox.showerror("Error", "Invalid item ID in selection")
            return

        # Get new quantity
        new_qty = simpledialog.askinteger(
            "Update Quantity",
            f"New quantity for {item_values[2]}:",
            minvalue=1,
            initialvalue=item_values[3]
        )
        
        if new_qty:
            # Update cart with proper type conversion
            for cart_item in self.cart:
                if cart_item['id'] == item_id:
                    cart_item['qty'] = new_qty
                    cart_item['subtotal'] = round(new_qty * cart_item['price'], 2)  # Ensure float handling
                    break
            self.update_cart_display()

    def update_cart_display(self):
        """Update cart display in treeview"""
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        # Repopulate with updated data
        for i, item in enumerate(self.cart, 1):
            self.tree.insert("", "end", values=(
                i,
                item['id'],
                item['name'],
                item['qty'],
                f"₹{item['price']:.2f}",
                f"₹{item['subtotal']:.2f}"
            ))
        
        # Update totals
        total = sum(item['subtotal'] for item in self.cart)
        qty_total = sum(item['qty'] for item in self.cart)
        self.total_label.config(text=f"₹{total:.2f}")
        self.qty_label.config(text=f"Quantity Total: {qty_total}")

    def clear_selected_items(self):
        """Remove selected items from cart"""
        selected = self.tree.selection()
        for i in selected:
            val = self.tree.item(i)['values']
            self.cart[:] = [item for item in self.cart if not (item['id'] == val[1])]
            self.tree.delete(i)
        self.update_cart_display()

    def clear_cart(self):
        """Clear all items from cart"""
        self.cart.clear()
        self.update_cart_display()

    def save_sale(self):
        """Save the current sale to database"""
        if not self.cart:
            messagebox.showwarning("Empty", "Cart is empty.")
            return None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        low_stock_items = []
        
        try:
            # Get next invoice number
            cursor.execute("SELECT value FROM settings WHERE key = 'last_invoice_number'")
            last_number = int(cursor.fetchone()[0])
            invoice_number = f"HYP-{last_number + 1}"
            
            total = sum(item['subtotal'] for item in self.cart)
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            table_number = self.table_entry.get() or None
            
            # Insert sale
            cursor.execute("""
                INSERT INTO sales (date, total, invoice_number, table_number)
                VALUES (?, ?, ?, ?)
            """, (date_str, total, invoice_number, table_number))
            sale_id = cursor.lastrowid

            # Process items and update stock
            for item in self.cart:
                # Insert sale item
                cursor.execute("""
                    INSERT INTO sale_items (sale_id, item_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                """, (sale_id, item['id'], item['qty'], item['price']))
                
                # Update stock quantity
                cursor.execute("""
                    UPDATE items 
                    SET quantity = quantity - ?
                    WHERE id = ?
                """, (item['qty'], item['id']))
                
                # Check stock level
                cursor.execute("SELECT quantity, name FROM items WHERE id = ?", (item['id'],))
                result = cursor.fetchone()
                if result:
                    stock, name = result
                    if stock < 10:
                        low_stock_items.append(f"{name} ({stock} remaining)")

            # Update invoice number
            cursor.execute("""
                UPDATE settings SET value = ? WHERE key = 'last_invoice_number'
            """, (str(last_number + 1),))
            
            conn.commit()
            
        except sqlite3.Error as e:
            conn.rollback()
            messagebox.showerror("Database Error", f"Failed to save sale: {str(e)}")
            return None
        finally:
            conn.close()
        
        # Show low stock warnings
        if low_stock_items:
            messagebox.showwarning(
                "Low Stock Alert",
                "The following items need restocking:\n- " + 
                "\n- ".join(low_stock_items)
            )
        
        messagebox.showinfo("Saved", f"Sale saved with invoice number: {invoice_number}")
        self.clear_cart()
        self.invoice_header_var.set(f"Invoice #: {self.get_next_invoice_number()}")
        return invoice_number

    def generate_pdf(self, invoice_number):
        try:
        # 1) User home → Downloads (fallback to home)
            user_home = os.path.expanduser("~")
            downloads = os.path.join(user_home, "Downloads")
            if not os.path.isdir(downloads):
                messagebox.showwarning(
                    "Warning",
                    f"No Downloads folder at:\n{downloads}\n"
                    "Saving invoices in your Home folder instead.",
                    parent=self.window
                )
                downloads = user_home

        # 2) Create invoices subfolder
            invoice_dir = os.path.join(downloads, "invoices")
            os.makedirs(invoice_dir, exist_ok=True)

        # 3) Build filename (with timestamp)
            filename = os.path.join(
                invoice_dir,
                f"{invoice_number}_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            )

        # 4) Fetch sale header
            conn = sqlite3.connect(DB_PATH)
            cur  = conn.cursor()
            cur.execute(
                "SELECT id, date, total FROM sales WHERE invoice_number = ?",
                (invoice_number,)
            )
            row = cur.fetchone()
            if not row:
                messagebox.showerror("Error", "Invoice not found", parent=self.window)
                conn.close()
                return None
            sale_id, date_str, total = row

        # 5) Fetch sale items
            cur.execute("""
                SELECT items.name, sale_items.quantity, sale_items.price
                FROM sale_items
                JOIN items ON sale_items.item_id = items.id
                WHERE sale_id = ?
            """, (sale_id,))
            items = cur.fetchall()
            conn.close()

        # 6) Draw the PDF
            c = canvas.Canvas(filename, pagesize=letter)
            w, h = letter

        # Header
            c.setFont("Helvetica-Bold", 16)
            c.drawString(72, h-72, "HD Super Mart")
            c.setFont("Helvetica", 12)
            c.drawString(72, h-90, "12505 Bel Red Road, Ste 212, Bellevue, WA 98005")
            c.drawString(72, h-108, "(425) 389 0173")

        # Invoice info
            c.drawString(72, h-140, f"Invoice #: {invoice_number}")
            c.drawString(72, h-155, f"Date:       {date_str}")
            c.drawString(72, h-170, "Cashier:    Admin")

        # Table header
            y = h-220
            c.setFont("Helvetica-Bold", 12)
            c.drawString(72,  y,   "Item")
            c.drawString(300, y,   "Qty")
            c.drawString(400, y,   "Price")
            c.drawString(500, y,   "Subtotal")

        # Table rows
            y -= 24
            c.setFont("Helvetica", 12)
            for name, qty, price in items:
                subtotal = qty * price
                c.drawString(72,  y,   name)
                c.drawString(300, y,   str(qty))
                c.drawString(400, y,   f"₹{price:.2f}")
                c.drawString(500, y,   f"₹{subtotal:.2f}")
                y -= 20

        # Grand total
            c.setFont("Helvetica-Bold", 14)
            c.drawString(400, y-40, f"Total: ₹{total:.2f}")

            c.save()

        # 7) Confirmation
            if os.path.isfile(filename):
                messagebox.showinfo(
                    "Invoice Saved",
                    f"Invoice PDF saved to:\n{filename}",
                    parent=self.window
                )
                return filename
            else:
                messagebox.showerror(
                    "Error",
                    f"Failed to write PDF to:\n{filename}",
                    parent=self.window
                )
                return None

        except Exception as e:
            messagebox.showerror(
                "PDF Error",
                f"Failed to generate PDF:\n{e}",
                parent=self.window
            )
            return None


    def print_pdf(self, filename):
    
        try:
            if not filename or not os.path.exists(filename):
                messagebox.showerror("Print Error", "PDF file does not exist", parent=self.window)
                return

            if os.name == 'nt':
                # Windows: shell‐print
                try:
                    os.startfile(filename, "print")
                except Exception:
                    # If direct print fails, open for manual print
                    os.startfile(filename)
                    messagebox.showinfo(
                        "Print Instructions",
                        "PDF opened—use its viewer’s Print command.",
                        parent=self.window
                    )
            elif os.name == 'posix':
            # macOS / Linux: use lp
                subprocess.run(["lp", filename], check=False)
            else:
                messagebox.showwarning(
                    "Print Error",
                    "Printing not supported on this OS.",
                    parent=self.window
                )

        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print PDF:\n{e}", parent=self.window)

    def get_next_invoice_number(self):
        """Get the next invoice number from settings"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'last_invoice_number'")
        result = cursor.fetchone()
        conn.close()
        return f"HYP-{int(result[0]) + 1}" if result else "HYP-10000"

    def print_thermal(self, invoice_number, table_number):
        """Print receipt to thermal printer"""
        try:
            from escpos.printer import Usb
            
            # Replace with your printer's vendor/product IDs - these need configuration
            printer = Usb(0x0416, 0x5011)  # Example IDs for Bixolon printer
            
            # Get sale data
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT items.name, sale_items.quantity, sale_items.price
                FROM sale_items
                JOIN items ON sale_items.item_id = items.id
                JOIN sales ON sale_items.sale_id = sales.id
                WHERE sales.invoice_number = ?
            """, (invoice_number,))
            items = cursor.fetchall()
            total = sum(qty * price for _, qty, price in items)
            conn.close()

            # Create receipt content
            printer.text("\nHD SUPER MART\n")
            printer.text("12505 Bel Red Road\n")
            printer.text(f"Invoice: {invoice_number}\n")
            printer.text(f"Table: {table_number}\n")
            printer.text(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            printer.text("-" * 32 + "\n")
            
            for name, qty, price in items:
                line = f"{name[:20]:<20} {qty:>3}x{price:>6.2f}"
                printer.text(line + "\n")
                
            printer.text("-" * 32 + "\n")
            printer.text(f"TOTAL: ₹{total:.2f}\n")
            printer.cut()
            
        except ImportError:
            # Handle case where escpos module is not installed
            messagebox.showwarning("Print Warning", 
                "Thermal printing requires the python-escpos module.\n"
                "Please install it with: pip install python-escpos")
            # Generate and open PDF as fallback
            pdf_file = self.generate_pdf(invoice_number)
            if pdf_file:
                self.print_pdf(pdf_file)
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print receipt: {str(e)}")

    def sanitize(self, text):
        """Sanitize text for output"""
        replacements = {
            '\u2009': ' ',   # Thin space
            '\u20b9': 'Rs.', # Indian Rupee sign
            '\u2013': '-',   # En dash
            '\u2019': "'"    # Right single quote
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        return text.encode('ascii', 'ignore').decode('ascii')

    def save_and_print(self):
        """Save the sale and print receipt"""
        invoice_number = self.save_sale()
        if invoice_number:
            table_number = self.table_entry.get() or "N/A"
            try:
                self.print_thermal(invoice_number, table_number)
            except Exception as e:
                messagebox.showerror("Print Error", f"Thermal printing failed: {str(e)}")
                # Fallback to PDF
                pdf_file = self.generate_pdf(invoice_number)
                if pdf_file:
                    self.print_pdf(pdf_file)

# Only make necessary directories
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Create and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = PosApp(root)
    root.mainloop()