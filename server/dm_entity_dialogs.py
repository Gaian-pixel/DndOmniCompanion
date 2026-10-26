# server/dm_entity_dialogs.py
"""
Modulo per i dialoghi dedicati alla gestione delle entità (giocatori, NPC, boss leggendari),
delle spille di stanza (Room Pins), delle trappole e della configurazione del combattimento.
Decongestiona server/dm_gui.py estraendo finestre secondarie e dialoghi specialistici.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
import random

from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_COLOR, TEXT_MUTED, FONT_TITLE, FONT_HEADER, FONT_BOLD, FONT_MAIN, FONT_SMALL
)
from common.hex_utils import Hex
from common.network_utils import send_message, broadcast
from common.i18n import _t


def open_combat_config(dm_gui, initiator_name=None):
    """Apre il dialogo di configurazione combattimento, selezione partecipanti e iniziativa NPC."""
    if dm_gui.server.game_state.combat_active:
        messagebox.showinfo(_t("combat", default="Combattimento"), _t("msg_combat_already_running", default="Un combattimento è già in corso."))
        return

    all_players = dm_gui.server.game_state.get_all_players()
    if not all_players:
        messagebox.showinfo(_t("combat", default="Combattimento"), _t("msg_no_players_combat", default="Nessun personaggio/NPC per iniziare il combattimento."))
        return

    dialog = tk.Toplevel(dm_gui.master)
    dialog.title(_t("combat_config_title", default="Configurazione Combattimento"))
    dialog.minsize(400, 550)
    dialog.transient(dm_gui.master)
    dialog.grab_set()
    apply_modern_window_style(dialog)

    if initiator_name:
        ttk.Label(dialog, text=f"{initiator_name} ha richiesto l'inizio del combattimento!", font=dm_gui.default_font, foreground="#D4AF37").pack(pady=(10, 5))

    # Filtro per distanza
    filter_frame = ttk.LabelFrame(dialog, text=_t("combat_filter_distance", default="Filtro per Distanza (Auto-selezione)"))
    filter_frame.pack(fill=tk.X, padx=10, pady=5)
    
    ttk.Label(filter_frame, text=_t("combat_origin", default="Origine:")).grid(row=0, column=0, padx=5, pady=5, sticky="e")
    origin_var = tk.StringVar(value=initiator_name if initiator_name else all_players[0].name)
    origin_combo = ttk.Combobox(filter_frame, textvariable=origin_var, values=[p.name for p in all_players], state="readonly")
    origin_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
    
    ttk.Label(filter_frame, text=_t("combat_radius_hex", default="Raggio (esagoni):")).grid(row=1, column=0, padx=5, pady=5, sticky="e")
    radius_var = tk.StringVar(value="6")
    ttk.Entry(filter_frame, textvariable=radius_var, width=5).grid(row=1, column=1, padx=5, pady=5, sticky="w")
    
    checkbox_vars = {}
    def apply_filter():
        origin_name = origin_var.get()
        try:
            rad = int(radius_var.get())
        except (ValueError, TypeError):
            rad = 0
        
        origin_p = dm_gui.server.game_state.find_player(origin_name)
        if not origin_p: return
        o_hex = Hex(origin_p.position[0], origin_p.position[1])
        
        for p in all_players:
            p_hex = Hex(p.position[0], p.position[1])
            dist = o_hex.distance(p_hex)
            checkbox_vars[p.name].set(dist <= rad)

    ttk.Button(filter_frame, text=_t("btn_select_nearby", default="Seleziona Vicini"), command=apply_filter).grid(row=1, column=2, padx=5, pady=5)

    ttk.Label(dialog, text=_t("combat_participants", default="Partecipanti:"), font=dm_gui.default_font).pack(pady=(10,0))

    listbox_frame = ttk.Frame(dialog)
    listbox_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    canvas = tk.Canvas(listbox_frame, bg=SURFACE_COLOR, highlightthickness=0)
    scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Create checkboxes
    for p in all_players:
        var = tk.BooleanVar(value=True)
        checkbox_vars[p.name] = var
        ttk.Checkbutton(scrollable_frame, text=f"{p.name} (HP: {p.hp}/{p.max_hp})", variable=var).pack(anchor="w", pady=2)

    def finalize_combat(selected_names, npc_initiatives):
        dm_gui.server.game_state.start_combat(participant_names=selected_names)
        if hasattr(dm_gui, "_auto_play_battle_music"):
            dm_gui._auto_play_battle_music()
        dm_gui.server.game_state.add_calendar_event(f"Combattimento Iniziato (Partecipanti: {len(selected_names)})")
        
        from common.protocol import make_request_initiative, make_player_stats_update
        for p in dm_gui.server.game_state.get_all_players():
            if p.name in selected_names:
                if p.conn is None: # NPC
                    p.initiative = npc_initiatives.get(p.name, p.initiative)
                    dm_gui.log_to_chat(f"[COMBAT] {p.name} (NPC) iniziativa: {p.initiative}")
                    broadcast(dm_gui.server.game_state, make_player_stats_update(p.name, p.hp, p.max_hp, p.initiative, p.conditions))
                else: # Player
                    send_message(p.conn, make_request_initiative())
        
        dm_gui.log_to_chat("[SISTEMA] Inizio Combattimento!")
        from common.protocol import make_chat_broadcast, make_game_state
        broadcast(dm_gui.server.game_state, make_chat_broadcast("Sistema", "Inizio Combattimento! Ai giocatori è stata richiesta l'iniziativa."))
        
        # Re-sort state and update
        dm_gui.server.game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
        dm_gui.server.game_state._trigger_gui_update()
        broadcast(dm_gui.server.game_state, make_game_state(dm_gui.server.game_state.get_state_dict()))
        dialog.destroy()

    def confirm():
        selected_names = [name for name, var in checkbox_vars.items() if var.get()]
        if not selected_names:
            messagebox.showwarning(_t("warning", default="Attenzione"), _t("msg_select_at_least_one_participant", default="Seleziona almeno un partecipante."))
            return
        
        npcs_in_combat = [p for p in dm_gui.server.game_state.get_all_players() if p.name in selected_names and p.conn is None]
        
        if not npcs_in_combat:
            finalize_combat(selected_names, {})
            return
            
        # Mostra dialog per l'iniziativa degli NPC
        init_dialog = tk.Toplevel(dialog)
        init_dialog.title(_t("npc_init_dialog_title", default="Iniziativa NPC"))
        init_dialog.minsize(300, 400)
        init_dialog.transient(dialog)
        init_dialog.grab_set()
        apply_modern_window_style(init_dialog)
        
        ttk.Label(init_dialog, text=_t("npc_init_dialog_prompt", default="Inserisci l'iniziativa per gli NPC:"), font=dm_gui.default_font).pack(pady=10)
        
        entries = {}
        frame = ttk.Frame(init_dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Canvas per scrollare se ci sono troppi NPC
        c = tk.Canvas(frame, bg=SURFACE_COLOR, highlightthickness=0)
        s = ttk.Scrollbar(frame, orient="vertical", command=c.yview)
        sf = ttk.Frame(c)
        sf.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))
        c.create_window((0, 0), window=sf, anchor="nw")
        c.configure(yscrollcommand=s.set)
        c.pack(side="left", fill="both", expand=True)
        s.pack(side="right", fill="y")
        
        for npc in npcs_in_combat:
            row = ttk.Frame(sf)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=npc.name, width=15).pack(side=tk.LEFT)
            auto_roll = random.randint(1, 20) + npc.initiative
            var = tk.StringVar(value=str(auto_roll))
            entries[npc.name] = var
            ttk.Entry(row, textvariable=var, width=5).pack(side=tk.RIGHT)
            
        def submit_init():
            npc_initiatives = {}
            for name, var in entries.items():
                try:
                    npc_initiatives[name] = int(var.get())
                except ValueError:
                    npc_initiatives[name] = 0
            init_dialog.destroy()
            finalize_combat(selected_names, npc_initiatives)
            
        ttk.Button(init_dialog, text=_t("btn_confirm_initiatives", default="Conferma Iniziative"), command=submit_init, style="Primary.TButton").pack(pady=10)

    ttk.Button(dialog, text=_t("btn_next", default="Avanti"), command=confirm, style='Primary.TButton').pack(pady=15)


def open_room_pin_dialog(dm_gui, pin, clicked_hex):
    """Apre il dialogo della spilla di stanza (Room Pin) con testo narrativo e note segrete DM."""
    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.minsize(520, 520)
    
    is_new = (pin is None)
    title_str = pin.get("title", f"Stanza [{clicked_hex.q}, {clicked_hex.r}]") if pin else f"Stanza [{clicked_hex.q}, {clicked_hex.r}]"
    read_aloud_str = pin.get("read_aloud", "") if pin else ""
    dm_notes_str = pin.get("dm_notes", "") if pin else ""
    
    win.title(f"📌 Spilla Stanza - {title_str}")

    hdr = tk.Frame(win, bg=SURFACE_COLOR, padx=12, pady=8)
    hdr.pack(fill=tk.X)
    tk.Label(hdr, text="Titolo Stanza / Area:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT, padx=(0, 8))
    title_entry = ttk.Entry(hdr, width=28)
    title_entry.insert(0, title_str)
    title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    body = tk.Frame(win, bg=BG_COLOR, padx=12, pady=8)
    body.pack(fill=tk.BOTH, expand=True)

    tk.Label(body, text="📜 Testo da Leggere ad Alta Voce (Descrizione per i Giocatori):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w", pady=(4, 2))
    txt_read_aloud = scrolledtext.ScrolledText(body, height=6, bg="#1E232A", fg="#F1F5F9", insertbackground="#F1F5F9", font=("Georgia", 10))
    txt_read_aloud.insert("1.0", read_aloud_str)
    txt_read_aloud.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    btn_broadcast_box = tk.Frame(body, bg=BG_COLOR)
    btn_broadcast_box.pack(fill=tk.X, pady=(0, 8))
    def broadcast_read_aloud():
        cur_title = title_entry.get().strip() or "Descrizione Stanza"
        text_to_read = txt_read_aloud.get("1.0", tk.END).strip()
        if not text_to_read:
            messagebox.showwarning("Testo Vuoto", "Non c'è alcun testo da leggere ad alta voce!", parent=win)
            return
        from common.protocol import make_chat_broadcast
        msg = f"📜 [{cur_title}]\n\"{text_to_read}\""
        broadcast(dm_gui.server.game_state, make_chat_broadcast("Narratore (DM)", msg))
        dm_gui.server.game_state.log_dm_message(f"[NARRATORE] {cur_title}: {text_to_read}")
        dm_gui.show_toast(f"Testo letto al gruppo: [{cur_title}]", title="📢 Narratore", toast_type="success")

    ttk.Button(btn_broadcast_box, text="📢 Leggi al Gruppo (Narratore in Chat)", command=broadcast_read_aloud, style="Primary.TButton").pack(side=tk.LEFT)

    tk.Label(body, text="🔒 Note Segrete del DM (Mostri, Trappole, Tesori, Tattiche):", font=FONT_BOLD, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(4, 2))
    txt_dm_notes = scrolledtext.ScrolledText(body, height=6, bg="#181B20", fg="#FCD34D", insertbackground="#FCD34D", font=("Segoe UI", 10))
    txt_dm_notes.insert("1.0", dm_notes_str)
    txt_dm_notes.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

    btns_row = tk.Frame(win, bg=SURFACE_COLOR, padx=12, pady=10)
    btns_row.pack(fill=tk.X)

    def save_pin():
        cur_title = title_entry.get().strip() or f"Stanza [{clicked_hex.q}, {clicked_hex.r}]"
        cur_read = txt_read_aloud.get("1.0", tk.END).strip()
        cur_notes = txt_dm_notes.get("1.0", tk.END).strip()
        pins = dm_gui.server.game_state.current_map.setdefault("room_pins", [])
        pin_data = pin if pin else {}
        pin_data["id"] = pin_data.get("id", f"pin_{clicked_hex.q}_{clicked_hex.r}")
        pin_data["q"] = clicked_hex.q
        pin_data["r"] = clicked_hex.r
        pin_data["title"] = cur_title
        pin_data["read_aloud"] = cur_read
        pin_data["dm_notes"] = cur_notes
        if is_new and pin_data not in pins:
            pins.append(pin_data)
        from common.protocol import make_map_data_update_broadcast
        broadcast(dm_gui.server.game_state, make_map_data_update_broadcast(dm_gui.server.game_state.current_map))
        dm_gui.server.game_state._trigger_gui_update()
        dm_gui.redraw_map_and_players()
        dm_gui.show_toast(f"Spilla salvata: {cur_title}", title="📌 Spilla Salvata", toast_type="success")
        win.destroy()

    def delete_pin():
        if is_new:
            win.destroy()
            return
        if messagebox.askyesno("Elimina Spilla", "Sei sicuro di voler eliminare questa spilla dalla mappa?", parent=win):
            pins = dm_gui.server.game_state.current_map.get("room_pins", [])
            if pin in pins:
                pins.remove(pin)
            from common.protocol import make_map_data_update_broadcast
            broadcast(dm_gui.server.game_state, make_map_data_update_broadcast(dm_gui.server.game_state.current_map))
            dm_gui.server.game_state._trigger_gui_update()
            dm_gui.redraw_map_and_players()
            dm_gui.show_toast("Spilla rimossa dalla mappa.", title="📌 Spilla Eliminata", toast_type="info")
            win.destroy()

    ttk.Button(btns_row, text="💾 Salva Spilla", command=save_pin, style="Success.TButton").pack(side=tk.LEFT, padx=(0, 6))
    if not is_new:
        ttk.Button(btns_row, text="🗑️ Elimina", command=delete_pin, style="Danger.TButton").pack(side=tk.LEFT)
    ttk.Button(btns_row, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT)


def open_assign_item_dialog(dm_gui, prefill_item=None):
    """Apre il dialogo per assegnare un oggetto dall'inventario a un giocatore."""
    sel = dm_gui.player_listbox.curselection()
    if not sel:
        messagebox.showinfo("Attenzione", "Seleziona prima un giocatore dalla lista a cui assegnare l'oggetto.")
        return
        
    display_text = dm_gui.player_listbox.get(sel[0])
    if display_text.startswith('---'): return
    player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"Assegna Oggetto a {player_name}")
    win.minsize(320, 260)

    ttk.Label(win, text="Nome Oggetto:").pack(pady=(10, 0))
    name_entry = ttk.Entry(win)
    name_entry.pack(fill=tk.X, padx=20, pady=5)

    ttk.Label(win, text="Descrizione:").pack(pady=(5, 0))
    desc_entry = ttk.Entry(win)
    desc_entry.pack(fill=tk.X, padx=20, pady=5)

    ttk.Label(win, text="Quantità:").pack(pady=(5, 0))
    qty_entry = ttk.Entry(win)
    qty_entry.insert(0, "1")
    qty_entry.pack(fill=tk.X, padx=20, pady=5)

    if prefill_item:
        name_entry.insert(0, prefill_item.get("name", ""))
        desc_entry.insert(0, prefill_item.get("desc", prefill_item.get("description", "")))
        qty_entry.delete(0, tk.END)
        qty_entry.insert(0, str(prefill_item.get("quantity", 1)))

    def submit():
        name = name_entry.get().strip()
        if not name:
            messagebox.showerror("Errore", "Il nome dell'oggetto è obbligatorio.")
            return
        desc = desc_entry.get().strip()
        try:
            qty = int(qty_entry.get().strip())
        except ValueError:
            messagebox.showerror("Errore", "La quantità deve essere un numero intero.")
            return

        item = {"name": name, "desc": desc, "quantity": qty}
        
        # Aggiungi all'inventario del giocatore
        with dm_gui.server.game_state.lock:
            if hasattr(player, "inventory"):
                player.inventory.append(item)
            else:
                player.inventory = [item]
                
        dm_gui.server.game_state._trigger_gui_update()
        dm_gui.log_to_chat(f"[SISTEMA] Assegnato {qty}x {name} a {player_name}")
        
        from common.protocol import make_receive_item
        if player.conn:
            send_message(player.conn, make_receive_item(item))
        messagebox.showinfo("Successo", f"Oggetto inviato a {player_name}!")
        win.destroy()

    ttk.Button(win, text="Assegna", command=submit).pack(pady=20)


def open_modify_hp_dialog(dm_gui):
    """Apre il dialogo rapido per la variazione manuale degli HP di un token."""
    sel = dm_gui.player_listbox.curselection()
    if not sel: return
    display_text = dm_gui.player_listbox.get(sel[0])
    if display_text.startswith('---'): return
    player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    delta_str = simpledialog.askstring("Modifica HP", f"Inserisci variazione HP per {player_name}\n(es. -5 per danno, +8 per cura):")
    if not delta_str: return
    
    try:
        delta = int(delta_str)
        with dm_gui.server.game_state.lock:
            player.hp = max(0, min(player.max_hp, player.hp + delta))
        dm_gui.server.game_state._trigger_gui_update()
        from common.protocol import make_player_stats_update
        broadcast(dm_gui.server.game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative))
        dm_gui.log_to_chat(f"[SISTEMA] HP di {player.name} aggiornati a {player.hp}/{player.max_hp}")
    except ValueError:
        messagebox.showerror("Errore", "Valore non valido.")


def open_conditions_dialog(dm_gui):
    """Apre la checklist delle condizioni 5e e la gestione effetti a tempo / Save-Ends per la pedina selezionata."""
    sel = dm_gui.player_listbox.curselection()
    if not sel: return
    display_text = dm_gui.player_listbox.get(sel[0])
    if display_text.startswith('---'): return
    player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    from common.effects_data import get_effect_presets, create_effect_instance
    from common.protocol import make_player_stats_update, make_chat_broadcast

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"{_t('tab_conditions_standard', default='Stati')} - {player_name}")
    win.minsize(440, 540)

    notebook = ttk.Notebook(win)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    # --- TAB 1: Condizioni Standard ---
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text=_t("tab_conditions_standard", default="Condizioni Standard"))

    ttk.Label(tab1, text=f"{_t('active_conditions_label', default='Condizioni Attive per')} {player_name}:").pack(pady=5)
    
    listbox = tk.Listbox(tab1, bg=SURFACE_COLOR, fg=TEXT_COLOR, selectmode=tk.MULTIPLE, font=dm_gui.default_font)
    listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    all_conditions = [
        "Accecato", "Affascinato", "Assordato", "Avvelenato", "In Fiamme", 
        "Invisibile", "Prono", "Spaventato", "Stordito", "Incosciente", 
        "Trattenuto", "Pietrificato", "Schivata", "Concentrazione", "Ira"
    ]
    
    for i, cond in enumerate(all_conditions):
        listbox.insert(tk.END, cond)
        if hasattr(player, "conditions") and cond in player.conditions:
            listbox.selection_set(i)

    def apply_conditions():
        selected_indices = listbox.curselection()
        new_conditions = [listbox.get(i) for i in selected_indices]
        with dm_gui.server.game_state.lock:
            player.conditions = new_conditions
        dm_gui.server.game_state._trigger_gui_update()
        broadcast(dm_gui.server.game_state, make_player_stats_update(
            player.name, player.hp, player.max_hp, player.initiative, new_conditions,
            getattr(player, "temp_hp", 0), active_effects=getattr(player, "active_effects", [])
        ))
        dm_gui.log_to_chat(f"[SISTEMA] Condizioni di {player.name} aggiornate: {', '.join(new_conditions) if new_conditions else 'Nessuna'}")
        win.destroy()

    ttk.Button(tab1, text=_t("apply", default="Applica Condizioni"), command=apply_conditions, style="Primary.TButton").pack(pady=10)

    # --- TAB 2: Effetti a Tempo & Save-Ends (5e) ---
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text=_t("tab_effects_timed", default="Effetti a Tempo & Save-Ends"))

    # Lista Effetti Attivi Correnti
    lbl_cur = ttk.Label(tab2, text=_t("active_effects_label", default="Effetti Attivi:") + f" ({player_name})", font=FONT_BOLD)
    lbl_cur.pack(anchor="w", padx=10, pady=(10, 4))

    fx_container = ttk.Frame(tab2)
    fx_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

    fx_list_canvas = tk.Canvas(fx_container, bg=SURFACE_COLOR, highlightthickness=0, height=120)
    fx_scroll = ttk.Scrollbar(fx_container, orient="vertical", command=fx_list_canvas.yview)
    fx_scroll_frame = ttk.Frame(fx_list_canvas)

    fx_scroll_frame.bind(
        "<Configure>",
        lambda e: fx_list_canvas.configure(scrollregion=fx_list_canvas.bbox("all"))
    )
    fx_list_canvas.create_window((0, 0), window=fx_scroll_frame, anchor="nw")
    fx_list_canvas.configure(yscrollcommand=fx_scroll.set)

    fx_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    fx_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def refresh_fx_list():
        for widget in fx_scroll_frame.winfo_children():
            widget.destroy()

        active_fxs = getattr(player, "active_effects", [])
        if not active_fxs:
            ttk.Label(fx_scroll_frame, text=_t("no_active_effects", default="Nessun effetto a tempo attivo."), foreground=TEXT_MUTED).pack(pady=10, padx=10)
            return

        for fx in active_fxs:
            row = ttk.Frame(fx_scroll_frame)
            row.pack(fill=tk.X, expand=True, pady=2, padx=4)

            icon = fx.get("icon", "✨")
            name = fx.get("name", "Effetto")
            dur = fx.get("duration_rounds")
            dur_str = f"{dur}r" if dur is not None and dur > 0 else "indefinito"
            save = fx.get("save_ends")
            save_str = f" [TS {save.get('stat')} CD {save.get('dc')}]" if save else ""
            desc = f"{icon} {name} ({dur_str}){save_str}"

            ttk.Label(row, text=desc, font=FONT_MAIN).pack(side=tk.LEFT, padx=5)

            eff_id = fx.get("id") or name
            def make_remove_cmd(eid):
                return lambda: remove_fx(eid)

            btn_del = ttk.Button(row, text="🗑️", width=3, command=make_remove_cmd(eff_id))
            btn_del.pack(side=tk.RIGHT, padx=5)

    def remove_fx(eff_id):
        with dm_gui.server.game_state.lock:
            player.remove_effect(eff_id)
        refresh_fx_list()
        dm_gui.server.game_state._trigger_gui_update()
        broadcast(dm_gui.server.game_state, make_player_stats_update(
            player.name, player.hp, player.max_hp, player.initiative, player.conditions,
            getattr(player, "temp_hp", 0), active_effects=getattr(player, "active_effects", [])
        ))
        dm_gui.log_to_chat(f"[EFFETTI] Rimosso effetto da {player.name}.")

    refresh_fx_list()

    # Sezione Aggiungi Preset 5e
    preset_frame = ttk.LabelFrame(tab2, text=_t("add_preset_effect", default="Applica Preset 5e"))
    preset_frame.pack(fill=tk.X, padx=10, pady=8)

    presets = get_effect_presets()
    preset_map = {f"{p['icon']} {p['name']} ({p['duration_rounds']}r)": p for p in presets}
    preset_combo_vals = list(preset_map.keys())

    preset_var = tk.StringVar(value=preset_combo_vals[0] if preset_combo_vals else "")
    preset_combo = ttk.Combobox(preset_frame, textvariable=preset_var, values=preset_combo_vals, state="readonly")
    preset_combo.pack(fill=tk.X, padx=8, pady=5)

    def apply_preset():
        selected_label = preset_var.get()
        p_data = preset_map.get(selected_label)
        if not p_data: return
        instance = create_effect_instance(
            p_data["key"],
            source="DM",
            dc=p_data["save_ends"]["dc"] if p_data.get("save_ends") else None,
            stat=p_data["save_ends"]["stat"] if p_data.get("save_ends") else None,
            duration_rounds=p_data["duration_rounds"],
            condition=p_data.get("condition"),
            icon=p_data.get("icon")
        )
        with dm_gui.server.game_state.lock:
            player.add_effect(instance)
        refresh_fx_list()
        dm_gui.server.game_state._trigger_gui_update()
        broadcast(dm_gui.server.game_state, make_player_stats_update(
            player.name, player.hp, player.max_hp, player.initiative, player.conditions,
            getattr(player, "temp_hp", 0), active_effects=getattr(player, "active_effects", [])
        ))
        broadcast(dm_gui.server.game_state, make_chat_broadcast("Sistema", f"✨ Applicato '{instance['name']}' a {player.name} ({instance['duration_rounds']} round)!"))
        dm_gui.log_to_chat(f"[EFFETTI] Applicato '{instance['name']}' a {player.name}.")

    ttk.Button(preset_frame, text=_t("btn_add_preset", default="Applica Preset Selezionato"), command=apply_preset, style="Accent.TButton").pack(pady=5)

    # Sezione Effetto Personalizzato
    cust_frame = ttk.LabelFrame(tab2, text=_t("custom_effect_title", default="Effetto Personalizzato"))
    cust_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

    row_c1 = ttk.Frame(cust_frame)
    row_c1.pack(fill=tk.X, padx=8, pady=3)
    ttk.Label(row_c1, text=_t("lbl_effect_name", default="Nome:")).pack(side=tk.LEFT)
    ent_cust_name = ttk.Entry(row_c1, width=15)
    ent_cust_name.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

    ttk.Label(row_c1, text="Icona:").pack(side=tk.LEFT, padx=(5, 0))
    icon_var = tk.StringVar(value="✨")
    icon_combo = ttk.Combobox(row_c1, textvariable=icon_var, values=["✨", "🛡️", "⚡", "🧊", "🔮", "🔥", "🟢", "😱", "🐌", "🙈", "👑"], width=3, state="readonly")
    icon_combo.pack(side=tk.LEFT, padx=5)

    ttk.Label(row_c1, text=_t("lbl_effect_duration", default="Round:")).pack(side=tk.LEFT, padx=(5, 0))
    spin_dur = ttk.Spinbox(row_c1, from_=1, to=100, width=4)
    spin_dur.set(10)
    spin_dur.pack(side=tk.LEFT, padx=5)

    row_c2 = ttk.Frame(cust_frame)
    row_c2.pack(fill=tk.X, padx=8, pady=3)

    chk_save_var = tk.BooleanVar(value=False)
    chk_save = ttk.Checkbutton(row_c2, text="TS Fine Turno (Save-Ends):", variable=chk_save_var)
    chk_save.pack(side=tk.LEFT)

    save_stat_var = tk.StringVar(value="SAG")
    stat_combo = ttk.Combobox(row_c2, textvariable=save_stat_var, values=["FOR", "DES", "COS", "INT", "SAG", "CAR"], width=4, state="readonly")
    stat_combo.pack(side=tk.LEFT, padx=5)

    ttk.Label(row_c2, text="CD:").pack(side=tk.LEFT)
    spin_dc = ttk.Spinbox(row_c2, from_=1, to=30, width=3)
    spin_dc.set(14)
    spin_dc.pack(side=tk.LEFT, padx=5)

    def apply_custom_effect():
        c_name = ent_cust_name.get().strip()
        if not c_name:
            messagebox.showwarning("Attenzione", "Inserisci un nome per l'effetto.")
            return
        try:
            c_dur = int(spin_dur.get().strip())
        except ValueError:
            c_dur = 10
        save_ends = None
        if chk_save_var.get():
            try:
                c_dc = int(spin_dc.get().strip())
            except ValueError:
                c_dc = 14
            save_ends = {"stat": save_stat_var.get(), "dc": c_dc, "timing": "end_of_turn"}

        new_instance = {
            "name": c_name,
            "icon": icon_var.get(),
            "source": "DM",
            "duration_rounds": c_dur,
            "decrement_timing": "round_end",
            "save_ends": save_ends,
            "condition": None
        }
        with dm_gui.server.game_state.lock:
            player.add_effect(new_instance)
        ent_cust_name.delete(0, tk.END)
        refresh_fx_list()
        dm_gui.server.game_state._trigger_gui_update()
        broadcast(dm_gui.server.game_state, make_player_stats_update(
            player.name, player.hp, player.max_hp, player.initiative, player.conditions,
            getattr(player, "temp_hp", 0), active_effects=getattr(player, "active_effects", [])
        ))
        broadcast(dm_gui.server.game_state, make_chat_broadcast("Sistema", f"✨ Applicato '{c_name}' a {player.name} ({c_dur} round)!"))
        dm_gui.log_to_chat(f"[EFFETTI] Applicato '{c_name}' a {player.name}.")

    ttk.Button(cust_frame, text=_t("btn_add_custom_effect", default="Aggiungi Effetto Personalizzato"), command=apply_custom_effect).pack(pady=5)



def open_aura_dialog(dm_gui):
    """Apre il dialogo di configurazione raggio e colore dell'aura dinamica per il token."""
    sel = dm_gui.player_listbox.curselection()
    if not sel: return
    display_text = dm_gui.player_listbox.get(sel[0])
    if display_text.startswith('---'): return
    player_name = display_text.split(" (HP")[0].replace("▶", "").strip()
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return
    
    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"Imposta Aura per {player_name}")
    win.minsize(250, 200)

    ttk.Label(win, text="Raggio (esagoni, 0 per disabilitare):").pack(pady=(10, 0))
    radius_entry = ttk.Entry(win)
    radius_entry.insert(0, str(getattr(player, 'aura_radius', 0)))
    radius_entry.pack(fill=tk.X, padx=20, pady=5)

    ttk.Label(win, text="Colore:").pack(pady=(10, 0))
    color_var = tk.StringVar(value=getattr(player, 'aura_color', 'yellow'))
    color_combo = ttk.Combobox(win, textvariable=color_var, values=["yellow", "blue", "red", "green", "purple", "white", "black"], state="readonly")
    color_combo.pack(fill=tk.X, padx=20, pady=5)

    def submit():
        try:
            rad = int(radius_entry.get().strip())
            col = color_var.get().strip()
            if rad < 0: rad = 0
            
            with dm_gui.server.game_state.lock:
                player.aura_radius = rad
                player.aura_color = col
                
            dm_gui.server.game_state._trigger_gui_update()
            from common.protocol import make_game_state
            broadcast(dm_gui.server.game_state, make_game_state(dm_gui.server.game_state.get_state_dict()))
            dm_gui.log_to_chat(f"[SISTEMA] Aura di {player.name} impostata a raggio {rad} ({col})")
            win.destroy()
        except ValueError:
            messagebox.showerror("Errore", "Il raggio deve essere un numero intero.")

    ttk.Button(win, text="Applica", command=submit).pack(pady=20)


def open_light_source_dialog(dm_gui):
    """Apre il dialogo di configurazione delle sorgenti di luce dinamiche (torce, lanterne, incantesimi)."""
    player_name = dm_gui.get_selected_player_name()
    if not player_name: return
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"Sorgente di Luce: {player_name}")
    win.minsize(360, 320)

    container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(container, text=f"🔦 Sorgente Luminosa - {player_name}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

    presets = [
        ("Spento / Nessuna Luce", 0, "#FFD700"),
        ("Torcia (4 hex / 20 ft)", 4, "#FFD700"),
        ("Lanterna Schermata (6 hex / 30 ft)", 6, "#FFA500"),
        ("Incantesimo Luce (4 hex - Bianca)", 4, "#66D9E8"),
        ("Luce Diurna (12 hex / 60 ft)", 12, "#FFFFFF")
    ]

    tk.Label(container, text="Preset Rapido:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    preset_var = tk.StringVar(value=presets[1][0] if getattr(player, "light_radius", 0) > 0 else presets[0][0])
    preset_combo = ttk.Combobox(container, textvariable=preset_var, values=[p[0] for p in presets], state="readonly")
    preset_combo.pack(fill=tk.X, pady=(2, 10))

    tk.Label(container, text="Raggio Personalizzato (Esagoni):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    rad_entry = ttk.Entry(container)
    rad_entry.insert(0, str(getattr(player, "light_radius", 0)))
    rad_entry.pack(fill=tk.X, pady=(2, 10))

    tk.Label(container, text="Colore Luce (Esadecimale o Nome):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    color_entry = ttk.Entry(container)
    color_entry.insert(0, getattr(player, "light_color", "#FFD700"))
    color_entry.pack(fill=tk.X, pady=(2, 12))

    def on_preset_select(e):
        sel_text = preset_var.get()
        for name, r, c in presets:
            if name == sel_text:
                rad_entry.delete(0, tk.END); rad_entry.insert(0, str(r))
                color_entry.delete(0, tk.END); color_entry.insert(0, c)
                break
    preset_combo.bind("<<ComboboxSelected>>", on_preset_select)

    def save_light():
        try:
            r = int(rad_entry.get().strip())
            c = color_entry.get().strip() or "#FFD700"
            player.light_radius = max(0, r)
            player.light_color = c
            dm_gui.server.game_state._trigger_gui_update()
            from common.protocol import make_player_stats_update
            broadcast(dm_gui.server.game_state, make_player_stats_update(
                player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)
            ))
            dm_gui.redraw_map_and_players()
            dm_gui.log_to_chat(f"[LUCE] Luce per {player.name} impostata a {r} hex ({c}).")
            win.destroy()
        except ValueError:
            messagebox.showerror("Errore", "Il raggio deve essere un numero intero.", parent=win)

    btn_row = tk.Frame(container, bg=BG_COLOR)
    btn_row.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(btn_row, text="Salva Luce", command=save_light, style="Gold.TButton").pack(side=tk.RIGHT)
    ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)


def open_boss_config_dialog(dm_gui):
    """Apre il dialogo di configurazione dei boss leggendari (resistenze e azioni leggendarie)."""
    player_name = dm_gui.get_selected_player_name()
    if not player_name: return
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"👑 Configura Boss Leggendario: {player_name}")
    win.minsize(360, 320)

    container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(container, text=f"👑 Meccaniche Boss - {player_name}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

    tk.Label(container, text="Resistenze Leggendarie Max (es. 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    res_max_entry = ttk.Entry(container)
    res_max_entry.insert(0, str(getattr(player, "legendary_resistances_max", 3)))
    res_max_entry.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="Resistenze Leggendarie Attuali:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    res_cur_entry = ttk.Entry(container)
    res_cur_entry.insert(0, str(getattr(player, "legendary_resistances_current", getattr(player, "legendary_resistances_max", 3))))
    res_cur_entry.pack(fill=tk.X, pady=(2, 10))

    tk.Label(container, text="Azioni Leggendarie per Round (es. 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    act_max_entry = ttk.Entry(container)
    act_max_entry.insert(0, str(getattr(player, "legendary_actions_max", 3)))
    act_max_entry.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="Azioni Leggendarie Attuali:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    act_cur_entry = ttk.Entry(container)
    act_cur_entry.insert(0, str(getattr(player, "legendary_actions_current", getattr(player, "legendary_actions_max", 3))))
    act_cur_entry.pack(fill=tk.X, pady=(2, 12))

    def save_boss():
        try:
            rmax = int(res_max_entry.get().strip())
            rcur = int(res_cur_entry.get().strip())
            amax = int(act_max_entry.get().strip())
            acur = int(act_cur_entry.get().strip())
            player.legendary_resistances_max = max(0, rmax)
            player.legendary_resistances_current = max(0, min(rmax, rcur))
            player.legendary_actions_max = max(0, amax)
            player.legendary_actions_current = max(0, min(amax, acur))
            dm_gui.server.game_state._trigger_gui_update()
            dm_gui.redraw_map_and_players()
            dm_gui.log_to_chat(f"[BOSS] {player.name} configurato: {rmax} Resistenze, {amax} Azioni.")
            win.destroy()
        except ValueError:
            messagebox.showerror("Errore", "Tutti i valori devono essere numeri interi.", parent=win)

    btn_row = tk.Frame(container, bg=BG_COLOR)
    btn_row.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(btn_row, text="Salva Boss", command=save_boss, style="Gold.TButton").pack(side=tk.RIGHT)
    ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)


def open_spend_legendary_action_dialog(dm_gui):
    """Apre il dialogo per consumare una o più azioni leggendarie per il boss selezionato."""
    player_name = dm_gui.get_selected_player_name()
    if not player_name: return
    player = dm_gui.server.game_state.find_player(player_name)
    if not player: return

    cur_act = getattr(player, "legendary_actions_current", 0)
    max_act = getattr(player, "legendary_actions_max", 0)
    if max_act == 0:
        messagebox.showinfo("Non è un Boss", f"{player_name} non ha azioni leggendarie configurate.\nConfigurale prima da 'Configura Boss Leggendario'.", parent=dm_gui.master)
        return

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"👑 Spendi Azione Leggendaria: {player_name}")
    win.minsize(360, 240)

    container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(container, text=f"👑 Azioni Disponibili: {cur_act}/{max_act}", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

    tk.Label(container, text="Nome Azione (es. Colpo di Coda, Movimento, Soffio):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    name_entry = ttk.Entry(container)
    name_entry.insert(0, "Azione Leggendaria")
    name_entry.pack(fill=tk.X, pady=(2, 8))

    tk.Label(container, text="Costo Azioni (1, 2 o 3):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    cost_combo = ttk.Combobox(container, values=["1", "2", "3"], state="readonly")
    cost_combo.set("1")
    cost_combo.pack(fill=tk.X, pady=(2, 12))

    def do_spend():
        cost = int(cost_combo.get())
        if cur_act < cost:
            messagebox.showerror("Azioni Insufficienti", f"Questo boss ha solo {cur_act} azioni rimaste (richieste: {cost}).", parent=win)
            return
        act_name = name_entry.get().strip() or "Azione Leggendaria"
        from server.commands import command_handlers
        command_handlers["SPEND_LEGENDARY_ACTION_REQUEST"]({"boss_name": player.name, "action_name": act_name, "cost": cost}, player, dm_gui.server.game_state)
        win.destroy()

    btn_row = tk.Frame(container, bg=BG_COLOR)
    btn_row.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(btn_row, text="⚡ Esegui Azione", command=do_spend, style="Gold.TButton").pack(side=tk.RIGHT)
    ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)


def open_place_trap_dialog(dm_gui, clicked_hex):
    """Apre il dialogo di piazzamento trappole con preset 5e (CD, danni, tipo)."""
    if not dm_gui.server.game_state.current_map:
        messagebox.showinfo("Nessuna Mappa", "Nessuna mappa attiva su cui piazzare trappole.", parent=dm_gui.master)
        return

    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title(f"⚠️ Piazza Trappola 5e [{clicked_hex.q}, {clicked_hex.r}]")
    win.minsize(380, 360)

    container = tk.Frame(win, bg=BG_COLOR, padx=16, pady=12)
    container.pack(fill=tk.BOTH, expand=True)

    tk.Label(container, text=f"⚠️ Nuova Trappola D&D 5e - Hex ({clicked_hex.q}, {clicked_hex.r})", font=FONT_HEADER, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(0, 10))

    presets = [
        ("Fossa con Punte (CD 13, 2d10 Perforante)", "Trappola a Fossa con Punte", 13, "2d10", "Perforante"),
        ("Dardi Avvelenati (CD 15, 2d8 Veleno)", "Trappola a Dardi Avvelenati", 15, "2d8", "Veleno"),
        ("Runa di Fuoco (CD 14, 4d6 Fuoco)", "Runa Esplosiva di Fuoco", 14, "4d6", "Fuoco"),
        ("Gabbia Cadente (CD 12, 1d10 Contundente)", "Trappola a Gabbia Pesante", 12, "1d10", "Contundente"),
        ("Spruzzo d'Acido (CD 14, 3d6 Acido)", "Trappola a Getto d'Acido", 14, "3d6", "Acido")
    ]

    tk.Label(container, text="Preset Trappola:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    preset_var = tk.StringVar(value=presets[0][0])
    preset_combo = ttk.Combobox(container, textvariable=preset_var, values=[p[0] for p in presets], state="readonly")
    preset_combo.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="Nome Trappola:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    name_entry = ttk.Entry(container)
    name_entry.insert(0, presets[0][1])
    name_entry.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="CD Tiro Salvezza (Destrezza):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    dc_entry = ttk.Entry(container)
    dc_entry.insert(0, str(presets[0][2]))
    dc_entry.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="Formula Danno (es. 2d10, 4d6):", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    dmg_entry = ttk.Entry(container)
    dmg_entry.insert(0, presets[0][3])
    dmg_entry.pack(fill=tk.X, pady=(2, 6))

    tk.Label(container, text="Tipo di Danno:", font=FONT_BOLD, bg=BG_COLOR, fg=TEXT_COLOR).pack(anchor="w")
    dtype_combo = ttk.Combobox(container, values=["Perforante", "Tagliente", "Contundente", "Fuoco", "Veleno", "Acido", "Fulmine"], state="readonly")
    dtype_combo.set(presets[0][4])
    dtype_combo.pack(fill=tk.X, pady=(2, 8))

    hidden_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(container, text="Nascosta ai giocatori finché non scatta", variable=hidden_var).pack(anchor="w", pady=(0, 10))

    def on_preset_sel(e):
        sel_text = preset_var.get()
        for p_title, p_name, p_dc, p_dmg, p_type in presets:
            if p_title == sel_text:
                name_entry.delete(0, tk.END); name_entry.insert(0, p_name)
                dc_entry.delete(0, tk.END); dc_entry.insert(0, str(p_dc))
                dmg_entry.delete(0, tk.END); dmg_entry.insert(0, p_dmg)
                dtype_combo.set(p_type)
                break
    preset_combo.bind("<<ComboboxSelected>>", on_preset_sel)

    def save_trap():
        try:
            dc = int(dc_entry.get().strip())
            name = name_entry.get().strip() or "Trappola"
            dmg = dmg_entry.get().strip() or "1d10"
            dtype = dtype_combo.get() or "Perforante"
            traps = dm_gui.server.game_state.current_map.setdefault("traps", [])
            traps.append({
                "q": clicked_hex.q,
                "r": clicked_hex.r,
                "name": name,
                "dc": dc,
                "damage": dmg,
                "damage_type": dtype,
                "triggered": False,
                "hidden": hidden_var.get()
            })
            dm_gui.redraw_map_and_players()
            from common.protocol import make_map_data_update_broadcast
            broadcast(dm_gui.server.game_state, make_map_data_update_broadcast(dm_gui.server.game_state.current_map))
            dm_gui.log_to_chat(f"[MAPPA] Trappola '{name}' (CD {dc}, {dmg} {dtype}) piazzata a [{clicked_hex.q}, {clicked_hex.r}].")
            win.destroy()
        except ValueError:
            messagebox.showerror("Errore", "La CD deve essere un numero intero.", parent=win)

    btn_row = tk.Frame(container, bg=BG_COLOR)
    btn_row.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(btn_row, text="⚠️ Piazza Trappola", command=save_trap, style="Gold.TButton").pack(side=tk.RIGHT)
    ttk.Button(btn_row, text="Annulla", command=win.destroy).pack(side=tk.RIGHT, padx=6)


def remove_trap_at(dm_gui, clicked_hex):
    """Rimuove la trappola presente nell'esagono selezionato."""
    cur_map = getattr(dm_gui.server.game_state, "current_map", None)
    if not cur_map: return
    traps = cur_map.get("traps", [])
    cur_map["traps"] = [t for t in traps if not (t.get("q") == clicked_hex.q and t.get("r") == clicked_hex.r)]
    dm_gui.redraw_map_and_players()
    from common.protocol import make_map_data_update_broadcast
    broadcast(dm_gui.server.game_state, make_map_data_update_broadcast(cur_map))
    dm_gui.log_to_chat(f"[MAPPA] Trappola a [{clicked_hex.q}, {clicked_hex.r}] rimossa.")


def reset_trap_at(dm_gui, clicked_hex):
    """Riattiva e nasconde nuovamente la trappola scattata nell'esagono."""
    cur_map = getattr(dm_gui.server.game_state, "current_map", None)
    if not cur_map: return
    traps = cur_map.get("traps", [])
    for t in traps:
        if t.get("q") == clicked_hex.q and t.get("r") == clicked_hex.r:
            t["triggered"] = False
            t["hidden"] = True
    dm_gui.redraw_map_and_players()
    from common.protocol import make_map_data_update_broadcast
    broadcast(dm_gui.server.game_state, make_map_data_update_broadcast(cur_map))
    dm_gui.log_to_chat(f"[MAPPA] Trappola a [{clicked_hex.q}, {clicked_hex.r}] riattivata e nascosta.")

