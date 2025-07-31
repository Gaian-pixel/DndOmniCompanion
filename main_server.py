# main_server.py
# Punto di avvio per l'applicazione Server.
import tkinter as tk
from server.server import DM_GUI

if __name__ == "__main__":
    root = tk.Tk()
    app = DM_GUI(root)
    root.mainloop()