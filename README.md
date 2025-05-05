# 🧾 Billing App

A complete **offline billing and inventory management** application built with **Python** and **Tkinter**. Ideal for small retail businesses to manage sales, inventory, invoicing, and more — all without internet.

---

## ✅ Features

- 🛒 Point-of-Sale (POS) module
- 📦 Inventory management (add/edit/restock)
- 📊 Ledger with Excel export (saved to Downloads folder)
- 🧾 Invoice PDF generation (auto-named and saved to Downloads/invoices)
- 📷 Barcode scanning (via webcam, using OpenCV + pyzbar)
- 📁 Daily bill saving by date in structured folders
- 🧠 Fast item lookup, total calculation, and print-ready invoice
- 💾 Offline support (uses local SQLite database)

---

## 🖼️ Pages

- Dashboard
- POS screen
- Add/Edit Inventory
- Invoice PDF

---

## 💡 Technologies Used

- **Python 3.x**
- **Tkinter** – GUI framework
- **SQLite** – Local database
- **OpenCV + pyzbar** – Barcode scanning
- **ReportLab** – PDF generation
- **Pandas** – Excel export
- **Pillow** – Image support (optional)

---

⚙️ Installation
1. Clone the Repository
  bash
  git clone https://github.com/Sanchay-7/Billing_App.git
  cd Billing_App
2. Install Requirements
  bash
  pip install -r requirements.txt
  requirements.txt

🚀 Running the Application
  bash
  python main.py
  The main dashboard will launch with access to all features.

🧾 Exported Files
  Invoices → ~/Downloads/invoices/InvoiceNumber_Date.pdf

  Sales Ledger Excel → ~/Downloads/Ledger_Date.xlsx

  Daily Bills → Saved under bills/YYYY-MM-DD/ folder

  📦 Build Executable for Windows
  Use PyInstaller to create a standalone .exe file:

  bash
  pip install pyinstaller

  pyinstaller --noconfirm --onefile --windowed main.py
  Output .exe will be located in the dist/ folder.

📜 License
This project is licensed under the MIT License. See LICENSE for details.

🙋 Author
Sanchay


📌 Notes
Tested on Windows 11

Barcode scanning may require a well-lit environment

No internet connection required
