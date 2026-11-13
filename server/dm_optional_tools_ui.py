"""Interfaccia grafica DM Workbench per tutte le regole opzionali 5e (PHB / DMG / MM / XGtE / TCE)."""
import tkinter as tk
from tkinter import ttk, scrolledtext
from common.messagebox import messagebox
from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE, ACCENT_RED,
    TEXT_COLOR, TEXT_MUTED, FONT_TITLE, FONT_BOLD, FONT_SMALL
)


def open_optional_rules_tools_dialog(dm_gui, initial_tab: int = 0):
    """Apre il pannello di controllo unificato Strumenti Regole 5e (PHB/DMG/MM/XGtE/TCE) per il DM."""
    gs = getattr(getattr(dm_gui, "server", None), "game_state", None)
    if gs is None:
        return None

    win = tk.Toplevel(dm_gui.master)
    win.title("📕 Strumenti Regole 5e (PHB / DMG / MM / XGtE / TCE)")
    win.minsize(780, 640)
    win.transient(dm_gui.master)
    apply_modern_window_style(win)

    from server.dm_optional_tools import (
        handle_optional_rule_action_request,
        calculate_sentient_ego,
        roll_artifact_properties,
        SIEGE_EQUIPMENT_CATALOG,
        BASTION_FACILITIES_CATALOG,
        apply_initiative_variant,
        compute_speed_factor_modifier,
    )
    from server.rules.class_abilities import (
        handle_frightful_presence_request,
        handle_swallow_request,
        handle_madness_request,
        handle_apply_poison_or_disease_request,
        handle_survival_tick_request,
        handle_surprise_request,
    )
    from server.dm_generators import RandomDungeonGenerator, SettlementGenerator

    players = [p.name for p in getattr(gs, "players", [])] or ["PG"]
    actor_var = tk.StringVar(value=players[0])
    target_var = tk.StringVar(value=players[-1])

    hdr = tk.Frame(win, bg=SURFACE_COLOR, padx=12, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
    hdr.pack(fill=tk.X, padx=8, pady=(8, 4))
    tk.Label(hdr, text="📕 Workbench Regole Opzionali & Strumenti DM", font=FONT_TITLE, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)

    sel_f = tk.Frame(hdr, bg=SURFACE_COLOR)
    sel_f.pack(side=tk.RIGHT)
    tk.Label(sel_f, text="Attore:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 4))
    cb_actor = ttk.Combobox(sel_f, textvariable=actor_var, values=players, state="readonly", width=16)
    cb_actor.pack(side=tk.LEFT, padx=(0, 8))
    tk.Label(sel_f, text="Bersaglio:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 4))
    cb_target = ttk.Combobox(sel_f, textvariable=target_var, values=players, state="readonly", width=16)
    cb_target.pack(side=tk.LEFT)

    nb = ttk.Notebook(win)
    nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

    out_log = scrolledtext.ScrolledText(win, height=6, bg=BG_COLOR, fg=TEXT_COLOR, font=("Consolas", 9), wrap=tk.WORD)
    out_log.pack(fill=tk.X, padx=8, pady=(2, 8))

    def _log(txt: str):
        out_log.insert(tk.END, f"{txt}\n")
        out_log.see(tk.END)
        if hasattr(dm_gui, "update_player_list"):
            try:
                dm_gui.update_player_list()
                dm_gui.update_canvas()
            except Exception:
                pass

    def _dispatch_opt(action: str, **kwargs):
        data = {"action": action, "actor_name": actor_var.get(), "target_name": target_var.get()}
        data.update(kwargs)
        handle_optional_rule_action_request(data, gs.find_player(actor_var.get()), gs)
        _log(f"▶ Eseguito '{action}' (Attore={actor_var.get()}, Bersaglio={target_var.get()})")

    # --- TAB 1: Combattimento, Mostri, Paura, Ferite & Sopravvivenza ---
    tab1 = ttk.Frame(nb, padding=10)
    nb.add(tab1, text="⚔️ Combattimento & Mostri")

    dc_var = tk.IntVar(value=15)
    param_f = ttk.Frame(tab1)
    param_f.pack(fill=tk.X, pady=(0, 8))
    ttk.Label(param_f, text="CD / Parametro:").pack(side=tk.LEFT)
    ttk.Spinbox(param_f, from_=5, to=30, textvariable=dc_var, width=5).pack(side=tk.LEFT, padx=(4, 12))
    poison_var = tk.StringVar(value="Veleno Base")
    ttk.Label(param_f, text="Veleno/Malattia/Ferita:").pack(side=tk.LEFT)
    ttk.Entry(param_f, textvariable=poison_var, width=22).pack(side=tk.LEFT, padx=4)

    btn_grid1 = ttk.Frame(tab1)
    btn_grid1.pack(fill=tk.BOTH, expand=True)
    btn_grid1.columnconfigure(0, weight=1)
    btn_grid1.columnconfigure(1, weight=1)
    btn_grid1.columnconfigure(2, weight=1)

    t1_actions = [
        ("🏳️ Check Morale Nemici (DMG)", lambda: _dispatch_opt("morale_check", reason="manual")),
        ("🌟 Punto Eroe: +1d6 Tiro", lambda: _dispatch_opt("hero_point", mode="roll_bonus")),
        ("💫 Punto Eroe: Stabilizza Morte", lambda: _dispatch_opt("hero_point", mode="death_save")),
        ("💗 Impulso Curativo (1 DV)", lambda: _dispatch_opt("healing_surge", count=1)),
        ("😱 Tiro Paura (DMG p.266)", lambda: _dispatch_opt("fear_save", dc=dc_var.get())),
        ("👁️ Tiro Orrore + Follia (DMG)", lambda: _dispatch_opt("horror_save", dc=dc_var.get())),
        ("🩺 Cura Ferita (Rigenerazione)", lambda: _dispatch_opt("cure_injury", method="regenerate")),
        ("🧪 Estrai Veleno (DMG p.258)", lambda: _dispatch_opt("harvest_poison", poison_name=poison_var.get())),
        ("🐉 Presenza Terrificante (MM)", lambda: (handle_frightful_presence_request({"dc": dc_var.get(), "actor_name": actor_var.get()}, None, gs), _log("🐉 Presenza Terrificante attivata."))),
        ("🐍 Inghiotti Bersaglio (MM)", lambda: (handle_swallow_request({"target_name": target_var.get(), "actor_name": actor_var.get(), "release": False}, None, gs), _log("🐍 Inghiotti eseguito."))),
        ("🤮 Rigurgita / Libera Stomaco", lambda: (handle_swallow_request({"target_name": target_var.get(), "actor_name": actor_var.get(), "release": True}, None, gs), _log("🤮 Bersaglio liberato."))),
        ("🌀 Applica Follia Breve (DMG)", lambda: (handle_madness_request({"target_name": target_var.get(), "tier": "short"}, None, gs), _log("🌀 Follia applicata."))),
        ("☠️ Applica Veleno (CD Specifica)", lambda: (handle_apply_poison_or_disease_request({"target_name": target_var.get(), "kind": "poison", "name": poison_var.get(), "dc": dc_var.get()}, None, gs), _log("☠️ Veleno applicato."))),
        ("💧 Tick Sopravvivenza (1 Giorno)", lambda: (handle_survival_tick_request({"event": "day_pass"}, None, gs), _log("💧 Tick Sopravvivenza eseguito."))),
        ("😲 Sorpreso ON (Toggle)", lambda: (handle_surprise_request({"target_name": target_var.get(), "surprised": True}, None, gs), _log("😲 Sorpresa applicata."))),
    ]
    for idx, (lbl, cmd) in enumerate(t1_actions):
        r, c = divmod(idx, 3)
        ttk.Button(btn_grid1, text=lbl, command=cmd).grid(row=r, column=c, sticky="ew", padx=4, pady=3)

    # Speed Factor Pre-Round Panel
    sf_frame = ttk.LabelFrame(tab1, text="⚡ Fattore Velocità (Speed Factor - DMG p. 270)", padding=8)
    sf_frame.pack(fill=tk.X, pady=(8, 0))
    sf_act_var = tk.StringVar(value="melee")
    ttk.Label(sf_frame, text="Azione Dichiarata per Attore:").pack(side=tk.LEFT)
    sf_cb = ttk.Combobox(
        sf_frame,
        textvariable=sf_act_var,
        values=["melee", "light / finesse (+2)", "heavy / loading (-2)", "ranged (-5)", "spell 1", "spell 3", "spell 5"],
        width=24,
    )
    sf_cb.pack(side=tk.LEFT, padx=6)

    def _apply_sf_decl():
        p_obj = gs.find_player(actor_var.get())
        if p_obj:
            p_obj.speed_factor_declared_action = sf_act_var.get()
            mod_v = compute_speed_factor_modifier(p_obj, sf_act_var.get())
            _log(f"⚡ {p_obj.name} dichiara '{sf_act_var.get()}' (mod Speed Factor: {mod_v:+d}).")

    def _reroll_init_variant():
        logs = apply_initiative_variant(gs)
        for m in logs:
            _log(m)

    ttk.Button(sf_frame, text="Dichiara per Attore", command=_apply_sf_decl).pack(side=tk.LEFT, padx=4)
    ttk.Button(sf_frame, text="🎲 Ricalcola Iniziativa Variante", command=_reroll_init_variant, style="Gold.TButton").pack(side=tk.RIGHT)

    # --- TAB 2: Trappole, Assedio, Senzienti & Artefatti ---
    tab2 = ttk.Frame(nb, padding=10)
    nb.add(tab2, text="⚙️ Trappole, Assedio & Artefatti")

    trap_f = ttk.LabelFrame(tab2, text="⚙️ Registra Trappola Complessa (Init 20/10 - XGtE)", padding=8)
    trap_f.pack(fill=tk.X, pady=(0, 8))
    trap_name = tk.StringVar(value="Lame Rotanti del Corridoio")
    trap_init = tk.IntVar(value=20)
    trap_stat = tk.StringVar(value="DES")
    trap_dc = tk.IntVar(value=15)
    trap_dmg = tk.StringVar(value="2d10")
    ttk.Entry(trap_f, textvariable=trap_name, width=26).grid(row=0, column=0, padx=4)
    ttk.Combobox(trap_f, textvariable=trap_init, values=[20, 10], width=4, state="readonly").grid(row=0, column=1, padx=4)
    ttk.Combobox(trap_f, textvariable=trap_stat, values=["FOR", "DES", "COS", "INT", "SAG", "CAR"], width=5, state="readonly").grid(row=0, column=2, padx=4)
    ttk.Spinbox(trap_f, from_=8, to=25, textvariable=trap_dc, width=4).grid(row=0, column=3, padx=4)
    ttk.Entry(trap_f, textvariable=trap_dmg, width=8).grid(row=0, column=4, padx=4)
    ttk.Button(
        trap_f,
        text="➕ Aggiungi Trappola",
        command=lambda: _dispatch_opt(
            "complex_trap_add",
            trap={
                "name": trap_name.get(),
                "initiative": trap_init.get(),
                "save_stat": trap_stat.get(),
                "dc": trap_dc.get(),
                "damage_formula": trap_dmg.get(),
            },
        ),
        style="Primary.TButton",
    ).grid(row=0, column=5, padx=6)

    siege_f = ttk.LabelFrame(tab2, text="🏰 Armi d'Assedio (DMG p. 255)", padding=8)
    siege_f.pack(fill=tk.X, pady=(0, 8))
    siege_var = tk.StringVar(value="ballista")
    ttk.Combobox(siege_f, textvariable=siege_var, values=list(SIEGE_EQUIPMENT_CATALOG.keys()), state="readonly", width=16).pack(side=tk.LEFT, padx=4)
    ttk.Button(siege_f, text="💥 Spara su Bersaglio", command=lambda: _dispatch_opt("siege_action", engine=siege_var.get()), style="Danger.TButton").pack(side=tk.LEFT, padx=6)

    sent_f = ttk.LabelFrame(tab2, text="🗡️ Oggetti Magici Senzienti & Artefatti (DMG p. 214-221)", padding=8)
    sent_f.pack(fill=tk.X)
    item_sent_var = tk.StringVar(value="Lama Nera Senziente")
    ego_var = tk.IntVar(value=14)
    ttk.Entry(sent_f, textvariable=item_sent_var, width=22).pack(side=tk.LEFT, padx=4)
    ttk.Label(sent_f, text="Ego:").pack(side=tk.LEFT)
    ttk.Spinbox(sent_f, from_=1, to=30, textvariable=ego_var, width=4).pack(side=tk.LEFT, padx=4)
    ttk.Button(sent_f, text="⚔️ Conflitto Ego", command=lambda: _dispatch_opt("sentient_conflict", item_name=item_sent_var.get(), ego=ego_var.get())).pack(side=tk.LEFT, padx=6)
    ttk.Button(sent_f, text="👑 Genera Proprietà Artefatto", command=lambda: (_dispatch_opt("roll_artifact"), _log(str(roll_artifact_properties()))), style="Gold.TButton").pack(side=tk.RIGHT, padx=4)

    # --- TAB 3: Bastioni, Seguaci, Fama & Devozione (DMG/TCE) ---
    tab3 = ttk.Frame(nb, padding=10)
    nb.add(tab3, text="🏰 Bastioni, Seguaci & Fama")

    sk_f = ttk.LabelFrame(tab3, text="🤝 Seguaci / Sidekicks (TCE)", padding=8)
    sk_f.pack(fill=tk.X, pady=(0, 8))
    sk_role = tk.StringVar(value="warrior")
    ttk.Combobox(sk_f, textvariable=sk_role, values=["warrior", "expert", "spellcaster"], state="readonly", width=16).pack(side=tk.LEFT, padx=4)
    ttk.Button(sk_f, text="⬆️ Sali di Livello Seguace (Bersaglio)", command=lambda: _dispatch_opt("sidekick_level_up", role=sk_role.get()), style="Primary.TButton").pack(side=tk.LEFT, padx=6)

    rp_f = ttk.LabelFrame(tab3, text="🏛️ Fama (Renown) & Pietà (Piety)", padding=8)
    rp_f.pack(fill=tk.X, pady=(0, 8))
    track_var = tk.StringVar(value="renown")
    delta_var = tk.IntVar(value=1)
    org_var = tk.StringVar(value="Ordine / Divinità")
    ttk.Combobox(rp_f, textvariable=track_var, values=["renown", "piety"], state="readonly", width=10).pack(side=tk.LEFT, padx=4)
    ttk.Spinbox(rp_f, from_=-5, to=10, textvariable=delta_var, width=4).pack(side=tk.LEFT, padx=4)
    ttk.Entry(rp_f, textvariable=org_var, width=22).pack(side=tk.LEFT, padx=4)
    ttk.Button(rp_f, text="Aggiorna Bersaglio", command=lambda: _dispatch_opt("renown_piety", track=track_var.get(), delta=delta_var.get(), label=org_var.get())).pack(side=tk.LEFT, padx=6)

    bas_f = ttk.LabelFrame(tab3, text="🏰 Ordini del Bastione (DMG 2024)", padding=8)
    bas_f.pack(fill=tk.X)
    fac_var = tk.StringVar(value="treasury")
    ttk.Combobox(bas_f, textvariable=fac_var, values=list(BASTION_FACILITIES_CATALOG.keys()), state="readonly", width=18).pack(side=tk.LEFT, padx=4)
    ttk.Button(bas_f, text="📜 Esegui Turno Bastione", command=lambda: _dispatch_opt("bastion_order", facility=fac_var.get()), style="Gold.TButton").pack(side=tk.LEFT, padx=6)

    # --- TAB 4: Generatori Mondo DMG (Dungeon & Insediamenti) ---
    tab4 = ttk.Frame(nb, padding=10)
    nb.add(tab4, text="🏛️ Generatori Dungeon & Città")

    gen_ctrl = ttk.Frame(tab4)
    gen_ctrl.pack(fill=tk.X, pady=(0, 6))
    rooms_var = tk.IntVar(value=5)
    ttk.Label(gen_ctrl, text="Stanze Dungeon:").pack(side=tk.LEFT)
    ttk.Spinbox(gen_ctrl, from_=2, to=15, textvariable=rooms_var, width=4).pack(side=tk.LEFT, padx=(4, 10))
    gen_txt = scrolledtext.ScrolledText(tab4, height=14, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=("Consolas", 10), wrap=tk.WORD)
    gen_txt.pack(fill=tk.BOTH, expand=True)

    def _gen_dungeon():
        res = RandomDungeonGenerator.generate(rooms_var.get())
        gen_txt.delete("1.0", tk.END)
        lines = [f"🏛️ DUNGEON CASUALE (DMG Appendice A)", f"Posizione: {res['location']}", f"Creatori: {res['creator']}", f"Scopo: {res['purpose']}", ""]
        for r in res["rooms"]:
            lines.append(f"• {r['name']} ({r['dimensions_ft']}) | Porta: {r['door']} | Trappola: {r['hazard']} | Dettaglio: {r['dressing']}")
        gen_txt.insert(tk.END, "\n".join(lines))

    def _gen_settlement():
        res = SettlementGenerator.generate()
        gen_txt.delete("1.0", tk.END)
        lines = [
            f"🏘️ INSEDIAMENTO CASUALE (DMG p. 112-114)",
            f"Nome: {res['name']} ({res['size']})",
            f"Popolazione: ~{res['population']} abitanti",
            f"Governo: {res['government']}",
            f"Tratto Distintivo: {res['notable_trait']}",
            f"Calamità/Trama Attuale: {res['current_calamity']}",
            f"Taverna Principale: {res['tavern']}",
        ]
        gen_txt.insert(tk.END, "\n".join(lines))

    def _send_gen_to_chat():
        txt = gen_txt.get("1.0", tk.END).strip()
        if txt and hasattr(dm_gui, "log_to_chat"):
            dm_gui.log_to_chat(txt)

    ttk.Button(gen_ctrl, text="🎲 Genera Dungeon", command=_gen_dungeon, style="Primary.TButton").pack(side=tk.LEFT, padx=4)
    ttk.Button(gen_ctrl, text="🏘️ Genera Insediamento", command=_gen_settlement, style="Gold.TButton").pack(side=tk.LEFT, padx=4)
    ttk.Button(gen_ctrl, text="💬 Copia nel Log DM", command=_send_gen_to_chat).pack(side=tk.RIGHT)

    # --- TAB 5: Calcolatori DMG (CR, Mob Attacks, Pergamene/Pozioni, Sociale, Veicoli, Terre Selvagge) ---
    tab5 = ttk.Frame(nb, padding=8)
    nb.add(tab5, text="🧮 CR, Mob, Navale & Sociale")

    cr_f = ttk.LabelFrame(tab5, text="🐉 Calcolatore Grado di Sfida (DMG p. 274)", padding=6)
    cr_f.pack(fill=tk.X, pady=(0, 6))
    cr_hp = tk.IntVar(value=85)
    cr_ac = tk.IntVar(value=15)
    cr_dpr = tk.IntVar(value=24)
    cr_atk = tk.IntVar(value=6)
    cr_res = tk.BooleanVar(value=False)
    for lbl, var, w in [("PF:", cr_hp, 5), ("CA:", cr_ac, 4), ("DPR:", cr_dpr, 5), ("TpC +:", cr_atk, 4)]:
        ttk.Label(cr_f, text=lbl).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Spinbox(cr_f, from_=0, to=999, textvariable=var, width=w).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Checkbutton(cr_f, text="Resistenze", variable=cr_res).pack(side=tk.LEFT, padx=4)
    ttk.Button(
        cr_f,
        text="Calcola CR",
        style="Primary.TButton",
        command=lambda: _dispatch_opt(
            "calc_cr",
            hp=cr_hp.get(),
            ac=cr_ac.get(),
            dpr=cr_dpr.get(),
            attack_bonus=cr_atk.get(),
            has_resistances=cr_res.get(),
        ),
    ).pack(side=tk.RIGHT, padx=4)

    mob_f = ttk.LabelFrame(tab5, text="👥 Attacchi di Folla / Mob Attacks (DMG p. 250)", padding=6)
    mob_f.pack(fill=tk.X, pady=(0, 6))
    mob_n = tk.IntVar(value=8)
    mob_atk = tk.IntVar(value=4)
    mob_dmg = tk.IntVar(value=5)
    for lbl, var, w in [("Attaccanti:", mob_n, 4), ("TpC +:", mob_atk, 4), ("Danni/Colpo:", mob_dmg, 4)]:
        ttk.Label(mob_f, text=lbl).pack(side=tk.LEFT, padx=(4, 2))
        ttk.Spinbox(mob_f, from_=1, to=200, textvariable=var, width=w).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(
        mob_f,
        text="Risolvi Mob vs Bersaglio",
        style="Gold.TButton",
        command=lambda: _dispatch_opt(
            "mob_attack",
            num_attackers=mob_n.get(),
            attack_bonus=mob_atk.get(),
            damage_per_hit=mob_dmg.get(),
            apply_damage=True,
        ),
    ).pack(side=tk.RIGHT, padx=4)

    alc_f = ttk.LabelFrame(tab5, text="🧪 Pozioni & Pergamene (DMG p. 140)", padding=6)
    alc_f.pack(fill=tk.X, pady=(0, 6))
    scr_lvl = tk.IntVar(value=3)
    scr_max = tk.IntVar(value=1)
    ttk.Label(alc_f, text="Liv. Pergamena:").pack(side=tk.LEFT, padx=(4, 2))
    ttk.Spinbox(alc_f, from_=0, to=9, textvariable=scr_lvl, width=3).pack(side=tk.LEFT, padx=2)
    ttk.Label(alc_f, text="Max Lanciabile:").pack(side=tk.LEFT, padx=(6, 2))
    ttk.Spinbox(alc_f, from_=0, to=9, textvariable=scr_max, width=3).pack(side=tk.LEFT, padx=2)
    ttk.Button(
        alc_f,
        text="📜 Usa Pergamena (Attore)",
        command=lambda: _dispatch_opt("spell_scroll", spell_level=scr_lvl.get(), max_castable_level=scr_max.get()),
    ).pack(side=tk.LEFT, padx=6)
    ttk.Button(
        alc_f,
        text="🧪 Miscela Pozioni d100",
        command=lambda: _dispatch_opt("potion_miscibility"),
    ).pack(side=tk.RIGHT, padx=4)

    soc_f = ttk.LabelFrame(tab5, text="🗣️ Sociale DMG p.245, Lealtà & ⛵ Veicoli DMG p.119", padding=6)
    soc_f.pack(fill=tk.X, pady=(0, 6))
    soc_att = tk.StringVar(value="indifferent")
    soc_chk = tk.IntVar(value=14)
    loy_d = tk.IntVar(value=1)
    ttk.Combobox(soc_f, textvariable=soc_att, values=["friendly", "indifferent", "hostile"], state="readonly", width=11).pack(side=tk.LEFT, padx=2)
    ttk.Spinbox(soc_f, from_=-5, to=35, textvariable=soc_chk, width=4).pack(side=tk.LEFT, padx=2)
    ttk.Button(soc_f, text="Sociale", command=lambda: _dispatch_opt("social_loyalty", attitude=soc_att.get(), check_total=soc_chk.get())).pack(side=tk.LEFT, padx=3)
    ttk.Spinbox(soc_f, from_=-5, to=5, textvariable=loy_d, width=3).pack(side=tk.LEFT, padx=(8, 2))
    ttk.Button(soc_f, text="Lealtà", command=lambda: _dispatch_opt("social_loyalty", loyalty_delta=loy_d.get())).pack(side=tk.LEFT, padx=2)
    veh_dmg = tk.IntVar(value=25)
    veh_comp = tk.StringVar(value="hull")
    ttk.Combobox(soc_f, textvariable=veh_comp, values=["hull", "sails", "helm"], state="readonly", width=6).pack(side=tk.LEFT, padx=(8, 2))
    ttk.Spinbox(soc_f, from_=1, to=200, textvariable=veh_dmg, width=4).pack(side=tk.LEFT, padx=2)
    ttk.Button(soc_f, text="⛵ Danni Nave", command=lambda: _dispatch_opt("vehicle_damage", component=veh_comp.get(), damage=veh_dmg.get())).pack(side=tk.RIGHT, padx=4)

    wild_f = ttk.LabelFrame(tab5, text="🧭 Navigazione, Foraggiamento & Pericoli Terre Selvagge (DMG p. 105-111)", padding=6)
    wild_f.pack(fill=tk.X)
    wild_ter = tk.StringVar(value="forest")
    wild_pace = tk.StringVar(value="normal")
    wild_haz = tk.StringVar(value="razorvine")
    ttk.Combobox(wild_f, textvariable=wild_ter, values=["grassland", "forest", "coast", "mountain", "swamp", "arctic", "desert", "underdark"], state="readonly", width=11).pack(side=tk.LEFT, padx=2)
    ttk.Combobox(wild_f, textvariable=wild_pace, values=["slow", "normal", "fast"], state="readonly", width=8).pack(side=tk.LEFT, padx=2)
    ttk.Button(wild_f, text="🧭 Check Viaggio", command=lambda: _dispatch_opt("wilderness_check", terrain=wild_ter.get(), pace=wild_pace.get())).pack(side=tk.LEFT, padx=4)
    ttk.Combobox(wild_f, textvariable=wild_haz, values=["quicksand", "razorvine", "brown_mold", "green_slime", "thin_ice", "frigid_water"], state="readonly", width=13).pack(side=tk.LEFT, padx=(8, 2))
    ttk.Button(wild_f, text="⚠️ Pericolo (Bersaglio)", command=lambda: _dispatch_opt("wilderness_check", hazard_type=wild_haz.get(), apply_damage=True)).pack(side=tk.RIGHT, padx=4)

    if 0 <= initial_tab < 5:
        nb.select(initial_tab)

    win.workbench_notebook = nb
    win.actor_var = actor_var
    win.target_var = target_var
    return win
