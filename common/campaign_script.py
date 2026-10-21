# common/campaign_script.py
"""
Motore Campaign-as-Code e DndScript per DndOmniCompanion.
Fornisce un linguaggio dichiarativo leggibile e naturale (stile Markdown narrativo)
per definire la struttura della campagna, con transpiler bidirezionale verso grafo a nodi (FlowGraph)
e verso gli oggetti VTT di D&D (Scene, Incontri, Quest, PNG, Segreti, Handouts).
Supporta logica condizionale avanzata (Successo/Fallimento, CD prove, Possesso oggetti)
e un'ampia varietà di blocchi narrativi e meccanici per D&D 5e.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


NODE_TYPES = {
    "scene": {"label": "Scena", "color": "#1971C2", "icon": "🗺️"},
    "encounter": {"label": "Incontro", "color": "#C92A2A", "icon": "⚔️"},
    "check": {"label": "Prova/CD", "color": "#0CA678", "icon": "🎲"},
    "trap": {"label": "Trappola", "color": "#D6336C", "icon": "⚠️"},
    "loot": {"label": "Tesoro", "color": "#F59F00", "icon": "💎"},
    "npc": {"label": "PNG", "color": "#7950F2", "icon": "👤"},
    "shop": {"label": "Emporio", "color": "#1098AD", "icon": "🏬"},
    "puzzle": {"label": "Enigma", "color": "#AE3EC9", "icon": "🧩"},
    "rest": {"label": "Riposo", "color": "#2F9E44", "icon": "⛺"},
    "lore": {"label": "Documento", "color": "#845EF7", "icon": "📜"},
    "event": {"label": "Evento", "color": "#F76707", "icon": "⏳"},
    "quest": {"label": "Quest", "color": "#FAB005", "icon": "🏆"},
    "hook": {"label": "Spunto", "color": "#40C057", "icon": "📢"},
    "choice": {"label": "Bivio", "color": "#FD7E14", "icon": "🔀"},
    "note": {"label": "Nota", "color": "#495057", "icon": "📝"},
    "off_track": {"label": "Fuori Pista", "color": "#E03131", "icon": "⚡"}
}

# Mappatura prefissi sintassi DndScript verso node_type
TYPE_PREFIXES = {
    "SCENA": "scene",
    "SCENE": "scene",
    "LUOGO": "scene",
    "LOCATION": "scene",
    "INCONTRO": "encounter",
    "ENCOUNTER": "encounter",
    "COMBAT": "encounter",
    "BATTAGLIA": "encounter",
    "FIGHT": "encounter",
    "PROVA": "check",
    "CHECK": "check",
    "TEST": "check",
    "TIRO": "check",
    "TIRO_SALVEZZA": "check",
    "TS": "check",
    "TRAPPOLA": "trap",
    "TRAP": "trap",
    "PERICOLO": "trap",
    "HAZARD": "trap",
    "TESORO": "loot",
    "LOOT": "loot",
    "BOTTINO": "loot",
    "PREMIO": "loot",
    "SCRIGNO": "loot",
    "CHEST": "loot",
    "PNG": "npc",
    "NPC": "npc",
    "PERSONAGGIO": "npc",
    "EMPORIO": "shop",
    "SHOP": "shop",
    "NEGOZIO": "shop",
    "MERCANTE": "shop",
    "STORE": "shop",
    "ENIGMA": "puzzle",
    "PUZZLE": "puzzle",
    "MISTERO": "puzzle",
    "INDOVINELLO": "puzzle",
    "RIDDLE": "puzzle",
    "RIPOSO": "rest",
    "ACCAMPAMENTO": "rest",
    "CAMP": "rest",
    "REST": "rest",
    "RIFUGIO": "rest",
    "SHELTER": "rest",
    "DOCUMENTO": "lore",
    "LORE": "lore",
    "LIBRO": "lore",
    "MANOSCRITTO": "lore",
    "HANDOUT": "lore",
    "LETTERA": "lore",
    "EVENTO": "event",
    "EVENT": "event",
    "OROLOGIO": "event",
    "TIMER": "event",
    "CATACLISMA": "event",
    "QUEST": "quest",
    "MISSIONE": "quest",
    "OBIETTIVO": "quest",
    "SPUNTO": "hook",
    "VOCE": "hook",
    "HOOK": "hook",
    "RUMOR": "hook",
    "BIVIO": "choice",
    "SCELTA": "choice",
    "CHOICE": "choice",
    "BRANCH": "choice",
    "NOTA": "note",
    "NOTE": "note",
    "MEMO": "note",
    "FUORI_PISTA": "off_track",
    "OFF_TRACK": "off_track",
    "IMPROVVISAZIONE": "off_track"
}

REVERSE_TYPE_PREFIXES = {
    "scene": "SCENA",
    "encounter": "INCONTRO",
    "check": "PROVA",
    "trap": "TRAPPOLA",
    "loot": "TESORO",
    "npc": "PNG",
    "shop": "EMPORIO",
    "puzzle": "ENIGMA",
    "rest": "RIPOSO",
    "lore": "DOCUMENTO",
    "event": "EVENTO",
    "quest": "QUEST",
    "hook": "VOCE",
    "choice": "BIVIO",
    "note": "NOTA",
    "off_track": "FUORI_PISTA"
}


@dataclass
class FlowNode:
    id: str
    node_type: str
    title: str
    x: float = 0.0
    y: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "title": self.title,
            "x": self.x,
            "y": self.y,
            "data": dict(self.data)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowNode":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            node_type=d.get("node_type", "note"),
            title=d.get("title", "Senza Titolo"),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            data=d.get("data", {})
        )


@dataclass
class FlowEdge:
    from_id: str
    to_id: str
    label: str = ""
    condition_type: str = "default"  # default, check, success, failure, item, else, custom
    condition_value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_id": self.from_id,
            "to_id": self.to_id,
            "label": self.label,
            "condition_type": self.condition_type,
            "condition_value": self.condition_value
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowEdge":
        return cls(
            from_id=d.get("from_id", ""),
            to_id=d.get("to_id", ""),
            label=d.get("label", ""),
            condition_type=d.get("condition_type", "default"),
            condition_value=d.get("condition_value", "")
        )


@dataclass
class FlowGraph:
    nodes: Dict[str, FlowNode] = field(default_factory=dict)
    edges: List[FlowEdge] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "metadata": dict(self.metadata)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowGraph":
        g = cls()
        g.metadata = d.get("metadata", {})
        for nd in d.get("nodes", []):
            node = FlowNode.from_dict(nd)
            g.nodes[node.id] = node
        for ed in d.get("edges", []):
            edge = FlowEdge.from_dict(ed)
            g.edges.append(edge)
        return g

    def get_node_by_title(self, title: str) -> Optional[FlowNode]:
        clean = title.strip().lower()
        for n in self.nodes.values():
            if n.title.strip().lower() == clean:
                return n
        return None


# ---------------------------------------------------------------------------
# PARSER: DndScript Text -> FlowGraph
# ---------------------------------------------------------------------------

class DndScriptParser:
    """
    Parser robusto ed elastico per la sintassi Campaign-as-Code (DndScript).
    Estrae nodi, collegamenti condizionali avanzati (Successo/Fallimento, CD prove, Oggetti)
    e metadati VTT.
    Non genera mai crash bloccanti per refusi o formattazione parziale.
    """

    def __init__(self):
        self.warnings: List[str] = []

    def parse(self, text: str, existing_positions: Optional[Dict[str, Tuple[float, float]]] = None) -> FlowGraph:
        self.warnings = []
        graph = FlowGraph()
        if not text or not text.strip():
            return graph

        lines = text.splitlines()
        current_node: Optional[FlowNode] = None
        # Struttura: (from_id, target_str, label, condition_type, condition_value)
        raw_edges: List[Tuple[str, str, str, str, str]] = []
        
        # Mappa titoli a ID per risoluzione collegamenti
        title_to_id: Dict[str, str] = {}
        
        # Pattern per header nodo: # TIPO: Titolo
        node_header_re = re.compile(r'^\s*#{1,3}\s*([A-Za-z0-9_]+)\s*:\s*(.+)$')
        
        # Pattern condizionali specifici su frecce:
        arrow_if_check_re = re.compile(r'^\s*->\s*(?:SE|IF)\s*\[([^\]]+)\]\s*->\s*(.+)$', re.IGNORECASE)
        arrow_success_re = re.compile(r'^\s*->\s*(?:SUCCESSO|SUCCESS|VITTORIA)\s*(?:\[([^\]]+)\])?\s*->\s*(.+)$', re.IGNORECASE)
        arrow_failure_re = re.compile(r'^\s*->\s*(?:FALLIMENTO|FAILURE|FALLITO|SCONFITTA)\s*(?:\[([^\]]+)\])?\s*->\s*(.+)$', re.IGNORECASE)
        arrow_else_re = re.compile(r'^\s*->\s*(?:ALTRIMENTI|ELSE)\s*->\s*(.+)$', re.IGNORECASE)
        arrow_item_re = re.compile(r'^\s*->\s*(?:SE POSSIEDE|IF HAS|OGGETTO|ITEM)\s*["\']?([^"\'\->]+)["\']?\s*->\s*(.+)$', re.IGNORECASE)
        arrow_full_re = re.compile(r'^\s*->\s*(?:"([^"]*)"|\'([^\']*)\')\s*->\s*(.+)$')
        arrow_simple_re = re.compile(r'^\s*->\s*(.+)$')
        
        # Pattern per chiavi: chiave: valore (supporta anche caratteri accentati es: abilità)
        key_val_re = re.compile(r'^\s*([a-zA-Z0-9_àèéìòùÀÈÉÌÒÙ-]+)\s*:\s*(.+)$')
        
        # Pattern per segreti/trappole con CD opzionale:
        secret_re = re.compile(r'^\s*[\*\-]\s*(SEGRETO|TRAPPOLA|INDICE|VOCE|HANDOUT)\s*(?:\[([^\]]+)\])?\s*:\s*(.+)$', re.IGNORECASE)

        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx].rstrip()
            stripped = line.strip()
            line_idx += 1

            if not stripped or stripped.startswith("//"):
                continue

            # 1. Riconoscimento Nuovo Nodo
            header_match = node_header_re.match(stripped)
            if header_match:
                raw_type = header_match.group(1).upper()
                node_title = header_match.group(2).strip().strip('"\'')
                node_type = TYPE_PREFIXES.get(raw_type, "note")

                node_id = f"node_{len(graph.nodes) + 1}_{re.sub(r'[^a-zA-Z0-9_]', '', node_title.lower())[:12]}"
                # Preserva posizioni esistenti se presenti
                init_x = 100.0 + (len(graph.nodes) % 4) * 260.0
                init_y = 100.0 + (len(graph.nodes) // 4) * 220.0
                if existing_positions and node_title.lower() in existing_positions:
                    init_x, init_y = existing_positions[node_title.lower()]

                current_node = FlowNode(
                    id=node_id,
                    node_type=node_type,
                    title=node_title,
                    x=init_x,
                    y=init_y,
                    data={}
                )
                graph.nodes[node_id] = current_node
                title_to_id[node_title.strip().lower()] = node_id
                continue

            # Se non abbiamo ancora un nodo, crea un nodo iniziale di benvenuto
            if current_node is None:
                current_node = FlowNode(
                    id="node_init",
                    node_type="hook",
                    title="Inizio Avventura",
                    x=100.0,
                    y=100.0,
                    data={}
                )
                graph.nodes[current_node.id] = current_node
                title_to_id["inizio avventura"] = current_node.id

            # 2. Riconoscimento Frecce Condizionali e Transizioni
            # A) -> SE [CD ...] -> DESTINAZIONE
            m_if_check = arrow_if_check_re.match(stripped)
            if m_if_check:
                chk_val = m_if_check.group(1).strip()
                tgt = m_if_check.group(2).strip()
                raw_edges.append((current_node.id, tgt, f"Se [{chk_val}]", "check", chk_val))
                continue

            # B) -> SUCCESSO -> DESTINAZIONE
            m_succ = arrow_success_re.match(stripped)
            if m_succ:
                extra = (m_succ.group(1) or "").strip()
                tgt = m_succ.group(2).strip()
                lbl = f"✅ Successo ({extra})" if extra else "✅ Successo"
                raw_edges.append((current_node.id, tgt, lbl, "success", extra))
                continue

            # C) -> FALLIMENTO -> DESTINAZIONE
            m_fail = arrow_failure_re.match(stripped)
            if m_fail:
                extra = (m_fail.group(1) or "").strip()
                tgt = m_fail.group(2).strip()
                lbl = f"❌ Fallimento ({extra})" if extra else "❌ Fallimento"
                raw_edges.append((current_node.id, tgt, lbl, "failure", extra))
                continue

            # D) -> ALTRIMENTI -> DESTINAZIONE
            m_else = arrow_else_re.match(stripped)
            if m_else:
                tgt = m_else.group(1).strip()
                raw_edges.append((current_node.id, tgt, "Altrimenti", "else", ""))
                continue

            # E) -> SE POSSIEDE "Oggetto" -> DESTINAZIONE
            m_item = arrow_item_re.match(stripped)
            if m_item:
                item_name = m_item.group(1).strip().strip('"\'')
                tgt = m_item.group(2).strip()
                raw_edges.append((current_node.id, tgt, f"🔑 {item_name}", "item", item_name))
                continue

            # F) -> "Etichetta generica" -> DESTINAZIONE
            m_full = arrow_full_re.match(stripped)
            if m_full:
                lbl = m_full.group(1) or m_full.group(2) or ""
                tgt = m_full.group(3).strip()
                c_type, c_val = self._classify_condition_label(lbl)
                raw_edges.append((current_node.id, tgt, lbl, c_type, c_val))
                continue

            # G) -> DESTINAZIONE
            m_simple = arrow_simple_re.match(stripped)
            if m_simple:
                tgt = m_simple.group(1).strip()
                raw_edges.append((current_node.id, tgt, "", "default", ""))
                continue

            # 3. Riconoscimento Segreti, Trappole, Handouts e Voci
            secret_match = secret_re.match(stripped)
            if secret_match:
                sec_type = secret_match.group(1).upper()
                sec_check = (secret_match.group(2) or "").strip()
                sec_val = secret_match.group(3).strip().strip('"\'')
                
                if sec_type in ("SEGRETO", "TRAPPOLA"):
                    secrets_list = current_node.data.setdefault("secrets", [])
                    secrets_list.append({
                        "type": sec_type,
                        "check": sec_check,
                        "text": sec_val,
                        "revealed": False
                    })
                elif sec_type == "VOCE":
                    rumors_list = current_node.data.setdefault("rumors", [])
                    rumors_list.append({"text": sec_val})
                elif sec_type == "HANDOUT":
                    handouts_list = current_node.data.setdefault("handouts", [])
                    handouts_list.append({"title": sec_check or sec_val, "file": sec_val})
                continue

            # 4. Riconoscimento Coppie Chiave: Valore per tutti i blocchi
            kv_match = key_val_re.match(stripped)
            if kv_match:
                key = kv_match.group(1).lower().replace("-", "_")
                # Normalizza caratteri accentati (es: abilità -> abilita, difficoltà -> difficolta)
                for acc, repl in [("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u")]:
                    key = key.replace(acc, repl)
                val = kv_match.group(2).strip().strip('"\'')

                # Proprietà Scena / Mappe
                if key in ("mappa", "map", "map_file"):
                    current_node.data["map_file"] = val
                elif key in ("meteo", "weather"):
                    current_node.data["weather"] = val
                elif key in ("luce", "light"):
                    current_node.data["light"] = val
                elif key in ("musica", "music", "audio"):
                    current_node.data["music"] = val
                elif key in ("narra", "read_aloud", "desc", "description"):
                    current_node.data["read_aloud"] = val
                # Proprietà Incontri
                elif key in ("mostri", "monsters"):
                    current_node.data["monsters"] = self._parse_monsters_string(val)
                elif key in ("cr", "sfida", "challenge"):
                    current_node.data["cr"] = val
                elif key in ("loot", "bottino", "ricompensa", "reward"):
                    current_node.data["loot"] = val
                # Proprietà PNG
                elif key in ("ruolo", "role"):
                    current_node.data["role"] = val
                elif key in ("allineamento", "alignment"):
                    current_node.data["alignment"] = val
                # Proprietà Quest
                elif key in ("obiettivi", "objectives"):
                    objs = [o.strip().strip('"\'') for o in val.split(",") if o.strip()]
                    current_node.data["objectives"] = objs
                elif key in ("xp", "punti_esperienza"):
                    try:
                        current_node.data["xp"] = int(val)
                    except ValueError:
                        current_node.data["xp"] = val
                # Proprietà Prove / Check
                elif key in ("abilita", "ability", "skill"):
                    current_node.data["ability"] = val
                elif key in ("cd", "dc", "difficolta"):
                    try:
                        current_node.data["cd"] = int(val)
                    except ValueError:
                        current_node.data["cd"] = val
                # Proprietà Trappole
                elif key in ("danno", "damage"):
                    current_node.data["damage"] = val
                elif key in ("salvezza", "save", "tiro_salvezza"):
                    current_node.data["save"] = val
                elif key in ("cd_disarma", "disarm_dc"):
                    current_node.data["disarm_dc"] = val
                # Proprietà Tesoro
                elif key in ("oro", "gold", "monete"):
                    current_node.data["gold"] = val
                elif key in ("oggetti", "items"):
                    if "," in val:
                        current_node.data["items"] = [i.strip().strip('"\'') for i in val.split(",") if i.strip()]
                    else:
                        current_node.data["items"] = [val.strip().strip('"\'')] if val else []
                elif key in ("magici", "magic_items"):
                    current_node.data["magic_items"] = val
                # Proprietà Emporio / Negozi
                elif key in ("mercante", "merchant"):
                    current_node.data["merchant"] = val
                elif key in ("tipo", "tipo_negozio", "shop_type"):
                    current_node.data["shop_type"] = val
                elif key in ("merci", "wares"):
                    current_node.data["wares"] = val
                # Proprietà Enigmi
                elif key in ("indizio", "clue"):
                    current_node.data["clue"] = val
                elif key in ("soluzione", "solution"):
                    current_node.data["solution"] = val
                # Proprietà Riposo / Accampamento
                elif key in ("sicurezza", "safety"):
                    current_node.data["safety"] = val
                elif key in ("tipo_riposo", "rest_type"):
                    current_node.data["rest_type"] = val
                # Proprietà Documenti / Lore
                elif key in ("autore", "author"):
                    current_node.data["author"] = val
                elif key in ("lingua", "language"):
                    current_node.data["language"] = val
                # Proprietà Eventi
                elif key in ("trigger", "innesco"):
                    current_node.data["trigger"] = val
                elif key in ("effetto", "effect"):
                    current_node.data["effect"] = val
                else:
                    current_node.data[key] = val
                continue

            # Qualsiasi altra riga di testo viene accumulata nelle note libere del nodo
            cur_notes = current_node.data.get("notes", "")
            current_node.data["notes"] = (cur_notes + "\n" + stripped).strip()

        # -------------------------------------------------------------------
        # Risoluzione Finale dei Collegamenti (Edges)
        # -------------------------------------------------------------------
        for src_id, raw_target, edge_label, cond_type, cond_val in raw_edges:
            target_clean = raw_target.strip()
            
            # Rimuovi eventuale prefisso del tipo (es: "SCENA: Ingresso Cripta" -> "Ingresso Cripta")
            for pfx in TYPE_PREFIXES.keys():
                if target_clean.upper().startswith(f"{pfx}:"):
                    target_clean = target_clean[len(pfx) + 1:].strip()
                    break
            target_clean = target_clean.strip('"\'').lower()

            target_id = title_to_id.get(target_clean)
            
            # Se la destinazione non esiste ancora, crea un nodo placeholder
            if not target_id:
                new_title = raw_target.strip().strip('"\'')
                inferred_type = "note"
                for pfx, t_code in TYPE_PREFIXES.items():
                    if new_title.upper().startswith(f"{pfx}:"):
                        inferred_type = t_code
                        new_title = new_title[len(pfx) + 1:].strip().strip('"\'')
                        break
                
                new_id = f"node_{len(graph.nodes) + 1}_{re.sub(r'[^a-zA-Z0-9_]', '', new_title.lower())[:12]}"
                new_node = FlowNode(
                    id=new_id,
                    node_type=inferred_type,
                    title=new_title,
                    x=100.0 + (len(graph.nodes) % 4) * 260.0,
                    y=100.0 + (len(graph.nodes) // 4) * 220.0,
                    data={}
                )
                graph.nodes[new_id] = new_node
                title_to_id[new_title.lower()] = new_id
                target_id = new_id

            graph.edges.append(FlowEdge(
                from_id=src_id,
                to_id=target_id,
                label=edge_label,
                condition_type=cond_type,
                condition_value=cond_val
            ))

        return graph

    def _classify_condition_label(self, lbl: str) -> Tuple[str, str]:
        """Classifica un'etichetta di bivio testuale per estrarre la condizione."""
        lbl_lower = lbl.lower()
        if "success" in lbl_lower or "vittoria" in lbl_lower or "superat" in lbl_lower:
            return "success", ""
        elif "fallim" in lbl_lower or "fail" in lbl_lower or "sconfitt" in lbl_lower:
            return "failure", ""
        elif "altrimenti" in lbl_lower or "else" in lbl_lower:
            return "else", ""
        elif "chiave" in lbl_lower or "possied" in lbl_lower or "has" in lbl_lower:
            return "item", lbl
        elif "cd" in lbl_lower or "dc" in lbl_lower or "prova" in lbl_lower:
            return "check", lbl
        return "custom", lbl

    def _parse_monsters_string(self, s: str) -> List[Dict[str, Any]]:
        monsters = []
        parts = [p.strip() for p in s.split(",") if p.strip()]
        for p in parts:
            match = re.match(r'^(?:(\d+)\s*[xX]?\s*)?["\']?([^"\']+)["\']?$', p)
            if match:
                qty = int(match.group(1)) if match.group(1) else 1
                name = match.group(2).strip()
                monsters.append({"name": name, "quantity": qty})
            else:
                monsters.append({"name": p, "quantity": 1})
        return monsters


# ---------------------------------------------------------------------------
# SERIALIZER: FlowGraph -> DndScript Text
# ---------------------------------------------------------------------------

class DndScriptSerializer:
    """
    Serializzatore bidirezionale: converte un FlowGraph in testo DndScript pulito,
    preservando condizioni avanzate e tutta la varietà di blocchi D&D 5e.
    """

    def serialize(self, graph: FlowGraph) -> str:
        lines: List[str] = []
        
        outgoing: Dict[str, List[FlowEdge]] = {}
        for edge in graph.edges:
            outgoing.setdefault(edge.from_id, []).append(edge)

        nodes_list = list(graph.nodes.values())
        if not nodes_list:
            return ""

        for idx, node in enumerate(nodes_list):
            pfx = REVERSE_TYPE_PREFIXES.get(node.node_type, "NOTA")
            lines.append(f"# {pfx}: {node.title}")

            d = node.data
            # Proprietà standard
            if "map_file" in d and d["map_file"]:
                lines.append(f'mappa: "{d["map_file"]}"')
            if "weather" in d and d["weather"]:
                lines.append(f'meteo: "{d["weather"]}"')
            if "light" in d and d["light"]:
                lines.append(f'luce: "{d["light"]}"')
            if "music" in d and d["music"]:
                lines.append(f'musica: "{d["music"]}"')
            if "read_aloud" in d and d["read_aloud"]:
                lines.append(f'narra: "{d["read_aloud"]}"')
            if "cr" in d and d["cr"]:
                lines.append(f'cr: "{d["cr"]}"')
            if "loot" in d and d["loot"]:
                lines.append(f'loot: "{d["loot"]}"')
            if "role" in d and d["role"]:
                lines.append(f'ruolo: "{d["role"]}"')
            if "alignment" in d and d["alignment"]:
                lines.append(f'allineamento: "{d["alignment"]}"')
            if "xp" in d and d["xp"]:
                lines.append(f'xp: {d["xp"]}')

            # Nuove proprietà blocchi avanzati
            if "ability" in d and d["ability"]:
                lines.append(f'abilita: "{d["ability"]}"')
            if "cd" in d and d["cd"]:
                lines.append(f'cd: "{d["cd"]}"')
            if "damage" in d and d["damage"]:
                lines.append(f'danno: "{d["damage"]}"')
            if "save" in d and d["save"]:
                lines.append(f'salvezza: "{d["save"]}"')
            if "gold" in d and d["gold"]:
                lines.append(f'oro: "{d["gold"]}"')
            if "items" in d and d["items"]:
                if isinstance(d["items"], list):
                    it_tokens = [f'"{it}"' for it in d["items"]]
                    lines.append(f'oggetti: {", ".join(it_tokens)}')
                else:
                    lines.append(f'oggetti: "{d["items"]}"')
            if "merchant" in d and d["merchant"]:
                lines.append(f'mercante: "{d["merchant"]}"')
            if "shop_type" in d and d["shop_type"]:
                lines.append(f'tipo: "{d["shop_type"]}"')
            if "clue" in d and d["clue"]:
                lines.append(f'indizio: "{d["clue"]}"')
            if "solution" in d and d["solution"]:
                lines.append(f'soluzione: "{d["solution"]}"')
            if "safety" in d and d["safety"]:
                lines.append(f'sicurezza: "{d["safety"]}"')
            if "author" in d and d["author"]:
                lines.append(f'autore: "{d["author"]}"')
            if "language" in d and d["language"]:
                lines.append(f'lingua: "{d["language"]}"')
            if "trigger" in d and d["trigger"]:
                lines.append(f'trigger: "{d["trigger"]}"')

            # Mostri
            if "monsters" in d and d["monsters"]:
                m_tokens = []
                for m in d["monsters"]:
                    q = m.get("quantity", 1)
                    nm = m.get("name", "Mostro")
                    m_tokens.append(f'{q}x "{nm}"' if q > 1 else f'"{nm}"')
                lines.append(f'mostri: {", ".join(m_tokens)}')

            # Obiettivi
            if "objectives" in d and d["objectives"]:
                obs = [f'"{o}"' for o in d["objectives"]]
                lines.append(f'obiettivi: {", ".join(obs)}')

            # Segreti & Trappole interni
            if "secrets" in d:
                for s in d["secrets"]:
                    s_type = s.get("type", "SEGRETO").upper()
                    chk = f' [{s["check"]}]' if s.get("check") else ""
                    lines.append(f'* {s_type}{chk}: "{s.get("text", "")}"')

            # Voci
            if "rumors" in d:
                for r in d["rumors"]:
                    lines.append(f'* VOCE: "{r.get("text", "")}"')

            # Handouts
            if "handouts" in d:
                for h in d["handouts"]:
                    title_attr = f' [titolo: "{h["title"]}"]' if h.get("title") else ""
                    lines.append(f'* HANDOUT: "{h.get("file", "")}"{title_attr}')

            # Note libere
            if "notes" in d and d["notes"]:
                for n_line in d["notes"].splitlines():
                    if n_line.strip():
                        lines.append(n_line.strip())

            # Connessioni e Condizioni in Uscita
            edges = outgoing.get(node.id, [])
            for e in edges:
                target_node = graph.nodes.get(e.to_id)
                if not target_node:
                    continue
                tgt_pfx = REVERSE_TYPE_PREFIXES.get(target_node.node_type, "NOTA")
                
                if e.condition_type == "success":
                    lines.append(f'-> SUCCESSO -> {tgt_pfx}: {target_node.title}')
                elif e.condition_type == "failure":
                    lines.append(f'-> FALLIMENTO -> {tgt_pfx}: {target_node.title}')
                elif e.condition_type == "check" and e.condition_value:
                    lines.append(f'-> SE [{e.condition_value}] -> {tgt_pfx}: {target_node.title}')
                elif e.condition_type == "item" and e.condition_value:
                    lines.append(f'-> SE POSSIEDE "{e.condition_value}" -> {tgt_pfx}: {target_node.title}')
                elif e.condition_type == "else":
                    lines.append(f'-> ALTRIMENTI -> {tgt_pfx}: {target_node.title}')
                elif e.label:
                    lines.append(f'-> "{e.label}" -> {tgt_pfx}: {target_node.title}')
                else:
                    lines.append(f'-> {tgt_pfx}: {target_node.title}')

            if idx < len(nodes_list) - 1:
                lines.append("")
                lines.append("")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# INTEGRAZIONE CON OGGETTI CAMPAIGN DI D&D OMNICOMPANION
# ---------------------------------------------------------------------------

def sync_flow_graph_to_campaign(graph: FlowGraph, campaign: Any):
    """
    Sincronizza le entità del FlowGraph all'interno dell'oggetto Campaign:
    - Nodi Scena ➔ campaign.scenes
    - Nodi Incontro ➔ campaign.encounters
    - Nodi Quest ➔ campaign.quests
    - Nodi PNG ➔ campaign.npcs
    - Nodi Emporio ➔ campaign.shops
    - Nodi Documento / Handouts ➔ campaign.handouts
    - Segreti & Trappole ➔ aggregati in campaign.dm_notes
    """
    scenes_map = {s.get("name", ""): s for s in campaign.scenes}
    encounters_map = {e.get("name", ""): e for e in campaign.encounters}
    quests_map = {q.get("title", ""): q for q in campaign.quests}
    npcs_map = {n.get("name", ""): n for n in campaign.npcs}
    shops_map = dict(getattr(campaign, "shops", {}))
    handouts_map = {h.get("title", ""): h for h in campaign.handouts}

    all_secrets = []

    for node in graph.nodes.values():
        d = node.data
        if node.node_type == "scene":
            scene_entry = scenes_map.get(node.title, {
                "name": node.title,
                "map_file": d.get("map_file", "maps/faerun.json"),
                "description": d.get("read_aloud", "")
            })
            scene_entry["map_file"] = d.get("map_file", scene_entry.get("map_file", "maps/faerun.json"))
            scene_entry["description"] = d.get("read_aloud", scene_entry.get("description", ""))
            scenes_map[node.title] = scene_entry

        elif node.node_type == "encounter":
            enc_entry = encounters_map.get(node.title, {
                "name": node.title,
                "act": "Atto 1",
                "description": d.get("read_aloud", ""),
                "monsters": []
            })
            enc_entry["description"] = d.get("read_aloud", enc_entry.get("description", ""))
            if "monsters" in d:
                enc_entry["monsters"] = d["monsters"]
            encounters_map[node.title] = enc_entry

        elif node.node_type == "quest":
            quest_entry = quests_map.get(node.title, {
                "title": node.title,
                "act": "Atto 1",
                "description": d.get("read_aloud", ""),
                "objectives": d.get("objectives", []),
                "rewards": d.get("loot", ""),
                "status": "Attiva"
            })
            quest_entry["description"] = d.get("read_aloud", quest_entry.get("description", ""))
            if "objectives" in d:
                quest_entry["objectives"] = d["objectives"]
            if "loot" in d:
                quest_entry["rewards"] = d["loot"]
            quests_map[node.title] = quest_entry

        elif node.node_type == "npc":
            npc_entry = npcs_map.get(node.title, {
                "name": node.title,
                "role": d.get("role", "Comune"),
                "alignment": d.get("alignment", "Neutrale"),
                "notes": d.get("notes", "") or d.get("read_aloud", "")
            })
            npc_entry["role"] = d.get("role", npc_entry.get("role", "Comune"))
            npc_entry["alignment"] = d.get("alignment", npc_entry.get("alignment", "Neutrale"))
            npcs_map[node.title] = npc_entry

        elif node.node_type == "shop":
            items = d.get("items", [])
            wares = d.get("wares", "")
            if items and not wares:
                wares = ", ".join(items) if isinstance(items, list) else str(items)
            shops_map[node.title] = {
                "name": node.title,
                "merchant": d.get("merchant", "Mercante"),
                "shop_type": d.get("shop_type", "Beni Generali"),
                "wares": wares,
                "inventory": items if isinstance(items, list) else ([wares] if wares else [])
            }

        elif node.node_type == "lore":
            if node.title not in handouts_map:
                handouts_map[node.title] = {
                    "title": node.title,
                    "description": d.get("read_aloud", "") or d.get("notes", ""),
                    "content": d.get("read_aloud", "") or d.get("notes", ""),
                    "image_path": d.get("map_file", ""),
                    "author": d.get("author", "Anonimo"),
                    "language": d.get("language", "Comune")
                }

        # Estrai segreti, trappole ed enigmi per il compendio DM
        if node.node_type == "check":
            all_secrets.append(f"• [PROVA] {node.title}: {d.get('ability', 'Abilità')} CD {d.get('cd', 10)}")
        elif node.node_type == "trap":
            all_secrets.append(f"• [TRAPPOLA] {node.title}: Danno {d.get('damage', '2d10')} | {d.get('save', 'TS Destrezza')}")
        elif node.node_type == "puzzle":
            clue = d.get("clue", "")
            sol = d.get("solution", "")
            diff = d.get("difficulty", "Media")
            all_secrets.append(f"• [ENIGMA] {node.title} (Diff: {diff}): Indizio \"{clue}\" | Soluzione \"{sol}\"")

        if "secrets" in d:
            for s in d["secrets"]:
                chk = f" [{s['check']}]" if s.get("check") else ""
                all_secrets.append(f"• ({node.title}) {s.get('type', 'SEGRETO')}{chk}: {s.get('text', '')}")

    campaign.scenes = list(scenes_map.values())
    campaign.encounters = list(encounters_map.values())
    campaign.quests = list(quests_map.values())
    campaign.npcs = list(npcs_map.values())
    campaign.shops = shops_map
    campaign.handouts = list(handouts_map.values())

    if all_secrets:
        header = "=== ENIGMI & PROVE DELLA CAMPAGNA ===\n"
        sec_block = header + "\n".join(all_secrets)
        if not campaign.dm_notes:
            campaign.dm_notes = sec_block
        elif "ENIGMI & PROVE DELLA CAMPAGNA" not in campaign.dm_notes:
            campaign.dm_notes = campaign.dm_notes.rstrip() + "\n\n" + sec_block


def generate_flow_from_campaign(campaign: Any) -> FlowGraph:
    graph = FlowGraph()
    x_cursor = 100.0
    y_cursor = 100.0

    hub_id = "node_hub"
    hub_node = FlowNode(
        id=hub_id,
        node_type="hook",
        title=campaign.name or "Inizio Campagna",
        x=x_cursor,
        y=y_cursor,
        data={
            "read_aloud": getattr(campaign, "description", ""),
            "weather": getattr(campaign, "start_weather", "Sereno")
        }
    )
    graph.nodes[hub_id] = hub_node
    x_cursor += 300.0

    scene_ids = []
    for sc in getattr(campaign, "scenes", []):
        sc_title = sc.get("name", "Scena")
        sc_id = f"scene_{len(graph.nodes) + 1}"
        s_node = FlowNode(
            id=sc_id,
            node_type="scene",
            title=sc_title,
            x=x_cursor,
            y=y_cursor,
            data={
                "map_file": sc.get("map_file", "maps/faerun.json"),
                "read_aloud": sc.get("description", "")
            }
        )
        graph.nodes[sc_id] = s_node
        scene_ids.append(sc_id)
        if len(scene_ids) == 1:
            graph.edges.append(FlowEdge(from_id=hub_id, to_id=sc_id, label="Inizio"))
        y_cursor += 180.0

    x_cursor += 300.0
    y_cursor = 100.0
    for enc in getattr(campaign, "encounters", []):
        enc_title = enc.get("name", "Incontro")
        enc_id = f"enc_{len(graph.nodes) + 1}"
        e_node = FlowNode(
            id=enc_id,
            node_type="encounter",
            title=enc_title,
            x=x_cursor,
            y=y_cursor,
            data={
                "read_aloud": enc.get("description", ""),
                "monsters": enc.get("monsters", [])
            }
        )
        graph.nodes[enc_id] = e_node
        if scene_ids:
            graph.edges.append(FlowEdge(from_id=scene_ids[0], to_id=enc_id, label="Ingaggio"))
        y_cursor += 180.0

    x_cursor += 300.0
    y_cursor = 100.0
    for q in getattr(campaign, "quests", []):
        q_title = q.get("title", "Missione")
        q_id = f"quest_{len(graph.nodes) + 1}"
        q_node = FlowNode(
            id=q_id,
            node_type="quest",
            title=q_title,
            x=x_cursor,
            y=y_cursor,
            data={
                "read_aloud": q.get("description", ""),
                "objectives": q.get("objectives", []),
                "loot": q.get("rewards", "")
            }
        )
        graph.nodes[q_id] = q_node
        y_cursor += 180.0

    return graph
