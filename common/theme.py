import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb

# Colori moderni per compatibilità (tema scuro D&D)
# Manteniamo le costanti per i Canvas e altre parti custom che usano colori espliciti
BG_COLOR = "#222222"
SURFACE_COLOR = "#303030"
SURFACE_COLOR_ALT = "#424242"
TEXT_COLOR = "#E0E0E0"
TEXT_MUTED = "#9E9E9E"
ACCENT_RED = "#E74C3C" # Colore 'primary' di darkly o rosso D&D
ACCENT_RED_HOVER = "#C0392B"
ACCENT_BLUE = "#3498DB"
ACCENT_BLUE_HOVER = "#2980B9"
ACCENT_GREEN = "#2ECC71"
ACCENT_GOLD = "#F1C40F"
BORDER_COLOR = "#555555"

# Font moderni
FONT_MAIN = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Georgia", 14, "bold") # Sapore fantasy

def setup_theme(root):
    # Inizializziamo il tema moderno di ttkbootstrap
    style = tb.Style(theme="darkly")
    
    # Mapping degli stili semantici esistenti (es. Primary.TButton) ai colori del tema
    # Per semplicità, possiamo usare le classi fornite da ttkbootstrap
    # ttkbootstrap usa nomi come "primary.TButton", "success.TButton", ecc.
    # Configuriamo i nostri vecchi nomi per essere compatibili
    
    colors = style.colors
    
    # Frame
    style.configure('Surface.TFrame', background=SURFACE_COLOR)
    
    # Label
    style.configure('Surface.TLabel', background=SURFACE_COLOR)
    style.configure('Title.TLabel', font=FONT_TITLE, foreground=ACCENT_GOLD)
    style.configure('Muted.TLabel', foreground=TEXT_MUTED, font=("Segoe UI", 8, "italic"))
    style.configure('Success.TLabel', foreground=colors.success, font=FONT_BOLD)
    style.configure('Danger.TLabel', foreground=colors.danger, font=FONT_BOLD)
    
    # Button generici e semantici
    # Creiamo gli stili ereditando da quelli di ttkbootstrap
    style.configure('Primary.TButton', background=colors.primary)
    style.map('Primary.TButton', background=[('active', ACCENT_RED_HOVER)])
    
    style.configure('Success.TButton', background=colors.success)
    style.map('Success.TButton', background=[('active', ACCENT_GREEN)])
    
    style.configure('Info.TButton', background=colors.info)
    style.map('Info.TButton', background=[('active', ACCENT_BLUE)])
    
    # Slot inventario
    style.configure('Slot.TButton', background=SURFACE_COLOR, foreground=TEXT_MUTED, padding=(4, 8))
    style.map('Slot.TButton', background=[('active', SURFACE_COLOR_ALT)])
    style.configure('SlotFilled.TButton', background='#33402A', foreground=TEXT_COLOR, padding=(4, 8))
    style.map('SlotFilled.TButton', background=[('active', '#455A35')])

    # Impostiamo il default font globalmente
    style.configure('.', font=FONT_MAIN)
    style.configure('Treeview', font=FONT_MAIN, rowheight=24)
    style.configure('Treeview.Heading', font=FONT_BOLD)

    # Opzioni di default per i widget tk classici
    root.option_add('*Listbox.background', SURFACE_COLOR)
    root.option_add('*Listbox.foreground', TEXT_COLOR)
    root.option_add('*Listbox.selectBackground', colors.primary)
    root.option_add('*Listbox.selectForeground', 'white')
    root.option_add('*Listbox.relief', 'flat')
    root.option_add('*Listbox.highlightThickness', 0)
    
    root.option_add('*Text.background', SURFACE_COLOR)
    root.option_add('*Text.foreground', TEXT_COLOR)
    root.option_add('*Text.insertBackground', TEXT_COLOR)
    root.option_add('*Text.relief', 'flat')
    
    root.option_add('*Menu.background', SURFACE_COLOR_ALT)
    root.option_add('*Menu.foreground', TEXT_COLOR)
    root.option_add('*Menu.activeBackground', colors.primary)
    root.option_add('*Menu.activeForeground', 'white')
    
    root.configure(bg=colors.bg)
    
def apply_modern_window_style(win):
    style = tb.Style()
    win.configure(bg=style.colors.bg)
