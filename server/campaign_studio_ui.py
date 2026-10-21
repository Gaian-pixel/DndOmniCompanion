# server/campaign_studio_ui.py
"""
Campaign Studio: Studio Split-Screen per la creazione di campagne D&D.
Unisce l'editor testuale 'Campaign-as-Code' (DndScript) a sinistra
con il Flow Canvas visuale drag-and-drop a destra, con sincronizzazione bidirezionale istantanea.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Callable, Any

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

    def _build_ui(self):
        # 1. Top Control Bar
        top_bar = tk.Frame(self, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1, padx=8, pady=6)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        tk.Label(
            top_bar, text="🧭 Campaign Studio", 
            font=("Georgia", 12, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GOLD
        ).pack(side=tk.LEFT, padx=(4, 12))

        # Pulsanti rapidi inserimento blocchi nel testo
        btn_box = tk.Frame(top_bar, bg=SURFACE_COLOR)
        btn_box.pack(side=tk.LEFT)

        ttk.Button(btn_box, text="+ Scena", command=lambda: self.insert_template("scene")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="+ Incontro", command=lambda: self.insert_template("encounter")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="+ PNG", command=lambda: self.insert_template("npc")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="+ Quest", command=lambda: self.insert_template("quest")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="+ Bivio ->", command=lambda: self.insert_template("branch")).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_box, text="⚡ Fuori Pista", command=lambda: self.insert_template("off_track")).pack(side=tk.LEFT, padx=2)

        # Azioni e Sincronizzazione
        sync_box = tk.Frame(top_bar, bg=SURFACE_COLOR)
        sync_box.pack(side=tk.RIGHT)

        ttk.Button(sync_box, text="🔍 Centra Flusso", command=self.center_canvas).pack(side=tk.RIGHT, padx=4)
        ttk.Button(sync_box, text="⟳ Aggiorna Flusso", command=self.sync_text_to_canvas, style="Gold.TButton").pack(side=tk.RIGHT, padx=4)

        self.lbl_stats = tk.Label(top_bar, text="", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED)
        self.lbl_stats.pack(side=tk.RIGHT, padx=12)

        # 2. Main PanedWindow (Split-Screen)
        paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG_COLOR, sashrelief="flat", sashwidth=4)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Sinistra: Editor DndScript
        left_frame = tk.Frame(paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(left_frame, minsize=320, width=440)

        hdr_left = tk.Frame(left_frame, bg=SURFACE_COLOR_ALT, padx=8, pady=4)
        hdr_left.pack(fill=tk.X)
        tk.Label(hdr_left, text="📝 DndScript • Campaign-as-Code", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        tk.Label(hdr_left, text="(Scrivi liberamente qui)", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(side=tk.RIGHT)

        self.txt_script = scrolledtext.ScrolledText(
            left_frame, wrap=tk.WORD, bg="#16181C", fg=TEXT_COLOR,
            insertbackground=ACCENT_GOLD, font=("Consolas", 10),
            relief="flat", highlightthickness=0
        )
        self.txt_script.pack(fill=tk.BOTH, expand=True)

        # Inserisci il testo iniziale
        initial_text = getattr(self.campaign, "flow_script", "")
        if not initial_text or not initial_text.strip():
            initial_text = self.serializer.serialize(self.graph)
        self.txt_script.insert("1.0", initial_text)

        # Binding per auto-sync debounced mentre si scrive
        self.txt_script.bind("<KeyRelease>", self._on_script_key_release)

        # Destra: Flow Canvas
        right_frame = tk.Frame(paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        paned.add(right_frame, minsize=400)

        hdr_right = tk.Frame(right_frame, bg=SURFACE_COLOR_ALT, padx=8, pady=4)
        hdr_right.pack(fill=tk.X)
        tk.Label(hdr_right, text="🧭 Flow Canvas • Visual Graph", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(side=tk.LEFT)
        tk.Label(hdr_right, text="Trascina i nodi o connetti le porte cerchiate", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(side=tk.RIGHT)

        self.flow_canvas = FlowCanvas(
            right_frame, graph=self.graph,
            on_change_callback=self._on_canvas_modified
        )
        self.flow_canvas.pack(fill=tk.BOTH, expand=True)

    # -----------------------------------------------------------------------
    # SINCRONIZZAZIONE TESTO <-> GRAFO
    # -----------------------------------------------------------------------

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

    def insert_template(self, block_type: str):
        snippet = ""
        if block_type == "scene":
            snippet = '\n\n# SCENA: Nuova Scena\nmappa: "maps/faerun.json"\nnarra: "Descrizione del luogo..."\n* SEGRETO [Percezione CD 12]: "Indizio nascosto qui..."\n-> "Se continuano a esplorare" -> SCENA: Prossimo Luogo'
        elif block_type == "encounter":
            snippet = '\n\n# INCONTRO: Nuovo Scontro\nmostri: 2x "Goblin", 1x "Hobgoblin"\ncr: 1\nloot: "20 mo, Pozione di Cura"\n-> "Dopo la vittoria" -> SCENA: Prossimo Luogo'
        elif block_type == "npc":
            snippet = '\n\n# PNG: Nome Personaggio\nruolo: "Mercante"\nallineamento: "Neutrale Buono"\n* SEGRETO: "Conosce la verità sulla cripta."'
        elif block_type == "quest":
            snippet = '\n\n# QUEST: Titolo Missione\nobiettivi: "Primo obiettivo", "Secondo obiettivo"\nloot: "100 mo"\nxp: 250'
        elif block_type == "branch":
            snippet = '\n-> "Se scelgono questa strada" -> SCENA: Destinazione'
        elif block_type == "off_track":
            snippet = '\n\n# FUORI_PISTA: Azione Improvvisata\nnarra: "I giocatori hanno preso una deviazione non prevista..."\n* NOTE: "Gestito al volo in sessione"'

        self.txt_script.insert(tk.INSERT, snippet)
        self.sync_text_to_canvas()

    def center_canvas(self):
        self.flow_canvas.reset_view()
