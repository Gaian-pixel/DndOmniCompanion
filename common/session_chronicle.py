# common/session_chronicle.py
"""
Modulo per il tracciamento degli eventi di gioco (Event Ledger),
la generazione della Cronistoria della Sessione (Session Chronicle & Recap)
e la retro-integrazione delle azioni 'Fuori Pista' nel grafo della campagna.
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid

from common.campaign_script import FlowNode, FlowEdge, FlowGraph


HARPTOS_MONTHS = ["", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn", "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"]


def format_harptos_date(date_dict: Optional[Dict[str, int]]) -> str:
    if not date_dict:
        return "Data sconosciuta"
    y = date_dict.get("year", 1492)
    m = date_dict.get("month", 1)
    d = date_dict.get("day", 1)
    h = date_dict.get("hour", 8)
    m_name = HARPTOS_MONTHS[m] if 1 <= m <= 12 else f"Mese {m}"
    return f"{d} {m_name}, {y} CV • Ore {h:02d}:00"


@dataclass
class SessionEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: str = "generic"  # node_visit, off_track, combat, secret, loot, dice, time, dm_note
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    title: str = ""
    description: str = ""
    is_off_track: bool = False
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "title": self.title,
            "description": self.description,
            "is_off_track": self.is_off_track,
            "data": dict(self.data)
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionEvent":
        return cls(
            id=d.get("id", str(uuid.uuid4())[:8]),
            event_type=d.get("event_type", "generic"),
            timestamp=d.get("timestamp", ""),
            title=d.get("title", ""),
            description=d.get("description", ""),
            is_off_track=bool(d.get("is_off_track", False)),
            data=d.get("data", {})
        )


@dataclass
class SessionLedger:
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    campaign_name: str = "Campagna D&D"
    real_start_time: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    real_end_time: str = ""
    start_game_date: Dict[str, int] = field(default_factory=lambda: {"year": 1492, "month": 1, "day": 1, "hour": 8})
    current_game_date: Dict[str, int] = field(default_factory=lambda: {"year": 1492, "month": 1, "day": 1, "hour": 8})
    current_weather: str = "Sereno"
    visited_node_ids: List[str] = field(default_factory=list)
    events: List[SessionEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "campaign_name": self.campaign_name,
            "real_start_time": self.real_start_time,
            "real_end_time": self.real_end_time,
            "start_game_date": dict(self.start_game_date),
            "current_game_date": dict(self.current_game_date),
            "current_weather": self.current_weather,
            "visited_node_ids": list(self.visited_node_ids),
            "events": [e.to_dict() for e in self.events]
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SessionLedger":
        led = cls(
            session_id=d.get("session_id", ""),
            campaign_name=d.get("campaign_name", "Campagna D&D"),
            real_start_time=d.get("real_start_time", ""),
            real_end_time=d.get("real_end_time", ""),
            start_game_date=d.get("start_game_date", {}),
            current_game_date=d.get("current_game_date", {}),
            current_weather=d.get("current_weather", "Sereno"),
            visited_node_ids=d.get("visited_node_ids", [])
        )
        for ev in d.get("events", []):
            led.events.append(SessionEvent.from_dict(ev))
        return led

    # -----------------------------------------------------------------------
    # Registrazione Eventi in Tempo Reale
    # -----------------------------------------------------------------------

    def record_node_visit(self, node_id: str, title: str, node_type: str = "scene", is_off_track: bool = False, details: str = ""):
        if node_id not in self.visited_node_ids:
            self.visited_node_ids.append(node_id)
        
        ev_type = "off_track" if is_off_track else "node_visit"
        pfx = "⚡ [FUORI PISTA] " if is_off_track else "🧭 "
        self.events.append(SessionEvent(
            event_type=ev_type,
            title=f"{pfx}{title}",
            description=details,
            is_off_track=is_off_track,
            data={"node_id": node_id, "node_type": node_type}
        ))

    def record_combat(self, title: str, monsters: List[Dict[str, Any]], rounds: int = 1, victory: bool = True, loot: str = "", xp: int = 0, is_off_track: bool = False):
        m_summary = ", ".join([f"{m.get('quantity', 1)}x {m.get('name', 'Nemico')}" for m in monsters]) if monsters else "Nessun mostro specificato"
        status_str = "Vittoria del Party" if victory else "Party in ritirata / Scontro interrotto"
        desc = f"Mostri affrontati: {m_summary} | Durata: {rounds} round | Esito: {status_str}"
        if loot:
            desc += f" | Bottino: {loot}"
        if xp > 0:
            desc += f" | XP: {xp}"

        self.events.append(SessionEvent(
            event_type="combat",
            title=f"⚔️ Scontro: {title}",
            description=desc,
            is_off_track=is_off_track,
            data={"monsters": monsters, "rounds": rounds, "victory": victory, "loot": loot, "xp": xp}
        ))

    def record_secret(self, title: str, check: str, text: str):
        desc = f"Segreto svelato con successo [{check}]: {text}" if check else f"Segreto svelato: {text}"
        self.events.append(SessionEvent(
            event_type="secret",
            title=f"🔒 Scaperta: {title}",
            description=desc,
            data={"check": check, "text": text}
        ))

    def record_loot(self, item_or_gold: str):
        self.events.append(SessionEvent(
            event_type="loot",
            title="🎒 Bottino Ottenuto",
            description=item_or_gold,
            data={"loot": item_or_gold}
        ))

    def record_dice_crit(self, player_name: str, formula: str, is_nat20: bool = True):
        roll_type = "20 NATURALE! (Successo Critico)" if is_nat20 else "1 NATURALE! (Fallimento Critico)"
        icon = "🌟" if is_nat20 else "💀"
        self.events.append(SessionEvent(
            event_type="dice",
            title=f"{icon} Tiro Epico: {player_name}",
            description=f"{player_name} ha tirato un {roll_type} con [{formula}]!",
            data={"player": player_name, "formula": formula, "is_nat20": is_nat20}
        ))

    def record_dm_note(self, note_text: str):
        self.events.append(SessionEvent(
            event_type="dm_note",
            title="📝 Nota del Master",
            description=note_text,
            data={"text": note_text}
        ))

    def record_time_advance(self, hours: int, new_date: Dict[str, int], new_weather: str):
        self.current_game_date = dict(new_date)
        self.current_weather = new_weather
        self.events.append(SessionEvent(
            event_type="time",
            title=f"⏳ Tempo Avanzato (+{hours}h)",
            description=f"Nuova data Harptos: {format_harptos_date(new_date)} | Meteo: {new_weather}",
            data={"hours": hours, "date": new_date, "weather": new_weather}
        ))

    def close_session(self):
        self.real_end_time = datetime.now().strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# GENERATORE REPORT E CRONISTORIA
# ---------------------------------------------------------------------------

class ChronicleGenerator:
    """Genera report eleganti in Markdown, HTML e testo compatto per Discord/WhatsApp."""

    @staticmethod
    def generate_markdown(ledger: SessionLedger, include_dm_notes: bool = True) -> str:
        lines = []
        lines.append(f"# 📜 Cronistoria della Sessione: {ledger.campaign_name}")
        lines.append(f"**Sessione:** `{ledger.session_id}` | **Data Reale:** {ledger.real_start_time}")
        if ledger.real_end_time:
            lines.append(f"**Fine Sessione:** {ledger.real_end_time}")
        
        lines.append(f"\n### ⏳ Tempo nel Mondo (Calendario di Harptos)")
        lines.append(f"- **Inizio:** {format_harptos_date(ledger.start_game_date)}")
        lines.append(f"- **Fine:** {format_harptos_date(ledger.current_game_date)}")
        lines.append(f"- **Meteo Attuale:** {ledger.current_weather}")

        # Sezione 1: Il Percorso & Nodi Visitati
        lines.append("\n---\n### 🧭 Il Viaggio del Party (Nodi & Spostamenti)")
        path_events = [e for e in ledger.events if e.event_type in ("node_visit", "off_track")]
        if path_events:
            for idx, pe in enumerate(path_events, 1):
                marker = "⚡ **[FUORI PISTA]**" if pe.is_off_track else "📍"
                lines.append(f"{idx}. {marker} **{pe.title.replace('⚡ [FUORI PISTA] ', '').replace('🧭 ', '')}** (`{pe.timestamp}`)")
                if pe.description:
                    lines.append(f"   > {pe.description}")
        else:
            lines.append("*Nessuno spostamento formale registrato in sessione.*")

        # Sezione 2: Fatti d'Arme & Combattimenti
        combat_events = [e for e in ledger.events if e.event_type == "combat"]
        if combat_events:
            lines.append("\n---\n### ⚔️ Fatti d'Arme & Combattimenti")
            for ce in combat_events:
                off = " *(Improvvisato)*" if ce.is_off_track else ""
                lines.append(f"- **{ce.title}{off}** (`{ce.timestamp}`): {ce.description}")

        # Sezione 3: Segreti Svelati & Indagini
        secret_events = [e for e in ledger.events if e.event_type == "secret"]
        if secret_events:
            lines.append("\n---\n### 🔒 Scoperte & Misteri Svelati")
            for se in secret_events:
                lines.append(f"- **{se.title}** (`{se.timestamp}`): {se.description}")

        # Sezione 4: Tiri Epici & Critici
        dice_events = [e for e in ledger.events if e.event_type == "dice"]
        if dice_events:
            lines.append("\n---\n### 🎲 Tiri Memorabili")
            for de in dice_events:
                lines.append(f"- {de.title}: {de.description}")

        # Sezione 5: Bottino & Risorse
        loot_events = [e for e in ledger.events if e.event_type == "loot"]
        if loot_events:
            lines.append("\n---\n### 🎒 Bottino & Risorse Acquisite")
            for le in loot_events:
                lines.append(f"- `{le.timestamp}`: {le.description}")

        # Sezione 6: Note del Master (opzionali)
        if include_dm_notes:
            note_events = [e for e in ledger.events if e.event_type == "dm_note"]
            if note_events:
                lines.append("\n---\n### 📝 Appunti del Master & Conseguenze Future")
                for ne in note_events:
                    lines.append(f"- `{ne.timestamp}`: {ne.description}")

        return "\n".join(lines)

    @staticmethod
    def generate_discord_text(ledger: SessionLedger) -> str:
        """Genera un riepilogo accattivante pronto per essere incollato su Discord o WhatsApp."""
        lines = []
        lines.append(f"⚔️ **RECAP SESSIONE: {ledger.campaign_name.upper()}** ⚔️")
        lines.append(f"📅 *{format_harptos_date(ledger.current_game_date)}*")
        lines.append("")
        
        path_events = [e for e in ledger.events if e.event_type in ("node_visit", "off_track")]
        if path_events:
            lines.append("🗺️ **Percorso intrapreso:**")
            path_str = " ➔ ".join([pe.title.replace('⚡ [FUORI PISTA] ', '⚡').replace('🧭 ', '') for pe in path_events])
            lines.append(f"> {path_str}")
            lines.append("")

        combats = [e for e in ledger.events if e.event_type == "combat"]
        if combats:
            lines.append("⚔️ **Scontri affrontati:**")
            for c in combats:
                lines.append(f"• {c.title}: {c.description}")
            lines.append("")

        secrets = [e for e in ledger.events if e.event_type == "secret"]
        if secrets:
            lines.append("🔍 **Scoperte & Indizi:**")
            for s in secrets:
                lines.append(f"• {s.description}")
            lines.append("")

        loot = [e for e in ledger.events if e.event_type == "loot"]
        if loot:
            lines.append("💰 **Bottino raccolto:**")
            for l in loot:
                lines.append(f"• {l.description}")
            lines.append("")

        crits = [e for e in ledger.events if e.event_type == "dice"]
        if crits:
            lines.append("🎲 **Momenti Critici:**")
            for cr in crits:
                lines.append(f"• {cr.description}")
            lines.append("")

        lines.append("✨ *Ci vediamo alla prossima avventura!*")
        return "\n".join(lines)

    @staticmethod
    def generate_html(ledger: SessionLedger) -> str:
        md_text = ChronicleGenerator.generate_markdown(ledger, include_dm_notes=True)
        # Semplice conversione HTML Dark Fantasy
        html_body = md_text.replace("\n", "<br>")
        return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Cronistoria Sessione - {ledger.campaign_name}</title>
<style>
body {{ background-color: #121316; color: #ECEFF1; font-family: 'Segoe UI', Tahoma, sans-serif; padding: 28px; line-height: 1.6; max-width: 900px; margin: 0 auto; }}
h1 {{ color: #D4AF37; border-bottom: 2px solid #A37F2C; padding-bottom: 8px; }}
h3 {{ color: #F59E0B; margin-top: 24px; }}
hr {{ border: 0; height: 1px; background: #2C2E33; margin: 20px 0; }}
strong {{ color: #FFFFFF; }}
code {{ background: #25262B; padding: 2px 6px; border-radius: 4px; color: #F1C40F; font-family: monospace; }}
blockquote {{ border-left: 3px solid #D4AF37; margin: 6px 0; padding-left: 12px; color: #909296; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# RETRO-INTEGRAZIONE DEL FUORI PISTA NEL GRAFO DELLA CAMPAGNA
# ---------------------------------------------------------------------------

def integrate_off_track_events_into_flow(ledger: SessionLedger, graph: FlowGraph) -> List[FlowNode]:
    """
    Scansiona gli eventi Fuori Pista registrati nel ledger e li trasforma
    in Nodi ufficiali e permanenti nel FlowGraph della campagna, collegandoli
    all'ultimo nodo conosciuto. Restituisce la lista dei nuovi nodi creati.
    """
    created_nodes: List[FlowNode] = []
    last_official_id: Optional[str] = None
    
    # Trova l'ultimo nodo ufficiale percorso prima del primo fuori pista
    for node_id in ledger.visited_node_ids:
        if node_id in graph.nodes and graph.nodes[node_id].node_type != "off_track":
            last_official_id = node_id

    off_track_events = [e for e in ledger.events if e.is_off_track]
    
    for idx, ote in enumerate(off_track_events):
        clean_title = ote.title.replace("⚡ [FUORI PISTA] ", "").replace("⚔️ Scontro: ", "").strip()
        
        # Determina il tipo di nodo
        n_type = "off_track"
        if ote.event_type == "combat":
            n_type = "encounter"
        elif "scena" in clean_title.lower() or "mappa" in clean_title.lower():
            n_type = "scene"

        new_id = f"node_off_{len(graph.nodes) + 1}_{clean_title[:8].lower().replace(' ', '_')}"
        
        # Posiziona il nuovo nodo accanto all'ultimo
        ref_node = graph.nodes.get(last_official_id) if last_official_id else None
        new_x = (ref_node.x + 280.0) if ref_node else (150.0 + idx * 240.0)
        new_y = (ref_node.y + 120.0 + idx * 100.0) if ref_node else (400.0 + idx * 100.0)

        node_data = {
            "read_aloud": ote.description,
            "notes": f"Improvvisato dal vivo durante la sessione {ledger.session_id}"
        }
        if ote.event_type == "combat" and "monsters" in ote.data:
            node_data["monsters"] = ote.data["monsters"]

        new_node = FlowNode(
            id=new_id,
            node_type=n_type,
            title=f"{clean_title} (Fuori Pista)",
            x=new_x,
            y=new_y,
            data=node_data
        )

        graph.nodes[new_id] = new_node
        created_nodes.append(new_node)

        # Crea collegamento dal nodo precedente al fuori pista
        if last_official_id:
            graph.edges.append(FlowEdge(
                from_id=last_official_id,
                to_id=new_id,
                label="Deviazione Fuori Pista"
            ))

        # Il nuovo nodo diventa l'ancora per i successivi fuori pista a catena
        last_official_id = new_id

    return created_nodes

