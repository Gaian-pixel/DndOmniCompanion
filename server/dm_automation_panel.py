# server/dm_automation_panel.py
"""
Modulo per la gestione dello stile di conduzione della campagna (DM Agency vs Full Automation)
e per il rendering e la risoluzione delle azioni in sospeso (Pending Actions: danni e porte).
Decongestiona server/dm_gui.py estraendo la logica di interfaccia relativa all'automazione.
"""
import tkinter as tk
from tkinter import ttk, simpledialog
from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_COLOR, TEXT_MUTED, FONT_TITLE, FONT_BOLD, FONT_SMALL
)
from components.ui_components import ToolTip


def open_automation_settings_dialog(dm_gui):
    """Apre il dialogo a schede per configurare il profilo di automazione e gli 11 switch granulari."""
    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.minsize(680, 720)
    win.title("⚙️ Stile Gestione Campagna & Automazione DM")

    gs = dm_gui.server.game_state
    cur_mode = getattr(gs, "automation_mode", "hybrid")
    cur_settings = dict(getattr(gs, "automation_settings", {}))

    # Bottom Bar (packed first at bottom so it stays pinned)
    bottom = tk.Frame(win, bg=SURFACE_COLOR, padx=14, pady=10, highlightbackground=BORDER_COLOR, highlightthickness=1)
    bottom.pack(fill=tk.X, side=tk.BOTTOM)

    hdr = tk.Frame(win, bg=SURFACE_COLOR, padx=14, pady=12, highlightbackground=BORDER_COLOR, highlightthickness=1)
    hdr.pack(fill=tk.X, side=tk.TOP)
    tk.Label(hdr, text="⚙️ Stile di Gestione Campagna", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
    tk.Label(
        hdr, 
        text="Configura l'equilibrio tra automazione digitale e arbitraggio manuale del Dungeon Master.\nPreserva la narrazione, l'interpretazione al tavolo e l'agency di master e giocatori.",
        font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED, justify=tk.LEFT
    ).pack(anchor="w", pady=(4, 0))

    # Scrollable middle container
    canvas = tk.Canvas(win, bg=BG_COLOR, highlightthickness=0)
    scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=BG_COLOR, padx=12, pady=10)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    mode_var = tk.StringVar(value=cur_mode if cur_mode in ("manual", "hybrid", "full") else "hybrid")
    
    # Checkbox vars for all 11 mechanics
    auto_dmg_var = tk.BooleanVar(value=cur_settings.get("auto_apply_damage", True))
    auto_aoe_var = tk.BooleanVar(value=cur_settings.get("auto_apply_aoe_damage", True))
    auto_door_var = tk.BooleanVar(value=cur_settings.get("auto_resolve_doors", True))
    turn_lock_var = tk.BooleanVar(value=cur_settings.get("strict_turn_lock", False))
    move_limits_var = tk.BooleanVar(value=cur_settings.get("strict_movement_limits", True))
    reactions_var = tk.BooleanVar(value=cur_settings.get("auto_prompt_reactions", True))
    conc_var = tk.BooleanVar(value=cur_settings.get("auto_concentration_check", True))
    death_var = tk.BooleanVar(value=cur_settings.get("auto_death_saves", True))
    adv_var = tk.BooleanVar(value=cur_settings.get("auto_calc_advantage", True))
    fow_var = tk.BooleanVar(value=cur_settings.get("auto_explore_fow", True))
    rest_var = tk.BooleanVar(value=cur_settings.get("auto_apply_rest_recovery", True))

    def on_preset_selected():
        m = mode_var.get()
        if m == "manual":
            auto_dmg_var.set(False)
            auto_aoe_var.set(False)
            auto_door_var.set(False)
            turn_lock_var.set(False)
            move_limits_var.set(False)
            reactions_var.set(False)
            conc_var.set(False)
            death_var.set(False)
            adv_var.set(False)
            fow_var.set(False)
            rest_var.set(False)
        elif m == "hybrid":
            auto_dmg_var.set(False)
            auto_aoe_var.set(False)
            auto_door_var.set(True)
            turn_lock_var.set(False)
            move_limits_var.set(True)
            reactions_var.set(True)
            conc_var.set(True)
            death_var.set(True)
            adv_var.set(True)
            fow_var.set(True)
            rest_var.set(True)
        elif m == "full":
            auto_dmg_var.set(True)
            auto_aoe_var.set(True)
            auto_door_var.set(True)
            turn_lock_var.set(True)
            move_limits_var.set(True)
            reactions_var.set(True)
            conc_var.set(True)
            death_var.set(True)
            adv_var.set(True)
            fow_var.set(True)
            rest_var.set(True)

    tk.Label(scrollable_frame, text="PROFILI DI GESTIONE PREDEFINITI:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(2, 6))

    presets = [
        ("manual", "🎲 Tavolo Tradizionale (Pen & Paper / Controllo DM RAW)", 
         "Esperienza autentica cartacea. Progettata per chi ama narrare come attorno a un tavolo fisico con dadi e miniature: nessuna modifica critica alle schede avviene a scatola chiusa. I danni (singoli e AoE) attendono la convalida del DM, le porte e gli scassi lasciano spazio alla narrazione di serrature e trappole, il movimento non impone muri software invisibili, e la rottura di concentrazione o le morti sono arbitrate dal master senza rigidità."),
        ("hybrid", "⚖️ Ibrido Assistito (Consigliato per Sessioni Fluide)", 
         "L'equilibrio ideale tra narrazione e comodità moderna. Il sistema esegue tutti i calcoli matematici complessi RAW (resistenze, coperture, visibilità, condizioni, CD), ma fornisce al DM comode schede fluttuanti a 1-click ([Pieno], [Dimezza], [Modifica], [Annulla]) per convalidare i danni a colpo sicuro. Mantiene vivo e alto il ritmo della sessione senza togliere il controllo al DM."),
        ("full", "⚡ Full Automation (Tattico Rapido / CRPG)", 
         "Massima automazione istantanea per combattimenti tattici serrati o dungeon crawl ad alto ritmo. I danni vengono applicati immediatamente agli HP appena il colpo va a segno, le porte si aprono subito su successo della CD, i turni bloccano rigorosamente chi non è attivo e le reazioni/TS vengono richiesti e risolti all'istante senza pause.")
    ]

    for p_val, p_title, p_desc in presets:
        p_card = tk.Frame(scrollable_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        p_card.pack(fill=tk.X, pady=4)
        rb = ttk.Radiobutton(p_card, text=p_title, value=p_val, variable=mode_var, command=on_preset_selected)
        rb.pack(anchor="w")
        tk.Label(p_card, text=p_desc, font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, justify=tk.LEFT, wraplength=580).pack(anchor="w", padx=(20, 0), pady=(3, 0))

    tk.Label(scrollable_frame, text="REGOLAZIONE GRANULARE PER MECCANICA:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(14, 6))

    # Sezione 1: Combattimento & Danni
    sec1 = tk.LabelFrame(scrollable_frame, text=" ⚔️ Combattimento & Risoluzione Danni ", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD, padx=10, pady=8)
    sec1.pack(fill=tk.X, pady=4)

    ttk.Checkbutton(sec1, text="Sottrazione automatica danni da attacchi a segno", variable=auto_dmg_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, ogni colpo genera una scheda DM fluttuante con pulsanti [Pieno] [Dimezza] [Modifica] [Annulla].", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec1, text="Sottrazione automatica danni da incantesimi / tiri salvezza AoE", variable=auto_aoe_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, i danni delle magie ad area richiedono la conferma del DM per ciascun bersaglio coinvolto.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec1, text="Calcolo automatico Vantaggio / Svantaggio (2d20)", variable=adv_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, le condizioni suggeriscono il modificatore senza forzare il doppio dado, lasciando la scelta a master e giocatori.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec1, text="Prompt automatici per Reazioni (AdO, Incantesimo Scudo)", variable=reactions_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, le reazioni vengono chiamate verbalmente dai giocatori al tavolo senza popup modali invasivi.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec1, text="Verifica e rottura automatica Concentrazione su danno subito", variable=conc_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, notifica l'obbligo del TS Costituzione in chat ma non cancella automaticamente l'incantesimo.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec1, text="Risoluzione automatica 0 HP, Morte Istantanea e KO mostri", variable=death_var).pack(anchor="w", pady=2)
    tk.Label(sec1, text="  ↳ Se disattivato, il DM arbitra se una creatura a 0 HP viene uccisa, resa incosciente o si arrende narrativamente.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    # Sezione 2: Mappa, Movimento & Esplorazione
    sec2 = tk.LabelFrame(scrollable_frame, text=" 🗺️ Mappa, Movimento & Esplorazione ", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_BLUE, padx=10, pady=8)
    sec2.pack(fill=tk.X, pady=6)

    ttk.Checkbutton(sec2, text="Blocco turni rigoroso in combattimento", variable=turn_lock_var).pack(anchor="w", pady=2)
    tk.Label(sec2, text="  ↳ Se attivo, solo la creatura attualmente di turno nell'iniziativa può muoversi o spendere azioni.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec2, text="Blocco rigido velocità massima (Speed) e costo Terreno Difficile", variable=move_limits_var).pack(anchor="w", pady=2)
    tk.Label(sec2, text="  ↳ Se disattivato, registra la distanza percorsa senza imporre muri software invalicabili all'arbitrio del tavolo.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec2, text="Risoluzione automatica prove scasso / sfondamento porte in base alla CD", variable=auto_door_var).pack(anchor="w", pady=2)
    tk.Label(sec2, text="  ↳ Se disattivato, il tiro mostra il dettaglio e il DM decide se la porta cede, resiste o innesca trabocchetti.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    ttk.Checkbutton(sec2, text="Svelamento dinamico automatico Nebbia di Guerra (FoW) attorno ai token", variable=fow_var).pack(anchor="w", pady=2)
    tk.Label(sec2, text="  ↳ Se disattivato, il DM rivela manualmente le aree della mappa preservando la suspense senza spoiler accidentali.", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    # Sezione 3: Riposo & Risorse
    sec3 = tk.LabelFrame(scrollable_frame, text=" ⛺ Riposo & Recupero Risorse ", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GREEN, padx=10, pady=8)
    sec3.pack(fill=tk.X, pady=6)

    ttk.Checkbutton(sec3, text="Ripristino automatico istantaneo Risorse al Riposo (HP, Slot, Dadi Vita)", variable=rest_var).pack(anchor="w", pady=2)
    tk.Label(sec3, text="  ↳ Se disattivato, la richiesta di riposo richiede conferma del DM (ideale per verificare incontri casuali notturni).", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

    def save_and_close():
        sel_mode = mode_var.get()
        new_settings = {
            "auto_apply_damage": bool(auto_dmg_var.get()),
            "auto_apply_aoe_damage": bool(auto_aoe_var.get()),
            "auto_resolve_doors": bool(auto_door_var.get()),
            "strict_turn_lock": bool(turn_lock_var.get()),
            "strict_movement_limits": bool(move_limits_var.get()),
            "auto_prompt_reactions": bool(reactions_var.get()),
            "auto_concentration_check": bool(conc_var.get()),
            "auto_death_saves": bool(death_var.get()),
            "auto_calc_advantage": bool(adv_var.get()),
            "auto_explore_fow": bool(fow_var.get()),
            "auto_apply_rest_recovery": bool(rest_var.get())
        }
        from server.rules.combat import handle_set_automation_mode_request
        handle_set_automation_mode_request({"mode": sel_mode, "settings": new_settings}, None, dm_gui.server.game_state)
        dm_gui.update_player_list()
        dm_gui.show_toast(f"Stile automazione impostato su: {sel_mode.upper()}", title="⚙️ Automazione", toast_type="success")
        win.destroy()

    btn_save = ttk.Button(bottom, text="💾 Salva ed Applica", style="Primary.TButton", command=save_and_close)
    btn_save.pack(side=tk.RIGHT, padx=4)
    btn_cancel = ttk.Button(bottom, text="Annulla", style="Tool.TButton", command=win.destroy)
    btn_cancel.pack(side=tk.RIGHT)


def update_pending_actions_ui(dm_gui):
    """Aggiorna il contenitore fluttuante delle azioni in sospeso (Danni e Porte)."""
    if not hasattr(dm_gui, "pending_actions_container") or not hasattr(dm_gui, "server") or not hasattr(dm_gui.server, "game_state"):
        return
        
    gs = dm_gui.server.game_state
    p_damages = getattr(gs, "pending_damages", {})
    p_doors = getattr(gs, "pending_doors", {})
    
    if not p_damages and not p_doors:
        dm_gui.pending_actions_container.pack_forget()
        return
        
    for widget in dm_gui.pending_actions_container.winfo_children():
        widget.destroy()
        
    if hasattr(dm_gui, "dm_quick_dice_strip"):
        dm_gui.pending_actions_container.pack(fill=tk.X, pady=(4, 2), before=dm_gui.dm_quick_dice_strip)
    else:
        dm_gui.pending_actions_container.pack(fill=tk.X, pady=(4, 2))
        
    hdr_frame = tk.Frame(dm_gui.pending_actions_container, bg=SURFACE_COLOR_ALT)
    hdr_frame.pack(fill=tk.X, pady=(0, 4))
    tk.Label(
        hdr_frame, text="⚡ DECISIONI DM IN SOSPESO", 
        font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD
    ).pack(side=tk.LEFT)
    total_count = len(p_damages) + len(p_doors)
    tk.Label(
        hdr_frame, text=f"({total_count})", 
        font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED
    ).pack(side=tk.LEFT, padx=4)
    
    # Schede Danni
    for p_id, p_info in list(p_damages.items()):
        card = tk.Frame(dm_gui.pending_actions_container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=4)
        card.pack(fill=tk.X, pady=2)
        
        atk = p_info.get("attacker", "Attaccante")
        tgt = p_info.get("target", "Bersaglio")
        raw_dmg = p_info.get("raw_damage", 0)
        dmg_type = p_info.get("damage_type", "Danno")
        is_crit = p_info.get("is_crit", False)
        wpn = p_info.get("weapon_name", "Attacco")
        
        crit_badge = " 🌟 CRITICO" if is_crit else ""
        txt_info = f"⚔️ {atk} -> {tgt} ({wpn}){crit_badge}: {raw_dmg} {dmg_type}"
        tk.Label(card, text=txt_info, font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR, anchor="w").pack(fill=tk.X)
        
        btns = tk.Frame(card, bg=SURFACE_COLOR)
        btns.pack(fill=tk.X, pady=(3, 0))
        
        btn_full = ttk.Button(btns, text="Pieno", style="Primary.TButton", command=lambda i=p_id: dm_gui.apply_pending_damage_gui(i, "apply"))
        btn_full.pack(side=tk.LEFT, padx=(0, 2))
        ToolTip(btn_full, f"Applica danno intero ({raw_dmg} {dmg_type}) con resistenze/immunità della scheda")
        
        btn_half = ttk.Button(btns, text="Dimezza", style="Gold.TButton", command=lambda i=p_id: dm_gui.apply_pending_damage_gui(i, "half"))
        btn_half.pack(side=tk.LEFT, padx=2)
        ToolTip(btn_half, f"Applica danno dimezzato ({max(1, raw_dmg // 2)} {dmg_type})")
        
        btn_custom = ttk.Button(btns, text="Modifica", style="Tool.TButton", command=lambda i=p_id, r=raw_dmg: dm_gui.apply_pending_damage_custom_gui(i, r))
        btn_custom.pack(side=tk.LEFT, padx=2)
        ToolTip(btn_custom, "Inserisci manualmente l'ammontare esatto di danno")
        
        btn_cancel = ttk.Button(btns, text="Annulla", style="Danger.TButton", command=lambda i=p_id: dm_gui.apply_pending_damage_gui(i, "cancel"))
        btn_cancel.pack(side=tk.LEFT, padx=2)
        ToolTip(btn_cancel, "Annulla e azzera questo danno (nessun HP sottratto)")

    # Schede Porte / Scasso
    for p_id, p_info in list(p_doors.items()):
        card = tk.Frame(dm_gui.pending_actions_container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=6, pady=4)
        card.pack(fill=tk.X, pady=2)
        
        p_name = p_info.get("player_name", "Giocatore")
        d_name = p_info.get("door_name", "Porta")
        method = p_info.get("method", "interazione")
        method_str = "Scasso" if method == "lockpick" else "Sfondamento"
        roll = p_info.get("roll", 0)
        dc = p_info.get("dc", 15)
        sugg = " (Suggerito: SUCCESSO)" if p_info.get("success_suggested") else " (Suggerito: FALLITO)"
        
        txt_info = f"🚪 {p_name} tenta {method_str} su {d_name} [Tiro {roll} vs CD {dc}]{sugg}"
        tk.Label(card, text=txt_info, font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD, anchor="w").pack(fill=tk.X)
        
        btns = tk.Frame(card, bg=SURFACE_COLOR)
        btns.pack(fill=tk.X, pady=(3, 0))
        
        btn_open = ttk.Button(btns, text="Spalanca", style="Primary.TButton", command=lambda i=p_id: dm_gui.resolve_pending_door_gui(i, "open"))
        btn_open.pack(side=tk.LEFT, padx=(0, 2))
        ToolTip(btn_open, f"La porta cede e si apre dinanzi a {p_name}")
        
        btn_lock = ttk.Button(btns, text="Resiste / Bloccata", style="Gold.TButton", command=lambda i=p_id: dm_gui.resolve_pending_door_gui(i, "locked"))
        btn_lock.pack(side=tk.LEFT, padx=2)
        ToolTip(btn_lock, "La serratura resiste e la porta rimane chiusa a chiave")
        
        btn_trap = ttk.Button(btns, text="Scatta Trappola", style="Danger.TButton", command=lambda i=p_id: dm_gui.resolve_pending_door_gui(i, "trap"))
        btn_trap.pack(side=tk.LEFT, padx=2)
        ToolTip(btn_trap, "Il tentativo goffo fa scattare una trappola o allarme")


def apply_pending_damage_gui(dm_gui, pending_id, action):
    """Invia al rules engine la risoluzione del danno in sospeso."""
    from server.rules.combat import handle_apply_pending_damage_request
    handle_apply_pending_damage_request({"pending_id": pending_id, "action": action}, None, dm_gui.server.game_state)
    dm_gui.update_pending_actions_ui()


def apply_pending_damage_custom_gui(dm_gui, pending_id, default_amount):
    """Chiede al DM l'importo personalizzato e lo applica."""
    val = simpledialog.askinteger("Danno Personalizzato", "Inserisci l'ammontare di danno da infliggere:", initialvalue=default_amount, minvalue=0, parent=dm_gui.master)
    if val is not None:
        from server.rules.combat import handle_apply_pending_damage_request
        handle_apply_pending_damage_request({"pending_id": pending_id, "action": "custom", "custom_amount": val}, None, dm_gui.server.game_state)
        dm_gui.update_pending_actions_ui()


def resolve_pending_door_gui(dm_gui, pending_id, outcome):
    """Invia al rules engine l'esito dello scasso o sfondamento della porta."""
    from server.rules.map_interaction import handle_resolve_pending_door_request
    handle_resolve_pending_door_request({"pending_id": pending_id, "outcome": outcome}, None, dm_gui.server.game_state)
    dm_gui.update_pending_actions_ui()

