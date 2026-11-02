# common/campaign_journal.py
"""
Modulo per il Diario Narrativo di Campagna (Multi-Session Campaign Journal).
Memorizza la cronologia continuativa di tutte le sessioni svolte,
sintetizza gli avvenimenti in prosa narrativa pulita (senza eccessi bardici né numeri asettici),
consente la modifica manuale da parte del DM, la sincronizzazione con i giocatori
e l'esportazione in Markdown, Discord e HTML pergamena bilingue (IT/EN).
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
import html

HARPTOS_MONTHS = [
    "", "Hammer", "Alturiak", "Ches", "Tarsakh", "Mirtul", "Kythorn",
    "Flamerule", "Eleasis", "Eleint", "Marpenoth", "Uktar", "Nightal"
]

HARPTOS_MONTHS_IT = [
    "", "Hammer (Profondo Inverno)", "Alturiak (L'Artiglio dell'Inverno)",
    "Ches (Il Tramonto)", "Tarsakh (Le Tempeste)", "Mirtul (Lo Scongelamento)",
    "Kythorn (Il Tempo dei Fiori)", "Flamerule (La Marea del Fuoco)",
    "Eleasis (Il Cielo Alto)", "Eleint (L'Affievolirsi)",
    "Marpenoth (La Caduta delle Foglie)", "Uktar (Il Marcire)", "Nightal (La Notte)"
]


def format_game_date(date_data: Any, language: str = "it") -> str:
    """Formatta la data di gioco (calendario Harptos o stringa generica)."""
    if not date_data:
        return "Data sconosciuta" if language == "it" else "Unknown date"
    if isinstance(date_data, str):
        return date_data
    if isinstance(date_data, dict):
        y = date_data.get("year", 1492)
        m = date_data.get("month", 1)
        d = date_data.get("day", 1)
        h = date_data.get("hour", 8)
        minute = date_data.get("minute", 0)
        months = HARPTOS_MONTHS_IT if language == "it" else HARPTOS_MONTHS
        m_name = months[m] if 1 <= m <= 12 else f"Mese {m}"
        time_str = f"Ore {h:02d}:{minute:02d}" if language == "it" else f"{h:02d}:{minute:02d}"
        return f"{d} {m_name}, {y} CV — {time_str}"
    return str(date_data)


@dataclass
class JournalEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    category: str = "generic"  # combat, exploration, door, trap, discovery, loot, rest, death, note
    title: str = ""
    description: str = ""
    actor: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "actor": self.actor,
            "data": dict(self.data)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalEvent":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            timestamp=data.get("timestamp", ""),
            category=data.get("category", "generic"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            actor=data.get("actor", ""),
            data=data.get("data", {})
        )


class JournalSession:
    """Rappresenta una singola sessione all'interno del Diario Continuativo di Campagna."""
    def __init__(
        self,
        session_number: int = 1,
        title: str = "",
        real_date: Optional[str] = None,
        game_date: Any = None,
        weather: str = "",
        location: str = "",
        prose: str = "",
        dm_notes: str = "",
        session_id: Optional[str] = None,
        is_concluded: bool = False
    ):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_number = session_number
        self.title = title or (f"Sessione {session_number}" if title == "" else title)
        self.real_date = real_date or datetime.now().strftime("%Y-%m-%d")
        self.game_date = game_date or "1 Ches, 1492 CV"
        self.weather = weather or "Sereno"
        self.location = location or "Faerûn"
        self.prose = prose
        self.dm_notes = dm_notes
        self.events: List[JournalEvent] = []
        self.is_concluded = is_concluded

    def add_event(self, category: str, title: str, description: str = "", actor: str = "", data: Optional[Dict[str, Any]] = None) -> JournalEvent:
        evt = JournalEvent(
            category=category,
            title=title,
            description=description,
            actor=actor,
            data=data or {}
        )
        self.events.append(evt)
        return evt

    def to_dict(self, include_dm_notes: bool = True) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_number": self.session_number,
            "title": self.title,
            "real_date": self.real_date,
            "game_date": self.game_date,
            "weather": self.weather,
            "location": self.location,
            "prose": self.prose,
            "dm_notes": self.dm_notes if include_dm_notes else "",
            "is_concluded": self.is_concluded,
            "events": [e.to_dict() for e in self.events]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JournalSession":
        sess = cls(
            session_number=data.get("session_number", 1),
            title=data.get("title", ""),
            real_date=data.get("real_date", ""),
            game_date=data.get("game_date", ""),
            weather=data.get("weather", "Sereno"),
            location=data.get("location", ""),
            prose=data.get("prose", ""),
            dm_notes=data.get("dm_notes", ""),
            session_id=data.get("session_id"),
            is_concluded=data.get("is_concluded", False)
        )
        sess.events = [JournalEvent.from_dict(e) for e in data.get("events", [])]
        return sess


class CampaignJournal:
    """Gestisce il Diario Continuativo della Campagna multi-sessione."""
    def __init__(self, campaign_name: str = "Campagna"):
        self.campaign_name = campaign_name
        self.sessions: List[JournalSession] = [
            JournalSession(session_number=1, title="Sessione 1")
        ]
        self.active_session_index: int = 0

    def get_active_session(self) -> JournalSession:
        if not self.sessions:
            sess = JournalSession(session_number=1, title=f"Sessione 1")
            self.sessions.append(sess)
            self.active_session_index = 0
            return sess
        if 0 <= self.active_session_index < len(self.sessions):
            return self.sessions[self.active_session_index]
        return self.sessions[-1]

    def get_all_events(self) -> List[JournalEvent]:
        """Restituisce la lista di tutti gli eventi registrati in tutte le sessioni."""
        events = []
        for s in self.sessions:
            events.extend(s.events)
        return events

    def start_new_session(
        self,
        title: str = "",
        real_date: Optional[str] = None,
        game_date: Any = None,
        weather: str = "",
        location: str = ""
    ) -> JournalSession:
        """Inizia una nuova sessione continuativa, preservando le precedenti."""
        if self.sessions and not self.sessions[-1].is_concluded:
            # Se la sessione precedente ha una sintesi non ancora generata, sintetizzala
            if not self.sessions[-1].prose:
                self.sessions[-1].prose = self.synthesize_prose(len(self.sessions) - 1)
            self.sessions[-1].is_concluded = True

        next_num = len(self.sessions) + 1
        new_sess = JournalSession(
            session_number=next_num,
            title=title or f"Sessione {next_num}",
            real_date=real_date or datetime.now().strftime("%Y-%m-%d"),
            game_date=game_date or (self.sessions[-1].game_date if self.sessions else "1 Ches, 1492 CV"),
            weather=weather or (self.sessions[-1].weather if self.sessions else "Sereno"),
            location=location or (self.sessions[-1].location if self.sessions else "Faerûn"),
            is_concluded=False
        )
        self.sessions.append(new_sess)
        self.active_session_index = len(self.sessions) - 1
        return new_sess

    def conclude_active_session(self, language: str = "it") -> JournalSession:
        active = self.get_active_session()
        active.is_concluded = True
        if not active.prose.strip():
            active.prose = self.synthesize_prose(self.active_session_index, language=language)
        return active

    def record_event(
        self,
        category: str,
        title: str,
        description: str = "",
        actor: str = "",
        data: Optional[Dict[str, Any]] = None
    ) -> JournalEvent:
        active = self.get_active_session()
        return active.add_event(category, title, description, actor, data)

    def synthesize_prose(self, session_index: int = -1, language: str = "it") -> str:
        """
        Sintetizza gli eventi registrati nella sessione indicata in prosa narrativa da GdR:
        chiara, cronologica e coinvolgente, senza eccessi poetici né elenchi asettici.
        """
        if session_index < 0:
            session_index = self.active_session_index
        if session_index < 0 or session_index >= len(self.sessions):
            return ""

        sess = self.sessions[session_index]
        events = sess.events
        if not events:
            return (
                "*Nessun evento registrato per questa sessione.*"
                if language == "it" else
                "*No events recorded for this session.*"
            )

        # Raggruppamento tematico degli eventi
        combats = [e for e in events if e.category == "combat"]
        doors = [e for e in events if e.category == "door"]
        traps = [e for e in events if e.category == "trap"]
        discoveries = [e for e in events if e.category in ("discovery", "secret")]
        loots = [e for e in events if e.category == "loot"]
        rests = [e for e in events if e.category == "rest"]
        deaths = [e for e in events if e.category == "death"]
        notes = [e for e in events if e.category in ("note", "generic")]

        sections: List[str] = []

        if language == "it":
            # Introduzione / Inquadramento
            date_str = format_game_date(sess.game_date, language="it")
            intro = f"La sessione ha preso avvio nei pressi di **{sess.location}** ({date_str}), sotto un cielo caratterizzato da condizioni di *{sess.weather}*."
            sections.append(intro)

            # 1. Esplorazione & Passaggi
            if doors or discoveries:
                exp_lines = []
                for d in doors:
                    actor_str = f"**{d.actor}**" if d.actor else "Il gruppo"
                    exp_lines.append(f"{actor_str} ha affrontato il passaggio: *{d.title}* ({d.description}).")
                for disc in discoveries:
                    exp_lines.append(f"È stato svelato un dettaglio degno di nota: **{disc.title}**. {disc.description}")
                if exp_lines:
                    sections.append("### 🗺️ Esplorazione & Percorso\n" + " ".join(exp_lines))

            # 2. Pericoli & Trappole
            if traps:
                trap_lines = []
                for t in traps:
                    actor_str = f"**{t.actor}**" if t.actor else "Il gruppo"
                    trap_lines.append(f"Lungo il cammino, {actor_str} ha innescato o individuato un pericolo: *{t.title}*. {t.description}")
                sections.append("### ⚠️ Pericoli & Trappole\n" + " ".join(trap_lines))

            # 3. Fatti d'Arme & Scontri
            if combats or deaths:
                combat_lines = []
                # Sintesi delle battaglie
                kill_events = [e for e in combats if "abbattuto" in e.description.lower() or "sconfitto" in e.description.lower()]
                down_events = [e for e in combats if "0 pv" in e.description.lower() or "caduto" in e.description.lower()]
                general_combat = [e for e in combats if e not in kill_events and e not in down_events]

                for gc in general_combat:
                    combat_lines.append(f"Si è acceso lo scontro: **{gc.title}**. {gc.description}")
                if kill_events:
                    kills_str = ", ".join(f"*{k.description}*" for k in kill_events)
                    combat_lines.append(f"La tenacia del gruppo ha avuto la meglio: {kills_str}.")
                if down_events:
                    downs_str = " ".join(d.description for d in down_events)
                    combat_lines.append(f"Il prezzo della vittoria è stato alto: {downs_str}")
                sections.append("### ⚔️ Fatti d'Arme & Combattimenti\n" + " ".join(combat_lines))

            # 4. Spoglie & Ricompense
            if loots:
                loot_lines = []
                for l in loots:
                    actor_str = f"**{l.actor}**" if l.actor else "Il gruppo"
                    loot_lines.append(f"{actor_str} ha ispezionato l'area rinvenendo: *{l.description}*.")
                sections.append("### 💰 Spoglie & Tesori\n" + " ".join(loot_lines))

            # 5. Riposi e Chiusura
            if rests:
                rest_lines = []
                for r in rests:
                    actor_str = f"**{r.actor}**" if r.actor else "La compagnia"
                    rest_lines.append(f"{actor_str} si è concessa un momento di sosta: *{r.title}* ({r.description}).")
                sections.append("### 🏕️ Bivacco & Riposo\n" + " ".join(rest_lines))

            # Note aggiuntive
            if notes:
                note_lines = [f"- {n.title}: {n.description}" for n in notes]
                sections.append("### 📜 Momenti Salienti & Memorie\n" + "\n".join(note_lines))

        else:
            # English Synthesis
            date_str = format_game_date(sess.game_date, language="en")
            intro = f"The session began near **{sess.location}** ({date_str}), under a sky marked by *{sess.weather}* conditions."
            sections.append(intro)

            if doors or discoveries:
                exp_lines = []
                for d in doors:
                    actor_str = f"**{d.actor}**" if d.actor else "The party"
                    exp_lines.append(f"{actor_str} tackled the passage: *{d.title}* ({d.description}).")
                for disc in discoveries:
                    exp_lines.append(f"A notable discovery was made: **{disc.title}**. {disc.description}")
                if exp_lines:
                    sections.append("### 🗺️ Exploration & Journey\n" + " ".join(exp_lines))

            if traps:
                trap_lines = []
                for t in traps:
                    actor_str = f"**{t.actor}**" if t.actor else "The group"
                    trap_lines.append(f"Along the trail, {actor_str} encountered a hazard: *{t.title}*. {t.description}")
                sections.append("### ⚠️ Hazards & Traps\n" + " ".join(trap_lines))

            if combats or deaths:
                combat_lines = []
                kill_events = [e for e in combats if "abbattuto" in e.description.lower() or "defeated" in e.description.lower() or "slain" in e.description.lower()]
                down_events = [e for e in combats if "0 pv" in e.description.lower() or "0 hp" in e.description.lower() or "fell" in e.description.lower()]
                general_combat = [e for e in combats if e not in kill_events and e not in down_events]

                for gc in general_combat:
                    combat_lines.append(f"Battle erupted: **{gc.title}**. {gc.description}")
                if kill_events:
                    kills_str = ", ".join(f"*{k.description}*" for k in kill_events)
                    combat_lines.append(f"The party's resolve prevailed: {kills_str}.")
                if down_events:
                    downs_str = " ".join(d.description for d in down_events)
                    combat_lines.append(f"The toll was heavy: {downs_str}")
                sections.append("### ⚔️ Battles & Skirmishes\n" + " ".join(combat_lines))

            if loots:
                loot_lines = []
                for l in loots:
                    actor_str = f"**{l.actor}**" if l.actor else "The party"
                    loot_lines.append(f"{actor_str} scavenged the area, securing: *{l.description}*.")
                sections.append("### 💰 Spoils & Treasure\n" + " ".join(loot_lines))

            if rests:
                rest_lines = []
                for r in rests:
                    actor_str = f"**{r.actor}**" if r.actor else "The company"
                    rest_lines.append(f"{actor_str} took time to rest and recover: *{r.title}* ({r.description}).")
                sections.append("### 🏕️ Camp & Rest\n" + " ".join(rest_lines))

            if notes:
                note_lines = [f"- {n.title}: {n.description}" for n in notes]
                sections.append("### 📜 Key Highlights & Lore\n" + "\n".join(note_lines))

        return "\n\n".join(sections)

    def export_session_markdown(self, session_index: int = -1, language: str = "it", include_dm_notes: bool = False) -> str:
        if session_index < 0:
            session_index = self.active_session_index
        if session_index < 0 or session_index >= len(self.sessions):
            return ""

        sess = self.sessions[session_index]
        lines = []
        lines.append(f"## {sess.title}")
        lines.append(f"**Data Reale / Real Date:** `{sess.real_date}` | **Mondo / World:** {format_game_date(sess.game_date, language)} | **Meteo:** {sess.weather}")
        lines.append(f"**Luogo / Location:** *{sess.location}*\n")

        prose = sess.prose.strip() or self.synthesize_prose(session_index, language=language)
        lines.append(prose)

        if include_dm_notes and sess.dm_notes.strip():
            lines.append("\n---\n#### 🔒 Note Riservate del Master")
            lines.append(f"> {sess.dm_notes.strip()}")

        return "\n".join(lines)

    def export_full_markdown(self, language: str = "it", include_dm_notes: bool = False) -> str:
        """Esporta l'intera cronistoria cumulativa di tutte le sessioni svolte."""
        title = f"# 📖 Cronache di Campagna: {self.campaign_name}" if language == "it" else f"# 📖 Campaign Chronicles: {self.campaign_name}"
        lines = [title, ""]
        if not self.sessions:
            lines.append("*Nessuna sessione ancora registrata.*" if language == "it" else "*No sessions recorded yet.*")
            return "\n".join(lines)

        for idx in range(len(self.sessions)):
            lines.append(self.export_session_markdown(idx, language=language, include_dm_notes=include_dm_notes))
            lines.append("\n---\n")

        return "\n".join(lines)

    def export_discord(self, session_index: int = -1, language: str = "it") -> str:
        """Esporta il recap compatto formattato per Discord/WhatsApp."""
        if session_index < 0:
            session_index = self.active_session_index
        if session_index < 0 or session_index >= len(self.sessions):
            return ""

        sess = self.sessions[session_index]
        lines = []
        lines.append(f"📜 **{self.campaign_name} — {sess.title}**")
        lines.append(f"🗓️ *{sess.real_date}* | 🧭 *{sess.location}* | 🌤️ *{sess.weather}*")
        lines.append("────────────────────────")

        prose = sess.prose.strip() or self.synthesize_prose(session_index, language=language)
        lines.append(prose)
        lines.append("────────────────────────")
        return "\n".join(lines)

    def export_html(self, session_index: Optional[int] = None, language: str = "it", include_dm_notes: bool = False) -> str:
        """Esporta il diario in una pergamena medievale HTML completa con tipografia Dark Fantasy."""
        title = self.campaign_name
        if session_index is not None and 0 <= session_index < len(self.sessions):
            sessions_to_render = [(session_index, self.sessions[session_index])]
        else:
            sessions_to_render = list(enumerate(self.sessions))

        content_html_parts = []
        for idx, sess in sessions_to_render:
            sess_prose = sess.prose.strip() or self.synthesize_prose(idx, language=language)
            # Conversione Markdown minimale in HTML
            paragraphs = []
            for block in sess_prose.split("\n\n"):
                block = block.strip()
                if not block:
                    continue
                if block.startswith("### "):
                    paragraphs.append(f"<h3>{html.escape(block[4:])}</h3>")
                elif block.startswith("## "):
                    paragraphs.append(f"<h2>{html.escape(block[3:])}</h2>")
                else:
                    # grassetto e corsivo
                    formatted = html.escape(block)
                    import re
                    formatted = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', formatted)
                    formatted = re.sub(r'\*(.+?)\*', r'<em>\1</em>', formatted)
                    paragraphs.append(f"<p>{formatted}</p>")

            dm_block = ""
            if include_dm_notes and sess.dm_notes.strip():
                dm_escaped = html.escape(sess.dm_notes.strip()).replace('\n', '<br>')
                dm_block = f"""
                <div class="dm-notes">
                    <strong>🔒 Note del Dungeon Master:</strong><br>
                    {dm_escaped}
                </div>
                """

            sess_html = f"""
            <article class="session-card">
                <header class="session-header">
                    <h2>{html.escape(sess.title)}</h2>
                    <div class="session-meta">
                        <span>🗓️ {html.escape(sess.real_date)}</span>
                        <span>🧭 {html.escape(sess.location)}</span>
                        <span>🌤️ {html.escape(sess.weather)}</span>
                        <span>⏳ {html.escape(format_game_date(sess.game_date, language))}</span>
                    </div>
                </header>
                <div class="session-body">
                    {''.join(paragraphs)}
                </div>
                {dm_block}
            </article>
            """
            content_html_parts.append(sess_html)

        html_out = f"""<!DOCTYPE html>
<html lang="{language}">
<head>
    <meta charset="UTF-8">
    <title>Cronache di Campagna — {html.escape(title)}</title>
    <style>
        body {{
            background-color: #120e0a;
            color: #e6d5bc;
            font-family: 'Georgia', 'Garamond', serif;
            line-height: 1.65;
            margin: 0;
            padding: 40px 20px;
        }}
        .parchment {{
            max-width: 900px;
            margin: 0 auto;
            background: #1e1711;
            border: 2px solid #8c6d3b;
            box-shadow: 0 0 25px rgba(0,0,0,0.8), inset 0 0 40px rgba(0,0,0,0.5);
            padding: 50px;
            border-radius: 8px;
        }}
        h1 {{
            text-align: center;
            color: #d4af37;
            font-size: 2.4em;
            letter-spacing: 2px;
            border-bottom: 2px solid #8c6d3b;
            padding-bottom: 15px;
            margin-top: 0;
            text-transform: uppercase;
        }}
        .session-card {{
            margin-bottom: 40px;
            padding-bottom: 30px;
            border-bottom: 1px dashed #5c4323;
        }}
        .session-card:last-child {{
            border-bottom: none;
        }}
        .session-header h2 {{
            color: #f3c267;
            font-size: 1.6em;
            margin-bottom: 8px;
        }}
        .session-meta {{
            font-size: 0.9em;
            color: #a89478;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 20px;
            font-style: italic;
        }}
        h3 {{
            color: #d19a42;
            font-size: 1.2em;
            margin-top: 25px;
            border-left: 3px solid #d19a42;
            padding-left: 10px;
        }}
        p {{
            margin: 10px 0;
            text-align: justify;
        }}
        .dm-notes {{
            background: #2b1f16;
            border-left: 4px solid #a855f7;
            padding: 12px 16px;
            margin-top: 20px;
            border-radius: 4px;
            font-size: 0.95em;
            color: #d8b4fe;
        }}
        @media print {{
            body {{ background: #fff; color: #111; padding: 0; }}
            .parchment {{ background: #fff; border: none; box-shadow: none; padding: 0; }}
            h1, h2, h3 {{ color: #000; }}
            .dm-notes {{ border-left-color: #000; background: #eee; color: #222; }}
        }}
    </style>
</head>
<body>
    <div class="parchment">
        <h1>📖 {html.escape(title)}</h1>
        {''.join(content_html_parts)}
    </div>
</body>
</html>
"""
        return html_out

    def to_dict(self, include_dm_notes: bool = True) -> Dict[str, Any]:
        return {
            "campaign_name": self.campaign_name,
            "active_session_index": self.active_session_index,
            "sessions": [s.to_dict(include_dm_notes=include_dm_notes) for s in self.sessions]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CampaignJournal":
        cj = cls(campaign_name=data.get("campaign_name", "Campagna"))
        cj.active_session_index = data.get("active_session_index", 0)
        cj.sessions = [JournalSession.from_dict(s) for s in data.get("sessions", [])]
        return cj

    def sanitize_for_players(self) -> Dict[str, Any]:
        """Restituisce la struttura serializzata escludendo le note private del DM."""
        return self.to_dict(include_dm_notes=False)
