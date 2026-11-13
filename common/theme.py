# common/theme.py
"""
Design System Dark Fantasy Moderno per DndOmniCompanion.
Ispirato all'estetica di Foundry VTT, Baldur's Gate 3 e D&D 5e.
"""
import tkinter as tk
from tkinter import ttk
import ttkbootstrap as tb

# --- PALETTE DARK FANTASY MODERNA (Baldur's Gate 3 / Foundry VTT Inspired) ---
BG_COLOR = "#0D0E12"           # Ossidiana profonda di fondo
SURFACE_COLOR = "#15171E"      # Ardesia scura / card ed elementi rialzati
SURFACE_COLOR_ALT = "#1E2029"  # Superfici secondarie / stato hover
SURFACE_LIGHT = "#272A36"      # Card evidenziate / slot

BORDER_COLOR = "#282C37"       # Bordi discreti dark
BORDER_SUBTLE = "#323745"
BORDER_GOLD = "#C59B27"        # Bordi rifiniti in oro antico

# Accenti tematici D&D
ACCENT_GOLD = "#E5C07B"        # Oro antico D&D
ACCENT_GOLD_LIGHT = "#FAD38D"  # Oro/Ambra accesa
ACCENT_GOLD_HOVER = "#C9A050"  # Oro hover scuro

ACCENT_RED = "#E05252"         # Cremisi / D&D Crimson
ACCENT_RED_HOVER = "#C53939"

ACCENT_GREEN = "#10B981"       # Smeraldo / Salute
ACCENT_GREEN_HOVER = "#059669"

ACCENT_BLUE = "#38BDF8"        # Blu Arcano / Info
ACCENT_BLUE_HOVER = "#0284C7"

ACCENT_PURPLE = "#A855F7"      # Viola Mistico / PNG

# Testo e tipografia
TEXT_COLOR = "#ECEFF1"         # Bianco morbido leggibile
TEXT_MUTED = "#909296"         # Grigio spento secondario
TEXT_GOLD = "#F1C40F"          # Testo dorato
TEXT_DARK = "#121316"          # Testo su bottoni chiari

# Font
FONT_TITLE = ("Georgia", 15, "bold")       # Titoli fantasy
FONT_HEADER = ("Segoe UI", 12, "bold")     # Intestazioni sezioni
FONT_MAIN = ("Segoe UI", 10)               # Corpo del testo
FONT_BOLD = ("Segoe UI", 10, "bold")       # Testo in evidenza
FONT_BADGE = ("Segoe UI", 9, "bold")       # Badge e pillole di stato
FONT_SMALL = ("Segoe UI", 8)               # Note e timestamp
FONT_REGULAR = FONT_MAIN                    # Alias di compatibilità per FONT_MAIN


def setup_theme(root):
    """Inizializza e configura globalmente il tema Dark Fantasy."""
    from common.ui_lifecycle import suppress_tk_bgerror
    suppress_tk_bgerror(root)

    if tb.Style.instance is not None:
        try:
            if not tb.Style.instance.master or not tb.Style.instance.master.winfo_exists():
                tb.Style.instance = None
        except Exception:
            tb.Style.instance = None

    available_themes = tb.Style().theme_names()
    theme_name = "bootstrap-dark" if "bootstrap-dark" in available_themes else "darkly"
    style = tb.Style(theme=theme_name)
    colors = style.colors

    # Configurazione Colori Principali
    style.configure('.', font=FONT_MAIN, background=BG_COLOR, foreground=TEXT_COLOR)

    # --- FRAME E CARDS ---
    style.configure('TFrame', background=BG_COLOR)
    style.configure('Surface.TFrame', background=SURFACE_COLOR)
    style.configure('Card.TFrame', background=SURFACE_COLOR, relief="solid", borderwidth=1)
    style.configure('CardAlt.TFrame', background=SURFACE_COLOR_ALT)

    # LabelFrame
    style.configure('TLabelframe', background=SURFACE_COLOR, bordercolor=BORDER_COLOR)
    style.configure('TLabelframe.Label', background=SURFACE_COLOR, foreground=ACCENT_GOLD, font=FONT_BOLD)

    # --- LABELS ---
    style.configure('TLabel', background=BG_COLOR, foreground=TEXT_COLOR, font=FONT_MAIN)
    style.configure('Surface.TLabel', background=SURFACE_COLOR, foreground=TEXT_COLOR)
    style.configure('Title.TLabel', font=FONT_TITLE, foreground=ACCENT_GOLD, background=SURFACE_COLOR)
    style.configure('GoldTitle.TLabel', font=FONT_TITLE, foreground=ACCENT_GOLD, background=BG_COLOR)
    style.configure('Header.TLabel', font=FONT_HEADER, foreground=TEXT_COLOR)
    style.configure('Muted.TLabel', foreground=TEXT_MUTED, font=FONT_SMALL)
    style.configure('Primary.TLabel', font=FONT_BOLD, foreground=ACCENT_BLUE, background=BG_COLOR)
    style.configure('Gold.TLabel', font=FONT_BOLD, foreground=ACCENT_GOLD, background=BG_COLOR)
    
    # Badge Labels (Pills)
    style.configure('Badge.TLabel', font=FONT_BADGE, foreground=ACCENT_GOLD, background=SURFACE_COLOR_ALT, padding=(6, 2))
    style.configure('BadgeRed.TLabel', font=FONT_BADGE, foreground="#FF6B6B", background="#3B1219", padding=(6, 2))
    style.configure('BadgeGreen.TLabel', font=FONT_BADGE, foreground="#51CF66", background="#132B1B", padding=(6, 2))
    style.configure('BadgeBlue.TLabel', font=FONT_BADGE, foreground="#4DABF7", background="#112233", padding=(6, 2))
    style.configure('Success.TLabel', foreground=colors.success, font=FONT_BOLD)
    style.configure('Danger.TLabel', foreground=colors.danger, font=FONT_BOLD)

    # --- BOTTONI ---
    # Bottone Dorato (Gold / Primary fantasy)
    style.configure('Gold.TButton', font=FONT_BOLD, background=ACCENT_GOLD, foreground=TEXT_DARK, borderwidth=0, padding=(10, 6))
    style.map('Gold.TButton', background=[('active', ACCENT_GOLD_LIGHT), ('pressed', ACCENT_GOLD_HOVER)])
    style.configure('Accent.TButton', font=FONT_BOLD, background=ACCENT_GOLD, foreground=TEXT_DARK, borderwidth=0, padding=(10, 6))
    style.map('Accent.TButton', background=[('active', ACCENT_GOLD_LIGHT), ('pressed', ACCENT_GOLD_HOVER)])

    # Bottone Secondario
    style.configure('Secondary.TButton', font=FONT_MAIN, background=SURFACE_COLOR_ALT, foreground=TEXT_COLOR, padding=(8, 5))
    style.map('Secondary.TButton', background=[('active', SURFACE_LIGHT)])

    # Bottone Cremisi (Crimson / Danger D&D)
    style.configure('Primary.TButton', font=FONT_BOLD, background=ACCENT_RED, foreground="#FFFFFF", borderwidth=0, padding=(10, 6))
    style.map('Primary.TButton', background=[('active', "#E03131"), ('pressed', ACCENT_RED_HOVER)])
    style.configure('Danger.TButton', font=FONT_BOLD, background=ACCENT_RED, foreground="#FFFFFF", padding=(8, 5))
    style.map('Danger.TButton', background=[('active', ACCENT_RED_HOVER)])

    # Bottone Smeraldo (Success)
    style.configure('Success.TButton', font=FONT_BOLD, background=ACCENT_GREEN, foreground="#FFFFFF", padding=(8, 5))
    style.map('Success.TButton', background=[('active', ACCENT_GREEN_HOVER)])

    # Bottone Arcano (Info)
    style.configure('Info.TButton', font=FONT_BOLD, background=ACCENT_BLUE, foreground="#FFFFFF", padding=(8, 5))
    style.map('Info.TButton', background=[('active', ACCENT_BLUE_HOVER)])

    # Bottone Scuro (Dark card action)
    style.configure('Dark.TButton', font=FONT_MAIN, background=SURFACE_COLOR_ALT, foreground=TEXT_COLOR, padding=(8, 5))
    style.map('Dark.TButton', background=[('active', SURFACE_LIGHT)])

    # Bottone Warning (Ambra / Avviso)
    style.configure('Warning.TButton', font=FONT_BOLD, background="#D97706", foreground="#FFFFFF", borderwidth=0, padding=(8, 5))
    style.map('Warning.TButton', background=[('active', "#F59E0B"), ('pressed', "#B45309")])

    # Bottone Compatto
    style.configure('Small.TButton', font=FONT_SMALL, background=SURFACE_COLOR_ALT, foreground=TEXT_COLOR, padding=(4, 2))
    style.map('Small.TButton', background=[('active', SURFACE_LIGHT)])

    # Bottone Toolbar Quadrato
    style.configure('Tool.TButton', font=("Segoe UI", 11), background=SURFACE_COLOR, foreground=TEXT_COLOR, padding=(4, 4))
    style.map('Tool.TButton', background=[('active', SURFACE_COLOR_ALT), ('selected', ACCENT_GOLD)])

    # Bottone Toolbar Attivo (evidenziato in oro quando uno strumento mappa è attivo)
    style.configure('ToolActive.TButton', font=("Segoe UI", 11, "bold"), background=ACCENT_GOLD, foreground=TEXT_DARK, padding=(4, 4))
    style.map('ToolActive.TButton', background=[('active', ACCENT_GOLD_LIGHT), ('pressed', ACCENT_GOLD_HOVER)])

    # Bottoni HUD Fluttuante VTT (Modern Dark Fantasy)
    style.configure('Hud.TButton', font=("Segoe UI", 10, "bold"), background=SURFACE_COLOR, foreground=TEXT_COLOR, padding=(6, 4))
    style.map('Hud.TButton', background=[('active', SURFACE_COLOR_ALT), ('pressed', ACCENT_GOLD)], foreground=[('pressed', TEXT_DARK)])
    style.configure('HudGold.TButton', font=("Segoe UI", 10, "bold"), background=SURFACE_COLOR_ALT, foreground=ACCENT_GOLD, padding=(6, 4))
    style.map('HudGold.TButton', background=[('active', ACCENT_GOLD), ('pressed', ACCENT_GOLD_HOVER)], foreground=[('active', TEXT_DARK)])
    style.configure('HudActive.TButton', font=("Segoe UI", 10, "bold"), background=ACCENT_GOLD, foreground=TEXT_DARK, padding=(6, 4))
    style.map('HudActive.TButton', background=[('active', ACCENT_GOLD_LIGHT), ('pressed', ACCENT_GOLD_HOVER)])

    # Bottoni Action Economy (Stati Attivo / Speso)
    style.configure('ActionActive.TButton', font=("Segoe UI", 8, "bold"), background=ACCENT_GREEN, foreground="#FFFFFF", padding=(4, 2))
    style.map('ActionActive.TButton', background=[('active', ACCENT_GREEN_HOVER)])
    style.configure('BonusActive.TButton', font=("Segoe UI", 8, "bold"), background="#3B82F6", foreground="#FFFFFF", padding=(4, 2))
    style.map('BonusActive.TButton', background=[('active', "#2563EB")])
    style.configure('ReactionActive.TButton', font=("Segoe UI", 8, "bold"), background="#F59E0B", foreground="#FFFFFF", padding=(4, 2))
    style.map('ReactionActive.TButton', background=[('active', "#D97706")])
    style.configure('ActionSpent.TButton', font=("Segoe UI", 8), background=SURFACE_COLOR_ALT, foreground=TEXT_MUTED, padding=(4, 2))
    style.map('ActionSpent.TButton', background=[('active', SURFACE_LIGHT)])

    # Bottone Dado Rapido (Quick Roll Pill in chat)
    style.configure('QuickDie.TButton', font=("Segoe UI", 8, "bold"), background=SURFACE_COLOR_ALT, foreground=ACCENT_GOLD, padding=(4, 2), borderwidth=1)
    style.map('QuickDie.TButton', background=[('active', ACCENT_GOLD), ('pressed', ACCENT_GOLD_HOVER)], foreground=[('active', TEXT_DARK)])

    # Hotbar Slot Buttons
    style.configure('Hotbar.TButton', font=("Segoe UI", 8), background=SURFACE_COLOR_ALT, foreground=TEXT_MUTED, padding=(2, 2))
    style.map('Hotbar.TButton', background=[('active', SURFACE_LIGHT)])
    style.configure('HotbarAssigned.TButton', font=("Segoe UI", 8, "bold"), background=SURFACE_COLOR_ALT, foreground=ACCENT_GOLD, padding=(2, 2))
    style.map('HotbarAssigned.TButton', background=[('active', ACCENT_GOLD), ('pressed', ACCENT_GOLD_HOVER)], foreground=[('active', TEXT_DARK)])

    # Slot Inventario
    style.configure('Slot.TButton', background=SURFACE_COLOR, foreground=TEXT_MUTED, padding=(4, 8), bordercolor=BORDER_COLOR)
    style.map('Slot.TButton', background=[('active', SURFACE_COLOR_ALT)])
    style.configure('SlotFilled.TButton', background='#253323', foreground=TEXT_COLOR, padding=(4, 8), bordercolor='#2B8A3E')
    style.map('SlotFilled.TButton', background=[('active', '#32472F')])

    # --- TREEVIEWS ---
    style.configure('Treeview', background=SURFACE_COLOR, fieldbackground=SURFACE_COLOR, 
                    foreground=TEXT_COLOR, font=FONT_MAIN, rowheight=28, borderwidth=0)
    style.map('Treeview', background=[('selected', '#2C3E50')], foreground=[('selected', '#FFFFFF')])
    style.configure('Treeview.Heading', background=SURFACE_COLOR_ALT, foreground=ACCENT_GOLD, 
                    font=FONT_BOLD, relief="flat", padding=(6, 4))

    # --- NOTEBOOK (TABS) ---
    style.configure('TNotebook', background=BG_COLOR, borderwidth=0)
    style.configure('TNotebook.Tab', font=FONT_BOLD, padding=(14, 8), background=SURFACE_COLOR, 
                    foreground=TEXT_MUTED, borderwidth=0)
    style.map('TNotebook.Tab', 
              background=[('selected', SURFACE_COLOR_ALT), ('active', SURFACE_LIGHT)],
              foreground=[('selected', ACCENT_GOLD), ('active', TEXT_COLOR)])

    # --- SCROLLBAR ---
    style.configure('Vertical.TScrollbar', background=SURFACE_COLOR_ALT, troughcolor=BG_COLOR, borderwidth=0, arrowsize=12)
    style.configure('Horizontal.TScrollbar', background=SURFACE_COLOR_ALT, troughcolor=BG_COLOR, borderwidth=0, arrowsize=12)

    # --- SPINBOX ---
    style.configure('TSpinbox', 
                    background=SURFACE_COLOR_ALT, 
                    fieldbackground=SURFACE_COLOR_ALT, 
                    foreground=TEXT_COLOR, 
                    arrowcolor=ACCENT_GOLD,
                    insertcolor=ACCENT_GOLD,
                    darkcolor=SURFACE_COLOR_ALT,
                    lightcolor=SURFACE_COLOR_ALT,
                    bordercolor=BORDER_COLOR,
                    padding=(4, 2))
    style.map('TSpinbox', 
              fieldbackground=[('readonly', SURFACE_COLOR_ALT), ('disabled', BG_COLOR), ('focus', SURFACE_LIGHT)],
              foreground=[('disabled', TEXT_MUTED), ('!disabled', TEXT_COLOR)],
              bordercolor=[('focus', ACCENT_GOLD)])

    # --- CONFIGURAZIONI GLOBALI PER WIDGET TK CLASSICI ---
    root.option_add('*Canvas.background', BG_COLOR)
    root.option_add('*Canvas.highlightThickness', 0)
    root.option_add('*Listbox.background', SURFACE_COLOR)
    root.option_add('*Listbox.foreground', TEXT_COLOR)
    root.option_add('*Listbox.selectBackground', ACCENT_GOLD)
    root.option_add('*Listbox.selectForeground', TEXT_DARK)
    root.option_add('*Listbox.relief', 'flat')
    root.option_add('*Listbox.highlightThickness', 1)
    root.option_add('*Listbox.highlightColor', BORDER_COLOR)
    root.option_add('*Listbox.font', FONT_MAIN)

    root.option_add('*Text.background', SURFACE_COLOR)
    root.option_add('*Text.foreground', TEXT_COLOR)
    root.option_add('*Text.insertBackground', ACCENT_GOLD)
    root.option_add('*Text.relief', 'flat')
    root.option_add('*Text.font', FONT_MAIN)

    root.option_add('*Entry.background', SURFACE_COLOR_ALT)
    root.option_add('*Entry.foreground', TEXT_COLOR)
    root.option_add('*Entry.insertBackground', ACCENT_GOLD)
    root.option_add('*Entry.font', FONT_MAIN)

    root.option_add('*Spinbox.background', SURFACE_COLOR_ALT)
    root.option_add('*Spinbox.foreground', TEXT_COLOR)
    root.option_add('*Spinbox.insertBackground', ACCENT_GOLD)
    root.option_add('*Spinbox.buttonBackground', SURFACE_COLOR)
    root.option_add('*Spinbox.font', FONT_MAIN)

    root.option_add('*Menu.background', SURFACE_COLOR)
    root.option_add('*Menu.foreground', TEXT_COLOR)
    root.option_add('*Menu.activeBackground', ACCENT_GOLD)
    root.option_add('*Menu.activeForeground', TEXT_DARK)
    root.option_add('*Menu.font', FONT_MAIN)
    root.option_add('*Menu.relief', 'flat')

    root.configure(bg=BG_COLOR)


def apply_modern_window_style(win, bind_escape=True, center_on_parent=True):
    """
    Applica lo sfondo scuro consistente e i best pattern UX alle finestre Toplevel:
    - Chiusura rapida con tasto Esc (per i dialoghi modali Toplevel)
    - Centratura automatica rispetto alla finestra genitore o allo schermo
    """
    try:
        win.configure(bg=BG_COLOR)
    except Exception:
        pass

    if isinstance(win, tk.Toplevel):
        if bind_escape:
            try:
                win.bind("<Escape>", lambda e: win.destroy())
            except Exception:
                pass
        if center_on_parent:
            idle_id = None
            def _cleanup(e=None):
                nonlocal idle_id
                if e and getattr(e, "widget", None) != win:
                    return
                if idle_id is not None:
                    try:
                        win.after_cancel(idle_id)
                    except Exception:
                        pass
                    idle_id = None

            def _center():
                nonlocal idle_id
                idle_id = None
                try:
                    if not win.winfo_exists():
                        return
                    win.update_idletasks()
                    w = win.winfo_width()
                    h = win.winfo_height()
                    if w <= 1 or h <= 1:
                        w = win.winfo_reqwidth()
                        h = win.winfo_reqheight()
                    parent = win.master
                    if parent and parent.winfo_exists() and parent.winfo_width() > 100:
                        px = parent.winfo_rootx()
                        py = parent.winfo_rooty()
                        pw = parent.winfo_width()
                        ph = parent.winfo_height()
                        x = max(10, px + (pw - w) // 2)
                        y = max(10, py + (ph - h) // 2)
                    else:
                        sw = win.winfo_screenwidth()
                        sh = win.winfo_screenheight()
                        x = max(10, (sw - w) // 2)
                        y = max(10, (sh - h) // 2)
                    win.geometry(f"+{x}+{y}")
                except Exception:
                    pass
            try:
                idle_id = win.after_idle(_center)
                win.bind("<Destroy>", _cleanup, add="+")
            except Exception:
                pass

