# main_client.py
# Punto di avvio per l'applicazione Client.
import tkinter as tk
from client.client import ClientGUI

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()