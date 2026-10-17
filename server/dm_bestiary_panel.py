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
import tkinter as tk
from tkinter import ttk
from common.i18n import _t
from common.theme import FONT_MAIN, FONT_SMALL, FONT_BOLD, SURFACE_COLOR, BORDER_COLOR, TEXT_COLOR
from common.game_state import Player
from common.protocol import make_player_joined, make_player_stats_update
from common.network_utils import broadcast
from common.pdf_manuals_indexer import PDFManualsIndexer
from common.srd_offline import search_monsters_offline


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
        b_search_row.pack(fill=tk.X, padx=6, pady=3)

        self.b_entry = ttk.Entry(b_search_row, textvariable=self.bestiario_search_var)
        self.b_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.b_entry.bind("<KeyRelease>", lambda e: self.search_bestiario())

        self.btn_bestiary_search = ttk.Button(
            b_search_row, text=_t("search"), command=self.search_bestiario, style="Primary.TButton"
        )
        self.btn_bestiary_search.pack(side=tk.LEFT)

        b_list_frame = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        b_list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self.bestiario_listbox = tk.Listbox(
            b_list_frame, bg=SURFACE_COLOR, fg=TEXT_COLOR, font=FONT_MAIN, borderwidth=0, relief="flat"
        )
        self.bestiario_listbox.pack(fill=tk.BOTH, expand=True)
        self.bestiario_listbox.bind("<<ListboxSelect>>", self._on_bestiario_selected)

        # Anteprima Statistiche Rapide Mostro
        self.bestiario_preview = tk.Label(
            self, text=_t("lbl_bestiary_preview_default"),
            font=FONT_SMALL, bg="#212529", fg=TEXT_COLOR, justify="left", wraplength=310, padx=6, pady=4
        )
        self.bestiario_preview.pack(fill=tk.X, padx=6, pady=(0, 4))

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

        # 1. Ricerca offline istantanea nei mostri indicizzati del Monster Manual PDF
        offline_results = []
        try:
            indexer = PDFManualsIndexer()
            for m in indexer.get_monsters():
                mname = m.get("title", "")
                kws = [k.lower() for k in m.get("keywords", [])]
                if not query or query in mname.lower() or any(query in k for k in kws):
                    offline_results.append({
                        "name": mname,
                        "source": "PDF (MM)",
                        "page_ref": m.get("page_ref", "MM"),
                        "monster_data": m.get("monster_data", {}),
                        "summary": m.get("summary", ""),
                        "full_rule": m
                    })
        except Exception as e:
            print("[BESTIARIO] Errore ricerca PDF offline:", e)

        # 2. Integrazione immediata dei dati SRD locali (open5e, creature codex, tome of beasts)
        try:
            local_srd = search_monsters_offline(query, max_results=80)
            seen_names = {r["name"].lower() for r in offline_results}
            for sm in local_srd:
                if sm["name"].lower() not in seen_names:
                    offline_results.append(sm)
                    seen_names.add(sm["name"].lower())
        except Exception as e:
            print("[BESTIARIO] Errore ricerca SRD offline:", e)

        # Se abbiamo risultati locali o query vuota, aggiorna subito la lista
        self._update_bestiario_list(offline_results[:100])

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

        if results and hasattr(self, 'bestiario_preview'):
            self.bestiario_listbox.selection_set(0)
            self._on_bestiario_selected()

    def _on_bestiario_selected(self, event=None):
        sel = self.bestiario_listbox.curselection()
        if not sel or sel[0] >= len(self.bestiario_results):
            return
        res = self.bestiario_results[sel[0]]
        mdata = res.get("monster_data", {})
        summary = res.get("summary", "")
        name = res.get("name", "")
        src = res.get("source", "Monster Manual")
        page = res.get("page_ref", "")

        if mdata:
            info = f"🐉 {name} [{src} - {page}]\nCA: {mdata.get('ac', 10)} | HP: {mdata.get('hp', 20)} | CR: {mdata.get('cr', '1')}\n{summary}"
        else:
            info = f"🌐 {name} [{src}]\n{summary}"
        self.bestiario_preview.config(text=info)

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
            ac = int(mdata.get("ac", 10))

            pos = [0, 0]
            if hasattr(self.dm_gui, 'map_canvas') and self.dm_gui.map_canvas and hasattr(self.dm_gui.map_canvas, '_last_clicked_hex') and self.dm_gui.map_canvas._last_clicked_hex:
                pos = [self.dm_gui.map_canvas._last_clicked_hex.q, self.dm_gui.map_canvas._last_clicked_hex.r]

            base_name = name
            idx = 1
            new_name = base_name
            while self.dm_gui.server.game_state.find_player(new_name):
                idx += 1
                new_name = f"{base_name} {idx}"

            npc = Player(new_name, None, None)
            npc.hp = hp
            npc.max_hp = hp
            npc.initiative = 0
            npc.position = pos
            npc.full_sheet = {
                "name": npc.name,
                "hp_current": npc.hp,
                "hp_max": npc.max_hp,
                "ac": ac
            }
            self.dm_gui.server.game_state.add_player(npc)
            self.dm_gui.server.game_state._trigger_gui_update()
            broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
            broadcast(self.dm_gui.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))
            return

        # 2. Se elemento online SRD, scarica e spawna da API
        index_selezionato = selected.get("index")
        if index_selezionato:
            threading.Thread(target=self._spawn_bestiario_thread, args=(index_selezionato,), daemon=True).start()

    def _spawn_bestiario_thread(self, index_selezionato):
        try:
            url = f"https://www.dnd5eapi.co/api/monsters/{index_selezionato}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode())

                name = data.get("name", "Mostro")
                hit_points = data.get("hit_points", 10)

                ac_list = data.get("armor_class", [])
                ac_value = 10
                if ac_list:
                    ac_item = ac_list[0]
                    if isinstance(ac_item, dict):
                        ac_value = ac_item.get("value", 10)
                    else:
                        ac_value = ac_item

                dex = data.get("dexterity", 10)
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

                npc = Player(new_name, None, None)
                npc.hp = hit_points
                npc.max_hp = hit_points
                npc.initiative = initiative
                npc.position = pos
                npc.full_sheet = {
                    "name": npc.name,
                    "hp_current": npc.hp,
                    "hp_max": npc.max_hp,
                    "ac": ac_value
                }

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
                    ac_value = int(mdata.get("ac", 10))
                    dex = int(mdata.get("dex", 10))
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

                    npc = Player(new_name, None, None)
                    npc.hp = hit_points
                    npc.max_hp = hit_points
                    npc.initiative = initiative
                    npc.position = pos
                    npc.full_sheet = {
                        "name": npc.name,
                        "hp_current": npc.hp,
                        "hp_max": npc.max_hp,
                        "ac": ac_value
                    }

                    self.dm_gui.server.game_state.add_player(npc)
                    self.dm_gui.server.game_state._trigger_gui_update()
                    broadcast(self.dm_gui.server.game_state, make_player_joined(npc.to_dict()))
                    broadcast(self.dm_gui.server.game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, []))
            except Exception as e2:
                print("[BESTIARIO] Fallback offline non riuscito:", e2)

