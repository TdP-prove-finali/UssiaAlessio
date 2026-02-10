import tkinter as tk
import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from UI.view import SerieAApp
from database.DAO import DatabaseManager

if __name__ == "__main__":
    # --- FASE DI RESET ---
    print("Avvio pulizia database...")
    db = DatabaseManager()
    db.reset_simulation()

    # --- AVVIO INTERFACCIA ---
    root = tk.Tk()
    app = SerieAApp(root)
    root.mainloop()