# server/dm_live_flow.py
"""
Modulo per il Controllo Live del Flusso della Campagna durante la sessione di gioco
e per la consultazione della Cronistoria & Recap di fine sessione (Session Chronicle).
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog
from typing import Optional, Any

from common.theme import (
    apply_modern_window_style, BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, SURFACE_LIGHT,
    BORDER_COLOR, BORDER_GOLD, ACCENT_GOLD, ACCENT_GOLD_LIGHT,
    ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE, TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    FONT_TITLE, FONT_HEADER, FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_BADGE
)
from common.messagebox import messagebox
from common.campaign_script import (
    FlowGraph, FlowNode, FlowEdge, DndScriptParser, DndScriptSerializer,
    sync_flow_graph_to_campaign
)
from common.session_chronicle import (
    SessionLedger, ChronicleGenerator, integrate_off_track_events_into_flow, format_harptos_date
)
from server.flow_canvas import FlowCanvas


class DMLiveFlowDialog(tk.Toplevel):
    """
    Finestra Flottante per il Controllo Live del Flusso e della Campagna.
    Permette al DM di governare la scena, lanciare incontri, trasmettere narrazioni,
    tracciare i bivi e gestire i fuori pista con libertà totale di override.
    """
    def __init__(self, master_gui, game_state, session_ledger: SessionLedger):
        super().__init__(master_gui.master)
        self.master_gui = master_gui
        self.game_state = game_state
        self.session_ledger = session_ledger

        self.title("🧭 D&D OmniCompanion • Controllo Flusso Live")
        self.geometry("1100x720")
        self.minsize(950, 600)
        self.transient(master_gui.master)
        apply_modern_window_style(self, bind_escape=False)
        self.configure(bg=BG_COLOR)

        # Recupera il grafo della campagna attiva
        self.campaign = getattr(self.game_state, "active_campaign", None)
        self.graph = FlowGraph()
        if self.campaign:
            flow_data = getattr(self.campaign, "flow_graph", None)
            if flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
                self.graph = FlowGraph.from_dict(flow_data)
            elif getattr(self.campaign, "flow_script", ""):
                parser = DndScriptParser()
                self.graph = parser.parse(self.campaign.flow_script)

        self._active_node_id = self.session_ledger.visited_node_ids[-1] if self.session_ledger.visited_node_ids else None
        if not self._active_node_id and self.graph.nodes:
            self._active_node_id = list(self.graph.nodes.keys())[0]
            self.session_ledger.visited_node_ids.append(self._active_node_id)

        self._setup_ui()
        self._update_action_panel()

    def _setup_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=10, pady=8)
        container.pack(fill=tk.BOTH, expand=True)

        # Header superiore
        top_bar = tk.Frame(container, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=10, pady=6)
        top_bar.pack(fill=tk.X, pady=(0, 6))

        c_name = self.campaign.name if self.campaign else "Campagna Senza Nome"
        tk.Label(top_bar, text=f"🧭 Flusso Live: {c_name}", font=FONT_HEADER, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        
        self.lbl_status = tk.Label(top_bar, text="", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_status.pack(side=tk.LEFT, padx=16)

        btn_box = tk.Frame(top_bar, bg=SURFACE_COLOR)
        btn_box.pack(side=tk.RIGHT)

        ttk.Button(btn_box, text="⚡ Modalità Fuori Pista", command=self.activate_free_roam_mode, style="Primary.TButton").pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="+ Nota Rapida DM", command=self.add_quick_dm_note).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="🔍 Centra", command=lambda: self.flow_canvas.reset_view()).pack(side=tk.RIGHT, padx=4)

        # Split frame verticale: Canvas in alto, Plancia Azioni in basso
        self.split_pane = tk.PanedWindow(container, orient=tk.VERTICAL, bg=BG_COLOR, sashrelief="flat", sashwidth=4)
        self.split_pane.pack(fill=tk.BOTH, expand=True)

        # Canvas Superiore
        canvas_frame = tk.Frame(self.split_pane, bg=BG_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.split_pane.add(canvas_frame, minsize=320, height=440)

        self.flow_canvas = FlowCanvas(
            canvas_frame, graph=self.graph,
            on_change_callback=self._on_canvas_graph_changed,
            is_dm_live=True
        )
        self.flow_canvas.pack(fill=tk.BOTH, expand=True)
        if self._active_node_id:
            self.flow_canvas.set_active_party_node(self._active_node_id)
        self.flow_canvas.visited_node_ids = list(self.session_ledger.visited_node_ids)

        # Plancia Azioni Inferiore (Controllo Nodo Attivo)
        self.actions_frame = tk.Frame(self.split_pane, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=12, pady=10)
        self.split_pane.add(self.actions_frame, minsize=160)

    def _on_canvas_graph_changed(self):
        if self.campaign:
            self.campaign.flow_graph = self.graph.to_dict()
            serializer = DndScriptSerializer()
            self.campaign.flow_script = serializer.serialize(self.graph)

    def _update_action_panel(self):
        for w in self.actions_frame.winfo_children():
            w.destroy()

        active_node = self.graph.nodes.get(self._active_node_id) if self._active_node_id else None
        
        # Header Plancia
        hdr_frame = tk.Frame(self.actions_frame, bg=SURFACE_COLOR)
        hdr_frame.pack(fill=tk.X, pady=(0, 8))

        if active_node:
            self.lbl_status.config(text=f"Posizione Party: {active_node.title} ({active_node.node_type})")
            tk.Label(hdr_frame, text=f"📍 Nodo Attivo: {active_node.title}", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(side=tk.LEFT)
            tk.Label(hdr_frame, text=f"[{active_node.node_type.upper()}]", font=FONT_BADGE, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, padx=6, pady=2).pack(side=tk.LEFT, padx=8)
        else:
            self.lbl_status.config(text="Posizione Party: Nessun nodo selezionato (Modalità Libera)")
            tk.Label(hdr_frame, text="⚡ Modalità Libera / Fuori Pista (Nessun nodo attivo)", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_RED).pack(side=tk.LEFT)

        main_row = tk.Frame(self.actions_frame, bg=SURFACE_COLOR)
        main_row.pack(fill=tk.BOTH, expand=True)
        main_row.columnconfigure(0, weight=2)
        main_row.columnconfigure(1, weight=3)

        # Colonna Sinistra: Azioni Dirette VTT
        col_actions = tk.Frame(main_row, bg=SURFACE_COLOR)
        col_actions.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(col_actions, text="⚡ Azioni Dirette nel VTT:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        
        btn_grid = tk.Frame(col_actions, bg=SURFACE_COLOR)
        btn_grid.pack(fill=tk.X)

        if active_node and active_node.node_type == "scene":
            map_file = active_node.data.get("map_file", "")
            ttk.Button(btn_grid, text="🗺️ Attiva Scena & Mappa", command=lambda: self.activate_scene_on_vtt(active_node), style="Gold.TButton").pack(fill=tk.X, pady=2)
        
        if active_node and active_node.node_type == "encounter":
            ttk.Button(btn_grid, text="⚔️ Lancia Incontro nel Combat Tracker", command=lambda: self.activate_encounter_on_vtt(active_node), style="Primary.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "check":
            ab = active_node.data.get("ability", "Prova")
            cd = active_node.data.get("cd", 10)
            ttk.Button(btn_grid, text=f"🎲 Richiedi Prova: {ab} (CD {cd})", command=lambda: self.broadcast_check(active_node), style="Gold.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "trap":
            cd = active_node.data.get("cd", 12)
            dmg = active_node.data.get("damage", "1d10")
            ttk.Button(btn_grid, text=f"⚠️ Fai Scattare Trappola (CD {cd} • {dmg})", command=lambda: self.trigger_trap(active_node), style="Danger.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "loot":
            g = active_node.data.get("gold", "0")
            items_c = len(active_node.data.get("items", []))
            ttk.Button(btn_grid, text=f"💎 Distribuisci Tesoro ({g} mo • {items_c} oggetti)", command=lambda: self.award_loot(active_node), style="Gold.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "shop":
            ttk.Button(btn_grid, text="🏬 Apri Mercante / Emporio", command=lambda: self.present_shop(active_node), style="Primary.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "puzzle":
            ttk.Button(btn_grid, text="🧩 Rivela Indizio Enigma", command=lambda: self.reveal_puzzle(active_node), style="Gold.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "rest":
            rt = active_node.data.get("rest_type", "Breve")
            ttk.Button(btn_grid, text=f"⛺ Esegui Riposo {rt}", command=lambda: self.commence_rest(active_node), style="Primary.TButton").pack(fill=tk.X, pady=2)

        if active_node and active_node.node_type == "lore":
            ttk.Button(btn_grid, text="📜 Condividi Documento in Chat", command=lambda: self.share_lore(active_node), style="Gold.TButton").pack(fill=tk.X, pady=2)

        if active_node and (active_node.data.get("read_aloud") or active_node.data.get("description")):
            ttk.Button(btn_grid, text="📜 Trasmetti Narrazione in Chat", command=lambda: self.broadcast_narration(active_node)).pack(fill=tk.X, pady=2)

        # Segreti del nodo
        secrets = active_node.data.get("secrets", []) if active_node else []
        if secrets:
            sec_box = tk.Frame(col_actions, bg=SURFACE_COLOR_ALT, padx=6, pady=4, highlightbackground=BORDER_COLOR, highlightthickness=1)
            sec_box.pack(fill=tk.X, pady=(6, 2))
            tk.Label(sec_box, text=f"🔒 Segreti disponibili ({len(secrets)}):", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w")
            for s in secrets:
                s_chk = f"[{s.get('check', '')}] " if s.get("check") else ""
                s_text = s.get("text", "")
                r_btn = tk.Frame(sec_box, bg=SURFACE_COLOR_ALT)
                r_btn.pack(fill=tk.X, pady=1)
                tk.Label(r_btn, text=f"• {s_chk}{s_text[:40]}...", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR).pack(side=tk.LEFT)
                ttk.Button(r_btn, text="Svela", command=lambda sec=s: self.reveal_secret(active_node, sec)).pack(side=tk.RIGHT)

        # Colonna Destra: Prossimi Bivi / Uscite
        col_branches = tk.Frame(main_row, bg=SURFACE_COLOR)
        col_branches.grid(row=0, column=1, sticky="nsew")

        tk.Label(col_branches, text="🔀 Prosegui Verso il Prossimo Bivio / Scena:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))
        
        branches_box = tk.Frame(col_branches, bg=SURFACE_COLOR_ALT, padx=8, pady=6, highlightbackground=BORDER_COLOR, highlightthickness=1)
        branches_box.pack(fill=tk.BOTH, expand=True)

        outgoing = [e for e in self.graph.edges if e.from_id == self._active_node_id] if self._active_node_id else []
        if outgoing:
            for edge in outgoing:
                target_node = self.graph.nodes.get(edge.to_id)
                if not target_node:
                    continue
                cond_type = getattr(edge, "condition_type", "default")
                cond_val = getattr(edge, "condition_value", "")

                if cond_type == "success":
                    prefix = "✅ [SUCCESSO] "
                elif cond_type == "failure":
                    prefix = "❌ [FALLIMENTO] "
                elif cond_type == "check":
                    prefix = f"🎲 [PROVA: {cond_val or edge.label}] "
                elif cond_type == "item":
                    prefix = f"🔑 [POSSIEDE: {cond_val or edge.label}] "
                elif cond_type == "else":
                    prefix = "↩️ [ALTRIMENTI] "
                elif edge.label:
                    prefix = f'"{edge.label}" ➔ '
                else:
                    prefix = "➔ "

                lbl = f"{prefix}{target_node.title}"
                b_row = tk.Frame(branches_box, bg=SURFACE_COLOR_ALT)
                b_row.pack(fill=tk.X, pady=2)
                ttk.Button(b_row, text=lbl, command=lambda tid=target_node.id, pfx=prefix.strip(): self.transition_to_node(tid, branch_info=pfx), style="Info.TButton").pack(fill=tk.X)
        else:
            tk.Label(branches_box, text="Nessun bivio prefissato. Fai clic destro su qualsiasi nodo del canvas per saltare liberamente o improvvisare.",
                     font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, wraplength=400).pack(anchor="w", pady=6)

    # -----------------------------------------------------------------------
    # AZIONI VTT
    # -----------------------------------------------------------------------

    def transition_to_node(self, target_node_id: str, is_off_track: bool = False, branch_info: str = ""):
        target_node = self.graph.nodes.get(target_node_id)
        if not target_node:
            return
        self._active_node_id = target_node_id
        self.flow_canvas.set_active_party_node(target_node_id)

        detail_text = target_node.data.get("read_aloud", "")
        if branch_info:
            detail_text = f"Scelta/Esito: {branch_info}. {detail_text}".strip()
            if hasattr(self.master_gui, "log_to_chat"):
                self.master_gui.log_to_chat(f"🔀 [FLUSSO] Il party segue: {branch_info} ➔ {target_node.title}")

        # Registra nel ledger
        self.session_ledger.record_node_visit(
            node_id=target_node.id,
            title=target_node.title,
            node_type=target_node.node_type,
            is_off_track=is_off_track,
            details=detail_text
        )
        self._update_action_panel()

    def activate_scene_on_vtt(self, node: FlowNode):
        map_file = node.data.get("map_file", "")
        if map_file and hasattr(self.master_gui, "load_map_from_file"):
            try:
                # Carica mappa sul canvas
                self.master_gui.server.game_state.map_file = map_file
                if hasattr(self.master_gui, "broadcast_game_state"):
                    self.master_gui.broadcast_game_state()
                self.master_gui.log_to_chat(f"🗺️ [FLUSSO] Scena '{node.title}' attivata ({map_file}).")
                messagebox.showinfo("Scena Attivata", f"Mappa '{map_file}' caricata con successo per tutti i giocatori!", parent=self)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile attivare la mappa: {e}", parent=self)

    def activate_encounter_on_vtt(self, node: FlowNode):
        monsters = node.data.get("monsters", [])
        if not monsters:
            messagebox.showinfo("Incontro", "Nessun mostro specificato in questo nodo.", parent=self)
            return

        # Popola NPC/Mostri nel combat tracker
        try:
            for m in monsters:
                m_name = m.get("name", "Mostro")
                qty = m.get("quantity", 1)
                for _ in range(qty):
                    self.master_gui.add_npc_by_name(m_name)
            
            self.session_ledger.record_combat(
                title=node.title,
                monsters=monsters,
                rounds=1,
                victory=True,
                loot=node.data.get("loot", ""),
                xp=node.data.get("xp", 0)
            )
            self.master_gui.log_to_chat(f"⚔️ [FLUSSO] Incontro '{node.title}' schierato sul Combat Tracker!")
            messagebox.showinfo("Combattimento Schierato", f"Mostri dell'incontro '{node.title}' aggiunti con successo all'iniziativa!", parent=self)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore schieramento incontro: {e}", parent=self)

    def broadcast_narration(self, node: FlowNode):
        text = node.data.get("read_aloud") or node.data.get("description", "")
        if not text:
            return
        if hasattr(self.master_gui, "broadcast_dm_narration"):
            self.master_gui.broadcast_dm_narration(text)
        elif hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(f"📜 [NARRAZIONE DM]\n{text}")
        messagebox.showinfo("Narrazione Trasmessa", "Testo descrittivo inviato nella chat di tutti i giocatori!", parent=self)

    def reveal_secret(self, node: FlowNode, secret_data: Dict[str, Any]):
        secret_data["revealed"] = True
        self.session_ledger.record_secret(
            title=node.title,
            check=secret_data.get("check", ""),
            text=secret_data.get("text", "")
        )
        self.master_gui.log_to_chat(f"🔍 [SEGRETO SVELATO] {node.title}: {secret_data.get('text', '')}")
        self._update_action_panel()
        messagebox.showinfo("Segreto Svelato", "Segreto registrato nella cronistoria della sessione!", parent=self)

    def broadcast_check(self, node: FlowNode):
        ab = node.data.get("ability", "Prova di Caratteristica")
        cd = node.data.get("cd", 10)
        msg = f"🎲 [PROVA RICHIESTA] Il Master richiede una prova di {ab} (CD {cd})!"
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        self.session_ledger.record_dm_note(f"Richiesta prova: {ab} (CD {cd}) per {node.title}")
        messagebox.showinfo("Prova Richiesta", f"Richiesta di {ab} (CD {cd}) trasmessa in chat!", parent=self)

    def trigger_trap(self, node: FlowNode):
        cd = node.data.get("cd", 12)
        dmg = node.data.get("damage", "1d10 Danno")
        save = node.data.get("save", "Destrezza")
        msg = f"⚠️ [TRAPPOLA ATTIVATA!] '{node.title}' scatta! TS {save} CD {cd}. Danno potenziale: {dmg}!"
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        self.session_ledger.record_dm_note(f"Trappola attivata: {node.title} (CD {cd}, {dmg})")
        messagebox.showinfo("Trappola Scattata", f"Allarme trappola '{node.title}' trasmesso in chat!", parent=self)

    def award_loot(self, node: FlowNode):
        g = node.data.get("gold", "0")
        items = node.data.get("items", [])
        items_str = ", ".join(items) if items else "Nessun oggetto speciale"
        msg = f"💎 [TESORO SCOPERTO] Il party trova: {g} monete d'oro e: {items_str}!"
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        self.session_ledger.record_dm_note(f"Tesoro distribuito: {g} mo, {items_str}")
        messagebox.showinfo("Tesoro Consegnato", f"Bottino di '{node.title}' annunciato ai giocatori!", parent=self)

    def present_shop(self, node: FlowNode):
        merch = node.data.get("merchant", "Mercante")
        stype = node.data.get("shop_type", "Bottega")
        items = node.data.get("items", [])
        items_str = ", ".join(items) if items else "merci assortite"
        msg = f"🏬 [EMPORIO] {node.title} ({stype}) gestito da {merch}.\nArticoli in vendita: {items_str}"
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        messagebox.showinfo("Emporio Aperto", f"Lista merci di {merch} trasmessa in chat!", parent=self)

    def reveal_puzzle(self, node: FlowNode):
        clue = node.data.get("clue", "") or node.data.get("read_aloud", "Nessun indizio.")
        diff = node.data.get("difficulty", "Media")
        msg = f"🧩 [ENIGMA: {node.title}] (Difficoltà {diff})\nIndizio per il party: \"{clue}\""
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        messagebox.showinfo("Enigma Trasmesso", "Indizio dell'enigma inviato ai giocatori!", parent=self)

    def commence_rest(self, node: FlowNode):
        rtype = node.data.get("rest_type", "Breve")
        safe = node.data.get("safety", "Sicuro")
        msg = f"⛺ [RIPOSO {rtype.upper()}] Il party si accampa per riposare (Luogo: {safe}). Recupero slot e dadi vita secondo le regole."
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        self.session_ledger.record_dm_note(f"Riposo {rtype} effettuato a {node.title}")
        messagebox.showinfo("Riposo Avviato", f"Riposo {rtype} annunciato in chat!", parent=self)

    def share_lore(self, node: FlowNode):
        auth = node.data.get("author", "Anonimo")
        lang = node.data.get("language", "Comune")
        text = node.data.get("read_aloud") or node.data.get("description", "Contenuto del documento...")
        msg = f"📜 [DOCUMENTO: {node.title}] (Autore: {auth}, Lingua: {lang})\n\"{text}\""
        if hasattr(self.master_gui, "log_to_chat"):
            self.master_gui.log_to_chat(msg)
        self.session_ledger.record_secret(title=node.title, check=f"Lingua {lang}", text=text)
        messagebox.showinfo("Documento Condiviso", f"Documento '{node.title}' inviato ai giocatori!", parent=self)

    def activate_free_roam_mode(self):
        self._active_node_id = None
        self.session_ledger.record_node_visit(
            node_id=f"off_{datetime.now().strftime('%H%M%S')}",
            title="Deviazione Libera Fuori Pista",
            node_type="off_track",
            is_off_track=True,
            details="Il party ha deviato dal percorso pianificato. Modalità Improvvisazione attiva."
        )
        self._update_action_panel()
        messagebox.showinfo("Modalità Fuori Pista", "Modalità Improvvisazione attivata! Tutte le azioni manuali verranno tracciate nella cronistoria.", parent=self)

    def add_quick_dm_note(self):
        note = simpledialog.askstring("Nota Rapida del Master", "Cosa è appena successo?", parent=self)
        if note and note.strip():
            self.session_ledger.record_dm_note(note.strip())
            messagebox.showinfo("Nota Registrata", "Nota salvata nella cronistoria della sessione!", parent=self)


# ---------------------------------------------------------------------------
# DIALOGO CRONISTORIA & RECAP DI FINE SESSIONE
# ---------------------------------------------------------------------------

class SessionChronicleDialog(tk.Toplevel):
    """
    Dialogo di Fine Sessione: mostra la Cronistoria completa,
    il formato condivisibile per Discord e permette la retro-integrazione del Fuori Pista.
    """
    def __init__(self, master_gui, session_ledger: SessionLedger, campaign: Any = None):
        super().__init__(master_gui.master)
        self.master_gui = master_gui
        self.session_ledger = session_ledger
        self.campaign = campaign
        self.session_ledger.close_session()

        self.title(f"📜 Cronistoria Sessione • {self.session_ledger.campaign_name}")
        self.geometry("920x640")
        self.minsize(800, 520)
        self.transient(master_gui.master)
        apply_modern_window_style(self, bind_escape=True)
        self.configure(bg=BG_COLOR)

        self._build_ui()

    def _build_ui(self):
        container = tk.Frame(self, bg=BG_COLOR, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        hdr = tk.Frame(container, bg=BG_COLOR)
        hdr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(hdr, text="📜 Cronistoria & Resoconto di Fine Sessione", font=FONT_TITLE, bg=BG_COLOR, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(hdr, text=f"Campagna: {self.session_ledger.campaign_name} • Data: {self.session_ledger.real_start_time}",
                 font=FONT_SMALL, bg=BG_COLOR, fg=TEXT_MUTED).pack(anchor="w")

        # Tabs
        notebook = ttk.Notebook(container)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Tab 1: Markdown Chronicle
        tab_md = ttk.Frame(notebook, padding=8)
        notebook.add(tab_md, text="📜 Diario Completo")
        txt_md = scrolledtext.ScrolledText(tab_md, wrap=tk.WORD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=("Consolas", 10), relief="flat")
        txt_md.pack(fill=tk.BOTH, expand=True)
        md_content = ChronicleGenerator.generate_markdown(self.session_ledger)
        txt_md.insert("1.0", md_content)
        txt_md.configure(state=tk.DISABLED)

        # Tab 2: Discord / WhatsApp Ready Text
        tab_disc = ttk.Frame(notebook, padding=8)
        notebook.add(tab_disc, text="💬 Condividi per Giocatori (Discord)")
        txt_disc = scrolledtext.ScrolledText(tab_disc, wrap=tk.WORD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, relief="flat")
        txt_disc.pack(fill=tk.BOTH, expand=True)
        disc_content = ChronicleGenerator.generate_discord_text(self.session_ledger)
        txt_disc.insert("1.0", disc_content)

        # Tab 3: Fuori Pista & Integrazione nel Grafo
        tab_off = ttk.Frame(notebook, padding=8)
        notebook.add(tab_off, text="⚡ Fuori Pista & Retro-Integrazione")
        self._build_off_track_tab(tab_off)

        # Bottom Bar
        bottom_bar = tk.Frame(container, bg=BG_COLOR)
        bottom_bar.pack(fill=tk.X)

        ttk.Button(bottom_bar, text="📋 Copia per Discord", command=lambda: self.copy_to_clipboard(disc_content)).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom_bar, text="💾 Esporta HTML...", command=self.export_html).pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom_bar, text="Chiudi", command=self.destroy).pack(side=tk.RIGHT)

    def _build_off_track_tab(self, parent):
        off_events = [e for e in self.session_ledger.events if e.is_off_track]
        
        tk.Label(parent, text="⚡ Azioni Improvvisate Fuori Pista:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_RED).pack(anchor="w", pady=(0, 4))
        
        if off_events:
            tk.Label(parent, text="I giocatori hanno intrapreso le seguenti deviazioni non pianificate. Puoi convertirle in nodi ufficiali della campagna con 1 clic!",
                     font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))
            
            box = scrolledtext.ScrolledText(parent, height=8, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, font=FONT_MAIN, relief="flat")
            box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            for ote in off_events:
                box.insert(tk.END, f"• [{ote.timestamp}] {ote.title}\n  {ote.description}\n\n")
            box.configure(state=tk.DISABLED)

            if self.campaign:
                ttk.Button(parent, text="⚡ Salva Fuori Pista nel Flusso della Campagna", command=self.retro_integrate_off_track, style="Gold.TButton").pack(fill=tk.X)
        else:
            tk.Label(parent, text="Nessuna deviazione Fuori Pista registrata in questa sessione. Il party ha seguito i percorsi previsti!",
                     font=FONT_MAIN, bg=SURFACE_COLOR, fg=ACCENT_GREEN).pack(anchor="w", pady=16)

    def retro_integrate_off_track(self):
        if not self.campaign:
            messagebox.showwarning("Attenzione", "Nessuna campagna attiva caricata.", parent=self)
            return

        flow_data = getattr(self.campaign, "flow_graph", None)
        graph = FlowGraph.from_dict(flow_data) if (flow_data and isinstance(flow_data, dict)) else FlowGraph()
        
        new_nodes = integrate_off_track_events_into_flow(self.session_ledger, graph)
        if not new_nodes:
            messagebox.showinfo("Informazione", "Nessun evento fuori pista convertibile.", parent=self)
            return

        # Salva nella campagna
        self.campaign.flow_graph = graph.to_dict()
        serializer = DndScriptSerializer()
        self.campaign.flow_script = serializer.serialize(graph)
        sync_flow_graph_to_campaign(graph, self.campaign)
        self.campaign.save()

        messagebox.showinfo(
            "Fuori Pista Integrato",
            f"{len(new_nodes)} nuovi nodi creati e integrati permanentemente nel flusso della campagna!\n"
            "Ora fanno ufficialmente parte del mondo di gioco.",
            parent=self
        )

    def copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copiato", "Testo copiato negli appunti! Pronto da incollare su Discord o WhatsApp.", parent=self)

    def export_html(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Esporta Cronistoria HTML",
            initialfile=f"Cronistoria_{self.session_ledger.session_id}.html",
            filetypes=[("HTML (*.html)", "*.html")]
        )
        if path:
            html = ChronicleGenerator.generate_html(self.session_ledger)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            messagebox.showinfo("Esportato", f"Cronistoria salvata con successo in:\n{path}", parent=self)

