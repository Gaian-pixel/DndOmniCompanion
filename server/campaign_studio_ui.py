# server/campaign_studio_ui.py
"""
Campaign Studio: Studio Split-Screen per la creazione di campagne D&D.
Unisce l'editor testuale 'Campaign-as-Code' (DndScript) a sinistra
con il Flow Canvas visuale drag-and-drop a destra, con sincronizzazione bidirezionale istantanea.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Callable, Any

from common.i18n import _t, get_language
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, SURFACE_LIGHT,
    BORDER_COLOR, BORDER_GOLD, ACCENT_GOLD, ACCENT_GOLD_LIGHT,
    ACCENT_RED, ACCENT_GREEN, ACCENT_BLUE, TEXT_COLOR, TEXT_MUTED, TEXT_DARK,
    FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_BADGE
)
from common.campaign_script import (
    DndScriptParser, DndScriptSerializer, FlowGraph,
    sync_flow_graph_to_campaign, generate_flow_from_campaign
)
from server.flow_canvas import FlowCanvas


SAMPLE_TEMPLATE = """# SCENA: Locanda del Cinghiale
mappa: "maps/faerun.json"
meteo: "Nebbia"
luce: "Notte"
musica: "Taverna"
narra: "Una locanda calda e fumosa nel villaggio di Rovescuro. I sussurri notturni terrorizzano gli abitanti."

* SEGRETO [Intuizione CD 12]: "Il locandiere è ricattato dal culto."
* VOCE: "La vecchia cripta a nord è profanata."
* HANDOUT: "mappa_segreta.png" [titolo: "Mappa Cifrata"]

-> "Se interrogano il locandiere" -> SCENA: Ingresso Cripta
-> "Se escono di notte per investigare" -> INCONTRO: Imboscata Lupi
-> "Se cercano il sindaco" -> PNG: Sindaco Roland


# INCONTRO: Imboscata Lupi
mostri: 3x "Lupo", 1x "Lupo Feroce"
cr: 2
musica: "Combattimento"
loot: "Pelli di lupo, 15 mo"

-> "Seguendo le tracce" -> SCENA: Ingresso Cripta


# SCENA: Ingresso Cripta
mappa: "maps/cripta.json"
narra: "Due pesanti battenti di pietra consumati dal tempo."

* SEGRETO [Arcano CD 14]: "Sigillo necromantico inciso sulla pietra."
* TRAPPOLA [Percezione CD 13]: "Lastra a pressione."


# PNG: Sindaco Roland
ruolo: "Sindaco del borgo"
allineamento: "Legale Buono"

-> "Accettata la missione" -> QUEST: Sussurri nella Cripta


# QUEST: Sussurri nella Cripta
obiettivi: "Raggiungi la cripta", "Purifica il santuario"
loot: "100 mo, Pozione di Cura"
xp: 300
"""


class CampaignStudioFrame(tk.Frame):
    """
    Pannello Studio Split-Screen per la composizione della campagna:
    - Sinistra: Scrittura in linguaggio DndScript
    - Destra: Flow Canvas visuale drag & drop interattivo
    """
    def __init__(self, master, campaign: Any, on_change_callback: Optional[Callable] = None):
        super().__init__(master, bg=BG_COLOR)
        self.campaign = campaign
        self.on_change_callback = on_change_callback
        
        self.parser = DndScriptParser()
        self.serializer = DndScriptSerializer()
        self._sync_job = None
        self._is_internal_update = False

        # Inizializza o carica il FlowGraph
        flow_data = getattr(self.campaign, "flow_graph", None)
        flow_script = getattr(self.campaign, "flow_script", "")

        if flow_script and flow_script.strip():
            self.graph = self.parser.parse(flow_script)
        elif flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
            self.graph = FlowGraph.from_dict(flow_data)
        else:
            # Auto-genera dal database esistente della campagna se ha già scene/incontri
            if getattr(self.campaign, "scenes", None) or getattr(self.campaign, "encounters", None):
                self.graph = generate_flow_from_campaign(self.campaign)
            else:
                self.graph = self.parser.parse(SAMPLE_TEMPLATE)

        self._build_ui()
        self.sync_text_to_canvas()
        self.after(100, self._bind_fullscreen_shortcuts)

    def _build_ui(self):
        # Main PanedWindow (Split-Screen: Sinistra = DndScript + Toolbar Blocchi, Destra = Flow Canvas + Controlli Grafo)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG_COLOR, sashrelief="flat", sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ===================================================================
        # COLONNA SINISTRA: Editor DndScript & Barra Inserimento Rapido
        # ===================================================================
        left_frame = tk.Frame(paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(left_frame, minsize=380, width=480)

        hdr_left = tk.Frame(left_frame, bg=SURFACE_COLOR_ALT, padx=10, pady=6)
        hdr_left.pack(fill=tk.X)
        tk.Label(hdr_left, text=_t("camp_studio_script_title", default="📝 DndScript • Campaign-as-Code"), font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        tk.Label(hdr_left, text=_t("camp_studio_script_sub", default="Sincronizzazione istantanea col grafo"), font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(side=tk.RIGHT)

        # Barra strumenti inserimento blocchi (2 righe compatte, zero overflow)
        script_toolbar = tk.Frame(left_frame, bg=SURFACE_COLOR, padx=6, pady=5, highlightbackground=BORDER_COLOR, highlightthickness=1)
        script_toolbar.pack(fill=tk.X)

        row_blocks = tk.Frame(script_toolbar, bg=SURFACE_COLOR)
        row_blocks.pack(fill=tk.X, pady=(0, 3))
        ttk.Button(row_blocks, text=_t("camp_studio_btn_scene", default="🗺️ + Scena"), style="Dark.TButton", command=lambda: self.insert_template("scene")).pack(side=tk.LEFT, padx=(0, 3), fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_encounter", default="⚔️ + Incontro"), style="Dark.TButton", command=lambda: self.insert_template("encounter")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_check", default="🎲 + Prova"), style="Dark.TButton", command=lambda: self.insert_template("check")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_trap", default="⚠️ + Trappola"), style="Dark.TButton", command=lambda: self.insert_template("trap")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_loot", default="💎 + Tesoro"), style="Dark.TButton", command=lambda: self.insert_template("loot")).pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)

        row_flow = tk.Frame(script_toolbar, bg=SURFACE_COLOR)
        row_flow.pack(fill=tk.X)
        ttk.Button(row_flow, text=_t("camp_studio_btn_comp_loot", default="📖 + Loot Compendio"), command=self.open_compendium_loot_picker, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 3), fill=tk.X, expand=True)
        ttk.Button(row_flow, text=_t("camp_studio_btn_branch", default="🔀 + Bivio ->"), style="Dark.TButton", command=lambda: self.insert_template("branch")).pack(side=tk.LEFT, padx=2)

        # Menubutton Condizioni
        mb_cond = ttk.Menubutton(row_flow, text=_t("camp_studio_btn_conds", default="Condizioni ▾"))
        menu_cond = tk.Menu(mb_cond, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        menu_cond.add_command(label="✅ -> SUCCESSO ->", command=lambda: self.insert_template("cond_success"))
        menu_cond.add_command(label="❌ -> FALLIMENTO ->", command=lambda: self.insert_template("cond_failure"))
        menu_cond.add_command(label="🎲 -> SE [Abilità CD] ->", command=lambda: self.insert_template("cond_check"))
        menu_cond.add_command(label="🔑 -> SE POSSIEDE \"...\" ->", command=lambda: self.insert_template("cond_item"))
        menu_cond.add_command(label="↩️ -> ALTRIMENTI ->", command=lambda: self.insert_template("cond_else"))
        mb_cond["menu"] = menu_cond
        mb_cond.pack(side=tk.LEFT, padx=2)

        # Menubutton Altri Blocchi
        mb_blocks = ttk.Menubutton(row_flow, text=_t("camp_studio_btn_other_blocks", default="Altri Blocchi ▾"))
        menu_blocks = tk.Menu(mb_blocks, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        menu_blocks.add_command(label="🏬 Emporio", command=lambda: self.insert_template("shop"))
        menu_blocks.add_command(label="🧩 Enigma", command=lambda: self.insert_template("puzzle"))
        menu_blocks.add_command(label="👤 PNG", command=lambda: self.insert_template("npc"))
        menu_blocks.add_command(label="⛺ Riposo", command=lambda: self.insert_template("rest"))
        menu_blocks.add_command(label="📜 Documento (Lore)", command=lambda: self.insert_template("lore"))
        menu_blocks.add_command(label="⏳ Evento", command=lambda: self.insert_template("event"))
        menu_blocks.add_command(label="📜 Quest", command=lambda: self.insert_template("quest"))
        menu_blocks.add_command(label="📢 Spunto Narrativo", command=lambda: self.insert_template("hook"))
        menu_blocks.add_command(label="⚡ Fuori Pista", command=lambda: self.insert_template("off_track"))
        menu_blocks.add_command(label="📝 Nota Narrativa", command=lambda: self.insert_template("note"))
        mb_blocks["menu"] = menu_blocks
        mb_blocks.pack(side=tk.LEFT, padx=(2, 0))

        self.txt_script = scrolledtext.ScrolledText(
            left_frame, wrap=tk.WORD, bg="#16181C", fg=TEXT_COLOR,
            insertbackground=ACCENT_GOLD, font=("Consolas", 10),
            relief="flat", highlightthickness=0, padx=8, pady=6
        )
        self.txt_script.pack(fill=tk.BOTH, expand=True)

        # Inserisci il testo iniziale
        initial_text = getattr(self.campaign, "flow_script", "")
        if not initial_text or not initial_text.strip():
            initial_text = self.serializer.serialize(self.graph)
        self.txt_script.insert("1.0", initial_text)

        # Binding per auto-sync debounced mentre si scrive
        self.txt_script.bind("<KeyRelease>", self._on_script_key_release)

        # ===================================================================
        # COLONNA DESTRA: Flow Canvas & Barra Controlli Visuali
        # ===================================================================
        right_frame = tk.Frame(paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(right_frame, minsize=420)

        hdr_right = tk.Frame(right_frame, bg=SURFACE_COLOR_ALT, padx=10, pady=5)
        hdr_right.pack(fill=tk.X)
        tk.Label(hdr_right, text=_t("camp_studio_canvas_title", default="🧭 Flow Canvas • Grafo Visuale"), font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(hdr_right, text="", font=FONT_BADGE, bg=SURFACE_COLOR, fg=ACCENT_GOLD, padx=8, pady=2)
        self.lbl_stats.pack(side=tk.LEFT, padx=10)

        ttk.Button(hdr_right, text=_t("camp_studio_btn_refresh_flow", default="⟳ Aggiorna Flusso"), command=self.sync_text_to_canvas, style="Gold.TButton").pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(hdr_right, text=_t("camp_studio_btn_center", default="🔍 Centra Vista"), command=self.center_canvas, style="Dark.TButton").pack(side=tk.RIGHT, padx=4)

        self.flow_canvas = FlowCanvas(
            right_frame, graph=self.graph,
            on_change_callback=self._on_canvas_modified
        )
        self.flow_canvas.pack(fill=tk.BOTH, expand=True)

    # -----------------------------------------------------------------------
    # SINCRONIZZAZIONE TESTO <-> GRAFO
    # -----------------------------------------------------------------------

    def set_campaign(self, campaign: Any):
        """Sostituisce la campagna corrente nello Studio, ricaricando DndScript e FlowGraph."""
        self.campaign = campaign
        flow_data = getattr(self.campaign, "flow_graph", None)
        flow_script = getattr(self.campaign, "flow_script", "")

        if flow_script and flow_script.strip():
            self.graph = self.parser.parse(flow_script)
        elif flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
            self.graph = FlowGraph.from_dict(flow_data)
        else:
            if getattr(self.campaign, "scenes", None) or getattr(self.campaign, "encounters", None):
                self.graph = generate_flow_from_campaign(self.campaign)
            else:
                self.graph = self.parser.parse(SAMPLE_TEMPLATE)

        initial_text = getattr(self.campaign, "flow_script", "")
        if not initial_text or not initial_text.strip():
            initial_text = self.serializer.serialize(self.graph)

        self._is_internal_update = True
        try:
            self.txt_script.delete("1.0", tk.END)
            self.txt_script.insert("1.0", initial_text)
        finally:
            self._is_internal_update = False

        self.flow_canvas.set_graph(self.graph)
        n_count = len(self.graph.nodes)
        e_count = len(self.graph.edges)
        self.lbl_stats.config(text=f"Nodi: {n_count} | Connessioni: {e_count}")
        self._save_to_campaign()

    def _on_script_key_release(self, event=None):
        if self._is_internal_update:
            return
        if self._sync_job:
            self.after_cancel(self._sync_job)
        self._sync_job = self.after(500, self.sync_text_to_canvas)

    def sync_text_to_canvas(self):
        """Compila il testo DndScript e aggiorna il FlowCanvas preservando le posizioni."""
        text = self.txt_script.get("1.0", tk.END).strip()
        if not text:
            return

        # Salva posizioni attuali dei nodi per non resettarle
        existing_pos = {}
        for n in self.graph.nodes.values():
            existing_pos[n.title.lower()] = (n.x, n.y)

        # Parsa
        new_graph = self.parser.parse(text, existing_positions=existing_pos)
        self.graph = new_graph

        # Aggiorna canvas
        self.flow_canvas.set_graph(self.graph)

        # Aggiorna statistiche
        n_count = len(self.graph.nodes)
        e_count = len(self.graph.edges)
        self.lbl_stats.config(text=f"Nodi: {n_count} | Connessioni: {e_count}")

        # Sincronizza nell'oggetto campaign
        self._save_to_campaign()

    def _on_canvas_modified(self):
        """Chiamato quando l'utente muove o modifica nodi o connessioni direttamente sul canvas."""
        if self._is_internal_update:
            return

        # Serializza il nuovo grafo in testo e aggiorna l'editor senza far saltare il cursore
        self._is_internal_update = True
        try:
            new_text = self.serializer.serialize(self.graph)
            cur_pos = self.txt_script.index(tk.INSERT)
            self.txt_script.delete("1.0", tk.END)
            self.txt_script.insert("1.0", new_text)
            self.txt_script.mark_set(tk.INSERT, cur_pos)
            self.lbl_stats.config(text=f"Nodi: {len(self.graph.nodes)} | Connessioni: {len(self.graph.edges)}")
            self._save_to_campaign()
        finally:
            self._is_internal_update = False

    def _save_to_campaign(self):
        """Salva il codice e il grafo nella campagna e sincronizza le entità VTT."""
        self.campaign.flow_script = self.txt_script.get("1.0", tk.END).strip()
        self.campaign.flow_graph = self.graph.to_dict()
        sync_flow_graph_to_campaign(self.graph, self.campaign)
        if self.on_change_callback:
            self.on_change_callback()

    # -----------------------------------------------------------------------
    # TEMPLATE RAPIDI DI INSERIMENTO
    # -----------------------------------------------------------------------

    def open_compendium_loot_picker(self):
        """Apre il Compendio 5e filtrato sugli oggetti/tesori e inserisce l'oggetto scelto nello script DndScript."""
        try:
            from server.compendium_ui import CompendiumDialog
            def _on_item_picked(item_data, category):
                name = (item_data.get("name") or item_data.get("title") or "").strip()
                if not name:
                    return
                self._insert_compendium_item_into_script(name)

            dlg = CompendiumDialog(
                self.winfo_toplevel(),
                on_import_callback=_on_item_picked,
                is_dm=True,
                initial_category="Oggetti Magici",
                action_label="💎 Inserisci nel Loot / Tesoro",
                allowed_categories=["Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici", "Equipaggiamento & Tesori"]
            )
            dlg.grab_set()
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il compendio: {e}", parent=self)

    def _insert_compendium_item_into_script(self, item_name: str):
        """Inserisce il nome dell'oggetto del Compendio nella riga corrente loot:/oggetti: o nel punto del cursore."""
        try:
            cur_idx = self.txt_script.index(tk.INSERT)
            line_num = int(str(cur_idx).split(".")[0])
            line_text = self.txt_script.get(f"{line_num}.0", f"{line_num}.end")
            low_line = line_text.strip().lower()
            if low_line.startswith(("loot:", "bottino:", "ricompensa:")) and line_text.rstrip().endswith('"'):
                col_pos = line_text.rfind('"')
                self.txt_script.insert(f"{line_num}.{col_pos}", f", {item_name}")
            elif low_line.startswith(("oggetti:", "items:", "magici:")):
                self.txt_script.insert(f"{line_num}.end", f', "{item_name}"')
            else:
                self.txt_script.insert(tk.INSERT, f'"{item_name}"')
            self.sync_text_to_canvas()
        except Exception:
            self.txt_script.insert(tk.INSERT, f'"{item_name}"')
            self.sync_text_to_canvas()

    def insert_template(self, block_type: str):
        snippet = ""
        if block_type == "scene":
            snippet = '\n\n# SCENA: Nuova Scena\nmappa: "maps/faerun.json"\nnarra: "Descrizione del luogo..."\n* SEGRETO [Percezione CD 12]: "Indizio nascosto qui..."\n-> "Se continuano a esplorare" -> SCENA: Prossimo Luogo'
        elif block_type == "encounter":
            snippet = '\n\n# INCONTRO: Nuovo Scontro\nmostri: 2x "Goblin", 1x "Hobgoblin"\ncr: 1\nloot: "20 mo, Pozione di Cura"\n-> "Dopo la vittoria" -> SCENA: Prossimo Luogo'
        elif block_type == "check":
            snippet = '\n\n# PROVA: Scassinare il Portone\nabilità: "Rapidità di Mano"\ncd: 15\n-> SUCCESSO -> SCENA: Sala del Tesoro\n-> FALLIMENTO -> TRAPPOLA: Dardo Avvelenato'
        elif block_type == "trap":
            snippet = '\n\n# TRAPPOLA: Dardi Avvelenati\ncd: 13\ndanno: "2d6 Veleno"\ntiro_salvezza: "Destrezza"\n-> SCENA: Corridoio Principale'
        elif block_type == "loot":
            snippet = '\n\n# TESORO: Forziere Nascosto\nmonete: "150 mo, 50 ma"\noggetti: "Pozione di Guarigione Superiore", "Pergamena di Volo"\n-> SCENA: Prossimo Luogo'
        elif block_type == "shop":
            snippet = '\n\n# EMPORIO: La Fucina d\'Oro\nmercante: "Gunnar il Fabbro"\ntipo: "Armature ed Equipaggiamento"\noggetti: "Spada Lunga +1", "Scudo di Mithral", "Razioni"'
        elif block_type == "puzzle":
            snippet = '\n\n# ENIGMA: Le Statue Elementali\ndifficoltà: "Media"\nindizio: "Il fuoco accende l\'acqua, ma il vento spegne la terra"\nsoluzione: "Allineare i bacili in senso orario"\n-> SUCCESSO -> SCENA: Santuario Segreto\n-> FALLIMENTO -> TRAPPOLA: Fiammata Magica'
        elif block_type == "rest":
            snippet = '\n\n# RIPOSO: Radura Protetta\ntipo: "Lungo"\nsicurezza: "Sicuro"\n-> SCENA: Il Risveglio'
        elif block_type == "lore":
            snippet = '\n\n# DOCUMENTO: Lettera Incompleta del Culto\nautore: "Malakor il Rosso"\nlingua: "Infernale"\nnarra: "Il testo accenna a un rituale che avrà luogo durante la luna nuova..."'
        elif block_type == "event":
            snippet = '\n\n# EVENTO: Arrivo della Guardia Cittadina\ninnesco: "Dopo 3 round di combattimento"\nnarra: "Il rumore delle campane d\'allarme risuona nella piazza."'
        elif block_type == "npc":
            snippet = '\n\n# PNG: Nome Personaggio\nruolo: "Mercante"\nallineamento: "Neutrale Buono"\n* SEGRETO: "Conosce la verità sulla cripta."'
        elif block_type == "quest":
            snippet = '\n\n# QUEST: Titolo Missione\nobiettivi: "Primo obiettivo", "Secondo obiettivo"\nloot: "100 mo"\nxp: 250'
        elif block_type == "hook":
            snippet = '\n\n# SPUNTO: Una Lettera Anonima\nnarra: "Un messaggero trafelato consegna un plico sigillato con cera nera..."\n-> "Se accettano l\'invito" -> SCENA: Locanda del Cinghiale'
        elif block_type == "off_track":
            snippet = '\n\n# FUORI_PISTA: Azione Improvvisata\nnarra: "I giocatori hanno preso una deviazione non prevista..."\n* NOTE: "Gestito al volo in sessione"'
        elif block_type == "note":
            snippet = '\n\n# NOTA: Promemoria DM\nnarra: "Ricordarsi del patto stipulato con l\'entità."'
        elif block_type == "branch":
            snippet = '\n-> "Se scelgono questa strada" -> SCENA: Destinazione'
        elif block_type == "cond_success":
            snippet = '\n-> SUCCESSO -> SCENA: Destinazione'
        elif block_type == "cond_failure":
            snippet = '\n-> FALLIMENTO -> SCENA: Conseguenza'
        elif block_type == "cond_check":
            snippet = '\n-> SE [Percezione CD 14] -> SCENA: Destinazione\n-> ALTRIMENTI -> SCENA: Altra Destinazione'
        elif block_type == "cond_item":
            snippet = '\n-> SE POSSIEDE "Chiave Antica" -> SCENA: Cripta Chiusa\n-> ALTRIMENTI -> SCENA: Porta Chiusa'
        elif block_type == "cond_else":
            snippet = '\n-> ALTRIMENTI -> SCENA: Destinazione'

        self.txt_script.insert(tk.INSERT, snippet)
        self.sync_text_to_canvas()

    def center_canvas(self):
        self.flow_canvas.reset_view()

    def _bind_fullscreen_shortcuts(self):
        try:
            top = self.winfo_toplevel()
            if top:
                top.bind("<F11>", self.toggle_fullscreen, add="+")
                top.bind("<Escape>", self.exit_fullscreen, add="+")
        except Exception:
            pass

    def toggle_fullscreen(self, event=None):
        top = self.winfo_toplevel()
        if not top:
            return
        is_fs = getattr(top, "_is_fullscreen", False)
        is_fs = not is_fs
        top._is_fullscreen = is_fs
        try:
            top.attributes("-fullscreen", is_fs)
            if hasattr(self, "btn_fs"):
                self.btn_fs.config(text="🗗 Finestra" if is_fs else "⛶ Schermo Intero")
        except Exception:
            pass

    def exit_fullscreen(self, event=None):
        top = self.winfo_toplevel()
        if top and getattr(top, "_is_fullscreen", False):
            top._is_fullscreen = False
            try:
                top.attributes("-fullscreen", False)
                if hasattr(self, "btn_fs"):
                    self.btn_fs.config(text="⛶ Schermo Intero")
            except Exception:
                pass

