# server/dm_travel_dialog.py
"""
Modulo per la gestione avanzata del viaggio, hex-crawl, sostentamento,
marce forzate, turni di guardia notturna e incontri casuali per bioma (D&D 5e RAW).
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
from common.travel_data import (
    BIOMES, DANGER_LEVELS, TRAVEL_PACES,
    get_biome_presets, get_danger_presets, generate_biome_encounter,
    calculate_effective_sentinel_pp, resolve_night_camp_simulation
)
from common.dice import roll_dice
from common.protocol import make_chat_broadcast, make_game_state
from server.network import broadcast


def open_travel_panel(dm_gui):
    """Apre la finestra di gestione del viaggio, formazione party, accampamento e incontri 5e."""
    win = tk.Toplevel(dm_gui.master)
    win.transient(dm_gui.master)
    win.grab_set()
    apply_modern_window_style(win)
    win.title("🧭 Gestione Viaggio, Accampamento & Incontri (D&D 5e RAW)")
    win.minsize(680, 760)
    
    gs = dm_gui.server.game_state
    months = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]
    month_name = months[gs.time_month] if hasattr(gs, 'time_month') and 1 <= gs.time_month <= 12 else "Mese Sconosciuto"

    # Intestazione Generale
    header_f = tk.Frame(win, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    header_f.pack(fill=tk.X, padx=12, pady=(10, 6))
    
    title_row = tk.Frame(header_f, bg=SURFACE_COLOR)
    title_row.pack(fill=tk.X, padx=12, pady=(8, 2))
    tk.Label(title_row, text="🧭 MOTORE DI ESPLORAZIONE, VIAGGIO & ACCAMPAMENTO (5e)", font=("Georgia", 12, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
    
    time_str = f"📅 {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00 | ⛅ {translate_weather(getattr(gs, 'weather', 'Sereno'))}"
    tk.Label(title_row, text=time_str, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.RIGHT)

    # Notebook con 3 Tab tematici
    notebook = ttk.Notebook(win)
    notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

    tab_march = ttk.Frame(notebook)
    tab_camp = ttk.Frame(notebook)
    tab_encounters = ttk.Frame(notebook)

    notebook.add(tab_march, text=" 🧭 Marcia & Formazione ")
    notebook.add(tab_camp, text=" 🏕️ Accampamento & Guardie ")
    notebook.add(tab_encounters, text=" 🎲 Incontri per Bioma ")

    # Helper calcolo bonus 5e
    def get_stat_mod(char_sheet, stat_name):
        if not char_sheet: return 0
        val = char_sheet.get("attributes", {}).get(stat_name, 10)
        try: return (int(val) - 10) // 2
        except (ValueError, TypeError): return 0

    def get_skill_mod(char_sheet, skill_name, stat_name):
        if not char_sheet: return 0
        mod = get_stat_mod(char_sheet, stat_name)
        sk = char_sheet.get("skills", {}).get(skill_name, 0)
        try: sk_val = int(sk)
        except (ValueError, TypeError): sk_val = 0
        return mod + sk_val

    def get_passive_perception(p, pace):
        sheet = getattr(p, "full_sheet", {}) or {}
        base_bonus = get_skill_mod(sheet, "Percezione", "SAG")
        pp = 10 + base_bonus
        if pace == "Lenta": pp += 5
        elif pace == "Veloce": pp -= 5
        return pp

    # =========================================================================
    # TAB 1: MARCIA & FORMAZIONE
    # =========================================================================
    march_canvas = tk.Canvas(tab_march, bg=BG_COLOR, highlightthickness=0)
    march_scroll = ttk.Scrollbar(tab_march, orient="vertical", command=march_canvas.yview)
    march_frame = ttk.Frame(march_canvas)
    march_frame.bind("<Configure>", lambda e: march_canvas.configure(scrollregion=march_canvas.bbox("all")))
    m_win = march_canvas.create_window((0, 0), window=march_frame, anchor="nw")
    march_canvas.bind("<Configure>", lambda e: march_canvas.itemconfig(m_win, width=e.width))
    march_canvas.configure(yscrollcommand=march_scroll.set)
    march_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    march_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    # Parametri Ambiente & Andatura
    params_box = tk.Frame(march_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
    params_box.pack(fill=tk.X, padx=10, pady=8)
    tk.Label(params_box, text="📍 PARAMETRI DI VIAGGIO & ANDATURA (5e RAW)", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 4))

    p_grid = tk.Frame(params_box, bg=SURFACE_COLOR_ALT)
    p_grid.pack(fill=tk.X, padx=10, pady=(2, 8))

    # Andatura
    tk.Label(p_grid, text="Andatura:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=0, column=0, sticky="w", pady=4)
    pace_var = tk.StringVar(value=getattr(gs, "travel_pace", "Normale"))
    pace_f = tk.Frame(p_grid, bg=SURFACE_COLOR_ALT)
    pace_f.grid(row=0, column=1, sticky="w", padx=10, pady=4)

    def on_pace_change():
        gs.travel_pace = pace_var.get()
        refresh_march_roster()
        broadcast(gs, make_game_state(gs.get_state_dict()))

    for p_key, p_val in TRAVEL_PACES.items():
        ttk.Radiobutton(pace_f, text=p_val["name_it"], variable=pace_var, value=p_key, command=on_pace_change).pack(side=tk.LEFT, padx=6)

    # Bioma
    tk.Label(p_grid, text="Bioma 5e:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=1, column=0, sticky="w", pady=4)
    biome_keys = list(BIOMES.keys())
    biome_names = [f"{BIOMES[k]['icon']} {BIOMES[k]['name_it']} (CD Nav {BIOMES[k]['dc_nav']})" for k in biome_keys]
    
    cur_biome_key = getattr(gs, "travel_biome", "foresta")
    cur_biome_idx = biome_keys.index(cur_biome_key) if cur_biome_key in biome_keys else 0
    biome_var = tk.StringVar(value=biome_names[cur_biome_idx])
    biome_combo = ttk.Combobox(p_grid, textvariable=biome_var, state="readonly", width=34, values=biome_names)
    biome_combo.grid(row=1, column=1, sticky="w", padx=10, pady=4)

    def on_biome_change(event=None):
        sel_idx = biome_combo.current()
        if 0 <= sel_idx < len(biome_keys):
            gs.travel_biome = biome_keys[sel_idx]
            gs.travel_terrain = BIOMES[biome_keys[sel_idx]]["name_it"].split()[0]
            broadcast(gs, make_game_state(gs.get_state_dict()))
    biome_combo.bind("<<ComboboxSelected>>", on_biome_change)

    # Grado di Pericolo
    tk.Label(p_grid, text="Pericolo Area:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).grid(row=2, column=0, sticky="w", pady=4)
    danger_keys = list(DANGER_LEVELS.keys())
    danger_names = [f"{DANGER_LEVELS[k]['icon']} {DANGER_LEVELS[k]['name_it']} (d20 >= {DANGER_LEVELS[k]['encounter_threshold']})" for k in danger_keys]
    cur_danger_key = getattr(gs, "travel_danger", "moderate")
    cur_danger_idx = danger_keys.index(cur_danger_key) if cur_danger_key in danger_keys else 1
    danger_var = tk.StringVar(value=danger_names[cur_danger_idx])
    danger_combo = ttk.Combobox(p_grid, textvariable=danger_var, state="readonly", width=34, values=danger_names)
    danger_combo.grid(row=2, column=1, sticky="w", padx=10, pady=4)

    def on_danger_change(event=None):
        sel_idx = danger_combo.current()
        if 0 <= sel_idx < len(danger_keys):
            gs.travel_danger = danger_keys[sel_idx]
            broadcast(gs, make_game_state(gs.get_state_dict()))
    danger_combo.bind("<<ComboboxSelected>>", on_danger_change)

    # Info Ore e Miglia Oggi
    stats_lbl_f = tk.Frame(params_box, bg=SURFACE_COLOR_ALT)
    stats_lbl_f.pack(fill=tk.X, padx=10, pady=(0, 8))
    
    hours_today = getattr(gs, "travel_hours_today", 0)
    miles_today = getattr(gs, "travel_miles_today", 0)
    h_color = ACCENT_RED if hours_today > 8 else TEXT_COLOR
    h_text = f"⏱️ Ore Viaggiate Oggi: {hours_today} / 8h  |  🗺️ Miglia Percorse: {miles_today} mi"
    if hours_today > 8:
        h_text += f"  ⚠️ Marcia Forzata Attiva (CD {10 + (hours_today - 8)})"
    lbl_march_stats = tk.Label(stats_lbl_f, text=h_text, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=h_color)
    lbl_march_stats.pack(anchor="w")

    # Roster Formazione Party
    party_box = tk.Frame(march_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    party_box.pack(fill=tk.X, padx=10, pady=6)
    tk.Label(party_box, text="👥 FORMAZIONE E RUOLI DEL GRUPPO (LIVE)", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 2))

    march_roster_container = tk.Frame(party_box, bg=SURFACE_COLOR)
    march_roster_container.pack(fill=tk.X, padx=10, pady=(2, 8))

    def refresh_march_roster():
        for w in march_roster_container.winfo_children():
            w.destroy()
        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()
        
        cur_p = pace_var.get()
        for p in party_members:
            row_f = tk.Frame(march_roster_container, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
            row_f.pack(fill=tk.X, pady=2)
            
            tk.Label(row_f, text=f"👤 {p.name}", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, width=14, anchor="w").pack(side=tk.LEFT, padx=6, pady=4)
            
            order_val = getattr(p, "marching_order", "Centro")
            tk.Label(row_f, text=f"Pos: [{order_val}]", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=14, anchor="w").pack(side=tk.LEFT, padx=4)
            
            role_val = getattr(p, "travel_role", "Nessuna")
            sheet = getattr(p, "full_sheet", {}) or {}
            stat_desc = ""
            if role_val == "Navigatore":
                surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                if cur_p == "Veloce": surv_mod -= 5
                stat_desc = f"(Sopravvivenza {surv_mod:+d})"
            elif role_val == "Sentinella":
                pp = get_passive_perception(p, cur_p)
                stat_desc = f"(PP: {pp})"
            elif role_val == "Cacciatore":
                surv_mod = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                stat_desc = f"(Sopravvivenza {surv_mod:+d})"
            elif role_val == "Furtivo":
                stealth_mod = get_skill_mod(sheet, "Furtività", "DES")
                stat_desc = f"(Furtività {stealth_mod:+d})"
                
            tk.Label(row_f, text=f"Ruolo: {role_val} {stat_desc}", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=28, anchor="w").pack(side=tk.LEFT, padx=4)
            
            exh = getattr(p, "exhaustion_level", 0)
            exh_col = ACCENT_RED if exh > 0 else TEXT_MUTED
            exh_txt = f"Sfinimento: {exh}/6" if exh > 0 else "Sfinimento: 0"
            tk.Label(row_f, text=exh_txt, font=("Segoe UI", 8, "bold"), bg=SURFACE_COLOR_ALT, fg=exh_col, width=14, anchor="e").pack(side=tk.RIGHT, padx=6)

    refresh_march_roster()

    # Consumo Razioni
    def do_consume_rations():
        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()
        msg = "🥖 [SISTEMA] CONSUMO RAZIONI & SOSTENTAMENTO GIORNALIERO:\n"
        for p in party_members:
            sheet = getattr(p, "full_sheet", None)
            if not sheet: continue
            has_ration = False
            has_water = False
            grid = sheet.get("inventory_grid", [])
            if isinstance(grid, list):
                for idx, it in enumerate(grid):
                    if not it or not isinstance(it, dict): continue
                    name_lower = str(it.get("name", "")).lower()
                    qty = int(it.get("qty", it.get("quantity", 1)) or 1)
                    if not has_ration and ("razion" in name_lower or "cibo" in name_lower) and qty > 0:
                        if qty - 1 <= 0: grid[idx] = None
                        else:
                            if "qty" in it: it["qty"] = qty - 1
                            if "quantity" in it: it["quantity"] = qty - 1
                        has_ration = True
                    elif not has_water and ("acqua" in name_lower or "otre" in name_lower) and qty > 0:
                        if qty - 1 <= 0: grid[idx] = None
                        else:
                            if "qty" in it: it["qty"] = qty - 1
                            if "quantity" in it: it["quantity"] = qty - 1
                        has_water = True
            
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
        refresh_march_roster()
        messagebox.showinfo("Razioni Consumate", "Razioni e acqua elaborate con successo per il gruppo.")

    # Avanzamento Marcia (4h o 8h)
    def do_march_advance(hours=4):
        cur_p = pace_var.get()
        b_key = getattr(gs, "travel_biome", "foresta")
        d_key = getattr(gs, "travel_danger", "moderate")
        biome_obj = BIOMES.get(b_key, BIOMES["foresta"])
        pace_obj = TRAVEL_PACES.get(cur_p, TRAVEL_PACES["Normale"])
        terrain_dc = biome_obj.get("dc_nav", 15)

        speed_mph = pace_obj["speed_mph"]
        miles_added = speed_mph * hours
        gs.travel_miles_today = getattr(gs, "travel_miles_today", 0) + miles_added
        gs.travel_hours_today = getattr(gs, "travel_hours_today", 0) + hours

        party_members = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
        if not party_members: party_members = gs.get_all_players()

        # 1. Navigazione
        navigators = [p for p in party_members if getattr(p, "travel_role", "") == "Navigatore"]
        if navigators:
            nav = navigators[0]
            sheet = getattr(nav, "full_sheet", {}) or {}
            bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
            if cur_p == "Veloce": bonus -= 5
            d20 = roll_dice("1d20")["total"]
            tot = d20 + bonus
            if tot >= terrain_dc:
                nav_msg = f"🧭 ROTTA MANTENUTA: Il Navigatore {nav.name} orienta la marcia! ({d20}{bonus:+d}={tot} vs CD {terrain_dc})"
            else:
                nav_msg = f"⚠️ SMARRITI: Il Navigatore {nav.name} perde la rotta! ({d20}{bonus:+d}={tot} vs CD {terrain_dc})"
        else:
            d20 = roll_dice("1d20")["total"]
            if d20 >= terrain_dc:
                nav_msg = f"🧭 ROTTA MANTENUTA: Il gruppo avanza a vista senza navigatore (d20: {d20} vs CD {terrain_dc})"
            else:
                nav_msg = f"⚠️ SMARRITI: Senza navigatore il gruppo perde la rotta! (d20: {d20} vs CD {terrain_dc})"

        # 2. Incontro Casuale
        enc_res = generate_biome_encounter(b_key, d_key, is_night=False)
        enc_msg = ""
        if enc_res.get("occurred"):
            title = enc_res.get("title")
            s_dc = enc_res.get("stealth_dc", 12)
            sentinels = [p for p in party_members if getattr(p, "travel_role", "") == "Sentinella"]
            if sentinels:
                best_s = max(sentinels, key=lambda s: get_passive_perception(s, cur_p))
                b_pp = get_passive_perception(best_s, cur_p)
                if b_pp >= s_dc:
                    enc_msg = f"⚔️ INCONTRO! La Sentinella {best_s.name} avvista '{title}' in anticipo! (PP {b_pp} vs Insidia CD {s_dc}) - Nessuna sorpresa!"
                else:
                    enc_msg = f"⚠️ IMBOSCATA! Nemici ({title}, Furtività CD {s_dc}) colgono il gruppo di sorpresa vs PP {b_pp}!"
            else:
                enc_msg = f"⚔️ INCONTRO CASUALE: '{title}'! (Nessuna sentinella di guardia)"
        else:
            enc_msg = "🌿 Marcia tranquilla: nessun pericolo ostile lungo la via."

        # 3. Caccia
        hunt_msg = ""
        if cur_p == "Veloce":
            hunt_msg = "🏹 Andatura Veloce: impossibile dedicarsi alla caccia."
        else:
            hunters = [p for p in party_members if getattr(p, "travel_role", "") == "Cacciatore"]
            if hunters:
                h = hunters[0]
                sheet = getattr(h, "full_sheet", {}) or {}
                s_bonus = get_skill_mod(sheet, "Sopravvivenza", "SAG")
                h_roll = roll_dice("1d20")["total"] + s_bonus
                if h_roll >= 15:
                    found = roll_dice("1d6")["total"] + max(0, get_stat_mod(sheet, "SAG"))
                    hunt_msg = f"🏹 CACCIA: {h.name} raccoglie {found} razioni e acqua fresca! (Tiro: {h_roll} vs CD 15)"
                else:
                    hunt_msg = f"🏹 CACCIA: {h.name} non trova provviste sufficienti (Tiro: {h_roll} vs CD 15)."

        # 4. Marcia Forzata
        exh_logs = []
        if gs.travel_hours_today > 8:
            extra = gs.travel_hours_today - 8
            con_dc = 10 + extra
            for p in party_members:
                sheet = getattr(p, "full_sheet", {}) or {}
                c_mod = get_stat_mod(sheet, "COS")
                d20_con = roll_dice("1d20")["total"]
                con_tot = d20_con + c_mod
                if con_tot < con_dc:
                    p.exhaustion_level = min(6, getattr(p, "exhaustion_level", 0) + 1)
                    conds = [c for c in getattr(p, "conditions", []) if not c.startswith("Sfinimento")]
                    conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
                    p.conditions = conds
                    if sheet:
                        sheet["exhaustion_level"] = p.exhaustion_level
                        sheet["conditions"] = conds
                    exh_logs.append(f"😫 {p.name}: Fallisce TS COS ({d20_con}{c_mod:+d}={con_tot} vs CD {con_dc}) -> Sfinimento Liv. {p.exhaustion_level}")
                else:
                    exh_logs.append(f"💪 {p.name}: Resiste alla fatica ({con_tot} vs CD {con_dc})")

        # Avanza l'ora sul server
        dm_gui.advance_time(hours, is_rest=False)

        res_msg = "========================================\n"
        res_msg += f"🧭 RESOCONTO MARCIA ({hours} ORE) - {miles_added} MIGLIA PERCORSE\n"
        res_msg += "========================================\n"
        res_msg += f"• Andatura: {cur_p} | Bioma: {biome_obj['name_it']} | Totale Oggi: {gs.travel_miles_today} mi ({gs.travel_hours_today}/8h)\n"
        res_msg += f"• {nav_msg}\n"
        res_msg += f"• {enc_msg}\n"
        if hunt_msg: res_msg += f"• {hunt_msg}\n"
        if exh_logs:
            res_msg += f"⚠️ MARCIA FORZATA (CD {10 + (gs.travel_hours_today - 8)}):\n"
            for el in exh_logs: res_msg += f"  - {el}\n"
        res_msg += "========================================"

        dm_gui.log_to_chat(res_msg, tab_name="Sistema")
        broadcast(gs, make_chat_broadcast("Viaggio", res_msg))
        broadcast(gs, make_game_state(gs.get_state_dict()))
        refresh_march_roster()
        h_color_n = ACCENT_RED if gs.travel_hours_today > 8 else TEXT_COLOR
        lbl_march_stats.config(text=f"⏱️ Ore Viaggiate Oggi: {gs.travel_hours_today} / 8h  |  🗺️ Miglia Percorse: {gs.travel_miles_today} mi", fg=h_color_n)

    # Pulsanti Azione Marcia
    m_act_f = tk.Frame(march_frame, bg=BG_COLOR)
    m_act_f.pack(fill=tk.X, padx=10, pady=12)

    ttk.Button(m_act_f, text="🚶 Avanza 4 Ore (Mezza Giornata)", command=lambda: do_march_advance(4), style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
    ttk.Button(m_act_f, text="🏃 Avanza 8 Ore (Giornata Intera)", command=lambda: do_march_advance(8), style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
    ttk.Button(m_act_f, text="🥖 Consuma Razioni", command=do_consume_rations, style="Info.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    # =========================================================================
    # TAB 2: ACCAMPAMENTO & TURNI DI GUARDIA NOTTURNA
    # =========================================================================
    camp_canvas = tk.Canvas(tab_camp, bg=BG_COLOR, highlightthickness=0)
    camp_scroll = ttk.Scrollbar(tab_camp, orient="vertical", command=camp_canvas.yview)
    camp_frame = ttk.Frame(camp_canvas)
    camp_frame.bind("<Configure>", lambda e: camp_canvas.configure(scrollregion=camp_canvas.bbox("all")))
    c_win = camp_canvas.create_window((0, 0), window=camp_frame, anchor="nw")
    camp_canvas.bind("<Configure>", lambda e: camp_canvas.itemconfig(c_win, width=e.width))
    camp_canvas.configure(yscrollcommand=camp_scroll.set)
    camp_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    camp_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    camp_header_box = tk.Frame(camp_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
    camp_header_box.pack(fill=tk.X, padx=10, pady=8)
    tk.Label(camp_header_box, text="🏕️ GESTIONE ACCAMPAMENTO & TURNI DI GUARDIA (8 ORE)", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 2))
    tk.Label(camp_header_box, text="Regole 5e RAW: Riposo Lungo 8h (max 2h di guardia per dormienti, 4h per elfi in Trance).",
             font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(anchor="w", padx=10, pady=(0, 6))

    # Opzioni Campo (Falò)
    camp_opts_f = tk.Frame(camp_header_box, bg=SURFACE_COLOR_ALT)
    camp_opts_f.pack(fill=tk.X, padx=10, pady=(0, 8))
    
    campfire_var = tk.BooleanVar(value=getattr(gs, "camp_has_campfire", True))
    chk_fire = ttk.Checkbutton(camp_opts_f, text="🔥 Falò Acceso (Luce elimina svantaggio al buio per guardie; aumenta visibilità campo)", variable=campfire_var)
    chk_fire.pack(anchor="w")

    # 4 Turni di Guardia
    shifts_box = tk.Frame(camp_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    shifts_box.pack(fill=tk.X, padx=10, pady=6)
    tk.Label(shifts_box, text="⏰ ASSEGNAZIONE SENTINELLE PER I 4 TURNI DI NOTTE", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 4))

    all_players = [p for p in gs.get_all_players() if getattr(p, "is_party_member", False) or not gs.combat_active]
    if not all_players: all_players = gs.get_all_players()
    player_names = ["Nessuno"] + [p.name for p in all_players]

    shift_combos = {}
    shift_pp_labels = {}
    cur_shifts = getattr(gs, "camp_watch_shifts", {})

    shift_info = [
        (1, "Turno 1 (22:00 - 00:00: Prima Serata)"),
        (2, "Turno 2 (00:00 - 02:00: Mezzanotte)"),
        (3, "Turno 3 (02:00 - 04:00: Cuore della Notte)"),
        (4, "Turno 4 (04:00 - 06:00: Alba)")
    ]

    for s_idx, s_title in shift_info:
        s_row = tk.Frame(shifts_box, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
        s_row.pack(fill=tk.X, padx=10, pady=3)

        tk.Label(s_row, text=s_title, font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, width=32, anchor="w").pack(side=tk.LEFT, padx=6, pady=4)

        cur_assigned = cur_shifts.get(s_idx) or cur_shifts.get(str(s_idx)) or "Nessuno"
        if cur_assigned not in player_names: cur_assigned = "Nessuno"

        s_var = tk.StringVar(value=cur_assigned)
        c_box = ttk.Combobox(s_row, textvariable=s_var, state="readonly", width=16, values=player_names)
        c_box.pack(side=tk.LEFT, padx=6)
        shift_combos[s_idx] = s_var

        pp_lbl = tk.Label(s_row, text="", font=("Segoe UI", 8), bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD, width=28, anchor="w")
        pp_lbl.pack(side=tk.LEFT, padx=6)
        shift_pp_labels[s_idx] = pp_lbl

        def make_shift_update(idx=s_idx, v_var=s_var, p_lbl=pp_lbl):
            def _update(event=None):
                p_name = v_var.get()
                p_obj = next((x for x in all_players if x.name == p_name), None)
                if p_obj:
                    st = calculate_effective_sentinel_pp(p_obj, campfire_var.get(), is_night=True)
                    dv_str = "👁️ Scurovisione" if st["has_darkvision"] else "Nessuna Scurovisione"
                    tr_str = " | 🧝 Trance (4h)" if st["is_elf_trance"] else ""
                    p_lbl.config(text=f"PP: {st['final_pp']} ({dv_str}{tr_str})", fg=ACCENT_GOLD)
                else:
                    p_lbl.config(text="Nessuna guardia (0 PP) ⚠️", fg=ACCENT_RED)
                # Salva su game state
                cur_shifts[idx] = p_name
                gs.camp_watch_shifts = cur_shifts
            return _update

        c_box.bind("<<ComboboxSelected>>", make_shift_update())
        make_shift_update()()

    # Risoluzione Notte & Riposo Lungo
    def do_resolve_night():
        assigned = {idx: shift_combos[idx].get() for idx in range(1, 5)}
        gs.camp_watch_shifts = assigned
        gs.camp_has_campfire = campfire_var.get()

        from server.rules.character import handle_resolve_night_camp_request
        handle_resolve_night_camp_request({"consume_rations": True}, None, gs)

        # Ricarica orario e statistiche
        time_str_new = f"📅 {gs.time_day} {month_name} {getattr(gs, 'time_year', 1492)} - {gs.time_hour:02d}:00 | ⛅ {translate_weather(getattr(gs, 'weather', 'Sereno'))}"
        lbl_march_stats.config(text=f"⏱️ Ore Viaggiate Oggi: {gs.travel_hours_today} / 8h  |  🗺️ Miglia Percorse: {gs.travel_miles_today} mi")
        refresh_march_roster()
        messagebox.showinfo("Notte Conclusa", "La notte e il Riposo Lungo sono stati elaborati! Consulta il log in chat.")

    camp_act_f = tk.Frame(camp_frame, bg=BG_COLOR)
    camp_act_f.pack(fill=tk.X, padx=10, pady=14)
    ttk.Button(camp_act_f, text="⛺ Risolvi Notte & Riposo Lungo (5e RAW)", command=do_resolve_night, style="Success.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    # =========================================================================
    # TAB 3: GENERATORE INCONTRI CASUALI PER BIOMA
    # =========================================================================
    enc_canvas = tk.Canvas(tab_encounters, bg=BG_COLOR, highlightthickness=0)
    enc_scroll = ttk.Scrollbar(tab_encounters, orient="vertical", command=enc_canvas.yview)
    enc_frame = ttk.Frame(enc_canvas)
    enc_frame.bind("<Configure>", lambda e: enc_canvas.configure(scrollregion=enc_canvas.bbox("all")))
    e_win = enc_canvas.create_window((0, 0), window=enc_frame, anchor="nw")
    enc_canvas.bind("<Configure>", lambda e: enc_canvas.itemconfig(e_win, width=e.width))
    enc_canvas.configure(yscrollcommand=enc_scroll.set)
    enc_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    enc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    enc_ctrl_box = tk.Frame(enc_frame, bg=SURFACE_COLOR_ALT, highlightbackground=BORDER_COLOR, highlightthickness=1)
    enc_ctrl_box.pack(fill=tk.X, padx=10, pady=8)
    tk.Label(enc_ctrl_box, text="🎲 GENERATORE INCONTRI CASUALI PER BIOMA", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 4))

    e_grid = tk.Frame(enc_ctrl_box, bg=SURFACE_COLOR_ALT)
    e_grid.pack(fill=tk.X, padx=10, pady=(0, 8))

    tk.Label(e_grid, text="Bioma di Riferimento:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).grid(row=0, column=0, sticky="w", pady=3)
    enc_biome_var = tk.StringVar(value=biome_names[cur_biome_idx])
    enc_b_combo = ttk.Combobox(e_grid, textvariable=enc_biome_var, state="readonly", width=30, values=biome_names)
    enc_b_combo.grid(row=0, column=1, sticky="w", padx=8, pady=3)

    tk.Label(e_grid, text="Grado di Pericolo:", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).grid(row=1, column=0, sticky="w", pady=3)
    enc_danger_var = tk.StringVar(value=danger_names[cur_danger_idx])
    enc_d_combo = ttk.Combobox(e_grid, textvariable=enc_danger_var, state="readonly", width=30, values=danger_names)
    enc_d_combo.grid(row=1, column=1, sticky="w", padx=8, pady=3)

    enc_night_var = tk.BooleanVar(value=False)
    chk_night = ttk.Checkbutton(e_grid, text="🌙 Incontro Notturno (soglia facilitata, pericoli aumentati)", variable=enc_night_var)
    chk_night.grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

    # Riquadro Risultato / Anteprima
    result_box = tk.Frame(enc_frame, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
    result_box.pack(fill=tk.X, padx=10, pady=6)

    tk.Label(result_box, text="📜 ANTEPRIMA INCONTRO ESTRATTO", font=("Segoe UI", 10, "bold"),
             bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", padx=10, pady=(6, 2))

    lbl_enc_title = tk.Label(result_box, text="Nessun incontro generato finora.", font=("Georgia", 11, "bold"), bg=SURFACE_COLOR, fg=TEXT_COLOR, wraplength=580, justify="left")
    lbl_enc_title.pack(anchor="w", padx=10, pady=2)

    lbl_enc_desc = tk.Label(result_box, text="Clicca 'Tira Incontro' o 'Forza Categoria' per estrarre un evento.", font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_MUTED, wraplength=580, justify="left")
    lbl_enc_desc.pack(anchor="w", padx=10, pady=2)

    lbl_enc_details = tk.Label(result_box, text="", font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=ACCENT_BLUE, wraplength=580, justify="left")
    lbl_enc_details.pack(anchor="w", padx=10, pady=(2, 8))

    current_extracted_encounter = {"data": None}

    def do_roll_encounter(force_cat=None):
        b_idx = enc_b_combo.current()
        d_idx = enc_d_combo.current()
        b_k = biome_keys[b_idx] if 0 <= b_idx < len(biome_keys) else "foresta"
        d_k = danger_keys[d_idx] if 0 <= d_idx < len(danger_keys) else "moderate"

        res = generate_biome_encounter(
            biome_key=b_k,
            danger_key=d_k,
            is_night=enc_night_var.get(),
            force_category=force_cat
        )
        current_extracted_encounter["data"] = res

        if not res.get("occurred"):
            lbl_enc_title.config(text=f"🌿 Nessun Incontro (Tiro d20: {res.get('roll')}/{res.get('threshold')})", fg=ACCENT_GREEN)
            lbl_enc_desc.config(text="La via è tranquilla e priva di minacce imminenti.")
            lbl_enc_details.config(text="")
            btn_broadcast.config(state="disabled")
            btn_spawn.config(state="disabled")
        else:
            cat_icons = {"combat": "⚔️ COMBATTIMENTO", "social": "🤝 SOCIALE", "discovery": "✨ SCOPERTA", "hazard": "⚠️ PERICOLO"}
            c_tag = cat_icons.get(res.get("category"), "INCONTRO")
            lbl_enc_title.config(text=f"{c_tag}: {res.get('title')}", fg=ACCENT_GOLD)
            lbl_enc_desc.config(text=res.get("description", ""))

            det_str = f"Distanza: {res.get('dist_hexes', 6)} esagoni  |  Furtività CD: {res.get('stealth_dc', 12)}"
            if res.get("monsters"):
                m_str = ", ".join([f"{m['count']}x {m['name']} (CR {m['cr']})" for m in res["monsters"]])
                det_str += f"\nCreature: {m_str}"
            if res.get("reward"):
                det_str += f"\nRicompensa/Esito: {res['reward']}"
            if res.get("save_stat"):
                det_str += f"\nTiro Salvezza: TS {res['save_stat']} CD {res['save_dc']} ({res.get('fail_effect', '')})"
            lbl_enc_details.config(text=det_str, fg=ACCENT_BLUE)
            btn_broadcast.config(state="normal")
            if res.get("monsters"):
                btn_spawn.config(state="normal")
            else:
                btn_spawn.config(state="disabled")

    def do_broadcast_encounter():
        enc = current_extracted_encounter.get("data")
        if not enc or not enc.get("occurred"): return
        msg = f"🎲 [INCONTRO 5e - {enc.get('category', '').upper()}] {enc.get('title')}\n{enc.get('description')}"
        if enc.get("monsters"):
            m_names = ", ".join([f"{m['count']}x {m['name']}" for m in enc["monsters"]])
            msg += f"\n⚔️ Nemici: {m_names} (a {enc.get('dist_hexes', 6)} esagoni, Furtività CD {enc.get('stealth_dc', 12)})"
        if enc.get("reward"): msg += f"\n✨ Esito: {enc['reward']}"
        if enc.get("save_stat"): msg += f"\n⚠️ Pericolo: Richiesto TS {enc['save_stat']} CD {enc['save_dc']} ({enc.get('fail_effect', '')})"
        broadcast(gs, make_chat_broadcast("Viaggio", msg))
        dm_gui.log_to_chat(msg)
        messagebox.showinfo("Inviato", "Incontro trasmesso a tutti i giocatori in chat.")

    def do_spawn_monsters():
        enc = current_extracted_encounter.get("data")
        if not enc or not enc.get("monsters"): return
        from common.srd_offline import get_monster_offline
        spawned_count = 0
        for m_info in enc["monsters"]:
            m_name = m_info["name"]
            m_cnt = m_info.get("count", 1)
            srd_data = get_monster_offline(m_name)
            if not srd_data:
                # Prova ricerca parziale
                from common.srd_offline import search_monsters_offline
                matches = search_monsters_offline(m_name)
                if matches: srd_data = matches[0]

            if srd_data:
                for _ in range(m_cnt):
                    dm_gui.on_monster_spawned(srd_data, "monsters")
                    spawned_count += 1
            else:
                # Fallback instanziazione generica
                for _ in range(m_cnt):
                    fallback_data = {"name": m_name, "hp": 15, "ac": 12, "speed": 30, "size": "Medium"}
                    dm_gui.on_monster_spawned(fallback_data, "monsters")
                    spawned_count += 1

        messagebox.showinfo("Mostri Schierati", f"Schierati con successo {spawned_count} mostri sulla mappa tattica!")

    # Pulsanti Generazione Incontro
    enc_btn_f = tk.Frame(enc_frame, bg=BG_COLOR)
    enc_btn_f.pack(fill=tk.X, padx=10, pady=10)

    ttk.Button(enc_btn_f, text="🎲 Tira Incontro Casuale", command=lambda: do_roll_encounter(None), style="Primary.TButton").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=3)
    ttk.Button(enc_btn_f, text="⚔️ Combattimento", command=lambda: do_roll_encounter("combat"), style="Warning.TButton").pack(side=tk.LEFT, padx=3)
    ttk.Button(enc_btn_f, text="🤝 Sociale", command=lambda: do_roll_encounter("social"), style="Info.TButton").pack(side=tk.LEFT, padx=3)
    ttk.Button(enc_btn_f, text="✨ Scoperta", command=lambda: do_roll_encounter("discovery"), style="Success.TButton").pack(side=tk.LEFT, padx=3)
    ttk.Button(enc_btn_f, text="⚠️ Pericolo", command=lambda: do_roll_encounter("hazard"), style="Danger.TButton").pack(side=tk.LEFT, padx=3)

    enc_act_f = tk.Frame(enc_frame, bg=BG_COLOR)
    enc_act_f.pack(fill=tk.X, padx=10, pady=(4, 12))

    btn_broadcast = ttk.Button(enc_act_f, text="📢 Invia Incontro in Chat", command=do_broadcast_encounter, style="Accent.TButton", state="disabled")
    btn_broadcast.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    btn_spawn = ttk.Button(enc_act_f, text="⚔️ Schiera Mostri sulla Mappa", command=do_spawn_monsters, style="Primary.TButton", state="disabled")
    btn_spawn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    # Chiusura
    ttk.Button(win, text="Chiudi", command=win.destroy).pack(side=tk.RIGHT, padx=12, pady=8)
