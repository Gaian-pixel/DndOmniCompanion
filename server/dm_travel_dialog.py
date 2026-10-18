# server/dm_travel_dialog.py
"""
Modulo per la gestione del viaggio, hex-crawl, sostentamento e marce forzate (D&D 5e RAW).
Decongestiona server/dm_gui.py estraendo il pannello di controllo esplorazione e roster di marcia.
"""
import tkinter as tk
from tkinter import ttk
from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE,
    TEXT_COLOR, TEXT_MUTED
)
from common.i18n import _t, translate_weather


def open_travel_panel(dm_gui):
    """Apre la finestra di gestione del viaggio, formazione party, razioni e marcia 5e."""
    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title("🧭 Gestione Viaggio & Hex Crawl (5e)")
    win.minsize(620, 720)
    
    gs = dm_gui.server.game_state
    months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
    month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"

    # Container scrollabile
    canvas = tk.Canvas(win, bg=BG_COLOR, highlightthickness=0)
    scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)
    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
    canvas.configure(yscrollcommand=scrollbar.set)
    
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Intestazione
    header_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    header_f.pack(fill=tk.X, padx=14, pady=(12, 8))
    tk.Label(header_f, text="🧭 PANNELLO GESTIONE VIAGGIO & HEX CRAWL", font=("Georgia", 13, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(10, 2))
    tk.Label(header_f, text="Controlla andatura, tiri di navigazione, imboscate nemiche, caccia e sostentamento del party.",
             font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 10))

    # Parametri e Ambiente
    env_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
    env_f.pack(fill=tk.X, padx=14, pady=6)
    tk.Label(env_f, text="📍 STATO DELL'AMBIENTE & MARCIA", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 4))
    
    weather_label = translate_weather(getattr(gs, 'weather', 'Sereno'))
    lbl_current_time = tk.Label(env_f, text=f"📅 Data & Ora: {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00  |  ⛅ Clima: {weather_label}",
                                font=("Segoe UI", 9), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR)
    lbl_current_time.pack(anchor="w", padx=12, pady=2)
    
    hours_today = getattr(gs, "travel_hours_today", 0)
    h_color = ACCENT_RED if hours_today > 8 else TEXT_COLOR
    h_text = f"⏱️ Ore Viaggiate Oggi: {hours_today} / 8h"
    if hours_today > 8:
        h_text += f" ⚠️ Marcia Forzata Attiva (CD {10 + (hours_today - 8)})"
    lbl_hours = tk.Label(env_f, text=h_text, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=h_color)
    lbl_hours.pack(anchor="w", padx=12, pady=2)

    # Selezione Andatura e Terreno
    param_grid = tk.Frame(env_f, bg=SURFACE_COLOR_ALT)
    param_grid.pack(fill=tk.X, padx=12, pady=(6, 10))
    
    tk.Label(param_grid, text="Andatura di Viaggio (5e):", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=0, column=0, sticky="w", pady=2)
    pace_var = tk.StringVar(value=getattr(gs, "travel_pace", "Normale"))
    pace_frame = tk.Frame(param_grid, bg=SURFACE_COLOR_ALT)
    pace_frame.grid(row=0, column=1, sticky="w", padx=10, pady=2)
    
    def on_pace_change():
        gs.travel_pace = pace_var.get()
        if hasattr(dm_gui, "_update_roster_labels"):
            dm_gui._update_roster_labels()
        
    for p_opt, p_desc in [("Lenta", "Lenta (2 mi/h, +5 PP, Furtivo)"), ("Normale", "Normale (3 mi/h)"), ("Veloce", "Veloce (4 mi/h, -5 PP, no caccia)")]:
        ttk.Radiobutton(pace_frame, text=p_opt, variable=pace_var, value=p_opt, command=on_pace_change).pack(side=tk.LEFT, padx=5)

    tk.Label(param_grid, text="Terreno Attuale:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=1, column=0, sticky="w", pady=6)
    terrain_var = tk.StringVar(value=getattr(gs, "travel_terrain", "Foresta"))
    terrain_combo = ttk.Combobox(param_grid, textvariable=terrain_var, state="readonly", width=30,
                                 values=["Pianura / Strada (CD 10)", "Foresta / Collina (CD 15)", "Palude / Montagna (CD 18)", "Deserto / Landa (CD 20)"])
    terrain_combo.grid(row=1, column=1, sticky="w", padx=10, pady=6)
    
    def on_terrain_select(event=None):
        val = terrain_var.get().split()[0]
        gs.travel_terrain = val
    terrain_combo.bind("<<ComboboxSelected>>", on_terrain_select)

    # Sezione Formazione e Roster Party
    party_f = tk.Frame(scrollable_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    party_f.pack(fill=tk.X, padx=14, pady=6)
    tk.Label(party_f, text="👥 FORMAZIONE E RUOLI DEL GRUPPO (LIVE)", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=12, pady=(8, 2))
    
    roster_container = tk.Frame(party_f, bg=SURFACE_COLOR)
    roster_container.pack(fill=tk.X, padx=12, pady=(4, 10))

    # Helper per calcolare bonus statistici 5e
    def get_stat_mod(char_sheet, stat_name):
        if not char_sheet: return 0
        val = char_sheet.get("attributes", {}).get(stat_name, 10)
        try: return (int(val) - 10) // 2
        except: return 0

    def get_skill_mod(char_sheet, skill_name, stat_name):
        if not char_sheet: return 0
        mod = get_stat_mod(char_sheet, stat_name)
        sk = char_sheet.get("skills", {}).get(skill_name, 0)
        try: sk_val = int(sk)
        except: sk_val = 0
        return mod + sk_val

    def get_passive_perception(p, pace):
        sheet = getattr(p, "full_sheet", {}) or {}
        base_bonus = get_skill_mod(sheet, "Percezione", "SAG")
        pp = 10 + base_bonus
        if pace == "Lenta": pp += 5
        elif pace == "Veloce": pp -= 5
        return pp

    def refresh_roster():
        for widget in roster_container.winfo_children():
            widget.destroy()
        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()
        
        cur_pace = pace_var.get()
        for p in party_members:
            row_f = tk.Frame(roster_container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
            row_f.pack(fill=tk.X, pady=2)
            
            name_lbl = tk.Label(row_f, text=f"👤 {p.name}", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, width=14, anchor="w")
            name_lbl.pack(side=tk.LEFT, padx=8, pady=4)
            
            order_val = getattr(p, "marching_order", "Centro")
            order_lbl = tk.Label(row_f, text=f"Pos: [{order_val}]", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=16, anchor="w")
            order_lbl.pack(side=tk.LEFT, padx=4)
            
            role_val = getattr(p, "travel_role", "Nessuna")
            sheet = getattr(p, "full_sheet", {}) or {}
            
            stat_desc = ""
            if role_val == "Navigatore":
                surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                if cur_pace == "Veloce": surv_mod -= 5
                stat_desc = f"(Sopravvivenza {surv_mod:+d})"
            elif role_val == "Sentinella":
                pp = get_passive_perception(p, cur_pace)
                stat_desc = f"(PP: {pp})"
            elif role_val == "Cacciatore":
                surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                stat_desc = f"(Sopravvivenza {surv_mod:+d})"
            elif role_val == "Furtivo":
                stealth_mod = get_skill_mod(sheet, "Furtività", "DES")
                stat_desc = f"(Furtività {stealth_mod:+d})"
            
            role_lbl = tk.Label(row_f, text=f"Ruolo: {role_val} {stat_desc}", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=28, anchor="w")
            role_lbl.pack(side=tk.LEFT, padx=4)
            
            exh = getattr(p, "exhaustion_level", 0)
            exh_color = ACCENT_RED if exh > 0 else TEXT_MUTED
            exh_text = f"Sfinimento: {exh}/6" if exh > 0 else "Sfinimento: 0"
            tk.Label(row_f, text=exh_text, font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=exh_color, width=14, anchor="e").pack(side=tk.RIGHT, padx=8)

    dm_gui._update_roster_labels = refresh_roster
    refresh_roster()

    # Funzione Consumo Razioni Party
    def consume_rations():
        from common.protocol import make_chat_broadcast, make_game_state
        from server.network import broadcast
        
        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()

        msg = "🥖 [SISTEMA] CONSUMO RAZIONI & SOSTENTAMENTO GIORNALIERO:\n"
        for p in party_members:
            sheet = getattr(p, "full_sheet", None)
            if not sheet:
                continue
            
            has_ration = False
            has_water = False

            # 1. Controlla e scala da inventory_grid
            grid = sheet.get("inventory_grid", [])
            if isinstance(grid, list):
                for idx, it in enumerate(grid):
                    if not it or not isinstance(it, dict): continue
                    name_lower = str(it.get("name", "")).lower()
                    qty = int(it.get("qty", it.get("quantity", 1)) or 1)
                    if not has_ration and ("razion" in name_lower or "cibo" in name_lower) and qty > 0:
                        if qty - 1 <= 0:
                            grid[idx] = None
                        else:
                            if "qty" in it: it["qty"] = qty - 1
                            if "quantity" in it: it["quantity"] = qty - 1
                        has_ration = True
                    elif not has_water and ("acqua" in name_lower or "otre" in name_lower) and qty > 0:
                        if qty - 1 <= 0:
                            grid[idx] = None
                        else:
                            if "qty" in it: it["qty"] = qty - 1
                            if "quantity" in it: it["quantity"] = qty - 1
                        has_water = True

            # 2. Controlla e scala da inventory classico se non ancora dedotto
            inv = sheet.get("inventory", [])
            if isinstance(inv, list):
                for it in inv:
                    if not isinstance(it, dict): continue
                    name_lower = str(it.get("name", "")).lower()
                    qty = int(it.get("quantity", it.get("qty", 1)) or 1)
                    if not has_ration and ("razion" in name_lower or "cibo" in name_lower) and qty > 0:
                        it["quantity"] = qty - 1
                        has_ration = True
                    elif not has_water and ("acqua" in name_lower or "otre" in name_lower) and qty > 0:
                        it["quantity"] = qty - 1
                        has_water = True
                sheet["inventory"] = [i for i in inv if not isinstance(i, dict) or int(i.get("quantity", i.get("qty", 1)) or 1) > 0]

            if not has_ration or not has_water:
                p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                p.conditions = conds
                sheet["exhaustion_level"] = p.exhaustion_level
                sheet["conditions"] = conds
                msg += f"❌ {p.name}: Provviste insufficienti! Subisce Sfinimento (Livello {p.exhaustion_level})\n"
            else:
                msg += f"✅ {p.name}: Ha consumato 1 Razione e 1 Otre d'Acqua.\n"

        gs._trigger_gui_update()
        broadcast(gs, make_game_state(gs.get_state_dict()))
        broadcast(gs, make_chat_broadcast("Sistema", msg))
        dm_gui.log_to_chat(msg)
        refresh_roster()
        messagebox.showinfo("Razioni Consumate", "Razioni e acqua giornaliere elaborate per tutti i membri del gruppo.")

    # Motore di Avanzamento Viaggio (5e Automated Engine)
    def do_travel(hours=4):
        from common.dice import roll_dice
        from common.protocol import make_chat_broadcast, make_game_state
        from server.network import broadcast

        cur_pace = pace_var.get()
        cur_terrain = terrain_var.get().split()[0]
        gs.travel_pace = cur_pace
        gs.travel_terrain = cur_terrain

        # Calcolo CD Terreno per Navigazione
        terrain_dc = 15
        if "Pianura" in terrain_var.get(): terrain_dc = 10
        elif "Foresta" in terrain_var.get(): terrain_dc = 15
        elif "Palude" in terrain_var.get() or "Montagna" in terrain_var.get(): terrain_dc = 18
        elif "Deserto" in terrain_var.get(): terrain_dc = 20

        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()

        # 1. TIRO NAVIGATORE (Sopravvivenza)
        navigators = [p for p in party_members if getattr(p, "travel_role", "") == "Navigatore"]
        nav_msg = ""
        if navigators:
            nav = navigators[0]
            sheet = getattr(nav, "full_sheet", {}) or {}
            bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
            if cur_pace == "Veloce": bonus -= 5
            d20 = roll_dice("1d20")["total"]
            nav_tot = d20 + bonus
            if nav_tot >= terrain_dc:
                nav_msg = f"🧭 ROTTA MANTENUTA: Il Navigatore {nav.name} orienta la marcia! (Tiro: {d20}{bonus:+d}={nav_tot} vs CD {terrain_dc})"
            else:
                nav_msg = f"⚠️ SMARRITI: Il Navigatore {nav.name} ha perso l'orientamento! (Tiro: {d20}{bonus:+d}={nav_tot} vs CD {terrain_dc})"
        else:
            d20 = roll_dice("1d20")["total"]
            if d20 >= terrain_dc:
                nav_msg = f"🧭 ROTTA MANTENUTA: Il gruppo avanza a vista senza navigatore (Tiro: {d20} vs CD {terrain_dc})"
            else:
                nav_msg = f"⚠️ SMARRITI: Senza navigatore il gruppo perde la rotta! (Tiro: {d20} vs CD {terrain_dc})"

        # 2. INCONTRO CASUALE & SENTINELLE
        enc_roll = roll_dice("1d20")["total"]
        has_encounter = (enc_roll >= 16)
        enc_msg = ""
        if has_encounter:
            ambush_dc = roll_dice("1d20+2")["total"]
            sentinels = [p for p in party_members if getattr(p, "travel_role", "") == "Sentinella"]
            if sentinels:
                best_sentinel = max(sentinels, key=lambda s: get_passive_perception(s, cur_pace))
                best_pp = get_passive_perception(best_sentinel, cur_pace)
                if best_pp >= ambush_dc:
                    enc_msg = f"⚔️ INCONTRO CASUALE! La Sentinella {best_sentinel.name} ha avvistato il pericolo in anticipo! (Percezione Passiva {best_pp} vs Insidia CD {ambush_dc}) - Nessuna sorpresa!"
                else:
                    enc_msg = f"⚠️ IMBOSCATA OSTILE! I nemici colgono il gruppo di sorpresa! (Insidia CD {ambush_dc} superata vs Percezione Passiva {best_pp} di {best_sentinel.name})"
            else:
                enc_msg = f"⚔️ INCONTRO CASUALE RILEVATO! (Tiro Incontro: {enc_roll}/20 - Nessuna sentinella di guardia)"
        else:
            enc_msg = f"🌿 Marcia tranquilla: nessun pericolo ostile lungo la via (Tiro: {enc_roll}/20)."

        # 3. CACCIA & FORAGING
        hunt_msg = ""
        if cur_pace == "Veloce":
            hunt_msg = "🏹 Andatura Veloce: impossibile dedicarsi alla caccia o raccolta."
        else:
            hunters = [p for p in party_members if getattr(p, "travel_role", "") == "Cacciatore"]
            if hunters:
                h = hunters[0]
                sheet = getattr(h, "full_sheet", {}) or {}
                surv_bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                h_roll = roll_dice("1d20")["total"] + surv_bonus
                if h_roll >= 15:
                    food_found = roll_dice("1d6")["total"] + max(0, get_stat_mod(sheet, "SAG"))
                    hunt_msg = f"🏹 CACCIA: {h.name} raccoglie con successo {food_found} razioni di cibo e acqua fresca! (Tiro: {h_roll} vs CD 15)"
                else:
                    hunt_msg = f"🏹 CACCIA: {h.name} non trova provviste sufficienti in quest'area (Tiro: {h_roll} vs CD 15)."

        # 4. MARCIA FORZATA (Ore > 8)
        gs.travel_hours_today = getattr(gs, "travel_hours_today", 0) + hours
        exhaustion_logs = []
        if gs.travel_hours_today > 8:
            extra_hours = gs.travel_hours_today - 8
            con_dc = 10 + extra_hours
            for p in party_members:
                sheet = getattr(p, "full_sheet", {}) or {}
                cos_mod = get_stat_mod(sheet, "COS")
                d20_con = roll_dice("1d20")["total"]
                con_tot = d20_con + cos_mod
                if con_tot < con_dc:
                    p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                    conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                    conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                    p.conditions = conds
                    if sheet:
                        sheet["exhaustion_level"] = p.exhaustion_level
                        sheet["conditions"] = conds
                    exhaustion_logs.append(f"😫 {p.name}: Fallisce TS COS (Tiro {d20_con}{cos_mod:+d}={con_tot} vs CD {con_dc}) -> Guadagna Sfinimento (Livello {p.exhaustion_level})")
                else:
                    exhaustion_logs.append(f"💪 {p.name}: Supera TS COS (Tiro {con_tot} vs CD {con_dc}) e resiste alla fatica.")

        # Avanzamento del tempo sul server
        dm_gui.advance_time(hours, is_rest=False)

        months_list = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
        cur_month = months_list[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese"

        msg = f"========================================\n"
        msg += f"🧭 RESOCONTO MARCIA ({hours} ORE) - {gs.time_day} {cur_month} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00\n"
        msg += f"========================================\n"
        msg += f"• Andatura: {cur_pace} | Terreno: {cur_terrain} | Ore oggi: {gs.travel_hours_today}/8h\n"
        msg += f"• {nav_msg}\n"
        msg += f"• {enc_msg}\n"
        if hunt_msg: msg += f"• {hunt_msg}\n"
        if exhaustion_logs:
            msg += f"⚠️ MARCIA FORZATA (CD {10 + (gs.travel_hours_today - 8)}):\n"
            for el in exhaustion_logs:
                msg += f"  - {el}\n"
        msg += "========================================"

        gs.add_calendar_event(f"Avanzamento Viaggio {hours}h ({cur_pace}, {cur_terrain}). Incontro: {enc_msg}")
        dm_gui.log_to_chat(msg, tab_name="Sistema")
        broadcast(dm_gui.server.game_state, make_chat_broadcast("Sistema", msg))
        broadcast(dm_gui.server.game_state, make_game_state(gs.get_state_dict()))
        win.destroy()

    # Pulsantiere Azioni
    action_f = tk.Frame(scrollable_frame, bg=BG_COLOR)
    action_f.pack(fill=tk.X, padx=14, pady=16)

    btn_advance4 = ttk.Button(action_f, text="🚶 Avanza 4 Ore (Mezza Giornata)", command=lambda: do_travel(4), style="Primary.TButton")
    btn_advance4.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    btn_advance8 = ttk.Button(action_f, text="🏃 Avanza 8 Ore (Giornata Intera)", command=lambda: do_travel(8), style="Primary.TButton")
    btn_advance8.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    btn_consume = ttk.Button(action_f, text="🥖 Consuma Razioni Party", command=consume_rations, style="Info.TButton")
    btn_consume.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    ttk.Button(action_f, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=4)

