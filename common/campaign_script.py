# common/campaign_script.py
"""
Motore Flow Graph per DndOmniCompanion.
Gestisce la struttura visuale gerarchica a 2 livelli della campagna:
- Livello 1 (Campagna): Macro-flusso di Scene e passaggi tra luoghi.
- Livello 2 (Scena): Micro-flusso interno con Incontri, Prove, Trappole, PNG, Quest, Tesori, Empori, Handout e Uscite.
Sincronizza direttamente il FlowGraph strutturato verso gli oggetti VTT di Campaign.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import uuid


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
    "exit": {"label": "Uscita Scena", "color": "#20C997", "icon": "🚪"},
    "note": {"label": "Nota", "color": "#495057", "icon": "📝"},
    "off_track": {"label": "Fuori Pista", "color": "#E03131", "icon": "⚡"},
}

EDGE_CONDITIONS = {
    "default": {"label": "Diretto / Standard", "icon": "➡️", "color": "#495057"},
    "success": {"label": "Successo", "icon": "✅", "color": "#2FB344"},
    "failure": {"label": "Fallimento", "icon": "❌", "color": "#E03131"},
    "check": {"label": "Se [Abilità CD]", "icon": "🎲", "color": "#F59F00"},
    "item": {"label": "Se possiede Oggetto", "icon": "🔑", "color": "#9775FA"},
    "else": {"label": "Altrimenti", "icon": "↩️", "color": "#868E96"},
    "custom": {"label": "Condizione Libera", "icon": "🔀", "color": "#38BDF8"},
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
            "data": dict(self.data),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowNode":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            node_type=d.get("node_type", "note"),
            title=d.get("title", "Senza Titolo"),
            x=float(d.get("x", 0.0)),
            y=float(d.get("y", 0.0)),
            data=dict(d.get("data", {})),
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
            "condition_value": self.condition_value,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowEdge":
        return cls(
            from_id=d.get("from_id", ""),
            to_id=d.get("to_id", ""),
            label=d.get("label", ""),
            condition_type=d.get("condition_type", "default"),
            condition_value=d.get("condition_value", ""),
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
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FlowGraph":
        g = cls()
        g.metadata = dict(d.get("metadata", {}))
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

    def next_node_id(self, prefix: str = "node") -> str:
        idx = len(self.nodes) + 1
        cand = f"{prefix}_{idx}"
        while cand in self.nodes:
            cand = f"{prefix}_{uuid.uuid4().hex[:6]}"
        return cand

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        label: str = "",
        condition_type: str = "default",
        condition_value: str = "",
        allow_duplicate: bool = False,
    ) -> Optional[FlowEdge]:
        if from_id not in self.nodes or to_id not in self.nodes or from_id == to_id:
            return None
        if not allow_duplicate:
            for existing in self.edges:
                if existing.from_id == from_id and existing.to_id == to_id:
                    return existing
        edge = FlowEdge(
            from_id=from_id,
            to_id=to_id,
            label=label,
            condition_type=condition_type or "default",
            condition_value=condition_value,
        )
        self.edges.append(edge)
        return edge

    def remove_edge_at(self, idx: int) -> Optional[FlowEdge]:
        if 0 <= idx < len(self.edges):
            return self.edges.pop(idx)
        return None


# ---------------------------------------------------------------------------
# INTEGRAZIONE CON OGGETTI CAMPAIGN DI D&D OMNICOMPANION
# ---------------------------------------------------------------------------

def _merge_monsters_preserving_stats(existing_monsters: Any, flow_monsters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggiorna i mostri dal nodo preservando HP/XP/iniziativa di mostri gia' configurati."""
    if not flow_monsters:
        return list(existing_monsters) if isinstance(existing_monsters, list) else []
    existing_by_name = {}
    if isinstance(existing_monsters, list):
        for em in existing_monsters:
            if isinstance(em, dict) and em.get("name"):
                existing_by_name[em["name"].strip().lower()] = em
    merged: List[Dict[str, Any]] = []
    for sm in flow_monsters:
        if not isinstance(sm, dict):
            continue
        name = sm.get("name", "Mostro")
        qty = sm.get("quantity", sm.get("count", 1))
        prev = existing_by_name.get(str(name).strip().lower())
        if prev and "hp" not in sm:
            item = dict(prev)
            item["quantity"] = qty
            item["count"] = qty
            merged.append(item)
        else:
            item = dict(sm)
            item.setdefault("count", qty)
            item.setdefault("quantity", qty)
            merged.append(item)
    return merged


def _resolve_loot_fields(d: Dict[str, Any]) -> tuple[Any, Any]:
    """Restituisce (loot_items, loot_currency) risolvendo la stringa loot se necessario."""
    loot_items = d.get("loot_items")
    loot_currency = d.get("loot_currency")
    loot_str = d.get("loot", "")
    if loot_str and (loot_items is None or loot_currency is None):
        from common.srd_offline import parse_loot_specification
        parsed = parse_loot_specification(loot_str)
        if loot_items is None:
            loot_items = parsed.get("items", [])
        if loot_currency is None:
            loot_currency = parsed.get("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
    return (
        loot_items if loot_items is not None else [],
        loot_currency if loot_currency is not None else {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0},
    )


def _extract_graph_entities(
    graph: FlowGraph,
    scenes_map: Dict[str, Dict[str, Any]],
    encounters_map: Dict[str, Dict[str, Any]],
    quests_map: Dict[str, Dict[str, Any]],
    npcs_map: Dict[str, Dict[str, Any]],
    shops_map: Dict[str, Dict[str, Any]],
    treasures_map: Dict[str, Dict[str, Any]],
    handouts_map: Dict[str, Dict[str, Any]],
    factions_map: Dict[str, Dict[str, Any]],
    all_secrets: List[str],
    *,
    scene_scope: str = "",
    allow_scene_registration: bool = True,
) -> None:
    """Estrae e aggiorna le entita' di campagna dai nodi di un FlowGraph senza duplicare logica."""
    for node in graph.nodes.values():
        d = node.data
        if node.node_type == "scene" and allow_scene_registration:
            scene_entry = dict(scenes_map.get(node.title, {
                "name": node.title,
                "map_file": d.get("map_file", "maps/faerun.json"),
                "description": d.get("read_aloud", ""),
            }))
            scene_entry["map_file"] = d.get("map_file", scene_entry.get("map_file", "maps/faerun.json"))
            scene_entry["description"] = d.get("read_aloud", scene_entry.get("description", ""))
            for meta_key in ("weather", "light", "music"):
                if d.get(meta_key):
                    scene_entry[meta_key] = d[meta_key]
                else:
                    scene_entry.pop(meta_key, None)
            scenes_map[node.title] = scene_entry

        elif node.node_type == "encounter":
            loot_items, loot_currency = _resolve_loot_fields(d)
            enc_entry = dict(encounters_map.get(node.title, {
                "name": node.title,
                "act": scene_scope or "Atto 1",
                "description": d.get("read_aloud", ""),
                "monsters": [],
                "loot": d.get("loot", ""),
                "loot_items": loot_items,
                "loot_currency": loot_currency,
            }))
            enc_entry["description"] = d.get("read_aloud", enc_entry.get("description", ""))
            if scene_scope:
                enc_entry["scene"] = scene_scope
            if d.get("cr"):
                enc_entry["cr"] = d["cr"]
            if d.get("music"):
                enc_entry["music"] = d["music"]
            if "monsters" in d and d["monsters"]:
                enc_entry["monsters"] = _merge_monsters_preserving_stats(
                    enc_entry.get("monsters", []), d["monsters"]
                )
            if "loot" in d or "loot_items" in d or "loot_currency" in d:
                enc_entry["loot"] = d.get("loot", "")
                enc_entry["loot_items"] = loot_items
                enc_entry["loot_currency"] = loot_currency
            encounters_map[node.title] = enc_entry

        elif node.node_type == "quest":
            reward_items, reward_currency = _resolve_loot_fields(d)
            quest_entry = dict(quests_map.get(node.title, {
                "title": node.title,
                "act": scene_scope or "Atto 1",
                "description": d.get("read_aloud", ""),
                "objectives": d.get("objectives", []),
                "rewards": d.get("loot", ""),
                "reward_items": reward_items,
                "reward_currency": reward_currency,
                "xp": d.get("xp", 0),
                "status": "Attiva",
            }))
            quest_entry["description"] = d.get("read_aloud", quest_entry.get("description", ""))
            if scene_scope:
                quest_entry["scene"] = scene_scope
            if "objectives" in d:
                quest_entry["objectives"] = list(d["objectives"])
            if "xp" in d:
                quest_entry["xp"] = d["xp"]
            if "loot" in d or "loot_items" in d or "loot_currency" in d:
                quest_entry["rewards"] = d.get("loot", "")
                quest_entry["reward_items"] = reward_items
                quest_entry["reward_currency"] = reward_currency
            quests_map[node.title] = quest_entry

        elif node.node_type == "loot":
            from common.srd_offline import resolve_compendium_item, parse_loot_specification
            resolved = d.get("resolved_items")
            if resolved is None and d.get("items"):
                resolved = [resolve_compendium_item(it) for it in d["items"]]
            gold_spec = d.get("loot_currency")
            if gold_spec is None and d.get("gold"):
                gold_spec = parse_loot_specification(d["gold"])["currency"]
            t_entry = {
                "title": node.title,
                "gold": d.get("gold", ""),
                "currency": gold_spec or {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0},
                "items": list(d.get("items", [])),
                "resolved_items": resolved or [],
            }
            if scene_scope:
                t_entry["scene"] = scene_scope
            treasures_map[node.title] = t_entry

        elif node.node_type == "npc":
            npc_entry = dict(npcs_map.get(node.title, {
                "name": node.title,
                "role": d.get("role", "Comune"),
                "alignment": d.get("alignment", "Neutrale"),
                "faction": d.get("faction", "Neutrale"),
                "notes": d.get("notes", "") or d.get("read_aloud", ""),
            }))
            npc_entry["role"] = d.get("role", npc_entry.get("role", "Comune"))
            npc_entry["alignment"] = d.get("alignment", npc_entry.get("alignment", "Neutrale"))
            if d.get("faction"):
                npc_entry["faction"] = d["faction"]
            if "read_aloud" in d or "notes" in d:
                npc_entry["notes"] = d.get("notes", "") or d.get("read_aloud", "")
            if scene_scope:
                npc_entry["scene"] = scene_scope
            fac_name = str(npc_entry.get("faction", "")).strip()
            if fac_name and fac_name.lower() not in ("", "neutrale", "nessuna") and fac_name not in factions_map:
                factions_map[fac_name] = {
                    "name": fac_name,
                    "alignment": npc_entry.get("alignment", "Neutrale"),
                    "description": "",
                    "allies": "",
                    "enemies": "",
                    "headquarters": scene_scope,
                    "reputation": 0,
                }
            npcs_map[node.title] = npc_entry

        elif node.node_type == "shop":
            from common.srd_offline import resolve_compendium_item
            import re as _re
            items = d.get("items", [])
            wares = d.get("wares", "")
            if items and not wares:
                wares = ", ".join(str(x.get("name", x)) if isinstance(x, dict) else str(x) for x in items) if isinstance(items, list) else str(items)
            inv_list = items if isinstance(items, list) else ([w.strip() for w in wares.split(",") if w.strip()] if wares else [])
            resolved_inv = d.get("resolved_items") or [
                it if isinstance(it, dict) and "price" in it else resolve_compendium_item(it.get("name", "") if isinstance(it, dict) else str(it))
                for it in inv_list
            ]
            normalized_items = []
            for entry in (resolved_inv or inv_list):
                if isinstance(entry, dict):
                    raw_cost = entry.get("price", entry.get("cost", 10))
                    if isinstance(raw_cost, str):
                        m_cost = _re.search(r"(\d+)", raw_cost)
                        price_val = int(m_cost.group(1)) if m_cost else 10
                    else:
                        try:
                            price_val = int(raw_cost)
                        except (ValueError, TypeError):
                            price_val = 10
                    item_copy = dict(entry)
                    item_copy.setdefault("name", entry.get("item", "Oggetto"))
                    item_copy["price"] = max(0, price_val)
                    normalized_items.append(item_copy)
                elif isinstance(entry, str) and entry.strip():
                    normalized_items.append({"name": entry.strip(), "price": 10})
            s_entry = {
                "name": node.title,
                "merchant": d.get("merchant", "Mercante"),
                "shop_type": d.get("shop_type", "Beni Generali"),
                "wares": wares,
                "items": normalized_items,
                "inventory": inv_list,
                "resolved_inventory": resolved_inv,
            }
            if scene_scope:
                s_entry["scene"] = scene_scope
            shops_map[node.title] = s_entry

        elif node.node_type == "lore":
            h_entry = dict(handouts_map.get(node.title, {}))
            txt_val = d.get("read_aloud", "") or d.get("notes", "") or h_entry.get("content", "")
            h_entry.update({
                "title": node.title,
                "description": txt_val,
                "content": txt_val,
                "image_path": d.get("map_file", h_entry.get("image_path", "")),
                "author": d.get("author", h_entry.get("author", "Anonimo")),
                "language": d.get("language", h_entry.get("language", "Comune")),
            })
            if scene_scope:
                h_entry["scene"] = scene_scope
            handouts_map[node.title] = h_entry

        if isinstance(d.get("handouts"), list):
            for hd in d["handouts"]:
                if isinstance(hd, dict):
                    h_title = str(hd.get("title") or hd.get("file") or "Handout").strip()
                    h_file = str(hd.get("file", "") or "").strip()
                    if h_title and h_title not in handouts_map:
                        h_obj = {
                            "title": h_title,
                            "description": d.get("read_aloud", "") or "",
                            "content": d.get("read_aloud", "") or "",
                            "image_path": h_file,
                        }
                        if scene_scope or node.node_type == "scene":
                            h_obj["scene"] = scene_scope or node.title
                        handouts_map[h_title] = h_obj

        # Estrai segreti, trappole ed enigmi per il compendio DM
        prefix_scope = f"[{scene_scope}] " if scene_scope else ""
        if node.node_type == "check":
            all_secrets.append(f"• {prefix_scope}[PROVA] {node.title}: {d.get('ability', 'Abilità')} CD {d.get('cd', 10)}")
        elif node.node_type == "trap":
            all_secrets.append(f"• {prefix_scope}[TRAPPOLA] {node.title}: Danno {d.get('damage', '2d10')} | {d.get('save', 'TS Destrezza')}")
        elif node.node_type == "puzzle":
            clue = d.get("clue", "")
            sol = d.get("solution", "")
            diff = d.get("difficulty", "Media")
            all_secrets.append(f'• {prefix_scope}[ENIGMA] {node.title} (Diff: {diff}): Indizio "{clue}" | Soluzione "{sol}"')

        if "secrets" in d:
            for s in d["secrets"]:
                if isinstance(s, dict):
                    chk = f" [{s['check']}]" if s.get("check") else ""
                    all_secrets.append(f"• {prefix_scope}({node.title}) {s.get('type', 'SEGRETO')}{chk}: {s.get('text', '')}")


DM_SECRETS_MARKER = "=== ENIGMI & PROVE DELLA CAMPAGNA ==="


def merge_dm_notes_sections(manual_source: str, generated_source: str) -> str:
    """Combina la porzione manuale delle note DM con l'eventuale blocco auto-generato degli enigmi."""
    manual_part = str(manual_source or "").split(DM_SECRETS_MARKER)[0].strip()
    gen_str = str(generated_source or "")
    secrets_part = ""
    if DM_SECRETS_MARKER in gen_str:
        secrets_part = gen_str[gen_str.index(DM_SECRETS_MARKER):].strip()
    parts = [p for p in (manual_part, secrets_part) if p]
    return "\n\n".join(parts)


def _finalize_dm_secrets_notes(campaign: Any, all_secrets: List[str]) -> None:
    """Aggiorna (o rimuove se vuota) la sezione automatica enigmi & prove in dm_notes senza duplicarla."""
    sec_block = f"{DM_SECRETS_MARKER}\n" + "\n".join(all_secrets) if all_secrets else ""
    campaign.dm_notes = merge_dm_notes_sections(getattr(campaign, "dm_notes", "") or "", sec_block)


def sync_flow_graph_to_campaign(graph: FlowGraph, campaign: Any):
    """
    Sincronizza le entità del FlowGraph all'interno dell'oggetto Campaign:
    - Nodi Scena ➔ campaign.scenes
    - Nodi Incontro ➔ campaign.encounters
    - Nodi Quest ➔ campaign.quests
    - Nodi PNG ➔ campaign.npcs
    - Nodi Emporio ➔ campaign.shops
    - Nodi Tesoro ➔ campaign.treasures
    - Nodi Documento / Handouts ➔ campaign.handouts
    - Segreti & Trappole ➔ aggregati in campaign.dm_notes
    """
    scenes_map = {s.get("name", ""): s for s in campaign.scenes}
    encounters_map = {e.get("name", ""): e for e in campaign.encounters}
    quests_map = {q.get("title", ""): q for q in campaign.quests}
    npcs_map = {n.get("name", ""): n for n in campaign.npcs}
    shops_map = dict(getattr(campaign, "shops", {}))
    treasures_map = {t.get("title", ""): t for t in getattr(campaign, "treasures", []) if isinstance(t, dict)}
    handouts_map = {h.get("title", ""): h for h in campaign.handouts}
    factions_map = {f.get("name", ""): f for f in getattr(campaign, "factions", []) if isinstance(f, dict)}
    all_secrets: List[str] = []

    _extract_graph_entities(
        graph,
        scenes_map,
        encounters_map,
        quests_map,
        npcs_map,
        shops_map,
        treasures_map,
        handouts_map,
        factions_map,
        all_secrets,
        scene_scope="",
        allow_scene_registration=True,
    )

    campaign.scenes = list(scenes_map.values())
    campaign.encounters = list(encounters_map.values())
    campaign.quests = list(quests_map.values())
    campaign.npcs = list(npcs_map.values())
    if hasattr(campaign, "factions"):
        campaign.factions = list(factions_map.values())
    campaign.shops = shops_map
    campaign.treasures = list(treasures_map.values())
    campaign.handouts = list(handouts_map.values())
    _finalize_dm_secrets_notes(campaign, all_secrets)


def summarize_subflow(subflow_data: Any) -> Dict[str, Any]:
    """Calcola conteggi per tipo e badge testuale compatto del sotto-flusso di una scena."""
    if isinstance(subflow_data, FlowGraph):
        nodes = list(subflow_data.nodes.values())
    elif isinstance(subflow_data, dict):
        raw_nodes = subflow_data.get("nodes", {})
        if isinstance(raw_nodes, dict):
            nodes = [FlowNode.from_dict(n) if isinstance(n, dict) else n for n in raw_nodes.values()]
        elif isinstance(raw_nodes, list):
            nodes = [FlowNode.from_dict(n) if isinstance(n, dict) else n for n in raw_nodes]
        else:
            nodes = []
    else:
        nodes = []

    counts: Dict[str, int] = {"total": len(nodes)}
    for n in nodes:
        t = getattr(n, "node_type", "note")
        counts[t] = counts.get(t, 0) + 1

    icon_order = ["encounter", "check", "trap", "npc", "quest", "lore", "loot", "shop", "puzzle", "exit"]
    parts = []
    for k in icon_order:
        if counts.get(k, 0) > 0:
            icon = NODE_TYPES.get(k, {}).get("icon", "•")
            parts.append(f"{icon}{counts[k]}")
    counts["summary_text"] = " ".join(parts) if parts else ("vuoto" if counts["total"] == 0 else f"{counts['total']} nodi")
    return counts


def get_scene_subflow_graph(scene: Dict[str, Any]) -> FlowGraph:
    """Carica il FlowGraph interno di una scena da subflow_graph."""
    if not isinstance(scene, dict):
        return FlowGraph()
    raw_graph = scene.get("subflow_graph")
    if isinstance(raw_graph, dict) and raw_graph.get("nodes") is not None:
        return FlowGraph.from_dict(raw_graph)
    return FlowGraph()


def save_scene_subflow(scene: Dict[str, Any], sub_graph: FlowGraph) -> Dict[str, Any]:
    """Salva subflow_graph nella scena e restituisce il riepilogo."""
    scene["subflow_graph"] = sub_graph.to_dict()
    scene.pop("subflow_script", None)
    return summarize_subflow(sub_graph)


def sync_macro_edges_from_subflows(macro_graph: FlowGraph, campaign: Any) -> bool:
    """Riflette nel grafo macro le uscite (USCITA o link SCENA) dichiarate dentro le singole scene."""
    scene_node_by_name = {
        n.title.strip().lower(): n.id
        for n in macro_graph.nodes.values()
        if n.node_type == "scene" and n.title.strip()
    }
    existing_pairs = {(e.from_id, e.to_id) for e in macro_graph.edges}
    added = False

    for scene in getattr(campaign, "scenes", []):
        if not isinstance(scene, dict):
            continue
        src_name = scene.get("name", "").strip().lower()
        src_id = scene_node_by_name.get(src_name)
        if not src_id:
            continue
        sub_graph = get_scene_subflow_graph(scene)
        for node in sub_graph.nodes.values():
            if node.node_type in ("exit", "scene"):
                target_name = str(node.data.get("target_scene") or node.title or "").strip()
                dst_id = scene_node_by_name.get(target_name.lower())
                if dst_id and dst_id != src_id and (src_id, dst_id) not in existing_pairs:
                    label = node.title if (node.data.get("target_scene") and node.title != target_name) else "Uscita"
                    macro_graph.edges.append(FlowEdge(from_id=src_id, to_id=dst_id, label=label))
                    existing_pairs.add((src_id, dst_id))
                    added = True
    return added


def sync_hierarchical_campaign_flows(macro_graph: Optional[FlowGraph], campaign: Any) -> FlowGraph:
    """
    Sincronizza il flusso gerarchico a 2 livelli (Livello 1 Scene + Livello 2 Sotto-flussi)
    nell'oggetto Campaign, aggregando incontri, quest, PNG, fazioni, negozi, tesori e handout.
    """
    if macro_graph is None:
        if getattr(campaign, "flow_graph", None) and isinstance(campaign.flow_graph, dict) and campaign.flow_graph.get("nodes"):
            macro_graph = FlowGraph.from_dict(campaign.flow_graph)
        else:
            macro_graph = FlowGraph()

    scenes_map = {s.get("name", ""): dict(s) for s in getattr(campaign, "scenes", []) if isinstance(s, dict) and s.get("name")}
    encounters_map = {e.get("name", ""): dict(e) for e in getattr(campaign, "encounters", []) if isinstance(e, dict) and e.get("name")}
    quests_map = {q.get("title", ""): dict(q) for q in getattr(campaign, "quests", []) if isinstance(q, dict) and q.get("title")}
    npcs_map = {n.get("name", ""): dict(n) for n in getattr(campaign, "npcs", []) if isinstance(n, dict) and n.get("name")}
    shops_map = dict(getattr(campaign, "shops", {}))
    treasures_map = {t.get("title", ""): dict(t) for t in getattr(campaign, "treasures", []) if isinstance(t, dict) and t.get("title")}
    handouts_map = {h.get("title", ""): dict(h) for h in getattr(campaign, "handouts", []) if isinstance(h, dict) and h.get("title")}
    factions_map = {f.get("name", ""): dict(f) for f in getattr(campaign, "factions", []) if isinstance(f, dict) and f.get("name")}
    all_secrets: List[str] = []

    _extract_graph_entities(
        macro_graph,
        scenes_map,
        encounters_map,
        quests_map,
        npcs_map,
        shops_map,
        treasures_map,
        handouts_map,
        factions_map,
        all_secrets,
        scene_scope="",
        allow_scene_registration=True,
    )

    macro_scene_by_name = {
        n.title.strip().lower(): n
        for n in macro_graph.nodes.values()
        if n.node_type == "scene" and n.title.strip()
    }
    for scene_name, scene_entry in list(scenes_map.items()):
        sub_graph = get_scene_subflow_graph(scene_entry)
        if sub_graph.nodes:
            _extract_graph_entities(
                sub_graph,
                scenes_map,
                encounters_map,
                quests_map,
                npcs_map,
                shops_map,
                treasures_map,
                handouts_map,
                factions_map,
                all_secrets,
                scene_scope=scene_name,
                allow_scene_registration=False,
            )
            if not scene_entry.get("subflow_graph"):
                scene_entry["subflow_graph"] = sub_graph.to_dict()
        summary = summarize_subflow(sub_graph)
        m_node = macro_scene_by_name.get(scene_name.strip().lower())
        if m_node:
            m_node.data["subflow_summary"] = summary
            m_node.data["subflow_summary_text"] = summary.get("summary_text", "")
        scenes_map[scene_name] = scene_entry

    campaign.scenes = list(scenes_map.values())
    campaign.encounters = list(encounters_map.values())
    campaign.quests = list(quests_map.values())
    campaign.npcs = list(npcs_map.values())
    if hasattr(campaign, "factions"):
        campaign.factions = list(factions_map.values())
    campaign.shops = shops_map
    campaign.treasures = list(treasures_map.values())
    campaign.handouts = list(handouts_map.values())
    _finalize_dm_secrets_notes(campaign, all_secrets)

    sync_macro_edges_from_subflows(macro_graph, campaign)
    campaign.flow_graph = macro_graph.to_dict()
    return macro_graph


def _build_subflow_from_legacy_entities(campaign: Any, scenes_list: List[Dict[str, Any]]) -> None:
    """Distribuisce le entita' di campagne senza subflow nelle rispettive scene."""
    if not scenes_list:
        return
    per_scene_nodes: Dict[str, FlowGraph] = {s.get("name", ""): FlowGraph() for s in scenes_list}
    scene_names = [s.get("name", "") for s in scenes_list]

    def _pick_scene_name(item: Dict[str, Any], act_hint: str = "") -> str:
        explicit = str(item.get("scene", "")).strip()
        if explicit:
            for sn in scene_names:
                if sn.lower() == explicit.lower():
                    return sn
        hint = str(act_hint or item.get("act", item.get("chapter", ""))).lower()
        if len(scene_names) > 1 and ("atto 2" in hint or "2" in hint or "catacombe" in hint):
            return scene_names[1]
        return scene_names[0]

    def _add_node(sc_name: str, node_type: str, title: str, data: Dict[str, Any]) -> None:
        g = per_scene_nodes.setdefault(sc_name, FlowGraph())
        nid = g.next_node_id(node_type)
        x = 120.0 + (len(g.nodes) % 3) * 260.0
        y = 100.0 + (len(g.nodes) // 3) * 190.0
        prev_id = list(g.nodes.keys())[-1] if g.nodes else None
        g.nodes[nid] = FlowNode(id=nid, node_type=node_type, title=title, x=x, y=y, data=data)
        if prev_id:
            g.edges.append(FlowEdge(from_id=prev_id, to_id=nid))

    for enc in getattr(campaign, "encounters", []):
        if isinstance(enc, dict) and enc.get("name"):
            sc = _pick_scene_name(enc)
            _add_node(sc, "encounter", enc["name"], {
                "read_aloud": enc.get("description", ""),
                "monsters": enc.get("monsters", []),
                "loot": enc.get("loot", ""),
            })
    for q in getattr(campaign, "quests", []):
        if isinstance(q, dict) and q.get("title"):
            sc = _pick_scene_name(q)
            _add_node(sc, "quest", q["title"], {
                "read_aloud": q.get("description", ""),
                "objectives": q.get("objectives", []),
                "loot": q.get("rewards", ""),
            })
    for npc in getattr(campaign, "npcs", []):
        if isinstance(npc, dict) and npc.get("name"):
            sc = _pick_scene_name(npc)
            _add_node(sc, "npc", npc["name"], {
                "role": npc.get("role", "Comune"),
                "alignment": npc.get("alignment", "Neutrale"),
                "faction": npc.get("faction", "Neutrale"),
                "read_aloud": npc.get("notes", ""),
            })
    for ho in getattr(campaign, "handouts", []):
        if isinstance(ho, dict) and ho.get("title"):
            sc = _pick_scene_name(ho)
            _add_node(sc, "lore", ho["title"], {
                "read_aloud": ho.get("content", "") or ho.get("description", ""),
                "map_file": ho.get("image_path", ""),
            })

    for scene in scenes_list:
        sc_name = scene.get("name", "")
        sub_g = per_scene_nodes.get(sc_name, FlowGraph())
        if sub_g.nodes or not scene.get("subflow_graph"):
            save_scene_subflow(scene, sub_g)


def ensure_hierarchical_campaign_flows(campaign: Any) -> FlowGraph:
    """
    Migra automaticamente campagne flat/legacy verso l'architettura gerarchica a 2 livelli:
    - Livello 1 (campaign.flow_graph): macro-flusso di sole Scene.
    - Livello 2 (scene['subflow_graph']): flusso interno di ogni Scena.
    Idempotente: su campagne gia' gerarchiche si limita ad allineare scene e riepiloghi.
    """
    macro_graph = FlowGraph()
    raw_fg = getattr(campaign, "flow_graph", None)
    if isinstance(raw_fg, dict) and raw_fg.get("nodes"):
        macro_graph = FlowGraph.from_dict(raw_fg)

    has_any_subflow = any(
        isinstance(s, dict) and isinstance(s.get("subflow_graph"), dict) and bool(s["subflow_graph"].get("nodes"))
        for s in getattr(campaign, "scenes", [])
    )

    non_scene_nodes = [n for n in macro_graph.nodes.values() if n.node_type != "scene"]
    scene_nodes_in_macro = [n for n in macro_graph.nodes.values() if n.node_type == "scene"]

    # Caso 1: flusso flat legacy (contiene nodi non-scena e nessuna scena ha ancora subflow)
    if macro_graph.nodes and non_scene_nodes and not has_any_subflow:
        new_macro = FlowGraph()
        scene_map: Dict[str, FlowNode] = {}
        if scene_nodes_in_macro:
            for sn in scene_nodes_in_macro:
                cloned = FlowNode.from_dict(sn.to_dict())
                new_macro.nodes[cloned.id] = cloned
                scene_map[cloned.id] = cloned
        else:
            default_sc_name = (
                campaign.scenes[0].get("name", "Scena Iniziale")
                if getattr(campaign, "scenes", None)
                else (getattr(campaign, "name", "") or "Scena Iniziale")
            )
            synth = FlowNode(
                id="scene_1",
                node_type="scene",
                title=default_sc_name,
                x=140.0,
                y=140.0,
                data={"map_file": getattr(campaign, "starting_map_file", None) or "maps/faerun.json"},
            )
            new_macro.nodes[synth.id] = synth
            scene_map[synth.id] = synth

        owner_scene_by_node: Dict[str, str] = {}
        adj: Dict[str, List[str]] = {}
        for edge in macro_graph.edges:
            adj.setdefault(edge.from_id, []).append(edge.to_id)

        for sid in scene_map:
            queue = list(adj.get(sid, []))
            visited = {sid}
            while queue:
                cur_id = queue.pop(0)
                if cur_id in visited or cur_id in scene_map:
                    continue
                visited.add(cur_id)
                owner_scene_by_node.setdefault(cur_id, sid)
                queue.extend(adj.get(cur_id, []))

        last_scene_id = next(iter(scene_map.keys()))
        for nid in macro_graph.nodes:
            if nid in scene_map:
                last_scene_id = nid
            elif nid not in owner_scene_by_node:
                owner_scene_by_node[nid] = last_scene_id

        subgraphs_by_sid: Dict[str, FlowGraph] = {sid: FlowGraph() for sid in scene_map}
        for nid, node in macro_graph.nodes.items():
            if nid in scene_map:
                continue
            owner_sid = owner_scene_by_node[nid]
            subgraphs_by_sid[owner_sid].nodes[nid] = FlowNode.from_dict(node.to_dict())

        macro_edges_seen = set()
        for edge in macro_graph.edges:
            src_sc = edge.from_id if edge.from_id in scene_map else owner_scene_by_node.get(edge.from_id)
            dst_sc = edge.to_id if edge.to_id in scene_map else owner_scene_by_node.get(edge.to_id)
            if edge.from_id in scene_map and edge.to_id in scene_map:
                if (edge.from_id, edge.to_id) not in macro_edges_seen:
                    new_macro.edges.append(FlowEdge(
                        from_id=edge.from_id, to_id=edge.to_id, label=edge.label,
                        condition_type=edge.condition_type, condition_value=edge.condition_value
                    ))
                    macro_edges_seen.add((edge.from_id, edge.to_id))
            elif src_sc and dst_sc and src_sc == dst_sc:
                sub_g = subgraphs_by_sid[src_sc]
                if edge.from_id in sub_g.nodes and edge.to_id in sub_g.nodes:
                    sub_g.edges.append(FlowEdge(
                        from_id=edge.from_id, to_id=edge.to_id, label=edge.label,
                        condition_type=edge.condition_type, condition_value=edge.condition_value
                    ))
            elif src_sc and dst_sc and src_sc != dst_sc:
                if (src_sc, dst_sc) not in macro_edges_seen:
                    new_macro.edges.append(FlowEdge(from_id=src_sc, to_id=dst_sc, label=edge.label or "Passaggio"))
                    macro_edges_seen.add((src_sc, dst_sc))
                if edge.from_id not in scene_map and edge.from_id in subgraphs_by_sid[src_sc].nodes:
                    sub_g = subgraphs_by_sid[src_sc]
                    target_title = scene_map[dst_sc].title
                    exit_id = f"exit_{dst_sc}"
                    if exit_id not in sub_g.nodes:
                        src_n = sub_g.nodes[edge.from_id]
                        sub_g.nodes[exit_id] = FlowNode(
                            id=exit_id, node_type="exit", title=target_title,
                            x=src_n.x + 240.0, y=src_n.y, data={"target_scene": target_title}
                        )
                    sub_g.edges.append(FlowEdge(
                        from_id=edge.from_id, to_id=exit_id, label=edge.label,
                        condition_type=edge.condition_type, condition_value=edge.condition_value
                    ))

        scenes_by_name = {s.get("name", "").lower(): s for s in getattr(campaign, "scenes", []) if isinstance(s, dict)}
        for sid, snode in scene_map.items():
            sc_dict = scenes_by_name.get(snode.title.lower())
            if sc_dict is None:
                sc_dict = {"name": snode.title, "map_file": snode.data.get("map_file", "maps/faerun.json"), "description": snode.data.get("read_aloud", "")}
                campaign.scenes.append(sc_dict)
                scenes_by_name[snode.title.lower()] = sc_dict
            save_scene_subflow(sc_dict, subgraphs_by_sid[sid])

        campaign.flow_graph = new_macro.to_dict()
        return sync_hierarchical_campaign_flows(new_macro, campaign)

    # Caso 2: flusso completamente vuoto
    if not macro_graph.nodes:
        scenes_list = list(getattr(campaign, "scenes", []))
        if not scenes_list and (getattr(campaign, "encounters", None) or getattr(campaign, "quests", None) or getattr(campaign, "npcs", None)):
            default_sc = campaign.ensure_scene_entry("Scena Iniziale", map_file=getattr(campaign, "starting_map_file", None) or "maps/faerun.json")
            scenes_list = [default_sc]

        new_macro = FlowGraph()
        x_cur, y_cur = 120.0, 140.0
        prev_sid = None
        for idx, sc in enumerate(scenes_list):
            if not isinstance(sc, dict):
                continue
            sid = f"scene_{idx + 1}"
            s_node = FlowNode(
                id=sid,
                node_type="scene",
                title=sc.get("name", f"Scena {idx + 1}"),
                x=x_cur,
                y=y_cur,
                data={"map_file": sc.get("map_file", "maps/faerun.json"), "read_aloud": sc.get("description", "")},
            )
            new_macro.nodes[sid] = s_node
            if prev_sid:
                new_macro.edges.append(FlowEdge(from_id=prev_sid, to_id=sid, label="Prosegue"))
            prev_sid = sid
            x_cur += 300.0

        if not has_any_subflow and scenes_list:
            _build_subflow_from_legacy_entities(campaign, scenes_list)

        campaign.flow_graph = new_macro.to_dict()
        return sync_hierarchical_campaign_flows(new_macro, campaign)

    # Caso 3: gia' gerarchico — allinea campaign.scenes e macro_graph
    macro_names = {n.title.strip().lower() for n in scene_nodes_in_macro if n.title.strip()}
    for idx, sc in enumerate(getattr(campaign, "scenes", [])):
        if not isinstance(sc, dict):
            continue
        sc_name = sc.get("name", "").strip()
        if sc_name and sc_name.lower() not in macro_names:
            nid = f"scene_{len(macro_graph.nodes) + idx + 1}"
            while nid in macro_graph.nodes:
                nid = f"scene_{uuid.uuid4().hex[:6]}"
            macro_graph.nodes[nid] = FlowNode(
                id=nid,
                node_type="scene",
                title=sc_name,
                x=120.0 + (len(macro_graph.nodes) % 4) * 280.0,
                y=140.0 + (len(macro_graph.nodes) // 4) * 200.0,
                data={"map_file": sc.get("map_file", "maps/faerun.json"), "read_aloud": sc.get("description", "")},
            )
            macro_names.add(sc_name.lower())

    return sync_hierarchical_campaign_flows(macro_graph, campaign)


def create_starter_sample_flows(campaign: Any) -> FlowGraph:
    """Inizializza una campagna vuota con un modello gerarchico di esempio puro in FlowGraph."""
    macro = FlowGraph()
    sc_locanda = FlowNode(
        id="scene_locanda",
        node_type="scene",
        title="Locanda del Cinghiale",
        x=120.0,
        y=140.0,
        data={
            "map_file": "maps/faerun.json",
            "weather": "Nebbia",
            "light": "Notte",
            "music": "Taverna",
            "read_aloud": "Una locanda calda e fumosa nel villaggio di Rovescuro. I sussurri notturni terrorizzano gli abitanti.",
        },
    )
    sc_cripta = FlowNode(
        id="scene_cripta",
        node_type="scene",
        title="Ingresso Cripta",
        x=440.0,
        y=140.0,
        data={
            "map_file": "maps/cripta.json",
            "read_aloud": "Due pesanti battenti di pietra consumati dal tempo.",
        },
    )
    macro.nodes[sc_locanda.id] = sc_locanda
    macro.nodes[sc_cripta.id] = sc_cripta
    macro.edges.append(FlowEdge(from_id=sc_locanda.id, to_id=sc_cripta.id, label="Se interrogano il locandiere"))
    campaign.flow_graph = macro.to_dict()

    # Sub-flow Scena 1: Locanda del Cinghiale
    sub_locanda = FlowGraph()
    n_voce = FlowNode(
        id="loc_voce",
        node_type="hook",
        title="Voci al Bancone",
        x=100.0,
        y=120.0,
        data={
            "read_aloud": "I clienti bisbigliano di luci spettrali tra le lapidi.",
            "secrets": [{"type": "SEGRETO", "check": "Intuizione CD 12", "text": "Il locandiere è ricattato dal culto."}],
            "handouts": [{"title": "Mappa Cifrata", "file": "mappa_segreta.png"}],
        },
    )
    n_png = FlowNode(
        id="loc_png",
        node_type="npc",
        title="Sindaco Roland",
        x=380.0,
        y=80.0,
        data={"role": "Sindaco del borgo", "alignment": "Legale Buono", "faction": "Ordine dell'Alba"},
    )
    n_quest = FlowNode(
        id="loc_quest",
        node_type="quest",
        title="Sussurri nella Cripta",
        x=660.0,
        y=80.0,
        data={
            "objectives": ["Raggiungi la cripta", "Purifica il santuario"],
            "loot": "100 mo, Pozione di Cura",
            "xp": 300,
        },
    )
    n_exit_c = FlowNode(
        id="loc_exit",
        node_type="exit",
        title="Ingresso Cripta",
        x=380.0,
        y=220.0,
        data={"target_scene": "Ingresso Cripta"},
    )
    for nd in (n_voce, n_png, n_quest, n_exit_c):
        sub_locanda.nodes[nd.id] = nd
    sub_locanda.edges.extend([
        FlowEdge(from_id=n_voce.id, to_id=n_png.id, label="Se cercano il sindaco"),
        FlowEdge(from_id=n_voce.id, to_id=n_exit_c.id, label="Se escono di notte"),
        FlowEdge(from_id=n_png.id, to_id=n_quest.id, label="Accettata la missione"),
    ])
    loc_entry = campaign.ensure_scene_entry(
        sc_locanda.title,
        map_file=sc_locanda.data["map_file"],
        description=sc_locanda.data["read_aloud"],
    )
    save_scene_subflow(loc_entry, sub_locanda)

    # Sub-flow Scena 2: Ingresso Cripta
    sub_cripta = FlowGraph()
    n_enc = FlowNode(
        id="cri_enc",
        node_type="encounter",
        title="Imboscata Lupi",
        x=100.0,
        y=120.0,
        data={
            "monsters": [
                {"name": "Lupo", "quantity": 3, "count": 3},
                {"name": "Lupo Feroce", "quantity": 1, "count": 1},
            ],
            "cr": "2",
            "music": "Combattimento",
            "loot": "Pelli di lupo, 15 mo",
        },
    )
    n_note = FlowNode(
        id="cri_note",
        node_type="note",
        title="Battenti della Cripta",
        x=380.0,
        y=120.0,
        data={
            "read_aloud": "Due pesanti battenti di pietra consumati dal tempo.",
            "secrets": [
                {"type": "SEGRETO", "check": "Arcano CD 14", "text": "Sigillo necromantico inciso sulla pietra."},
                {"type": "TRAPPOLA", "check": "Percezione CD 13", "text": "Lastra a pressione."},
            ],
        },
    )
    n_exit_l = FlowNode(
        id="cri_exit",
        node_type="exit",
        title="Locanda del Cinghiale",
        x=660.0,
        y=120.0,
        data={"target_scene": "Locanda del Cinghiale"},
    )
    for nd in (n_enc, n_note, n_exit_l):
        sub_cripta.nodes[nd.id] = nd
    sub_cripta.edges.extend([
        FlowEdge(from_id=n_enc.id, to_id=n_note.id, label="Superati i lupi"),
        FlowEdge(from_id=n_note.id, to_id=n_exit_l.id, label="Torna in villaggio"),
    ])
    cri_entry = campaign.ensure_scene_entry(
        sc_cripta.title,
        map_file=sc_cripta.data["map_file"],
        description=sc_cripta.data["read_aloud"],
    )
    save_scene_subflow(cri_entry, sub_cripta)

    return ensure_hierarchical_campaign_flows(campaign)


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
            "weather": getattr(campaign, "start_weather", "Sereno"),
        },
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
                "read_aloud": sc.get("description", ""),
            },
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
                "monsters": enc.get("monsters", []),
            },
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
                "loot": q.get("rewards", ""),
            },
        )
        graph.nodes[q_id] = q_node
        y_cursor += 180.0

    return graph
