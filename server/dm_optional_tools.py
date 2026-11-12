"""
Pannello Strumenti DM 5e (PHB / DMG / MM):
Fornisce al Dungeon Master controlli diretti per attivare/gestire:
- Sorpresa (Round 1), Presenza Terrificante, Inghiottire (Swallow), Immersione/Respiro, Calcolo Salto
- Follia DMG, Veleni & Malattie DMG, Manovre Opzionali DMG, Inseguimenti, Sopravvivenza, Oggetti & Soglia Danno
"""
import tkinter as tk
from tkinter import ttk, messagebox

from common.dnd5e_tables import (
    calculate_jump_distances,
    DMG_POISONS,
    DMG_DISEASES,
    OBJECT_MATERIALS_AC,
    OBJECT_SIZE_HP,
    entity_get_effective_attr,
)
from server.rules.class_abilities import (
    handle_surprise_request,
    handle_frightful_presence_request,
    handle_swallow_request,
    handle_submerged_breath_request,
    handle_madness_request,
    handle_apply_poison_or_disease_request,
    handle_dmg_maneuver_request,
    handle_survival_tick_request,
    handle_chase_dash_request,
)


def open_optional_rules_tools_dialog(dm_gui):
    """Apre la finestra degli Strumenti Regole 5e Avanzate per il Dungeon Master."""
    win = tk.Toplevel(dm_gui.master)
    win.title("📕 Strumenti Regole 5e (PHB / DMG / MM)")
    win.geometry("660x600")
    win.transient(dm_gui.master)
    win.grab_set()

    server = getattr(dm_gui, "server", None)
    game_state = getattr(server, "game_state", None) if server else None
    player_names = [p.name for p in getattr(game_state, "players", [])] if game_state else []
    default_target = player_names[0] if player_names else ""

    nb = ttk.Notebook(win)
    nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tab_combat = ttk.Frame(nb, padding=10)
    tab_dmg = ttk.Frame(nb, padding=10)
    tab_env = ttk.Frame(nb, padding=10)
    nb.add(tab_combat, text="⚔️ Combattimento & Mostri")
    nb.add(tab_dmg, text="📕 Follia, Veleni, Manovre DMG")
    nb.add(tab_env, text="🌊 Sopravvivenza, Salto & Oggetti")

    # --- TAB 1: Combattimento & Tratti Mostri ---
    frm_sur = ttk.LabelFrame(tab_combat, text="Sorpresa (PHB p. 189) & Immersione (PHB p. 198)", padding=8)
    frm_sur.pack(fill=tk.X, pady=(0, 8))
    tgt_var = tk.StringVar(value=default_target)
    ttk.Label(frm_sur, text="Bersaglio:").grid(row=0, column=0, sticky="w", padx=4)
    tgt_cb = ttk.Combobox(frm_sur, textvariable=tgt_var, values=player_names, width=24)
    tgt_cb.grid(row=0, column=1, padx=4)

    def _toggle_surprise(state_val: bool):
        if game_state and tgt_var.get():
            handle_surprise_request({"target_name": tgt_var.get(), "surprised": state_val}, None, game_state)

    def _toggle_submerged():
        if game_state and tgt_var.get():
            handle_submerged_breath_request({"actor_name": tgt_var.get(), "action": "toggle_submerged"}, None, game_state)

    ttk.Button(frm_sur, text="⚡ Sorpreso ON", command=lambda: _toggle_surprise(True)).grid(row=0, column=2, padx=4)
    ttk.Button(frm_sur, text="✔ Rimuovi Sorpresa", command=lambda: _toggle_surprise(False)).grid(row=0, column=3, padx=4)
    ttk.Button(frm_sur, text="🌊 Toggle Immerso", command=_toggle_submerged).grid(row=1, column=1, pady=6, sticky="w", padx=4)
    ttk.Button(
        frm_sur,
        text="⏱ -1 Round Respiro",
        command=lambda: game_state and tgt_var.get() and handle_submerged_breath_request({"actor_name": tgt_var.get(), "action": "tick_breath"}, None, game_state),
    ).grid(row=1, column=2, pady=6, padx=4)

    frm_mm = ttk.LabelFrame(tab_combat, text="Tratti Speciali Mostri (MM)", padding=8)
    frm_mm.pack(fill=tk.X, pady=(0, 8))
    src_var = tk.StringVar(value=default_target)
    ttk.Label(frm_mm, text="Attore / Mostro:").grid(row=0, column=0, sticky="w", padx=4)
    ttk.Combobox(frm_mm, textvariable=src_var, values=player_names, width=22).grid(row=0, column=1, padx=4)
    dc_var = tk.StringVar(value="16")
    ttk.Label(frm_mm, text="CD:").grid(row=0, column=2, padx=4)
    ttk.Entry(frm_mm, textvariable=dc_var, width=5).grid(row=0, column=3, padx=4)

    ttk.Button(
        frm_mm,
        text="😱 Presenza Terrificante",
        command=lambda: game_state and src_var.get() and handle_frightful_presence_request({"actor_name": src_var.get(), "dc": int(dc_var.get() or 16)}, None, game_state),
    ).grid(row=1, column=1, pady=6, sticky="w", padx=4)
    ttk.Button(
        frm_mm,
        text="🐍 Inghiotti (Swallow)",
        command=lambda: game_state and src_var.get() and tgt_var.get() and handle_swallow_request({"actor_name": src_var.get(), "target_name": tgt_var.get(), "release": False}, None, game_state),
    ).grid(row=1, column=2, pady=6, padx=4)
    ttk.Button(
        frm_mm,
        text="🤢 Rigurgita",
        command=lambda: game_state and src_var.get() and tgt_var.get() and handle_swallow_request({"actor_name": src_var.get(), "target_name": tgt_var.get(), "release": True}, None, game_state),
    ).grid(row=1, column=3, pady=6, padx=4)

    # --- TAB 2: DMG Follia, Veleni/Malattie, Manovre ---
    frm_mad = ttk.LabelFrame(tab_dmg, text="Follia (DMG p. 258-260)", padding=8)
    frm_mad.pack(fill=tk.X, pady=(0, 8))
    mad_tier = tk.StringVar(value="short")
    ttk.Label(frm_mad, text="Bersaglio:").grid(row=0, column=0, padx=4)
    ttk.Combobox(frm_mad, textvariable=tgt_var, values=player_names, width=20).grid(row=0, column=1, padx=4)
    ttk.Combobox(frm_mad, textvariable=mad_tier, values=["short", "long", "indefinite"], width=12, state="readonly").grid(row=0, column=2, padx=4)
    ttk.Button(
        frm_mad,
        text="🌀 Tira Tabella Follia",
        command=lambda: game_state and tgt_var.get() and handle_madness_request({"target_name": tgt_var.get(), "tier": mad_tier.get()}, None, game_state),
    ).grid(row=0, column=3, padx=4)

    frm_poi = ttk.LabelFrame(tab_dmg, text="Veleni & Malattie DMG (p. 256-258)", padding=8)
    frm_poi.pack(fill=tk.X, pady=(0, 8))
    pd_kind = tk.StringVar(value="poison")
    pd_names = list(DMG_POISONS.keys()) + list(DMG_DISEASES.keys())
    pd_name = tk.StringVar(value=pd_names[0] if pd_names else "")
    ttk.Combobox(frm_poi, textvariable=pd_kind, values=["poison", "disease"], width=10, state="readonly").grid(row=0, column=0, padx=4)
    ttk.Combobox(frm_poi, textvariable=pd_name, values=pd_names, width=28).grid(row=0, column=1, padx=4)
    ttk.Button(
        frm_poi,
        text="☠️ Applica (TS COS)",
        command=lambda: game_state and tgt_var.get() and handle_apply_poison_or_disease_request({"target_name": tgt_var.get(), "kind": pd_kind.get(), "name": pd_name.get()}, None, game_state),
    ).grid(row=0, column=2, padx=4)

    frm_man = ttk.LabelFrame(tab_dmg, text="Manovre Opzionali DMG (p. 271-272)", padding=8)
    frm_man.pack(fill=tk.X, pady=(0, 8))
    dmg_man = tk.StringVar(value="disarm")
    ttk.Label(frm_man, text="Attaccante:").grid(row=0, column=0, padx=4)
    ttk.Combobox(frm_man, textvariable=src_var, values=player_names, width=18).grid(row=0, column=1, padx=4)
    ttk.Combobox(frm_man, textvariable=dmg_man, values=["disarm", "overrun", "tumble", "shove_aside"], width=14, state="readonly").grid(row=0, column=2, padx=4)
    ttk.Button(
        frm_man,
        text="⚔️ Esegui vs Bersaglio",
        command=lambda: game_state and src_var.get() and tgt_var.get() and handle_dmg_maneuver_request({"actor_name": src_var.get(), "target_name": tgt_var.get(), "maneuver": dmg_man.get()}, None, game_state),
    ).grid(row=0, column=3, padx=4)

    # --- TAB 3: Sopravvivenza, Salto, Oggetti ---
    frm_surv = ttk.LabelFrame(tab_env, text="Sopravvivenza, Clima Estremo & Inseguimenti DMG", padding=8)
    frm_surv.pack(fill=tk.X, pady=(0, 8))
    ttk.Button(
        frm_surv,
        text="🥖 Tick Fame/Sete (+1 Giorno)",
        command=lambda: game_state and handle_survival_tick_request({"event": "day_pass"}, None, game_state),
    ).grid(row=0, column=0, padx=4, pady=4)
    ttk.Button(
        frm_surv,
        text="🔥 Clima: Caldo Estremo",
        command=lambda: game_state and handle_survival_tick_request({"event": "extreme_heat"}, None, game_state),
    ).grid(row=0, column=1, padx=4, pady=4)
    ttk.Button(
        frm_surv,
        text="❄️ Clima: Freddo Estremo",
        command=lambda: game_state and handle_survival_tick_request({"event": "extreme_cold"}, None, game_state),
    ).grid(row=0, column=2, padx=4, pady=4)
    ttk.Button(
        frm_surv,
        text="🏃 Scatto Inseguimento + Complicazione",
        command=lambda: game_state and tgt_var.get() and handle_chase_dash_request({"actor_name": tgt_var.get()}, None, game_state),
    ).grid(row=1, column=0, columnspan=2, padx=4, pady=4, sticky="w")

    frm_calc = ttk.LabelFrame(tab_env, text="Calcolatore Salto (PHB p. 182) & CA/HP Oggetti (DMG p. 246)", padding=8)
    frm_calc.pack(fill=tk.BOTH, expand=True)
    calc_out = tk.Text(frm_calc, height=11, wrap="word")
    calc_out.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

    def _calc_jump_and_objects():
        lines = []
        if game_state and tgt_var.get():
            pl = game_state.find_player(tgt_var.get())
            if pl:
                str_s = entity_get_effective_attr(pl, "FOR")
                j = calculate_jump_distances(str_s, running_start=True)
                lines.append(f"Salto con Rincorsa per {pl.name} (FOR {str_s}):")
                lines.append(f"  • Lungo: {j['long_jump_ft']} ft ({j['long_jump_m']} m) | Alto: {j['high_jump_ft']} ft ({j['high_jump_m']} m)")
        lines.append("\nCA Oggetti DMG: " + ", ".join(f"{k}={v}" for k, v in OBJECT_MATERIALS_AC.items()))
        lines.append("HP Oggetti DMG (Fragile/Resiliente): " + ", ".join(f"{k}:{v}" for k, v in OBJECT_SIZE_HP.items()))
        calc_out.delete("1.0", tk.END)
        calc_out.insert("1.0", "\n".join(lines))

    _calc_jump_and_objects()
    ttk.Button(frm_calc, text="🔄 Aggiorna Calcoli per Bersaglio", command=_calc_jump_and_objects).pack(anchor="e")

    ttk.Button(win, text="Chiudi", command=win.destroy).pack(pady=(0, 10))
