# server/dm_bestiary_panel.py
"""
Pannello Bestiario per il Dungeon Master.
Consente la ricerca istantanea offline su manuali PDF indicizzati e database SRD 5.1
(oltre 1.000 mostri da SRD, Creature Codex e Tome of Beasts), con arricchimento
online asincrono e spawning automatico sulla griglia tattica.
"""

import threading
import json
import urllib.request
import re
import tkinter as tk
from tkinter import ttk
from common.i18n import _t
from common.theme import FONT_MAIN, FONT_SMALL, FONT_BOLD, SURFACE_COLOR, BORDER_COLOR, TEXT_COLOR
from common.game_state import Player
from common.protocol import make_player_joined, make_player_stats_update
from common.network_utils import broadcast
from common.srd_offline import (
    search_monsters_offline,
    extract_and_normalize_attributes,
    normalize_ac_value,
    normalize_speed_value,
    normalize_size_value,
    normalize_damage_list,
    extract_legendary_stats,
    extract_darkvision_flag,
    match_monster_cr,
    match_monster_type,
    get_monster_offline,
)


class DMBestiaryPanel(ttk.Frame):
    """Pannello Bestiario del DM per ricerca, consultazione e spawning di creature."""

    def __init__(self, parent, dm_gui):
        super().__init__(parent)
        self.dm_gui = dm_gui
        self.bestiario_results = []
        self.setup_ui()

    def setup_ui(self):
        self.lbl_bestiary_header = ttk.Label(self, text=_t("lbl_bestiary_header"), font=FONT_BOLD)
        self.lbl_bestiary_header.pack(pady=(6, 2), anchor="w", padx=6)

        self.bestiario_search_var = tk.StringVar()
        b_search_row = ttk.Frame(self)
        b_search_row.pack(fill=tk.X, padx=6, pady=(2, 3))

        self.b_entry = ttk.Entry(b_search_row, textvariable=self.bestiario_search_var)
        self.b_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.b_entry.bind("<KeyRelease>", lambda e: self.search_bestiario())

        self.btn_bestiary_search = ttk.Button(
            b_search_row, text=_t("search"), command=self.search_bestiario, style="Primary.TButton"
        )
        self.btn_bestiary_search.pack(side=tk.LEFT)

        # Filtri Rapidi CR e Tipo Creatura
        filter_row = ttk.Frame(self)
        filter_row.pack(fill=tk.X, padx=6, pady=(0, 4))

        ttk.Label(filter_row, text="CR:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
        self.cr_filter_var = tk.StringVar(value="Tutti i CR")
        cr_vals = ["Tutti i CR", "CR 0 - 1/2", "CR 1 - 4", "CR 5 - 9", "CR 10 - 14", "CR 15 - 19", "CR 20+"]
        self.cb_cr = ttk.Combobox(filter_row, textvariable=self.cr_filter_var, values=cr_vals, state="readonly", width=11)
        self.cb_cr.pack(side=tk.LEFT, padx=(0, 4))
        self.cb_cr.bind("<<ComboboxSelected>>", lambda e: self.search_bestiario())

        ttk.Label(filter_row, text="Tipo:", font=FONT_SMALL).pack(side=tk.LEFT, padx=(0, 2))
        self.type_filter_var = tk.StringVar(value="Tutti i Tipi")
        type_vals = [
            "Tutti i Tipi", "Aberrazione", "Bestia", "Drago", "Elementale", "Fata",
            "Gigante", "Immondo", "Melma", "Mostruosità", "Non Morto", "Pianta", "Umanoide"
        ]
        self.cb_type = ttk.Combobox(filter_row, textvariable=self.type_filter_var, values=type_vals, state="readonly", width=12)
        self.cb_type.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cb_type.bind("<<ComboboxSelected>>", lambda e: self.search_bestiario())

        b_list_frame = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        b_list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=2)

        self.bestiario_listbox = tk.Listbox(
            b_list_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN, borderwidth=0, relief="flat",
            selectbackground="#1E3A8A", selectforeground="#FDE68A"
        )
        self.bestiario_listbox.pack(fill=tk.BOTH, expand=True)
        self.bestiario_listbox.bind("<<ListboxSelect>>", self._on_bestiario_selected)
        self.bestiario_listbox.bind("<Double-Button-1>", lambda e: self.spawn_bestiario())

        # Anteprima Statblock Compatta Dark Fantasy
        self.preview_card = tk.Frame(self, bg="#181B22", highlightbackground="#A37F2C", highlightthickness=1, padx=6, pady=6)
        self.preview_card.pack(fill=tk.X, padx=6, pady=(2, 4))

        self.lbl_prev_title = tk.Label(self.preview_card, text=_t("lbl_bestiary_preview_default"), font=("Segoe UI", 9, "bold"), bg="#181B22", fg="#F59E0B", anchor="w")
        self.lbl_prev_title.pack(fill=tk.X)
        # Riferimento di retrocompatibilità per dm_gui
        self.bestiario_preview = self.lbl_prev_title

        self.prev_badges_frame = tk.Frame(self.preview_card, bg="#181B22")
        self.prev_badges_frame.pack(fill=tk.X, pady=2)

        self.lbl_prev_badges = tk.Label(self.prev_badges_frame, text="", font=("Segoe UI", 8), bg="#181B22", fg="#ECEFF1", anchor="w")
        self.lbl_prev_badges.pack(fill=tk.X)

        self.lbl_prev_attrs = tk.Label(self.preview_card, text="", font=("Segoe UI", 8), bg="#181B22", fg="#9CA3AF", anchor="w")
        self.lbl_prev_attrs.pack(fill=tk.X)

        self.lbl_prev_actions = tk.Label(self.preview_card, text="", font=("Segoe UI", 8), bg="#181B22", fg="#FBBF24", justify="left", wraplength=310, anchor="w")
        self.lbl_prev_actions.pack(fill=tk.X)

        b_btn_frame = ttk.Frame(self)
        b_btn_frame.pack(fill=tk.X, padx=6, pady=(2, 6))

        self.btn_bestiary_spawn = ttk.Button(
            b_btn_frame, text=_t("btn_spawn_on_map"), command=self.spawn_bestiario, style="Gold.TButton"
        )
        self.btn_bestiary_spawn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

        self.btn_bestiary_full = ttk.Button(
            b_btn_frame, text=_t("btn_full_sheet"), command=self.open_bestiario_manual_entry, style="Info.TButton"
        )
        self.btn_bestiary_full.pack(side=tk.LEFT, padx=(2, 0))

    def search_bestiario(self):
        query = self.bestiario_search_var.get().strip().lower()
        cr_f = getattr(self, "cr_filter_var", None)
        type_f = getattr(self, "type_filter_var", None)
        cr_filter = cr_f.get() if cr_f else "Tutti i CR"
        type_filter = type_f.get() if type_f else "Tutti i Tipi"

        # 1. Ricerca offline istantanea nei mostri indicizzati del Monster Manual PDF
        offline_results = []
        try:
            from common.pdf_manuals_indexer import PDFManualsIndexer
            indexer = PDFManualsIndexer()
            for m in indexer.get_monsters():
                mname = m.get("title", "")
                kws = [k.lower() for k in m.get("keywords", [])]
                mdata = m.get("monster_data", {})
                if cr_filter != "Tutti i CR" and not match_monster_cr(mdata.get("cr"), cr_filter):
                    continue
                if type_filter != "Tutti i Tipi" and not match_monster_type(mdata.get("type"), type_filter):
                    continue
                if not query or query in mname.lower() or any(query in k for k in kws):
                    offline_results.append({
                        "name": mname,
                        "source": "PDF (MM)",
                        "page_ref": m.get("page_ref", "MM"),
                        "monster_data": mdata,
                        "summary": m.get("summary", ""),
                        "full_rule": m
                    })
        except Exception as e:
            print("[BESTIARIO] Errore ricerca PDF offline:", e)

        # 2. Integrazione immediata dei dati SRD locali (open5e, creature codex, tome of beasts)
        try:
            local_srd = search_monsters_offline(query, max_results=120)
            seen_names = {r["name"].lower() for r in offline_results}
            for sm in local_srd:
                mdata = sm.get("monster_data", {})
                if cr_filter != "Tutti i CR" and not match_monster_cr(mdata.get("cr"), cr_filter):
                    continue
                if type_filter != "Tutti i Tipi" and not match_monster_type(mdata.get("type"), type_filter):
                    continue
                if sm["name"].lower() not in seen_names:
                    offline_results.append(sm)
                    seen_names.add(sm["name"].lower())
        except Exception as e:
            print("[BESTIARIO] Errore ricerca SRD offline:", e)

        # Se abbiamo risultati locali o query vuota, aggiorna subito la lista
        self._update_bestiario_list(offline_results[:120])

        # Se c'è una query testuale, cerca anche su SRD online in background
        if query:
            threading.Thread(target=self._search_bestiario_thread, args=(query, offline_results), daemon=True).start()

    def _search_bestiario_thread(self, query, initial_results):
        try:
            url = f"https://www.dnd5eapi.co/api/monsters/?name={query}".replace(" ", "+")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode())
                srd_results = data.get("results", [])

                seen_names = {r["name"].lower() for r in initial_results}
                combined = list(initial_results)
                for s in srd_results:
                    s_name = s.get("name", "")
                    if s_name.lower() not in seen_names:
                        combined.append({
                            "name": s_name,
                            "source": "SRD Online",
                            "index": s.get("index"),
                            "summary": f"Mostro SRD 5.1 ({s_name})"
                        })
                self.dm_gui.master.after(0, self._update_bestiario_list, combined[:150])
        except Exception:
            pass  # Offline o timeout SRD: i risultati locali del PDF e dell'SRD locale bastano

    def _update_bestiario_list(self, results):
        self.bestiario_listbox.delete(0, tk.END)
        self.bestiario_results = results
        # Mantiene sincronizzato anche l'attributo dm_gui per retrocompatibilità
        if hasattr(self.dm_gui, "bestiario_results"):
            self.dm_gui.bestiario_results = results

        for res in results:
            src = res.get("source", "MM")
            name = res.get("name", "Unknown")
            mdata = res.get("monster_data", {})
            if mdata:
                tag = f"[{mdata.get('cr', '1')}] {name} (CA {mdata.get('ac', 10)}, HP {mdata.get('hp', 20)})"
            else:
                tag = f"🌐 {name} ({src})"
            self.bestiario_listbox.insert(tk.END, tag)

        if results and hasattr(self, 'lbl_prev_title'):
            self.bestiario_listbox.selection_set(0)
            self._on_bestiario_selected()

    def _on_bestiario_selected(self, event=None):
        sel = self.bestiario_listbox.curselection()
        if not sel or sel[0] >= len(self.bestiario_results):
            return
        res = self.bestiario_results[sel[0]]
        mdata = res.get("monster_data", {})
        name = res.get("name", "")
        src = res.get("source", "Monster Manual")
        page = res.get("page_ref", "")

        # Se non ha monster_data ma abbiamo il nome, tenta il fetch da record offline istantaneo
        if not mdata:
            local_rec = get_monster_offline(name)
            if local_rec:
                mdata = local_rec

        if mdata:
            attrs = mdata.get("attributes") or extract_and_normalize_attributes(mdata, name)
            ac_val = normalize_ac_value(mdata.get("ac", mdata.get("armor_class", 10)))
            speed_val, speed_disp, _ = normalize_speed_value(mdata.get("speed", 30))
            hp_val = mdata.get("hp", mdata.get("hit_points", 20))
            cr_val = mdata.get("cr", mdata.get("challenge_rating", "1"))

            self.lbl_prev_title.config(text=f"🐉 {name} [{src} {page}]".strip())
            self.lbl_prev_badges.config(text=f"🛡️ CA: {ac_val}  •  ❤️ HP: {hp_val}  •  👟 {speed_disp}  •  🏆 CR {cr_val}")
            self.lbl_prev_attrs.config(text=f"FOR {attrs.get('FOR', 10)} | DES {attrs.get('DES', 10)} | COS {attrs.get('COS', 10)} | INT {attrs.get('INT', 10)} | SAG {attrs.get('SAG', 10)} | CAR {attrs.get('CAR', 10)}")

            # Prime azioni o attacchi
            actions = mdata.get("actions", [])
            if actions:
                act_lines = []
                for a in actions[:2]:
                    a_name = a.get("name", "Attacco") if isinstance(a, dict) else str(a).split(".")[0]
                    a_desc = a.get("desc", "") if isinstance(a, dict) else str(a)
                    # Cerca TpC o danno
                    m_hit = re.search(r'Hit:\s*([0-9]+\s*\([^)]+\))', a_desc)
                    dmg = f" (💥 {m_hit.group(1)})" if m_hit else ""
                    act_lines.append(f"⚔️ {a_name}{dmg}")
                self.lbl_prev_actions.config(text="  •  ".join(act_lines))
            else:
                self.lbl_prev_actions.config(text=res.get("summary", ""))
        else:
            self.lbl_prev_title.config(text=f"🌐 {name} [{src}]")
            self.lbl_prev_badges.config(text="Seleziona 'Scheda Completa' o fai doppio click per visualizzare.")
            self.lbl_prev_attrs.config(text="")
            self.lbl_prev_actions.config(text=res.get("summary", ""))

    def open_bestiario_manual_entry(self):
        sel = self.bestiario_listbox.curselection()
        if not sel or sel[0] >= len(self.bestiario_results):
            return
        res = self.bestiario_results[sel[0]]
        self.dm_gui.open_manuals_dialog(initial_query=res.get("name", ""))

    def spawn_bestiario(self):
        sel = self.bestiario_listbox.curselection()
        if not sel or sel[0] >= len(self.bestiario_results):
            return
        selected = self.bestiario_results[sel[0]]

        # 1. Se mostro con monster_data (PDF Manual o SRD offline), spawna all'istante offline!
        if "monster_data" in selected and selected["monster_data"]:
            mdata = selected["monster_data"]
            name = mdata.get("name", selected.get("name", "Mostro"))
            hp = int(mdata.get("hp", 20))
            ac = normalize_ac_value(mdata.get("ac", mdata.get("armor_class", 10)))
            speed_val, speed_disp, speed_unit = normalize_speed_value(mdata.get("speed", 30))
            attrs = extract_and_normalize_attributes(mdata, name)
            dex_val = attrs.get("DES", 10)
            initiative = (dex_val - 10) // 2

            pos = [0, 0]
            if hasattr(self.dm_gui, 'map_canvas') and self.dm_gui.map_canvas and hasattr(self.dm_gui.map_canvas, '_last_clicked_hex') and self.dm_gui.map_canvas._last_clicked_hex:
                pos = [self.dm_gui.map_canvas._last_clicked_hex.q, self.dm_gui.map_canvas._last_clicked_hex.r]

            base_name = name
            idx = 1
            new_name = base_name
            while self.dm_gui.server.game_state.find_player(new_name):
                idx += 1
                new_name = f"{base_name} {idx}"

            npc = self._build_npc_player(new_name, mdata, hp, ac, initiative, speed_val, speed_disp, speed_unit, attrs, pos)
            self.dm_gui.server.game_state.add_player(npc)
            self.dm_gui.server.game_state._trigger_gui_update()
            broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
            broadcast(self.dm_gui.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))
            return

        # 2. Se elemento online SRD, scarica e spawna da API
        index_selezionato = selected.get("index")
        if index_selezionato:
            threading.Thread(target=self._spawn_bestiario_thread, args=(index_selezionato,), daemon=True).start()

    def _build_npc_player(self, name, mdata, hp, ac, initiative, speed_val, speed_disp, speed_unit, attrs, pos):
        npc = Player(name, None, None)
        npc.hp = hp
        npc.max_hp = hp
        npc.initiative = initiative
        npc.position = pos
        npc.speed = speed_val
        npc.speed_unit = speed_unit
        npc.size = normalize_size_value(mdata.get("size"))
        npc.damage_resistances = normalize_damage_list(mdata.get("damage_resistances", mdata.get("resistances", [])))
        npc.damage_immunities = normalize_damage_list(mdata.get("damage_immunities", mdata.get("immunities", [])))
        npc.damage_vulnerabilities = normalize_damage_list(mdata.get("damage_vulnerabilities", mdata.get("vulnerabilities", [])))
        leg_res, leg_act, has_lair = extract_legendary_stats(mdata)
        npc.legendary_resistances_max = leg_res
        npc.legendary_resistances_current = leg_res
        npc.legendary_actions_max = leg_act
        npc.legendary_actions_current = leg_act
        npc.has_lair_actions = has_lair
        npc.has_darkvision = extract_darkvision_flag(mdata)

        npc.full_sheet = {
            "name": npc.name,
            "char_class": "Mostro/NPC",
            "level": 1,
            "hp_current": npc.hp,
            "hp_max": npc.max_hp,
            "ac": ac,
            "speed": speed_val,
            "speed_display": speed_disp,
            "speed_unit": speed_unit,
            "attributes": attrs,
            "cr": str(mdata.get("challenge_rating", mdata.get("cr", "1"))),
            "size": mdata.get("size", "Medium"),
            "actions": mdata.get("actions", []),
            "features": mdata.get("special_abilities", mdata.get("features", [])),
            "languages": mdata.get("languages", ""),
            "senses": mdata.get("senses", ""),
            "damage_resistances": npc.damage_resistances,
            "damage_immunities": npc.damage_immunities,
            "damage_vulnerabilities": npc.damage_vulnerabilities,
            "legendary_resistances_max": leg_res,
            "legendary_actions_max": leg_act,
            "has_lair_actions": has_lair
        }
        return npc

    def _spawn_bestiario_thread(self, index_selezionato):
        try:
            url = f"https://www.dnd5eapi.co/api/monsters/{index_selezionato}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode())

                name = data.get("name", "Mostro")
                hit_points = data.get("hit_points", 10)

                ac_value = normalize_ac_value(data.get("armor_class", data.get("ac", 10)))
                speed_val, speed_disp, speed_unit = normalize_speed_value(data.get("speed", 30))

                attrs = extract_and_normalize_attributes(data, name)
                dex = attrs.get("DES", 10)
                initiative = (dex - 10) // 2

                pos = [0, 0]
                if hasattr(self.dm_gui, 'map_canvas') and self.dm_gui.map_canvas and hasattr(self.dm_gui.map_canvas, '_last_clicked_hex') and self.dm_gui.map_canvas._last_clicked_hex:
                    pos = [self.dm_gui.map_canvas._last_clicked_hex.q, self.dm_gui.map_canvas._last_clicked_hex.r]

                base_name = name
                idx = 1
                new_name = base_name
                while self.dm_gui.server.game_state.find_player(new_name):
                    idx += 1
                    new_name = f"{base_name} {idx}"

                npc = self._build_npc_player(new_name, data, hit_points, ac_value, initiative, speed_val, speed_disp, speed_unit, attrs, pos)

                self.dm_gui.server.game_state.add_player(npc)
                self.dm_gui.server.game_state._trigger_gui_update()
                broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
                broadcast(self.dm_gui.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))

        except Exception as e:
            print("[BESTIARIO] Errore API online, tentativo fallback offline SRD:", e)
            try:
                local_hits = search_monsters_offline(str(index_selezionato).replace("-", " "))
                if local_hits:
                    mdata = local_hits[0]["monster_data"]
                    name = mdata.get("name", "Mostro")
                    hit_points = int(mdata.get("hp", 10))
                    ac_value = normalize_ac_value(mdata.get("ac", mdata.get("armor_class", 10)))
                    speed_val, speed_disp, speed_unit = normalize_speed_value(mdata.get("speed", 30))
                    attrs = extract_and_normalize_attributes(mdata, name)
                    dex = attrs.get("DES", 10)
                    initiative = (dex - 10) // 2

                    pos = [0, 0]
                    if hasattr(self.dm_gui, 'map_canvas') and self.dm_gui.map_canvas and hasattr(self.dm_gui.map_canvas, '_last_clicked_hex') and self.dm_gui.map_canvas._last_clicked_hex:
                        pos = [self.dm_gui.map_canvas._last_clicked_hex.q, self.dm_gui.map_canvas._last_clicked_hex.r]

                    base_name = name
                    idx = 1
                    new_name = base_name
                    while self.dm_gui.server.game_state.find_player(new_name):
                        idx += 1
                        new_name = f"{base_name} {idx}"

                    npc = self._build_npc_player(new_name, mdata, hit_points, ac_value, initiative, speed_val, speed_disp, speed_unit, attrs, pos)

                    self.dm_gui.server.game_state.add_player(npc)
                    self.dm_gui.server.game_state._trigger_gui_update()
                    broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
                    broadcast(self.dm_gui.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))
            except Exception as e2:
                print("[BESTIARIO] Fallback offline non riuscito:", e2)


