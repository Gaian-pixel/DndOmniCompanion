# server/campaign_studio_ui.py
"""
Campaign Studio: Studio Visuale a Flussi Gerarchici per la creazione di campagne D&D.
Integra l'Ispettore Contestuale Visuale (Nodi, Segreti, Bivi e Connessioni) a sinistra,
il Flow Canvas drag-and-drop con tavolozza blocchi a destra e il Drawer Entità in basso.
"""

import copy
import os
import re
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Callable, Any, Dict, List, Set, Tuple

from common.i18n import _t
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT,
    BORDER_COLOR, ACCENT_GOLD,
    TEXT_COLOR, TEXT_MUTED,
    FONT_MAIN, FONT_BOLD, FONT_SMALL, FONT_BADGE,
)
from common.campaign_script import (
    NODE_TYPES, EDGE_CONDITIONS, FlowGraph, FlowNode,
    sync_hierarchical_campaign_flows, ensure_hierarchical_campaign_flows,
    get_scene_subflow_graph, save_scene_subflow, summarize_subflow,
    create_starter_sample_flows,
)
from common.srd_offline import resolve_compendium_item, parse_loot_specification
from server.flow_canvas import FlowCanvas


_NODE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "scene": {
        "title": "Nuova Scena",
        "data": {
            "map_file": "maps/faerun.json",
            "read_aloud": "Descrizione del luogo...",
            "secrets": [{"check": "Percezione CD 12", "text": "Indizio nascosto qui..."}],
        },
        "outcomes": [
            {
                "node_type": "scene",
                "base_title": "Prossimo Luogo",
                "condition_type": "custom",
                "condition_value": "Esplorazione",
                "label": "Se continuano a esplorare",
                "offset": (270.0, 0.0),
                "data": {"map_file": "maps/faerun.json", "read_aloud": ""},
            }
        ],
    },
    "encounter": {
        "title": "Nuovo Scontro",
        "data": {
            "monsters": [{"qty": 2, "name": "Goblin"}, {"qty": 1, "name": "Hobgoblin"}],
            "cr": "1",
            "loot": "20 mo, Pozione di Cura",
            "read_aloud": "Agguato nemico nell'ombra.",
        },
        "outcomes": [
            {
                "node_type": "scene",
                "base_title": "Prossimo Luogo",
                "condition_type": "success",
                "label": "Dopo la vittoria",
                "offset": (270.0, 0.0),
                "data": {},
            }
        ],
    },
    "check": {
        "title": "Scassinare il Portone",
        "data": {
            "ability": "Rapidità di Mano",
            "cd": 15,
            "read_aloud": "Un meccanismo complesso protegge l'accesso.",
        },
        "outcomes": [
            {
                "node_type": "scene",
                "base_title": "Sala del Tesoro",
                "condition_type": "success",
                "label": "Successo",
                "offset": (270.0, -70.0),
                "data": {},
            },
            {
                "node_type": "trap",
                "base_title": "Dardo Avvelenato",
                "condition_type": "failure",
                "label": "Fallimento",
                "offset": (270.0, 70.0),
                "data": {"cd": 13, "damage": "2d6 Veleno", "save": "Destrezza"},
            },
        ],
    },
    "trap": {
        "title": "Dardi Avvelenati",
        "data": {
            "cd": 13,
            "damage": "2d6 Veleno",
            "save": "Destrezza",
            "read_aloud": "Uno scatto metallico tradisce il meccanismo nascosto.",
        },
        "outcomes": [
            {
                "node_type": "scene",
                "base_title": "Corridoio Principale",
                "condition_type": "default",
                "label": "",
                "offset": (270.0, 0.0),
                "data": {},
            }
        ],
    },
    "loot": {
        "title": "Forziere Nascosto",
        "data": {
            "gold": "150 mo, 50 ma",
            "items": ["Pozione di Guarigione Superiore", "Pergamena di Volo"],
            "read_aloud": "Un baule rinforzato in ferro giace sotto le macerie.",
        },
    },
    "shop": {
        "title": "La Fucina d'Oro",
        "data": {
            "merchant": "Gunnar il Fabbro",
            "shop_type": "Armature ed Equipaggiamento",
            "items": ["Spada Lunga +1", "Scudo di Mithral", "Razioni"],
        },
    },
    "puzzle": {
        "title": "Le Statue Elementali",
        "data": {
            "difficulty": "Media",
            "clue": "Il fuoco accende l'acqua, ma il vento spegne la terra",
            "solution": "Allineare i bacili in senso orario",
            "read_aloud": "Quattro statue di pietra circondano un altare inciso.",
        },
        "outcomes": [
            {
                "node_type": "scene",
                "base_title": "Santuario Segreto",
                "condition_type": "success",
                "label": "Successo",
                "offset": (270.0, -70.0),
                "data": {},
            },
            {
                "node_type": "trap",
                "base_title": "Fiammata Magica",
                "condition_type": "failure",
                "label": "Fallimento",
                "offset": (270.0, 70.0),
                "data": {"cd": 14, "damage": "3d6 Fuoco", "save": "Destrezza"},
            },
        ],
    },
    "rest": {
        "title": "Radura Protetta",
        "data": {
            "rest_type": "Lungo",
            "safety": "Sicuro",
            "read_aloud": "Un rifugio riparato dove riprendere fiato.",
        },
    },
    "lore": {
        "title": "Lettera Incompleta del Culto",
        "data": {
            "author": "Malakor il Rosso",
            "language": "Infernale",
            "read_aloud": "Il testo accenna a un rituale che avrà luogo durante la luna nuova...",
        },
    },
    "event": {
        "title": "Arrivo della Guardia Cittadina",
        "data": {
            "trigger": "Dopo 3 round di combattimento",
            "read_aloud": "Il rumore delle campane d'allarme risuona nella piazza.",
        },
    },
    "npc": {
        "title": "Nome Personaggio",
        "data": {
            "role": "Mercante",
            "alignment": "Neutrale Buono",
            "faction": "",
            "secrets": [{"check": "Intuizione CD 12", "text": "Conosce la verità sulla cripta."}],
        },
    },
    "quest": {
        "title": "Titolo Missione",
        "data": {
            "objectives": ["Primo obiettivo", "Secondo obiettivo"],
            "loot": "100 mo",
            "xp": 250,
            "read_aloud": "Un incarico urgente attende il gruppo.",
        },
    },
    "hook": {
        "title": "Una Lettera Anonima",
        "data": {
            "read_aloud": "Un messaggero trafelato consegna un plico sigillato con cera nera...",
        },
    },
    "choice": {
        "title": "Bivio Narrativo",
        "data": {
            "read_aloud": "Il gruppo deve scegliere quale strada imboccare.",
        },
    },
    "off_track": {
        "title": "Azione Improvvisata",
        "data": {
            "read_aloud": "I giocatori hanno preso una deviazione non prevista...",
            "notes": "Gestito al volo in sessione",
        },
    },
    "note": {
        "title": "Promemoria DM",
        "data": {
            "read_aloud": "Ricordarsi del patto stipulato con l'entità.",
        },
    },
    "exit": {
        "title": "Prossima Scena",
        "data": {"target_scene": "Prossima Scena"},
    },
}


_WEATHER_VALUES = ["", "Sereno", "Pioggia", "Tempesta", "Neve", "Nebbia", "Oscurità"]

# Schema dichiarativo dei campi specifici per ogni node_type nell'Ispettore visuale.
# Formato: (data_key, etichetta, widget_kind, extra)
_NODE_FIELD_SPECS: Dict[str, List[Tuple[str, str, str, Any]]] = {
    "scene": [
        ("map_file", "Mappa VTT associata", "map", None),
        ("weather", "Meteo", "readonly_combo", _WEATHER_VALUES),
        ("light", "Illuminazione", "combo", ["Luce Diurna", "Penombra", "Buio", "Notte", "Torce"]),
        ("music", "Tema Musicale", "entry", None),
    ],
    "encounter": [
        ("monsters", "Mostri (es. 2x Goblin, 1x Hobgoblin)", "monsters", None),
        ("cr", "Grado Sfida (CR)", "entry", None),
        ("music", "Musica Combattimento", "entry", None),
        ("loot", "Bottino / Ricompensa", "loot_str", None),
    ],
    "check": [
        ("ability", "Abilità / Caratteristica", "combo", [
            "Percezione", "Indagare", "Intuizione", "Furtività", "Rapidità di Mano",
            "Persuasione", "Inganno", "Intimidire", "Atletica", "Acrobazia",
            "Arcano", "Storia", "Religione", "Sopravvivenza", "Medicina",
        ]),
        ("cd", "Classe Difficoltà (CD)", "int", 10),
    ],
    "trap": [
        ("cd", "CD Individuazione / Disinnesco", "int", 12),
        ("damage", "Danni (es. 2d6 Veleno)", "entry", None),
        ("save", "Tiro Salvezza", "combo", ["Destrezza", "Costituzione", "Forza", "Saggezza", "Intelligenza", "Carisma"]),
    ],
    "loot": [
        ("gold", "Monete / Tesoro", "entry", None),
        ("items", "Oggetti (separati da virgola)", "loot_items", None),
    ],
    "shop": [
        ("merchant", "Mercante / Bottegaio", "entry", None),
        ("shop_type", "Tipologia Emporio", "combo", ["Emporio Generale", "Armeria", "Alchimista & Pozioni", "Bottega Arcana", "Locanda"]),
        ("items", "Inventario (separato da virgola)", "loot_items", None),
    ],
    "npc": [
        ("role", "Ruolo", "entry", None),
        ("alignment", "Allineamento", "combo", [
            "Legale Buono", "Neutrale Buono", "Caotico Buono",
            "Legale Neutrale", "Neutrale Puro", "Caotico Neutrale",
            "Legale Malvagio", "Neutrale Malvagio", "Caotico Malvagio",
        ]),
        ("faction", "Fazione / Organizzazione", "faction_combo", None),
    ],
    "quest": [
        ("objectives", "Obiettivi (uno per riga)", "multiline", None),
        ("loot", "Ricompensa / Bottino", "loot_str", None),
        ("xp", "Punti Esperienza (XP)", "int", 0),
    ],
    "puzzle": [
        ("difficulty", "Difficoltà", "combo", ["Facile", "Media", "Difficile", "Mortale"]),
        ("clue", "Indizio", "entry", None),
        ("solution", "Soluzione", "entry", None),
    ],
    "rest": [
        ("rest_type", "Tipo di Riposo", "combo", ["Breve", "Lungo"]),
        ("safety", "Livello Sicurezza", "combo", ["Sicuro", "Insidioso", "Ostile"]),
    ],
    "lore": [
        ("author", "Autore", "entry", None),
        ("language", "Lingua", "entry", None),
        ("map_file", "Allegato Grafico / Handout", "handout_file", None),
    ],
    "event": [
        ("trigger", "Innesco Evento", "entry", None),
    ],
    "exit": [
        ("target_scene", "Scena di Destinazione", "scene_combo", None),
    ],
    "off_track": [
        ("notes", "Annotazioni Rapide DM", "entry", None),
    ],
    "choice": [
        ("options", "Opzioni (una per riga)", "multiline", None),
    ],
}


def _parse_monsters_text(raw: str) -> List[Dict[str, Any]]:
    monsters: List[Dict[str, Any]] = []
    for chunk in str(raw or "").split(","):
        part = chunk.strip()
        if not part:
            continue
        m = re.match(r'^(\d+)\s*[xX×]\s*(.+)$', part)
        if m:
            monsters.append({"qty": max(1, int(m.group(1))), "name": m.group(2).strip()})
            continue
        m_rev = re.match(r'^(.+?)\s*[xX×]\s*(\d+)$', part)
        if m_rev:
            monsters.append({"qty": max(1, int(m_rev.group(2))), "name": m_rev.group(1).strip()})
            continue
        monsters.append({"qty": 1, "name": part})
    return monsters


def _format_monsters_text(monsters: Any) -> str:
    if isinstance(monsters, str):
        return monsters
    if not isinstance(monsters, list):
        return ""
    parts = []
    for m in monsters:
        if isinstance(m, dict):
            qty = m.get("qty", m.get("count", m.get("quantity", 1)))
            name = m.get("name", "")
            if name:
                parts.append(f"{qty}x {name}")
        elif str(m).strip():
            parts.append(str(m).strip())
    return ", ".join(parts)


_SECRET_TYPE_VALUES = ["SEGRETO", "INDIZIO", "TRAPPOLA", "PASSAGGIO"]
_SECRET_NO_CHECK_LABEL = "Nessuna (Automatico)"
_SECRET_CHECK_VALUES = [
    _SECRET_NO_CHECK_LABEL,
    "Percezione",
    "Indagare",
    "Intuizione",
    "Arcano",
    "Storia",
    "Religione",
    "Natura",
    "Furtività",
    "Persuasione",
    "Inganno",
    "Intimidire",
    "Sopravvivenza",
    "Medicina",
    "Rapidità di Mano",
    "Atletica",
    "TS Destrezza",
    "TS Costituzione",
    "TS Saggezza",
    "TS Intelligenza",
]


def _parse_secret_check(check_str: str) -> Tuple[str, str]:
    """Scompone 'Abilità CD XX' in (abilità, cd_str) mantenendo compatibilità con testi legacy."""
    raw = str(check_str or "").strip()
    if not raw or raw.lower() in ("nessuna", "nessuna (automatico)", "automatico"):
        return _SECRET_NO_CHECK_LABEL, ""
    m = re.match(r"^(.*?)\s*(?:CD|DC)\s*(\d+)\s*$", raw, re.IGNORECASE)
    if m:
        ability = m.group(1).strip() or "Percezione"
        return ability, m.group(2)
    return raw, ""


def _format_secret_check(ability_raw: str, cd_raw: str) -> str:
    """Compone la stringa canonica 'Abilità CD XX' dai controlli guidati (o '' se automatico)."""
    ability = str(ability_raw or "").strip()
    if not ability or ability == _SECRET_NO_CHECK_LABEL or ability.lower().startswith("nessuna"):
        return ""
    if re.search(r"\b(?:CD|DC)\s*\d+\b", ability, re.IGNORECASE):
        return ability
    cd_clean = str(cd_raw or "").strip()
    if cd_clean:
        try:
            cd_int = max(1, min(40, int(cd_clean)))
            return f"{ability} CD {cd_int}"
        except ValueError:
            return ability
    return ability


class CampaignStudioFrame(tk.Frame):
    """
    Pannello Studio Visuale Gerarchico a 2 Livelli per campagne D&D (100% Flow):
    - Livello 1 (Campagna): Macro-flusso di Scene e passaggi tra luoghi.
    - Livello 2 (Scena): Micro-flusso interno (Incontri, Prove, PNG, Trappole, Quest, Uscite).
    Colonna sinistra: Ispettore Contestuale Visuale (Proprietà tipizzate, Segreti, Bivi/Archi).
    Colonna destra: Flow Canvas interattivo + Tavolozza Blocchi + Drawer Entità collassabile.
    """

    def __init__(
        self,
        master,
        campaign: Any,
        on_change_callback: Optional[Callable] = None,
        on_inspect_callback: Optional[Callable[[str, Any], None]] = None,
    ):
        super().__init__(master, bg=BG_COLOR)
        self.campaign = campaign
        self.on_change_callback = on_change_callback
        self.on_inspect_callback = on_inspect_callback

        self.active_scene_name: Optional[str] = None
        self._drawer_visible = True
        self._inspector_node_id: Optional[str] = None
        self._inspector_edge_idx: Optional[int] = None
        self._inspector_widgets: Dict[str, Any] = {}
        self._inspector_apply_job = None
        self._inspector_building = False

        self._prepare_campaign_hierarchy()
        self.graph = (
            FlowGraph.from_dict(self.campaign.flow_graph)
            if isinstance(getattr(self.campaign, "flow_graph", None), dict)
            else FlowGraph()
        )

        self._build_ui()
        self._load_active_level_into_views(sync_campaign=True)
        self._bind_job = self.after(100, self._bind_fullscreen_shortcuts)

        def _on_studio_destroyed(e=None):
            if e and getattr(e, "widget", None) != self:
                return
            top = getattr(self, "_fullscreen_top", None)
            if top is not None:
                for seq, attr in (("<F11>", "_f11_bind_id"), ("<Escape>", "_esc_bind_id")):
                    bid = getattr(self, attr, None)
                    if bid:
                        try:
                            top.unbind(seq, bid)
                        except Exception:
                            pass
                        setattr(self, attr, None)
                self._fullscreen_top = None
            for job_attr in ("_bind_job", "_inspector_apply_job"):
                job = getattr(self, job_attr, None)
                if job is not None:
                    try:
                        self.after_cancel(job)
                    except Exception:
                        pass
                    setattr(self, job_attr, None)

        self.bind("<Destroy>", _on_studio_destroyed, add="+")

    def _prepare_campaign_hierarchy(self) -> None:
        """Assicura che la campagna corrente abbia un FlowGraph gerarchico a 2 livelli pronto."""
        raw_fg = getattr(self.campaign, "flow_graph", None)
        has_graph = bool(isinstance(raw_fg, dict) and raw_fg.get("nodes"))
        has_entities = bool(
            getattr(self.campaign, "scenes", None)
            or getattr(self.campaign, "encounters", None)
            or getattr(self.campaign, "quests", None)
            or getattr(self.campaign, "npcs", None)
            or getattr(self.campaign, "handouts", None)
        )
        if not has_graph and not has_entities:
            create_starter_sample_flows(self.campaign)
        ensure_hierarchical_campaign_flows(self.campaign)

    # -----------------------------------------------------------------------
    # COSTRUZIONE INTERFACCIA
    # -----------------------------------------------------------------------

    def _build_ui(self):
        # Barra superiore Breadcrumb & Navigazione Gerarchica
        self.hdr_nav = tk.Frame(
            self, bg=SURFACE_COLOR_ALT, padx=10, pady=6,
            highlightbackground=BORDER_COLOR, highlightthickness=1,
        )
        self.hdr_nav.pack(fill=tk.X, padx=4, pady=(4, 0))

        self.btn_nav_root = ttk.Button(
            self.hdr_nav,
            text=_t("camp_studio_nav_root", default="🏰 Flusso Scene"),
            command=self.exit_to_campaign,
            style="Dark.TButton",
        )
        self.btn_nav_root.pack(side=tk.LEFT)

        self.lbl_nav_sep = tk.Label(self.hdr_nav, text="›", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)
        self.lbl_nav_scene = tk.Label(self.hdr_nav, text="", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD)
        self.lbl_nav_hint = tk.Label(self.hdr_nav, text="", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED)
        self.lbl_nav_hint.pack(side=tk.LEFT, padx=(10, 0))

        self.btn_toggle_drawer = ttk.Button(
            self.hdr_nav,
            text=_t("camp_studio_btn_drawer", default="📚 Entità & Fazioni ▾"),
            command=self.toggle_entity_drawer,
            style="Dark.TButton",
        )
        self.btn_toggle_drawer.pack(side=tk.RIGHT, padx=(6, 0))

        self.btn_enter_scene = ttk.Button(
            self.hdr_nav,
            text=_t("camp_studio_btn_enter", default="↳ Entra nella Scena"),
            command=self.enter_selected_or_first_scene,
            style="Gold.TButton",
        )
        self.btn_enter_scene.pack(side=tk.RIGHT, padx=4)

        self.btn_back_scenes = ttk.Button(
            self.hdr_nav,
            text=_t("camp_studio_btn_back", default="← Torna alle Scene"),
            command=self.exit_to_campaign,
            style="Primary.TButton",
        )

        # Main PanedWindow Orizzontale: Sinistra = Ispettore Visuale, Destra = Canvas + Drawer
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=BG_COLOR, sashrelief="flat", sashwidth=6)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # ===================================================================
        # COLONNA SINISTRA: Ispettore Contestuale Visuale Nodi & Connessioni
        # ===================================================================
        left_frame = tk.Frame(self.main_paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.main_paned.add(left_frame, minsize=340, width=410)

        hdr_left = tk.Frame(left_frame, bg=SURFACE_COLOR_ALT, padx=10, pady=6)
        hdr_left.pack(fill=tk.X)
        self.lbl_inspector_title = tk.Label(
            hdr_left,
            text=_t("camp_studio_inspector_title", default="🎛️ Ispettore Nodo & Connessioni"),
            font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD,
        )
        self.lbl_inspector_title.pack(side=tk.LEFT)
        self.lbl_inspector_scope = tk.Label(
            hdr_left,
            text=_t("camp_studio_inspector_sub", default="Modifica visiva proprietà, segreti e bivi"),
            font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED,
        )
        self.lbl_inspector_scope.pack(side=tk.RIGHT)

        # Corpo scrollabile dell'Ispettore
        insp_wrap = tk.Frame(left_frame, bg=SURFACE_COLOR)
        insp_wrap.pack(fill=tk.BOTH, expand=True)
        self.inspector_scroll_canvas = tk.Canvas(insp_wrap, bg=SURFACE_COLOR, highlightthickness=0)
        insp_sb = ttk.Scrollbar(insp_wrap, orient=tk.VERTICAL, command=self.inspector_scroll_canvas.yview)
        self.inspector_panel = tk.Frame(self.inspector_scroll_canvas, bg=SURFACE_COLOR, padx=10, pady=8)
        self._inspector_window_id = self.inspector_scroll_canvas.create_window(
            (0, 0), window=self.inspector_panel, anchor="nw"
        )
        self.inspector_scroll_canvas.configure(yscrollcommand=insp_sb.set)
        self.inspector_scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        insp_sb.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_insp_configure(_event=None):
            self.inspector_scroll_canvas.configure(scrollregion=self.inspector_scroll_canvas.bbox("all"))

        def _on_canvas_width(event):
            self.inspector_scroll_canvas.itemconfigure(self._inspector_window_id, width=max(300, event.width))

        self.inspector_panel.bind("<Configure>", _on_insp_configure)
        self.inspector_scroll_canvas.bind("<Configure>", _on_canvas_width)

        def _on_insp_wheel(event):
            first, last = self.inspector_scroll_canvas.yview()
            if first <= 0.0 and last >= 1.0:
                return
            delta = -1 if getattr(event, "delta", 0) > 0 or getattr(event, "num", None) == 4 else 1
            self.inspector_scroll_canvas.yview_scroll(delta, "units")

        def _bind_wheel(_e=None):
            self.inspector_scroll_canvas.bind_all("<MouseWheel>", _on_insp_wheel)
            self.inspector_scroll_canvas.bind_all("<Button-4>", _on_insp_wheel)
            self.inspector_scroll_canvas.bind_all("<Button-5>", _on_insp_wheel)

        def _unbind_wheel(_e=None):
            self.inspector_scroll_canvas.unbind_all("<MouseWheel>")
            self.inspector_scroll_canvas.unbind_all("<Button-4>")
            self.inspector_scroll_canvas.unbind_all("<Button-5>")

        insp_wrap.bind("<Enter>", _bind_wheel)
        insp_wrap.bind("<Leave>", _unbind_wheel)

        # ===================================================================
        # COLONNA DESTRA (VERTICALE): Tavolozza + Flow Canvas | Drawer Entità
        # ===================================================================
        self.right_paned = tk.PanedWindow(self.main_paned, orient=tk.VERTICAL, bg=BG_COLOR, sashrelief="flat", sashwidth=6)
        self.main_paned.add(self.right_paned, minsize=480)

        right_top = tk.Frame(self.right_paned, bg=SURFACE_COLOR, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.right_paned.add(right_top, minsize=270, height=410)

        hdr_right = tk.Frame(right_top, bg=SURFACE_COLOR_ALT, padx=10, pady=5)
        hdr_right.pack(fill=tk.X)
        self.lbl_canvas_title = tk.Label(
            hdr_right,
            text=_t("camp_studio_canvas_title", default="🧭 Flow Canvas • Grafo Visuale"),
            font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD,
        )
        self.lbl_canvas_title.pack(side=tk.LEFT)

        self.lbl_stats = tk.Label(hdr_right, text="", font=FONT_BADGE, bg=SURFACE_COLOR, fg=ACCENT_GOLD, padx=8, pady=2)
        self.lbl_stats.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            hdr_right,
            text=_t("camp_studio_btn_refresh_flow", default="⟳ Riordina Layout"),
            command=self.rearrange_flow_layout,
            style="Gold.TButton",
        ).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(
            hdr_right,
            text=_t("camp_studio_btn_center", default="🔍 Centra Vista"),
            command=self.center_canvas,
            style="Dark.TButton",
        ).pack(side=tk.RIGHT, padx=4)

        # Tavolozza Blocchi Visuali (Macro Scene / Micro Scena Interna)
        self.block_toolbar = tk.Frame(
            right_top, bg=SURFACE_COLOR, padx=8, pady=5,
            highlightbackground=BORDER_COLOR, highlightthickness=1,
        )
        self.block_toolbar.pack(fill=tk.X)

        self.toolbar_macro = tk.Frame(self.block_toolbar, bg=SURFACE_COLOR)
        ttk.Button(
            self.toolbar_macro,
            text=_t("camp_studio_btn_scene", default="🗺️ + Scena"),
            style="Dark.TButton",
            command=lambda: self.add_block("scene"),
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            self.toolbar_macro,
            text=_t("camp_studio_btn_branch", default="🔀 + Bivio ->"),
            style="Dark.TButton",
            command=lambda: self.add_block("branch"),
        ).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            self.toolbar_macro,
            text="📢 + Spunto",
            style="Dark.TButton",
            command=lambda: self.add_block("hook"),
        ).pack(side=tk.LEFT, padx=2)

        self.toolbar_scene = tk.Frame(self.block_toolbar, bg=SURFACE_COLOR)
        row_blocks = tk.Frame(self.toolbar_scene, bg=SURFACE_COLOR)
        row_blocks.pack(fill=tk.X, pady=(0, 3))
        ttk.Button(row_blocks, text=_t("camp_studio_btn_encounter", default="⚔️ + Incontro"), style="Dark.TButton", command=lambda: self.add_block("encounter")).pack(side=tk.LEFT, padx=(0, 3), fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_check", default="🎲 + Prova"), style="Dark.TButton", command=lambda: self.add_block("check")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_trap", default="⚠️ + Trappola"), style="Dark.TButton", command=lambda: self.add_block("trap")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text=_t("camp_studio_btn_loot", default="💎 + Tesoro"), style="Dark.TButton", command=lambda: self.add_block("loot")).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        ttk.Button(row_blocks, text="👤 + PNG", style="Dark.TButton", command=lambda: self.add_block("npc")).pack(side=tk.LEFT, padx=(2, 0), fill=tk.X, expand=True)

        row_flow = tk.Frame(self.toolbar_scene, bg=SURFACE_COLOR)
        row_flow.pack(fill=tk.X)
        ttk.Button(row_flow, text=_t("camp_studio_btn_comp_loot", default="📖 + Loot Compendio"), command=self.open_compendium_loot_picker, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 3), fill=tk.X, expand=True)
        ttk.Button(row_flow, text=_t("camp_studio_btn_exit", default="🚪 + Uscita Scena"), style="Dark.TButton", command=lambda: self.add_block("exit")).pack(side=tk.LEFT, padx=2)
        ttk.Button(row_flow, text=_t("camp_studio_btn_branch", default="🔀 + Bivio ->"), style="Dark.TButton", command=lambda: self.add_block("branch")).pack(side=tk.LEFT, padx=2)

        mb_blocks = ttk.Menubutton(row_flow, text=_t("camp_studio_btn_other_blocks", default="Altri Blocchi ▾"))
        menu_blocks = tk.Menu(mb_blocks, tearoff=0, bg=SURFACE_COLOR, fg=TEXT_COLOR)
        menu_blocks.add_command(label="🏬 Emporio", command=lambda: self.add_block("shop"))
        menu_blocks.add_command(label="🧩 Enigma", command=lambda: self.add_block("puzzle"))
        menu_blocks.add_command(label="⛺ Riposo", command=lambda: self.add_block("rest"))
        menu_blocks.add_command(label="📜 Documento / Handout", command=lambda: self.add_block("lore"))
        menu_blocks.add_command(label="⏳ Evento", command=lambda: self.add_block("event"))
        menu_blocks.add_command(label="🏆 Quest", command=lambda: self.add_block("quest"))
        menu_blocks.add_command(label="📢 Spunto Narrativo", command=lambda: self.add_block("hook"))
        menu_blocks.add_command(label="⚡ Fuori Pista", command=lambda: self.add_block("off_track"))
        menu_blocks.add_command(label="📝 Nota Narrativa", command=lambda: self.add_block("note"))
        mb_blocks["menu"] = menu_blocks
        mb_blocks.pack(side=tk.LEFT, padx=(2, 0))

        # Barra Ispettore Rapida sopra il Canvas
        self.inspector_bar = tk.Frame(right_top, bg="#1C2026", padx=10, pady=4, highlightbackground=BORDER_COLOR, highlightthickness=1)
        self.inspector_bar.pack(fill=tk.X)
        self.lbl_inspected_node = tk.Label(
            self.inspector_bar,
            text="Seleziona un nodo o una connessione sul grafo (doppio clic su una Scena per aprirla)",
            font=FONT_SMALL, bg="#1C2026", fg=TEXT_MUTED, anchor="w",
        )
        self.lbl_inspected_node.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.inspector_actions_box = tk.Frame(self.inspector_bar, bg="#1C2026")
        self.inspector_actions_box.pack(side=tk.RIGHT)

        self.flow_canvas = FlowCanvas(
            right_top,
            graph=self.graph,
            on_change_callback=self._on_canvas_modified,
            on_node_drilldown_callback=self._on_node_drilldown,
            on_select_callback=self._on_canvas_node_selected,
            on_edge_select_callback=self._on_canvas_edge_selected,
        )
        self.flow_canvas.pack(fill=tk.BOTH, expand=True)

        # Drawer Collassabile Inferiore per Entità Campagna & Fazioni
        self.entity_drawer_frame = tk.Frame(
            self.right_paned, bg=SURFACE_COLOR,
            highlightbackground=BORDER_COLOR, highlightthickness=1,
        )
        self.right_paned.add(self.entity_drawer_frame, minsize=160, height=230)

        self.entity_notebook = ttk.Notebook(self.entity_drawer_frame)
        self.entity_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.tab_scenes_frame = ttk.Frame(self.entity_notebook, padding=6)
        self.tab_encounters_frame = ttk.Frame(self.entity_notebook, padding=6)
        self.tab_quests_frame = ttk.Frame(self.entity_notebook, padding=6)
        self.tab_npcs_factions_frame = ttk.Frame(self.entity_notebook, padding=6)
        self.tab_handouts_frame = ttk.Frame(self.entity_notebook, padding=6)

        self.entity_notebook.add(self.tab_scenes_frame, text=_t("camp_tab_scenes", default="🗺️ Scene & Mappe"))
        self.entity_notebook.add(self.tab_encounters_frame, text=_t("camp_tab_encounters", default="⚔️ Incontri Tattici"))
        self.entity_notebook.add(self.tab_quests_frame, text=_t("camp_tab_quests", default="📖 Trame & Missioni"))
        self.entity_notebook.add(self.tab_npcs_factions_frame, text=_t("camp_tab_npcs", default="🎭 PNG & Fazioni"))
        self.entity_notebook.add(self.tab_handouts_frame, text=_t("camp_tab_handouts", default="📜 Handouts & Indizi"))

    # -----------------------------------------------------------------------
    # NAVIGAZIONE GERARCHICA (LIVELLO 1 SCENA MACRO <-> LIVELLO 2 SUB-FLUSSO)
    # -----------------------------------------------------------------------

    def _update_level_chrome(self) -> None:
        """Aggiorna breadcrumb, tavolozza blocchi, filtro canvas e stato bottoni."""
        in_scene = self.active_scene_name is not None
        self.toolbar_macro.pack_forget()
        self.toolbar_scene.pack_forget()

        if in_scene:
            self.toolbar_scene.pack(fill=tk.X)
            self.flow_canvas.allowed_node_types = None
            self.btn_nav_root.config(style="Dark.TButton")
            if not self.lbl_nav_sep.winfo_manager():
                self.lbl_nav_sep.pack(side=tk.LEFT, padx=6, after=self.btn_nav_root)
            if not self.lbl_nav_scene.winfo_manager():
                self.lbl_nav_scene.pack(side=tk.LEFT, after=self.lbl_nav_sep)
            self.lbl_nav_scene.config(text=f"🗺️ {self.active_scene_name}")
            sc_entry = self.campaign.get_scene_by_name(self.active_scene_name) or {}
            map_name = sc_entry.get("map_file", "maps/faerun.json")
            self.lbl_nav_hint.pack_forget()
            self.lbl_nav_hint.config(text=f"({map_name})")
            self.lbl_nav_hint.pack(side=tk.LEFT, padx=(8, 0), after=self.lbl_nav_scene)
            self.btn_enter_scene.pack_forget()
            self.btn_back_scenes.pack(side=tk.RIGHT, padx=4)
            self.lbl_inspector_title.config(text=f"🎛️ Ispettore • {self.active_scene_name}")
            self.lbl_inspector_scope.config(text="Incontri, PNG, Prove, Uscite")
            self.lbl_canvas_title.config(text=f"🧭 Flusso Interno • {self.active_scene_name}")
        else:
            self.toolbar_macro.pack(fill=tk.X)
            self.flow_canvas.allowed_node_types = ["scene"]
            self.lbl_nav_sep.pack_forget()
            self.lbl_nav_scene.pack_forget()
            self.lbl_nav_hint.pack_forget()
            self.lbl_nav_hint.config(text=_t("camp_studio_hint_macro", default="Doppio clic su una Scena o 'Entra' per il flusso interno"))
            self.lbl_nav_hint.pack(side=tk.LEFT, padx=(10, 0), after=self.btn_nav_root)
            self.btn_back_scenes.pack_forget()
            if not self.btn_enter_scene.winfo_manager():
                self.btn_enter_scene.pack(side=tk.RIGHT, padx=4)
            self.lbl_inspector_title.config(text=_t("camp_studio_inspector_title", default="🎛️ Ispettore Nodo & Connessioni"))
            self.lbl_inspector_scope.config(text="Scene & Collegamenti")
            self.lbl_canvas_title.config(text=_t("camp_studio_canvas_title", default="🧭 Flow Canvas • Grafo Visuale"))

        self._refresh_inspector_selection()

    def _refresh_subflow_badges_on_macro(self) -> None:
        """Aggiorna i conteggi di riepilogo su tutti i nodi scena del grafo macro attivo."""
        if self.active_scene_name is not None:
            return
        for node in self.graph.nodes.values():
            if node.node_type == "scene":
                sc_entry = self.campaign.get_scene_by_name(node.title)
                if sc_entry:
                    summary = summarize_subflow(get_scene_subflow_graph(sc_entry))
                    node.data["subflow_summary"] = summary
                    node.data["subflow_summary_text"] = summary.get("summary_text", "")

    def _load_active_level_into_views(self, sync_campaign: bool = False) -> None:
        """Carica il FlowGraph corrispondente al livello corrente (Campagna o Scena)."""
        self._cancel_inspector_apply()
        self.flow_canvas.selected_node_id = None
        self.flow_canvas.selected_edge_index = None

        if self.active_scene_name is None:
            raw_fg = getattr(self.campaign, "flow_graph", None)
            self.graph = FlowGraph.from_dict(raw_fg) if isinstance(raw_fg, dict) else FlowGraph()
            self._refresh_subflow_badges_on_macro()
        else:
            sc_entry = self.campaign.ensure_scene_entry(self.active_scene_name)
            self.graph = get_scene_subflow_graph(sc_entry)

        self.flow_canvas.set_graph(self.graph)
        self.lbl_stats.config(text=f"Nodi: {len(self.graph.nodes)} | Connessioni: {len(self.graph.edges)}")
        self._update_level_chrome()
        if sync_campaign:
            self._save_to_campaign()

    def _on_node_drilldown(self, node: FlowNode) -> None:
        if node.node_type == "scene":
            self.enter_scene(node.title)

    def _on_canvas_node_selected(self, node: Optional[FlowNode]) -> None:
        if self._inspector_node_id and self._inspector_node_id != (node.id if node else None):
            self._commit_inspector_edits()
        self._refresh_inspector_bar(node, edge_idx=None)
        if node is not None:
            self._build_node_inspector(node)
        elif getattr(self.flow_canvas, "selected_edge_index", None) is None:
            self._build_empty_inspector()

    def _on_canvas_edge_selected(self, edge_idx: Optional[int]) -> None:
        if self._inspector_node_id is not None or (
            self._inspector_edge_idx is not None and self._inspector_edge_idx != edge_idx
        ):
            self._commit_inspector_edits()
        if edge_idx is not None and 0 <= edge_idx < len(self.graph.edges):
            self._refresh_inspector_bar(None, edge_idx=edge_idx)
            self._build_edge_inspector(edge_idx)
        elif getattr(self.flow_canvas, "selected_node_id", None) is None:
            self._refresh_inspector_bar(None, edge_idx=None)
            self._build_empty_inspector()

    def _refresh_inspector_selection(self) -> None:
        sel_id = getattr(self.flow_canvas, "selected_node_id", None)
        sel_edge = getattr(self.flow_canvas, "selected_edge_index", None)
        sel_node = self.graph.nodes.get(sel_id) if sel_id else None
        if sel_node is not None:
            self._refresh_inspector_bar(sel_node, edge_idx=None)
            self._build_node_inspector(sel_node)
        elif sel_edge is not None and 0 <= sel_edge < len(self.graph.edges):
            self._refresh_inspector_bar(None, edge_idx=sel_edge)
            self._build_edge_inspector(sel_edge)
        else:
            self._refresh_inspector_bar(None, edge_idx=None)
            self._build_empty_inspector()

    def _refresh_inspector_bar(self, node: Optional[FlowNode], edge_idx: Optional[int] = None) -> None:
        for w in self.inspector_actions_box.winfo_children():
            w.destroy()

        if edge_idx is not None and 0 <= edge_idx < len(self.graph.edges):
            edge = self.graph.edges[edge_idx]
            src = self.graph.nodes.get(edge.from_id)
            dst = self.graph.nodes.get(edge.to_id)
            src_name = src.title if src else edge.from_id
            dst_name = dst.title if dst else edge.to_id
            cond_meta = EDGE_CONDITIONS.get(edge.condition_type, EDGE_CONDITIONS["default"])
            self.lbl_inspected_node.config(
                text=f"{cond_meta['icon']} Connessione: {src_name}  →  {dst_name}",
                fg=ACCENT_GOLD,
            )
            ttk.Button(
                self.inspector_actions_box,
                text="🗑️ Elimina Connessione",
                command=lambda idx=edge_idx: self._delete_edge_from_inspector(idx),
                style="Danger.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))
            return

        if node is None:
            hint = (
                "Seleziona un nodo interno o aggiungine uno dalla tavolozza sopra"
                if self.active_scene_name
                else "Seleziona una Scena (doppio clic per aprire il flusso interno)"
            )
            self.lbl_inspected_node.config(text=hint, fg=TEXT_MUTED)
            return

        icon = NODE_TYPES.get(node.node_type, {}).get("icon", "•")
        self.lbl_inspected_node.config(text=f"{icon} {node.title}", fg=ACCENT_GOLD)

        if node.node_type == "scene" and self.active_scene_name is None:
            ttk.Button(
                self.inspector_actions_box,
                text="↳ Apri Flusso",
                command=lambda n=node: self.enter_scene(n.title),
                style="Gold.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))
        elif node.node_type == "exit":
            dest = str(node.data.get("target_scene") or node.title).strip()
            ttk.Button(
                self.inspector_actions_box,
                text=f"↳ Vai a '{dest[:18]}'",
                command=lambda d=dest: self.enter_scene(d),
                style="Gold.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))

        if self.on_inspect_callback and node.node_type in ("scene", "encounter", "npc", "quest", "lore"):
            btn_lbl = {
                "scene": "🗺️ Gestisci Mappa",
                "encounter": "⚔️ Editor Mostri",
                "npc": "👤 Scheda PNG",
                "quest": "🏆 Dettagli Quest",
                "lore": "📜 Handout",
            }.get(node.node_type, "✏️ Dettagli")
            ttk.Button(
                self.inspector_actions_box,
                text=btn_lbl,
                command=lambda n=node: self.on_inspect_callback(n.node_type, n),
                style="Dark.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))

    # -----------------------------------------------------------------------
    # ISPETTORE CONTESTUALE VISUALE (SINISTRA)
    # -----------------------------------------------------------------------

    def _clear_inspector_panel(self) -> None:
        self._cancel_inspector_apply()
        self._inspector_node_id = None
        self._inspector_edge_idx = None
        self._inspector_widgets.clear()
        for w in self.inspector_panel.winfo_children():
            w.destroy()

    def _cancel_inspector_apply(self) -> None:
        job = getattr(self, "_inspector_apply_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._inspector_apply_job = None

    def _schedule_inspector_apply(self) -> None:
        if self._inspector_building:
            return
        self._cancel_inspector_apply()
        self._inspector_apply_job = self.after(220, self._commit_inspector_edits)

    def _commit_inspector_edits(self) -> None:
        """Applica le modifiche correnti dell'Ispettore Visuale al nodo o all'arco selezionato."""
        self._cancel_inspector_apply()
        if self._inspector_building or not self._inspector_widgets:
            return

        if self._inspector_node_id and self._inspector_node_id in self.graph.nodes:
            node = self.graph.nodes[self._inspector_node_id]
            changed = False

            ent_title = self._inspector_widgets.get("_title")
            if ent_title is not None and ent_title.winfo_exists():
                new_title = ent_title.get().strip() or node.title or "Senza Titolo"
                if new_title != node.title:
                    node.title = new_title
                    changed = True

            combo_type = self._inspector_widgets.get("_node_type")
            if combo_type is not None and combo_type.winfo_exists():
                new_type = combo_type.get().strip()
                if new_type in NODE_TYPES and new_type != node.node_type:
                    node.node_type = new_type
                    changed = True

            txt_ra = self._inspector_widgets.get("_read_aloud")
            if txt_ra is not None and txt_ra.winfo_exists():
                ra_val = txt_ra.get("1.0", tk.END).strip()
                if ra_val != str(node.data.get("read_aloud", "") or ""):
                    if ra_val:
                        node.data["read_aloud"] = ra_val
                    else:
                        node.data.pop("read_aloud", None)
                    changed = True

            for key, spec_meta in self._inspector_widgets.get("_fields", {}).items():
                kind, widget = spec_meta
                if not widget.winfo_exists():
                    continue
                if kind == "multiline":
                    raw_lines = [ln.strip() for ln in widget.get("1.0", tk.END).splitlines() if ln.strip()]
                    if node.data.get(key) != raw_lines:
                        node.data[key] = raw_lines
                        changed = True
                elif kind == "monsters":
                    raw_val = widget.get().strip()
                    parsed_monsters = _parse_monsters_text(raw_val)
                    if node.data.get("monsters") != parsed_monsters:
                        node.data["monsters"] = parsed_monsters
                        changed = True
                elif kind == "loot_items":
                    raw_val = widget.get().strip()
                    items = [i.strip().strip('"\'') for i in raw_val.split(",") if i.strip()]
                    if node.data.get(key) != items:
                        node.data[key] = items
                        node.data["resolved_items"] = [resolve_compendium_item(it) for it in items]
                        changed = True
                elif kind == "loot_str":
                    raw_val = widget.get().strip()
                    if str(node.data.get(key, "") or "") != raw_val:
                        node.data[key] = raw_val
                        parsed = parse_loot_specification(raw_val)
                        node.data["loot_currency"] = parsed["currency"]
                        node.data["loot_items"] = parsed["items"]
                        changed = True
                elif kind == "int":
                    raw_val = widget.get().strip()
                    try:
                        int_val = int(raw_val)
                    except ValueError:
                        int_val = node.data.get(key, 0)
                    if node.data.get(key) != int_val:
                        node.data[key] = int_val
                        changed = True
                else:
                    raw_val = widget.get().strip()
                    if str(node.data.get(key, "") or "") != raw_val:
                        if raw_val:
                            node.data[key] = raw_val
                        else:
                            node.data.pop(key, None)
                        if key == "target_scene" and node.node_type == "exit" and raw_val and not ent_title.get().strip():
                            node.title = raw_val
                        changed = True

            # Eventuale segreto digitato ma non ancora aggiunto col pulsante '+'
            p_form = self._inspector_widgets.get("_pending_secret_form")
            if p_form:
                ent_txt = p_form.get("txt_entry")
                if ent_txt is not None and ent_txt.winfo_exists():
                    sec_type, sec_chk, sec_txt = p_form["get_data"]()
                    if sec_txt:
                        node.data.setdefault("secrets", []).append({
                            "type": sec_type,
                            "check": sec_chk,
                            "text": sec_txt,
                        })
                        p_form["reset"]()
                        if hasattr(self, "_secrets_refresh_fn") and callable(self._secrets_refresh_fn):
                            self._secrets_refresh_fn()
                        changed = True

            if changed:
                self._save_to_campaign()
                self._refresh_inspector_bar(node, edge_idx=None)

        elif self._inspector_edge_idx is not None and 0 <= self._inspector_edge_idx < len(self.graph.edges):
            edge = self.graph.edges[self._inspector_edge_idx]
            changed = False
            w_cond = self._inspector_widgets.get("_edge_cond")
            w_val = self._inspector_widgets.get("_edge_val")
            w_lbl = self._inspector_widgets.get("_edge_lbl")
            if w_cond is not None and w_cond.winfo_exists():
                new_cond = w_cond.get().strip() or "default"
                if new_cond in EDGE_CONDITIONS and edge.condition_type != new_cond:
                    edge.condition_type = new_cond
                    changed = True
            if w_val is not None and w_val.winfo_exists():
                new_val = w_val.get().strip()
                if edge.condition_value != new_val:
                    edge.condition_value = new_val
                    changed = True
            if w_lbl is not None and w_lbl.winfo_exists():
                new_lbl = w_lbl.get().strip()
                if edge.label != new_lbl:
                    edge.label = new_lbl
                    changed = True
            if changed:
                self._save_to_campaign()
                self._refresh_inspector_bar(None, edge_idx=self._inspector_edge_idx)

    def _build_empty_inspector(self) -> None:
        self._clear_inspector_panel()
        box = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR_ALT, padx=12, pady=14, highlightbackground=BORDER_COLOR, highlightthickness=1)
        box.pack(fill=tk.X, pady=(6, 10))
        level_title = f"Scena: {self.active_scene_name}" if self.active_scene_name else "Macro-Flusso Campagna"
        tk.Label(box, text=f"🧭 {level_title}", font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=ACCENT_GOLD).pack(anchor="w")
        tk.Label(
            box,
            text=(
                "Seleziona un nodo o una connessione sul Flow Canvas per modificarne visivamente titolo, narrazione, "
                "parametri, segreti e condizioni di bivio.\n\n"
                "• Trascina dalla porta destra (●) di un nodo a un altro per creare una connessione.\n"
                "• Clicca una connessione per impostare Successo, Fallimento, Prove CD o Oggetti richiesti.\n"
                "• Doppio clic su una Scena per entrare nel suo flusso interno."
            ),
            font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED, justify="left", wraplength=330,
        ).pack(anchor="w", pady=(8, 0))

    def _build_node_inspector(self, node: FlowNode) -> None:
        self._clear_inspector_panel()
        self._inspector_building = True
        try:
            self._inspector_node_id = node.id
            type_info = NODE_TYPES.get(node.node_type, NODE_TYPES["note"])
            fields_map: Dict[str, Tuple[str, Any]] = {}
            self._inspector_widgets["_fields"] = fields_map

            # --- Intestazione Tipo & Titolo ---
            hdr = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR_ALT, padx=8, pady=6, highlightbackground=BORDER_COLOR, highlightthickness=1)
            hdr.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                hdr,
                text=f"{type_info['icon']} {type_info['label'].upper()}  •  ID: {node.id}",
                font=FONT_BADGE, bg=SURFACE_COLOR_ALT, fg=type_info["color"],
            ).pack(anchor="w")

            tk.Label(self.inspector_panel, text="Titolo del Nodo:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            ent_title = ttk.Entry(self.inspector_panel, font=FONT_MAIN)
            ent_title.insert(0, node.title)
            ent_title.pack(fill=tk.X, pady=(2, 8))
            ent_title.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
            ent_title.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            self._inspector_widgets["_title"] = ent_title

            tk.Label(self.inspector_panel, text="Tipo Blocco:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            combo_type = ttk.Combobox(self.inspector_panel, values=list(NODE_TYPES.keys()), state="readonly")
            combo_type.set(node.node_type if node.node_type in NODE_TYPES else "note")
            combo_type.pack(fill=tk.X, pady=(2, 8))

            def _on_type_changed(_e=None):
                self._commit_inspector_edits()
                refreshed = self.graph.nodes.get(node.id)
                if refreshed:
                    self._build_node_inspector(refreshed)

            combo_type.bind("<<ComboboxSelected>>", _on_type_changed)
            self._inspector_widgets["_node_type"] = combo_type

            # --- Testo da Leggere / Descrizione ---
            tk.Label(self.inspector_panel, text="Narrazione / Descrizione (Read-Aloud):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            txt_ra = tk.Text(
                self.inspector_panel, height=4, bg="#16181C", fg=TEXT_COLOR,
                insertbackground=ACCENT_GOLD, font=FONT_MAIN, relief="flat",
                highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD,
            )
            txt_ra.insert("1.0", str(node.data.get("read_aloud", "") or ""))
            txt_ra.pack(fill=tk.X, pady=(2, 8))
            txt_ra.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
            txt_ra.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            self._inspector_widgets["_read_aloud"] = txt_ra

            # --- Campi Tipizzati Contestuali ---
            specs = _NODE_FIELD_SPECS.get(node.node_type, [])
            if specs:
                sec_lbl = tk.Label(self.inspector_panel, text="⚙️ Proprietà Specifiche", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD)
                sec_lbl.pack(anchor="w", pady=(4, 4))
                for key, lbl, kind, extra in specs:
                    fields_map[key] = (kind, self._render_typed_field(node, key, lbl, kind, extra))

            # --- Segreti & Prove Nascoste del DM ---
            self._build_secrets_section(node)

            # --- Connessioni in Uscita & Aggiunta Rapida Bivio ---
            self._build_outgoing_edges_section(node)

            # --- Azioni Nodo ---
            act_row = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR)
            act_row.pack(fill=tk.X, pady=(10, 4))
            ttk.Button(
                act_row,
                text="🗑️ Elimina Nodo",
                command=lambda nid=node.id: self._delete_node_from_inspector(nid),
                style="Danger.TButton",
            ).pack(side=tk.LEFT)
            ttk.Button(
                act_row,
                text="✓ Applica Ora",
                command=self._commit_inspector_edits,
                style="Gold.TButton",
            ).pack(side=tk.RIGHT)
        finally:
            self._inspector_building = False

    def _render_typed_field(self, node: FlowNode, key: str, label: str, kind: str, extra: Any) -> Any:
        tk.Label(self.inspector_panel, text=f"{label}:", font=FONT_SMALL, bg=SURFACE_COLOR, fg=TEXT_MUTED).pack(anchor="w")

        if kind == "multiline":
            txt = tk.Text(
                self.inspector_panel, height=3, bg="#16181C", fg=TEXT_COLOR,
                insertbackground=ACCENT_GOLD, font=FONT_MAIN, relief="flat",
                highlightbackground=BORDER_COLOR, highlightthickness=1, wrap=tk.WORD,
            )
            cur = node.data.get(key, [])
            val_text = "\n".join(str(x) for x in cur) if isinstance(cur, list) else str(cur or "")
            txt.insert("1.0", val_text)
            txt.pack(fill=tk.X, pady=(1, 6))
            txt.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
            txt.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            return txt

        row = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR)
        row.pack(fill=tk.X, pady=(1, 6))

        if kind in ("combo", "readonly_combo", "scene_combo", "faction_combo"):
            values = list(extra or [])
            if kind == "scene_combo":
                values = [s.get("name", "") for s in getattr(self.campaign, "scenes", []) if s.get("name")]
            elif kind == "faction_combo":
                values = [f.get("name", "") for f in getattr(self.campaign, "factions", []) if f.get("name")]
            cur_val = str(node.data.get(key, "") or "")
            if cur_val and cur_val not in values:
                values.append(cur_val)
            cb_state = "readonly" if kind == "readonly_combo" else "normal"
            widget = ttk.Combobox(row, values=values, state=cb_state)
            widget.set(cur_val)
            widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
            widget.bind("<<ComboboxSelected>>", lambda _e: self._commit_inspector_edits())
            if cb_state != "readonly":
                widget.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
                widget.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            if kind == "scene_combo":
                ttk.Button(
                    row,
                    text="↳ Vai",
                    command=lambda w=widget: self.enter_scene(w.get().strip()),
                    style="Dark.TButton",
                ).pack(side=tk.RIGHT, padx=(4, 0))
            return widget

        widget = ttk.Entry(row, font=FONT_MAIN)
        if kind == "monsters":
            widget.insert(0, _format_monsters_text(node.data.get("monsters", [])))
        elif kind == "loot_items":
            cur = node.data.get(key, [])
            widget.insert(0, ", ".join(cur) if isinstance(cur, list) else str(cur or ""))
        elif kind == "int":
            widget.insert(0, str(node.data.get(key, extra if extra is not None else 0)))
        else:
            widget.insert(0, str(node.data.get(key, "") or ""))
        widget.pack(side=tk.LEFT, fill=tk.X, expand=True)
        widget.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
        widget.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())

        if kind in ("map", "handout_file"):
            def _pick_file(w=widget):
                path = filedialog.askopenfilename(parent=self)
                if path:
                    try:
                        rel = os.path.relpath(path, os.getcwd()).replace("\\", "/")
                    except Exception:
                        rel = path
                    w.delete(0, tk.END)
                    w.insert(0, rel)
                    self._commit_inspector_edits()
            ttk.Button(row, text="📁", width=3, command=_pick_file, style="Dark.TButton").pack(side=tk.RIGHT, padx=(4, 0))
        elif kind in ("loot_items", "loot_str"):
            ttk.Button(
                row,
                text="📖+",
                width=4,
                command=lambda w=widget: self._pick_compendium_into_entry(w),
                style="Gold.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))
        elif kind == "monsters" and self.on_inspect_callback:
            ttk.Button(
                row,
                text="⚔️",
                width=3,
                command=lambda n=node: self.on_inspect_callback("encounter", n),
                style="Dark.TButton",
            ).pack(side=tk.RIGHT, padx=(4, 0))

        return widget

    def _pick_compendium_into_entry(self, entry_widget: ttk.Entry) -> None:
        try:
            from server.compendium_ui import CompendiumDialog

            def _on_pick(item_data, _cat):
                name = (item_data.get("name") or item_data.get("title") or "").strip()
                if not name or not entry_widget.winfo_exists():
                    return
                cur = entry_widget.get().strip()
                entry_widget.delete(0, tk.END)
                entry_widget.insert(0, f"{cur}, {name}" if cur else name)
                self._commit_inspector_edits()

            dlg = CompendiumDialog(
                self.winfo_toplevel(),
                on_import_callback=_on_pick,
                is_dm=True,
                initial_category="Oggetti Magici",
                action_label="💎 Aggiungi al Nodo",
                allowed_categories=["Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici", "Equipaggiamento & Tesori"],
            )
            dlg.grab_set()
        except Exception:
            pass

    def _create_guided_secret_form(
        self,
        parent: tk.Widget,
        bg: str,
        init_type: str = "SEGRETO",
        init_check: str = "",
        init_text: str = "",
        on_submit: Optional[Callable[[], None]] = None,
        action_builder: Optional[Callable[[tk.Frame], None]] = None,
    ) -> Dict[str, Any]:
        """Costruisce controlli guidati condivisi (Tipo + Prova + CD + Indizio) per aggiunta e modifica."""
        r_type = tk.Frame(parent, bg=bg)
        r_type.pack(fill=tk.X, pady=(0, 3))
        tk.Label(r_type, text="Tipo:", font=FONT_SMALL, bg=bg, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))
        norm_type = str(init_type or "SEGRETO").strip().upper() or "SEGRETO"
        type_vals = list(_SECRET_TYPE_VALUES)
        if norm_type not in type_vals:
            type_vals.append(norm_type)
        cb_type = ttk.Combobox(r_type, values=type_vals, state="readonly", font=FONT_SMALL, width=13)
        cb_type.set(norm_type)
        cb_type.pack(side=tk.LEFT, fill=tk.X, expand=True)

        r_chk = tk.Frame(parent, bg=bg)
        r_chk.pack(fill=tk.X, pady=(0, 3))
        tk.Label(r_chk, text="Prova:", font=FONT_SMALL, bg=bg, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))
        init_ability, init_cd = _parse_secret_check(init_check)
        chk_vals = list(_SECRET_CHECK_VALUES)
        if init_ability not in chk_vals:
            chk_vals.append(init_ability)
        cb_chk = ttk.Combobox(r_chk, values=chk_vals, state="readonly", font=FONT_SMALL)
        cb_chk.set(init_ability)
        cb_chk.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        tk.Label(r_chk, text="CD:", font=FONT_SMALL, bg=bg, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 4))
        sp_cd = ttk.Spinbox(r_chk, from_=5, to=30, width=4, font=FONT_SMALL)
        sp_cd.pack(side=tk.LEFT)

        def _sync_cd_state(populate_default: bool = True) -> None:
            ab = cb_chk.get().strip()
            is_auto = not ab or ab == _SECRET_NO_CHECK_LABEL or ab.lower().startswith("nessuna")
            if is_auto:
                if not sp_cd.get().strip():
                    sp_cd.set("12")
                sp_cd.configure(state="disabled")
            else:
                sp_cd.configure(state="normal")
                if populate_default and not sp_cd.get().strip():
                    sp_cd.set("12")

        sp_cd.set(init_cd if init_cd else ("12" if init_ability == _SECRET_NO_CHECK_LABEL or init_ability in _SECRET_CHECK_VALUES else ""))
        _sync_cd_state(populate_default=False)
        cb_chk.bind("<<ComboboxSelected>>", lambda _e: _sync_cd_state(populate_default=(cb_chk.get().strip() in _SECRET_CHECK_VALUES)))

        r_txt = tk.Frame(parent, bg=bg)
        r_txt.pack(fill=tk.X)
        tk.Label(r_txt, text="Indizio:", font=FONT_SMALL, bg=bg, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))
        ent_txt = ttk.Entry(r_txt, font=FONT_SMALL)
        if init_text:
            ent_txt.insert(0, init_text)
        ent_txt.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        if action_builder:
            action_builder(r_txt)
        if on_submit:
            ent_txt.bind("<Return>", lambda _e: on_submit())
            sp_cd.bind("<Return>", lambda _e: on_submit())

        def _get_data() -> Tuple[str, str, str]:
            t_val = (cb_type.get().strip().upper() or "SEGRETO") if cb_type.winfo_exists() else "SEGRETO"
            ab_val = cb_chk.get().strip() if cb_chk.winfo_exists() else _SECRET_NO_CHECK_LABEL
            cd_val = sp_cd.get().strip() if sp_cd.winfo_exists() else ""
            txt_val = ent_txt.get().strip() if ent_txt.winfo_exists() else ""
            return t_val, _format_secret_check(ab_val, cd_val), txt_val

        def _reset() -> None:
            if cb_type.winfo_exists():
                cb_type.set("SEGRETO")
            if cb_chk.winfo_exists():
                cb_chk.set(_SECRET_NO_CHECK_LABEL)
            if sp_cd.winfo_exists():
                sp_cd.configure(state="normal")
                sp_cd.set("12")
                sp_cd.configure(state="disabled")
            if ent_txt.winfo_exists():
                ent_txt.delete(0, tk.END)

        return {
            "type_combo": cb_type,
            "check_combo": cb_chk,
            "cd_spin": sp_cd,
            "txt_entry": ent_txt,
            "get_data": _get_data,
            "reset": _reset,
        }

    def _build_secrets_section(self, node: FlowNode) -> None:
        tk.Label(self.inspector_panel, text="🗝️ Segreti & Indizi DM", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(6, 3))
        sec_box = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR_ALT, padx=8, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
        sec_box.pack(fill=tk.X, pady=(0, 6))

        list_container = tk.Frame(sec_box, bg=SURFACE_COLOR_ALT)
        list_container.pack(fill=tk.X)
        editing_state: Dict[str, Optional[int]] = {"idx": None}

        def _render_secrets_list() -> None:
            for w in list_container.winfo_children():
                w.destroy()
            secrets = node.data.get("secrets")
            if not isinstance(secrets, list) or not secrets:
                tk.Label(list_container, text="Nessun segreto configurato.", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(anchor="w")
                return

            for idx, sec in enumerate(secrets):
                sec_type = str(sec.get("type", "SEGRETO") or "SEGRETO").strip().upper() if isinstance(sec, dict) else "SEGRETO"
                chk_val = str(sec.get("check", "") or "").strip() if isinstance(sec, dict) else ""
                txt_val = str(sec.get("text", "") or "").strip() if isinstance(sec, dict) else str(sec)

                if editing_state["idx"] == idx:
                    ed_box = tk.Frame(list_container, bg=SURFACE_COLOR, padx=6, pady=6, highlightbackground=ACCENT_GOLD, highlightthickness=1)
                    ed_box.pack(fill=tk.X, pady=2)
                    edit_ref: Dict[str, Any] = {}

                    def _save_edit(i=idx):
                        form = edit_ref.get("form")
                        if not form:
                            return
                        new_type, new_c, new_t = form["get_data"]()
                        if not new_t:
                            return
                        cur_list = list(node.data.get("secrets") or [])
                        if 0 <= i < len(cur_list):
                            cur_list[i] = {"type": new_type, "check": new_c, "text": new_t}
                            node.data["secrets"] = cur_list
                        editing_state["idx"] = None
                        self._commit_inspector_edits()
                        self._save_to_campaign()
                        _render_secrets_list()

                    def _cancel_edit():
                        editing_state["idx"] = None
                        _render_secrets_list()

                    def _edit_btns(row_w: tk.Frame) -> None:
                        ttk.Button(row_w, text="✓", width=3, command=_save_edit, style="Gold.TButton").pack(side=tk.LEFT, padx=(0, 2))
                        ttk.Button(row_w, text="✕", width=3, command=_cancel_edit, style="Dark.TButton").pack(side=tk.LEFT)

                    edit_ref["form"] = self._create_guided_secret_form(
                        ed_box,
                        bg=SURFACE_COLOR,
                        init_type=sec_type,
                        init_check=chk_val,
                        init_text=txt_val,
                        on_submit=_save_edit,
                        action_builder=_edit_btns,
                    )
                    continue

                s_row = tk.Frame(list_container, bg=SURFACE_COLOR_ALT)
                s_row.pack(fill=tk.X, pady=2)
                meta_lbl = f"{sec_type} · {chk_val}" if chk_val else sec_type
                disp = f"[{meta_lbl}] {txt_val}"
                tk.Label(s_row, text=f"• {disp}", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, wraplength=255, justify="left", anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

                def _start_edit(i=idx):
                    editing_state["idx"] = i
                    _render_secrets_list()

                ttk.Button(s_row, text="×", width=2, command=lambda i=idx: _remove_sec(i), style="Dark.TButton").pack(side=tk.RIGHT, padx=(2, 0))
                ttk.Button(s_row, text="✏️", width=3, command=_start_edit, style="Dark.TButton").pack(side=tk.RIGHT)

        def _remove_sec(idx: int) -> None:
            if editing_state["idx"] == idx:
                editing_state["idx"] = None
            self._remove_node_secret(node, idx)

        self._secrets_refresh_fn = _render_secrets_list
        _render_secrets_list()

        # Form guidato condiviso (Tipo + Prova + CD + Indizio)
        form_box = tk.Frame(sec_box, bg=SURFACE_COLOR_ALT)
        form_box.pack(fill=tk.X, pady=(6, 0))
        add_ref: Dict[str, Any] = {}

        def _add_sec(_event=None):
            form = add_ref.get("form")
            if not form:
                return
            sec_type, chk, txt = form["get_data"]()
            if not txt:
                return
            form["reset"]()
            node.data.setdefault("secrets", []).append({"type": sec_type, "check": chk, "text": txt})
            self._commit_inspector_edits()
            self._save_to_campaign()
            _render_secrets_list()

        def _add_btn(row_w: tk.Frame) -> None:
            ttk.Button(row_w, text="+ Aggiungi", command=_add_sec, style="Gold.TButton").pack(side=tk.RIGHT)

        add_form = self._create_guided_secret_form(
            form_box,
            bg=SURFACE_COLOR_ALT,
            on_submit=_add_sec,
            action_builder=_add_btn,
        )
        add_ref["form"] = add_form
        self._inspector_widgets["_pending_secret_form"] = add_form

    def _remove_node_secret(self, node: FlowNode, idx: int) -> None:
        secrets = node.data.get("secrets", [])
        if isinstance(secrets, list) and 0 <= idx < len(secrets):
            secrets.pop(idx)
            if not secrets:
                node.data.pop("secrets", None)
            self._save_to_campaign()
            if hasattr(self, "_secrets_refresh_fn") and callable(self._secrets_refresh_fn):
                self._secrets_refresh_fn()
            else:
                self._build_node_inspector(node)

    def _build_outgoing_edges_section(self, node: FlowNode) -> None:
        tk.Label(self.inspector_panel, text="🔀 Bivi & Connessioni in Uscita", font=FONT_BOLD, bg=SURFACE_COLOR, fg=ACCENT_GOLD).pack(anchor="w", pady=(6, 3))
        edge_box = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR_ALT, padx=6, pady=6, highlightbackground=BORDER_COLOR, highlightthickness=1)
        edge_box.pack(fill=tk.X, pady=(0, 6))

        outgoing = [(idx, e) for idx, e in enumerate(self.graph.edges) if e.from_id == node.id]
        if not outgoing:
            tk.Label(edge_box, text="Nessuna connessione in uscita.", font=FONT_SMALL, bg=SURFACE_COLOR_ALT, fg=TEXT_MUTED).pack(anchor="w")
        else:
            for e_idx, edge in outgoing:
                dst = self.graph.nodes.get(edge.to_id)
                dst_title = dst.title if dst else edge.to_id
                cond_meta = EDGE_CONDITIONS.get(edge.condition_type, EDGE_CONDITIONS["default"])
                lbl_extra = f": {edge.label}" if edge.label else (f" [{edge.condition_value}]" if edge.condition_value else "")
                row = tk.Frame(edge_box, bg=SURFACE_COLOR_ALT)
                row.pack(fill=tk.X, pady=1)
                ttk.Button(
                    row,
                    text=f"{cond_meta['icon']}{lbl_extra} → {dst_title[:22]}",
                    command=lambda idx=e_idx: self.flow_canvas.select_edge(idx, notify=True),
                    style="Dark.TButton",
                ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
                ttk.Button(
                    row,
                    text="🗑️",
                    width=3,
                    command=lambda idx=e_idx: self._delete_edge_from_node_inspector(node.id, idx),
                    style="Danger.TButton",
                ).pack(side=tk.RIGHT)

        other_nodes = [n for n in self.graph.nodes.values() if n.id != node.id]
        if other_nodes:
            conn_row = tk.Frame(edge_box, bg=SURFACE_COLOR_ALT)
            conn_row.pack(fill=tk.X, pady=(6, 0))
            target_labels = [f"{n.title} ({n.id})" for n in other_nodes]
            combo_target = ttk.Combobox(conn_row, values=target_labels, state="readonly", width=18)
            combo_target.current(0)
            combo_target.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
            combo_cond = ttk.Combobox(conn_row, values=list(EDGE_CONDITIONS.keys()), state="readonly", width=9)
            combo_cond.set("default")
            combo_cond.pack(side=tk.LEFT, padx=(0, 4))

            def _connect_selected():
                sel_i = combo_target.current()
                if sel_i < 0 or sel_i >= len(other_nodes):
                    return
                dst_node = other_nodes[sel_i]
                self._commit_inspector_edits()
                self.graph.add_edge(node.id, dst_node.id, condition_type=combo_cond.get() or "default")
                self._save_to_campaign()
                self._build_node_inspector(node)

            ttk.Button(conn_row, text="+ Collega", command=_connect_selected, style="Gold.TButton").pack(side=tk.RIGHT)

    def _delete_edge_from_node_inspector(self, node_id: str, edge_idx: int) -> None:
        self._commit_inspector_edits()
        if self.graph.remove_edge_at(edge_idx) is not None:
            self._save_to_campaign()
            node = self.graph.nodes.get(node_id)
            if node:
                self._build_node_inspector(node)

    def _build_edge_inspector(self, edge_idx: int) -> None:
        self._clear_inspector_panel()
        if not (0 <= edge_idx < len(self.graph.edges)):
            self._build_empty_inspector()
            return
        self._inspector_building = True
        try:
            self._inspector_edge_idx = edge_idx
            edge = self.graph.edges[edge_idx]
            src = self.graph.nodes.get(edge.from_id)
            dst = self.graph.nodes.get(edge.to_id)
            src_title = src.title if src else edge.from_id
            dst_title = dst.title if dst else edge.to_id
            cond_meta = EDGE_CONDITIONS.get(edge.condition_type, EDGE_CONDITIONS["default"])

            hdr = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR_ALT, padx=8, pady=8, highlightbackground=BORDER_COLOR, highlightthickness=1)
            hdr.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                hdr,
                text=f"{cond_meta['icon']} CONNESSIONE / BIVIO",
                font=FONT_BADGE, bg=SURFACE_COLOR_ALT, fg=cond_meta["color"],
            ).pack(anchor="w")
            tk.Label(
                hdr,
                text=f"{src_title}  →  {dst_title}",
                font=FONT_BOLD, bg=SURFACE_COLOR_ALT, fg=TEXT_COLOR, wraplength=320, justify="left",
            ).pack(anchor="w", pady=(4, 0))

            nav_row = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR)
            nav_row.pack(fill=tk.X, pady=(0, 8))
            if src:
                ttk.Button(nav_row, text="← Nodo Origine", command=lambda nid=src.id: self.flow_canvas.select_node(nid), style="Dark.TButton").pack(side=tk.LEFT)
            if dst:
                ttk.Button(nav_row, text="Nodo Destinazione →", command=lambda nid=dst.id: self.flow_canvas.select_node(nid), style="Dark.TButton").pack(side=tk.RIGHT)

            tk.Label(self.inspector_panel, text="Tipo Condizione:", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            combo_cond = ttk.Combobox(self.inspector_panel, values=list(EDGE_CONDITIONS.keys()), state="readonly")
            combo_cond.set(edge.condition_type if edge.condition_type in EDGE_CONDITIONS else "default")
            combo_cond.pack(fill=tk.X, pady=(2, 8))
            combo_cond.bind("<<ComboboxSelected>>", lambda _e: self._commit_inspector_edits())
            self._inspector_widgets["_edge_cond"] = combo_cond

            # Pulsanti rapidi condizione
            preset_row = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR)
            preset_row.pack(fill=tk.X, pady=(0, 8))
            for ck in ("default", "success", "failure", "check", "item", "else"):
                cm = EDGE_CONDITIONS[ck]
                ttk.Button(
                    preset_row,
                    text=cm["icon"],
                    width=3,
                    command=lambda key=ck: self._apply_edge_preset(edge_idx, key),
                    style="Dark.TButton",
                ).pack(side=tk.LEFT, padx=2)

            tk.Label(self.inspector_panel, text="Valore Condizione (es. Percezione CD 14 / Chiave):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            ent_val = ttk.Entry(self.inspector_panel, font=FONT_MAIN)
            ent_val.insert(0, edge.condition_value or "")
            ent_val.pack(fill=tk.X, pady=(2, 8))
            ent_val.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
            ent_val.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            self._inspector_widgets["_edge_val"] = ent_val

            tk.Label(self.inspector_panel, text="Etichetta personalizzata sul grafo (opzionale):", font=FONT_BOLD, bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(anchor="w")
            ent_lbl = ttk.Entry(self.inspector_panel, font=FONT_MAIN)
            ent_lbl.insert(0, edge.label or "")
            ent_lbl.pack(fill=tk.X, pady=(2, 12))
            ent_lbl.bind("<KeyRelease>", lambda _e: self._schedule_inspector_apply())
            ent_lbl.bind("<FocusOut>", lambda _e: self._commit_inspector_edits())
            self._inspector_widgets["_edge_lbl"] = ent_lbl

            act_row = tk.Frame(self.inspector_panel, bg=SURFACE_COLOR)
            act_row.pack(fill=tk.X)
            ttk.Button(
                act_row,
                text="🗑️ Elimina Collegamento",
                command=lambda idx=edge_idx: self._delete_edge_from_inspector(idx),
                style="Danger.TButton",
            ).pack(side=tk.LEFT)
            ttk.Button(
                act_row,
                text="✓ Applica",
                command=self._commit_inspector_edits,
                style="Gold.TButton",
            ).pack(side=tk.RIGHT)
        finally:
            self._inspector_building = False

    def _delete_node_from_inspector(self, node_id: str) -> None:
        self._clear_inspector_panel()
        self.flow_canvas._delete_node(node_id)

    def _delete_edge_from_inspector(self, edge_idx: int) -> None:
        self._clear_inspector_panel()
        self.flow_canvas._delete_edge(edge_idx)

    def _apply_edge_preset(self, edge_idx: int, cond_type: str) -> None:
        self.flow_canvas._quick_set_edge_condition(edge_idx, cond_type)
        self._build_edge_inspector(edge_idx)

    # -----------------------------------------------------------------------
    # LIVELLI, SALVATAGGIO E INJECTION ENTITA'
    # -----------------------------------------------------------------------

    def enter_scene(self, scene_name: str) -> None:
        """Salva il livello corrente ed entra nel sotto-flusso interno della Scena specificata."""
        target = str(scene_name or "").strip()
        if not target:
            return
        self._commit_inspector_edits()
        self._save_to_campaign()
        self.campaign.ensure_scene_entry(target)
        self.active_scene_name = target
        self._load_active_level_into_views(sync_campaign=True)

    def enter_selected_or_first_scene(self) -> None:
        """Entra nella Scena selezionata sul canvas, oppure nella prima Scena della campagna."""
        sel_id = getattr(self.flow_canvas, "selected_node_id", None)
        sel_node = self.graph.nodes.get(sel_id) if sel_id else None
        if sel_node and sel_node.node_type == "scene":
            self.enter_scene(sel_node.title)
            return
        if sel_node and sel_node.node_type == "exit":
            dest = str(sel_node.data.get("target_scene") or sel_node.title).strip()
            if dest:
                self.enter_scene(dest)
                return
        if getattr(self.campaign, "scenes", None):
            first_name = self.campaign.scenes[0].get("name", "")
            if first_name:
                self.enter_scene(first_name)
                return
        for n in self.graph.nodes.values():
            if n.node_type == "scene":
                self.enter_scene(n.title)
                return

    def exit_to_campaign(self) -> None:
        """Salva il sotto-flusso della Scena attiva e torna al Livello 1 (Flusso Scene)."""
        if self.active_scene_name is None:
            return
        self._commit_inspector_edits()
        self._save_to_campaign()
        prev_scene = self.active_scene_name
        self.active_scene_name = None
        sync_hierarchical_campaign_flows(None, self.campaign)
        self._load_active_level_into_views(sync_campaign=False)
        node = self.graph.get_node_by_title(prev_scene)
        if node:
            self.flow_canvas.select_node(node.id, notify=True)
        if self.on_change_callback:
            self.on_change_callback()

    def toggle_entity_drawer(self) -> None:
        """Mostra o nasconde il pannello inferiore unificato di Scene, Incontri, Quest, PNG & Fazioni, Handouts."""
        if self._drawer_visible:
            try:
                self.right_paned.forget(self.entity_drawer_frame)
            except Exception:
                pass
            self._drawer_visible = False
            self.btn_toggle_drawer.config(text=_t("camp_studio_btn_drawer", default="📚 Entità & Fazioni ▸").replace("▾", "▸"))
        else:
            try:
                self.right_paned.add(self.entity_drawer_frame, minsize=160, height=230)
            except Exception:
                pass
            self._drawer_visible = True
            self.btn_toggle_drawer.config(text=_t("camp_studio_btn_drawer", default="📚 Entità & Fazioni ▾"))

    def open_entity_tab(self, tab_key: str) -> None:
        """Espande il drawer inferiore e seleziona la scheda richiesta."""
        if not self._drawer_visible:
            self.toggle_entity_drawer()
        tab_map = {
            "scenes": self.tab_scenes_frame,
            "encounters": self.tab_encounters_frame,
            "quests": self.tab_quests_frame,
            "npcs": self.tab_npcs_factions_frame,
            "factions": self.tab_npcs_factions_frame,
            "handouts": self.tab_handouts_frame,
        }
        frame = tab_map.get(tab_key)
        if frame is not None:
            try:
                self.entity_notebook.select(frame)
            except Exception:
                pass

    def inject_entity_into_scene(
        self,
        block_type: str,
        title: str,
        node_data: Optional[Dict[str, Any]] = None,
        target_scene_name: Optional[str] = None,
    ) -> None:
        """Inserisce un'entità strutturata (Incontro, PNG, Quest, Handout) direttamente nel sotto-flusso della scena."""
        if self.active_scene_name is None:
            dest_scene = target_scene_name
            if not dest_scene:
                sel_id = getattr(self.flow_canvas, "selected_node_id", None)
                sel_node = self.graph.nodes.get(sel_id) if sel_id else None
                if sel_node and sel_node.node_type == "scene":
                    dest_scene = sel_node.title
                elif getattr(self.campaign, "scenes", None):
                    dest_scene = self.campaign.scenes[0].get("name", "Scena Iniziale")
                else:
                    dest_scene = "Scena Iniziale"
            self.enter_scene(dest_scene)

        self._commit_inspector_edits()
        clean_title = str(title or "Elemento").strip()
        existing = self.graph.get_node_by_title(clean_title)
        if existing:
            self.flow_canvas.select_node(existing.id, notify=True)
            return

        selected_id = getattr(self.flow_canvas, "selected_node_id", None)
        selected_node = self.graph.nodes.get(selected_id) if selected_id else None
        occupied = [(n.x, n.y) for n in self.graph.nodes.values()]
        if selected_node is not None:
            bx, by = self._find_free_canvas_position(selected_node.x + 270.0, selected_node.y, occupied)
        else:
            max_y = max((n.y for n in self.graph.nodes.values()), default=100.0)
            bx, by = self._find_free_canvas_position(120.0, max_y + 150.0 if occupied else 120.0, occupied)

        new_id = self.graph.next_node_id(f"node_{block_type}")
        new_node = FlowNode(
            id=new_id,
            node_type=block_type,
            title=clean_title,
            x=bx,
            y=by,
            data=copy.deepcopy(node_data) if isinstance(node_data, dict) else {},
        )
        self.graph.nodes[new_id] = new_node
        if selected_node is not None:
            self.graph.add_edge(selected_node.id, new_id)

        self._save_to_campaign()
        self.flow_canvas.select_node(new_id, notify=True)

    def save_all_levels(self) -> None:
        """Garantisce il salvataggio del livello attivo, dei campi dell'Ispettore e della coerenza gerarchica."""
        self._commit_inspector_edits()
        self._save_to_campaign()
        sync_hierarchical_campaign_flows(None, self.campaign)

    def set_campaign(self, campaign: Any):
        """Sostituisce la campagna corrente nello Studio, ricaricando la gerarchia a 2 livelli."""
        self._cancel_inspector_apply()
        self.campaign = campaign
        self.active_scene_name = None
        if hasattr(self, "flow_canvas"):
            self.flow_canvas.selected_node_id = None
            self.flow_canvas.selected_edge_index = None
        self._prepare_campaign_hierarchy()
        self._load_active_level_into_views(sync_campaign=True)

    def _on_canvas_modified(self):
        """Chiamato quando l'utente muove o modifica nodi o connessioni direttamente sul canvas."""
        self.lbl_stats.config(text=f"Nodi: {len(self.graph.nodes)} | Connessioni: {len(self.graph.edges)}")
        self._save_to_campaign()
        sel_id = getattr(self.flow_canvas, "selected_node_id", None)
        sel_edge = getattr(self.flow_canvas, "selected_edge_index", None)
        if sel_edge is not None and 0 <= sel_edge < len(self.graph.edges):
            self._refresh_inspector_bar(None, edge_idx=sel_edge)
            self._build_edge_inspector(sel_edge)
        elif sel_id and sel_id in self.graph.nodes:
            node = self.graph.nodes[sel_id]
            self._refresh_inspector_bar(node, edge_idx=None)
            self._build_node_inspector(node)
        else:
            self._refresh_inspector_bar(None, edge_idx=None)
            self._build_empty_inspector()

    def _save_to_campaign(self):
        """Salva il FlowGraph del livello corrente e sincronizza le entità VTT della campagna."""
        if self.active_scene_name is None:
            self.campaign.flow_graph = self.graph.to_dict()
            sync_hierarchical_campaign_flows(self.graph, self.campaign)
            self._refresh_subflow_badges_on_macro()
            self.lbl_stats.config(text=f"Nodi: {len(self.graph.nodes)} | Connessioni: {len(self.graph.edges)}")
            if hasattr(self, "flow_canvas"):
                self.flow_canvas.render()
        else:
            sc_entry = self.campaign.ensure_scene_entry(self.active_scene_name)
            save_scene_subflow(sc_entry, self.graph)
            sync_hierarchical_campaign_flows(None, self.campaign)
            self.lbl_stats.config(text=f"Nodi: {len(self.graph.nodes)} | Connessioni: {len(self.graph.edges)}")
            if hasattr(self, "flow_canvas"):
                self.flow_canvas.render()

        if self.on_change_callback:
            self.on_change_callback()

    # -----------------------------------------------------------------------
    # TAVOLOZZA BLOCCHI VISUALI & COMPENDIO
    # -----------------------------------------------------------------------

    def open_compendium_loot_picker(self):
        """Apre il Compendio 5e filtrato sugli oggetti/tesori e li inserisce nel nodo selezionato o in un nuovo Tesoro."""
        try:
            from server.compendium_ui import CompendiumDialog

            def _on_item_picked(item_data, _category):
                name = (item_data.get("name") or item_data.get("title") or "").strip()
                if not name:
                    return
                self._insert_compendium_item_into_selection(name)

            dlg = CompendiumDialog(
                self.winfo_toplevel(),
                on_import_callback=_on_item_picked,
                is_dm=True,
                initial_category="Oggetti Magici",
                action_label="💎 Inserisci nel Loot / Tesoro",
                allowed_categories=["Equipaggiamento", "Armi", "Pozioni", "Oggetti Magici", "Equipaggiamento & Tesori"],
            )
            dlg.grab_set()
        except Exception as e:
            from common.messagebox import messagebox
            messagebox.showerror("Errore", f"Impossibile aprire il compendio: {e}", parent=self)

    def _insert_compendium_item_into_selection(self, item_name: str) -> None:
        self._commit_inspector_edits()
        sel_id = getattr(self.flow_canvas, "selected_node_id", None)
        sel_node = self.graph.nodes.get(sel_id) if sel_id else None

        if sel_node and sel_node.node_type in ("loot", "shop"):
            items = list(sel_node.data.get("items", []))
            items.append(item_name)
            sel_node.data["items"] = items
            sel_node.data["resolved_items"] = [resolve_compendium_item(it) for it in items]
            self._save_to_campaign()
            self._build_node_inspector(sel_node)
            return

        if sel_node and sel_node.node_type in ("encounter", "quest"):
            cur = str(sel_node.data.get("loot", "") or "").strip()
            new_loot = f"{cur}, {item_name}" if cur else item_name
            sel_node.data["loot"] = new_loot
            parsed = parse_loot_specification(new_loot)
            sel_node.data["loot_currency"] = parsed["currency"]
            sel_node.data["loot_items"] = parsed["items"]
            self._save_to_campaign()
            self._build_node_inspector(sel_node)
            return

        # Altrimenti crea un nuovo nodo Tesoro collegato al nodo selezionato (se presente)
        occupied = [(n.x, n.y) for n in self.graph.nodes.values()]
        if sel_node:
            px, py = self._find_free_canvas_position(sel_node.x + 270.0, sel_node.y, occupied)
        else:
            max_y = max((n.y for n in self.graph.nodes.values()), default=100.0)
            px, py = self._find_free_canvas_position(120.0, max_y + 140.0 if occupied else 100.0, occupied)

        used = {n.title.strip().lower() for n in self.graph.nodes.values() if n.title}
        title = self._next_unique_title(f"Tesoro: {item_name}", used)
        nid = self.graph.next_node_id("node_loot")
        new_node = FlowNode(
            id=nid,
            node_type="loot",
            title=title,
            x=px,
            y=py,
            data={"gold": "0 mo", "items": [item_name], "resolved_items": [resolve_compendium_item(item_name)]},
        )
        self.graph.nodes[nid] = new_node
        if sel_node:
            self.graph.add_edge(sel_node.id, nid)
        self._save_to_campaign()
        self.flow_canvas.select_node(nid, notify=True)

    def _next_unique_title(self, base_title: str, used_titles: Set[str]) -> str:
        """Restituisce un titolo univoco non ancora usato (es. 'Nome', 'Nome 2', 'Nome 3')."""
        candidate = base_title
        idx = 2
        while candidate.strip().lower() in used_titles:
            candidate = f"{base_title} {idx}"
            idx += 1
        used_titles.add(candidate.strip().lower())
        return candidate

    def _find_free_canvas_position(
        self, anchor_x: float, anchor_y: float, occupied: List[Tuple[float, float]]
    ) -> Tuple[float, float]:
        """Trova coordinate libere vicine all'ancora evitando sovrapposizioni tra nodi."""
        for col_step in range(4):
            px = anchor_x + col_step * 260.0
            for row_step in range(10):
                py = max(40.0, anchor_y + row_step * 120.0)
                if not any(abs(ox - px) < 225.0 and abs(oy - py) < 95.0 for ox, oy in occupied):
                    occupied.append((px, py))
                    return px, py
        occupied.append((anchor_x, anchor_y))
        return anchor_x, anchor_y

    def add_block(self, block_type: str) -> None:
        """Crea un nuovo nodo (ed eventuali bivi/esiti collegati) direttamente nel FlowGraph."""
        self._commit_inspector_edits()
        selected_id = getattr(self.flow_canvas, "selected_node_id", None)
        selected_node = self.graph.nodes.get(selected_id) if selected_id else None

        if block_type == "branch":
            self._add_branch_block(selected_node)
            return

        spec = _NODE_TEMPLATES.get(block_type)
        if not spec:
            return

        used_titles: Set[str] = {n.title.strip().lower() for n in self.graph.nodes.values() if n.title}
        base_title = spec["title"]
        node_data = copy.deepcopy(spec.get("data", {}))

        if block_type == "exit":
            dest_cand = ""
            for sc in getattr(self.campaign, "scenes", []):
                nm = str(sc.get("name", "") or "").strip()
                if nm and nm.lower() != str(self.active_scene_name or "").strip().lower():
                    dest_cand = nm
                    break
            if dest_cand:
                base_title = dest_cand
                node_data["target_scene"] = dest_cand

        node_title = self._next_unique_title(base_title, used_titles)
        occupied = [(n.x, n.y) for n in self.graph.nodes.values()]
        if selected_node is not None:
            base_x, base_y = self._find_free_canvas_position(selected_node.x + 270.0, selected_node.y, occupied)
        else:
            max_y = max((n.y for n in self.graph.nodes.values()), default=100.0)
            base_x, base_y = self._find_free_canvas_position(100.0, max_y + 140.0 if occupied else 100.0, occupied)

        main_id = self.graph.next_node_id(f"node_{block_type}")
        main_node = FlowNode(
            id=main_id,
            node_type=block_type,
            title=node_title,
            x=base_x,
            y=base_y,
            data=node_data,
        )
        self.graph.nodes[main_id] = main_node

        if selected_node is not None:
            self.graph.add_edge(selected_node.id, main_id)

        # Crea eventuali nodi di esito collegati (es. Successo / Fallimento su Prove ed Enigmi)
        allowed_types = getattr(self.flow_canvas, "allowed_node_types", None)
        for out_spec in spec.get("outcomes", []):
            out_type = out_spec.get("node_type", "scene")
            if allowed_types and out_type not in allowed_types:
                out_type = allowed_types[0]
            out_title = self._next_unique_title(out_spec.get("base_title", "Esito"), used_titles)
            dx, dy = out_spec.get("offset", (270.0, 0.0))
            ox, oy = self._find_free_canvas_position(base_x + dx, base_y + dy, occupied)
            out_id = self.graph.next_node_id(f"node_{out_type}")
            self.graph.nodes[out_id] = FlowNode(
                id=out_id,
                node_type=out_type,
                title=out_title,
                x=ox,
                y=oy,
                data=copy.deepcopy(out_spec.get("data", {})),
            )
            self.graph.add_edge(
                main_id,
                out_id,
                label=out_spec.get("label", ""),
                condition_type=out_spec.get("condition_type", "default"),
                condition_value=out_spec.get("condition_value", ""),
            )

        self._save_to_campaign()
        # Se un nodo era selezionato, mantiene la selezione sul nodo di partenza (così più clic su + Prova vi si agganciano)
        if selected_node is not None and selected_node.id in self.graph.nodes:
            self.flow_canvas.select_node(selected_node.id, notify=True)
        else:
            self.flow_canvas.selected_node_id = None
            self.flow_canvas.selected_edge_index = None
            self.flow_canvas.render()
            self._refresh_inspector_selection()

    def _add_branch_block(self, selected_node: Optional[FlowNode]) -> None:
        """Aggiunge un bivio condizionale sul livello attivo e seleziona subito il nuovo arco nell'Ispettore."""
        used_titles = {n.title.strip().lower() for n in self.graph.nodes.values() if n.title}
        occupied = [(n.x, n.y) for n in self.graph.nodes.values()]
        in_macro = (self.active_scene_name is None)
        target_type = "scene" if in_macro else "choice"
        base_label = "Destinazione Bivio" if in_macro else "Bivio Narrativo"
        title = self._next_unique_title(base_label, used_titles)

        if selected_node is not None:
            px, py = self._find_free_canvas_position(selected_node.x + 270.0, selected_node.y + 60.0, occupied)
        else:
            max_y = max((n.y for n in self.graph.nodes.values()), default=100.0)
            px, py = self._find_free_canvas_position(120.0, max_y + 140.0 if occupied else 100.0, occupied)

        nid = self.graph.next_node_id(f"node_{target_type}")
        self.graph.nodes[nid] = FlowNode(
            id=nid,
            node_type=target_type,
            title=title,
            x=px,
            y=py,
            data={"map_file": "maps/faerun.json"} if in_macro else {"read_aloud": "Scelta del gruppo."},
        )

        new_edge_idx = None
        if selected_node is not None:
            self.graph.add_edge(
                selected_node.id,
                nid,
                label="Se scelgono questa via",
                condition_type="custom",
                condition_value="Condizione",
            )
            new_edge_idx = len(self.graph.edges) - 1

        self._save_to_campaign()
        if new_edge_idx is not None:
            self.flow_canvas.select_edge(new_edge_idx, notify=True)
        else:
            self.flow_canvas.select_node(nid, notify=True)

    def rearrange_flow_layout(self) -> None:
        """Riordina le posizioni X/Y dei nodi del livello corrente senza duplicare o alterare i dati."""
        self._commit_inspector_edits()
        if not self.graph.nodes:
            return
        in_deg: Dict[str, int] = {nid: 0 for nid in self.graph.nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self.graph.nodes}
        for e in self.graph.edges:
            if e.from_id in adj and e.to_id in in_deg:
                adj[e.from_id].append(e.to_id)
                in_deg[e.to_id] += 1

        roots = [nid for nid, deg in in_deg.items() if deg == 0]
        if not roots:
            roots = [next(iter(self.graph.nodes.keys()))]

        depths: Dict[str, int] = {}
        queue: List[Tuple[str, int]] = [(r, 0) for r in roots]
        while queue:
            cur_id, d = queue.pop(0)
            if cur_id in depths:
                continue
            depths[cur_id] = d
            for nxt in adj.get(cur_id, []):
                if nxt not in depths:
                    queue.append((nxt, d + 1))

        for nid in self.graph.nodes:
            depths.setdefault(nid, 0)

        by_col: Dict[int, List[str]] = {}
        for nid, d in depths.items():
            by_col.setdefault(d, []).append(nid)

        for col, nids in sorted(by_col.items()):
            for row, nid in enumerate(nids):
                node = self.graph.nodes[nid]
                node.x = 100.0 + col * 270.0
                node.y = 80.0 + row * 125.0

        self._save_to_campaign()
        self.flow_canvas.render()

    def center_canvas(self):
        self.flow_canvas.reset_view()

    def _bind_fullscreen_shortcuts(self):
        try:
            top = self.winfo_toplevel()
            if top:
                self._fullscreen_top = top
                self._f11_bind_id = top.bind("<F11>", self.toggle_fullscreen, add="+")
                self._esc_bind_id = top.bind("<Escape>", self.exit_fullscreen, add="+")
        except Exception:
            pass

    def toggle_fullscreen(self, event=None):
        top = self.winfo_toplevel()
        if not top:
            return
        is_fs = not getattr(top, "_is_fullscreen", False)
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
