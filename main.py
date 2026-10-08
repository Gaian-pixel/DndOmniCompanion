import tkinter as tk
from tkinter import ttk
import sys
import os

# Assicuriamoci che i moduli interni siano importabili dal path principale
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from common.theme import setup_theme, apply_modern_window_style, FONT_TITLE, FONT_MAIN

def start_app():
    root = tk.Tk()
    root.withdraw() # Nascondi temporaneamente la finestra principale finché non scegliamo
    setup_theme(root)

    dialog = tk.Toplevel(root)
    dialog.title("D&D OmniCompanion")
    dialog.geometry("450x250")
    dialog.resizable(False, False)
    apply_modern_window_style(dialog)
    
    # Se l'utente chiude il dialog, chiudi tutta l'applicazione
    dialog.protocol("WM_DELETE_WINDOW", lambda: root.destroy())

    ttk.Label(dialog, text="D&D OmniCompanion", font=FONT_TITLE, foreground="#D4AF37").pack(pady=(20, 5))
    ttk.Label(dialog, text="Seleziona la modalità di avvio:", font=FONT_MAIN).pack(pady=(0, 20))

    def launch_dm():
        dialog.destroy()
        from server.server import DM_GUI
        root.deiconify()
        app = DM_GUI(root)

    def launch_player():
        dialog.destroy()
        from client.client import ClientGUI
        root.deiconify()
        app = ClientGUI(root)

    btn_frame = ttk.Frame(dialog)
    btn_frame.pack(pady=10)

    ttk.Button(btn_frame, text="👑 Ospita Partita (Dungeon Master)", command=launch_dm, style="Primary.TButton", width=30).pack(pady=5)
    ttk.Button(btn_frame, text="⚔️ Unisciti alla Partita (Giocatore)", command=launch_player, style="Success.TButton", width=30).pack(pady=5)

    root.eval('tk::PlaceWindow . center')
    root.mainloop()

if __name__ == "__main__":
    start_app()

