# common/srd_offline.py
"""
Modulo per la consultazione offline e fallback immediato delle risorse D&D 5e SRD.
Carica e indicizza in memoria i file JSON locali in srd_data/ per:
- Incantesimi (319 incantesimi SRD 5.1)
- Mostri e Creature (oltre 1.000 mostri da SRD, Creature Codex e Tome of Beasts)
- Oggetti Magici (237 oggetti magici SRD)
- Progressione e Privilegi di Livello (Classi core 1-20)

Fornisce supporto bilingue IT/EN trasparente.
"""

import os
import json
import re
import ast
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRD_DIR = os.path.join(BASE_DIR, "srd_data")

# Dizionario traduzione incantesimi più comuni Italiano -> Inglese
SPELL_IT_TO_EN = {
    "dardo incantato": "magic missile",
    "palla di fuoco": "fireball",
    "cura ferite": "cure wounds",
    "scudo": "shield",
    "armatura magica": "mage armor",
    "luce": "light",
    "benedizione": "bless",
    "guarigione": "heal",
    "fulmine": "lightning bolt",
    "invisibilità": "invisibility",
    "invisibilita": "invisibility",
    "volare": "fly",
    "teletrasporto": "teleport",
    "sonno": "sleep",
    "identificare": "identify",
    "individuazione del magico": "detect magic",
    "parola guaritrice": "healing word",
    "raggio di gelo": "ray of frost",
    "scurovisione": "darkvision",
    "velocità": "haste",
    "velocita": "haste",
    "lentezza": "slow",
    "unto": "grease",
    "mani brucianti": "burning hands",
    "passo velato": "misty step",
    "lama infuocata": "flame blade",
    "devastazione": "blight",
    "resurrezione": "resurrection",
    "desiderio": "wish",
    "controincantesimo": "counterspell",
    "dissolvi magie": "dispel magic",
    "esplosione mistica": "eldritch blast",
    "colpo accurato": "true strike",
    "silenzio": "silence",
    "camminare sull'acqua": "water walk",
    "respirare sott'acqua": "water breathing",
    "suggestione": "suggestion",
    "porta dimensionale": "dimension door",
    "muro di fuoco": "wall of fire",
    "muro di forza": "wall of force",
    "muro di ghiaccio": "wall of ice",
    "fermare il tempo": "time stop",
    "caduta morbida": "feather fall",
    "individuazione dei pensieri": "detect thoughts",
    "levitazione": "levitate",
    "spruzzo di colori": "color spray",
    "fiamma perenne": "continual flame",
    "oscurità": "darkness",
    "oscurita": "darkness",
    "luce diurna": "daylight",
}

# Dizionario traduzione mostri più comuni Italiano -> Inglese
MONSTER_IT_TO_EN = {
    "orco": "orc",
    "scheletro": "skeleton",
    "drago": "dragon",
    "drago rosso": "red dragon",
    "drago nero": "black dragon",
    "drago blu": "blue dragon",
    "drago verde": "green dragon",
    "drago bianco": "white dragon",
    "goblin": "goblin",
    "hobgoblin": "hobgoblin",
    "bugbear": "bugbear",
    "zombie": "zombie",
    "ghoul": "ghoul",
    "ghast": "ghast",
    "mummia": "mummy",
    "vampiro": "vampire",
    "licantropo": "werewolf",
    "lupo": "wolf",
    "lupo crudele": "dire wolf",
    "ragno gigante": "giant spider",
    "ragno": "spider",
    "ratto gigante": "giant rat",
    "pipistrello gigante": "giant bat",
    "orso bruno": "brown bear",
    "orso gufo": "owlbear",
    "orsogufo": "owlbear",
    "troll": "troll",
    "ogre": "ogre",
    "gigante delle colline": "hill giant",
    "gigante del fuoco": "fire giant",
    "gigante del gelo": "frost giant",
    "gigante delle tempeste": "storm giant",
    "gargolla": "gargoyle",
    "golem di ferro": "iron golem",
    "golem di pietra": "stone golem",
    "golem di argilla": "clay golem",
    "golem di carne": "flesh golem",
    "idra": "hydra",
    "minotauro": "minotaur",
    "medusa": "medusa",
    "chimera": "chimera",
    "pegaso": "pegasus",
    "grifone": "griffon",
    "ippogrifo": "hippogriff",
    "basilisco": "basilisk",
    "beholder": "beholder",
    "osservatore": "beholder",
    "succube": "succubus",
    "demone": "demon",
    "diavolo": "devil",
    "coboldo": "kobold",
    # Draghi per categoria d'età
    "drago blu antico": "ancient blue dragon",
    "drago rosso antico": "ancient red dragon",
    "drago nero antico": "ancient black dragon",
    "drago verde antico": "ancient green dragon",
    "drago bianco antico": "ancient white dragon",
    "drago d'oro antico": "ancient gold dragon",
    "drago d'argento antico": "ancient silver dragon",
    "drago di bronzo antico": "ancient bronze dragon",
    "drago di rame antico": "ancient copper dragon",
    "drago d'ottone antico": "ancient brass dragon",
    "drago blu adulto": "adult blue dragon",
    "drago rosso adulto": "adult red dragon",
    "drago nero adulto": "adult black dragon",
    "drago verde adulto": "adult green dragon",
    "drago bianco adulto": "adult white dragon",
    "drago d'oro adulto": "adult gold dragon",
    "drago d'argento adulto": "adult silver dragon",
    "drago blu giovane": "young blue dragon",
    "drago rosso giovane": "young red dragon",
    "drago nero giovane": "young black dragon",
    "drago verde giovane": "young green dragon",
    "drago bianco giovane": "young white dragon",
    "cucciolo di drago blu": "blue dragon wyrmling",
    "cucciolo di drago rosso": "red dragon wyrmling",
    "lich": "lich",
    "tarrasque": "tarrasque",
    "tarasque": "tarrasque",
    "scortica menti": "mind flayer",
    "divoratore di menti": "mind flayer",
    "mind flayer": "mind flayer",
}

# Tabella progressione privilegi e slot incantesimo 5e offline
CLASS_PROGRESSION_TABLE = {
    "fighter": {
        "hit_die": 10,
        "features": {
            1: ["Stile di Combattimento (Fighting Style)", "Secondo Fiato (Second Wind)"],
            2: ["Azione Impetuosa (Action Surge - 1 uso)"],
            3: ["Archetipo Marziale (Martial Archetype)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)"],
            6: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            7: ["Privilegio Archetipo Marziale"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Indomito (Indomitable - 1 uso)"],
            10: ["Privilegio Archetipo Marziale"],
            11: ["Attacco Extra (2)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Indomito (Indomitable - 2 usi)"],
            14: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            15: ["Privilegio Archetipo Marziale"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Azione Impetuosa (2 usi)", "Indomito (3 usi)"],
            18: ["Privilegio Archetipo Marziale"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Attacco Extra (3)"],
        }
    },
    "barbarian": {
        "hit_die": 12,
        "features": {
            1: ["Ira (Rage - 2 usi)", "Difesa Senza Armatura (Unarmored Defense)"],
            2: ["Attacco Irruente (Reckless Attack)", "Senso del Pericolo (Danger Sense)"],
            3: ["Cammino Primordiale (Primal Path - Ira 3 usi)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)", "Movimento Veloce (Fast Movement +10 ft)"],
            6: ["Privilegio Cammino Primordiale (Ira 4 usi)"],
            7: ["Istinto Ferino (Feral Instinct)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Critico Brutale (Brutal Critical 1 dado)"],
            10: ["Privilegio Cammino Primordiale"],
            11: ["Ira Implacabile (Relentless Rage)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento - Ira 5 usi)"],
            13: ["Critico Brutale (Brutal Critical 2 dadi)"],
            14: ["Privilegio Cammino Primordiale"],
            15: ["Ira Persistente (Persistent Rage)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Critico Brutale (Brutal Critical 3 dadi - Ira 6 usi)"],
            18: ["Forza Indomabile (Indomitable Might)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Campione Primordiale (Primal Champion +4 FOR, +4 COS - Ira Illimitata)"],
        }
    },
    "rogue": {
        "hit_die": 8,
        "features": {
            1: ["Maestria (Expertise)", "Attacco Furtivo (Sneak Attack 1d6)", "Gergo dei Ladri (Thieves' Cant)"],
            2: ["Azione Scaltra (Cunning Action)"],
            3: ["Archetipo Ladresco (Roguish Archetype)", "Attacco Furtivo (2d6)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Schivata Prodigiosa (Uncanny Dodge)", "Attacco Furtivo (3d6)"],
            6: ["Maestria (Expertise aggiuntiva)"],
            7: ["Evasione (Evasion)", "Attacco Furtivo (4d6)"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (5d6)"],
            10: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            11: ["Dote Affidabile (Reliable Talent)", "Attacco Furtivo (6d6)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (7d6)"],
            14: ["Senso Cieco (Blindsense 10 ft)"],
            15: ["Mente Sfuggente (Slippery Mind)", "Attacco Furtivo (8d6)"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Privilegio Archetipo Ladresco", "Attacco Furtivo (9d6)"],
            18: ["Elusivo (Elusive)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)", "Attacco Furtivo (10d6)"],
            20: ["Colpo di Fortuna (Stroke of Luck)"],
        }
    },
    "wizard": {
        "hit_die": 6,
        "features": {
            1: ["Incantesimi (Spellcasting)", "Recupero Arcano (Arcane Recovery)"],
            2: ["Tradizione Arcana (Arcane Tradition)"],
            3: ["Slot Incantesimo 2° Livello"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Slot Incantesimo 3° Livello"],
            6: ["Privilegio Tradizione Arcana"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Privilegio Tradizione Arcana"],
            11: ["Slot Incantesimo 6° Livello"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Privilegio Tradizione Arcana"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 9° Livello"],
            18: ["Padronanza degli Incantesimi (Spell Mastery)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Incantesimi Personali (Signature Spells)"],
        }
    },
    "cleric": {
        "hit_die": 8,
        "features": {
            1: ["Incantesimi (Spellcasting)", "Dominio Divino (Divine Domain)"],
            2: ["Incanalare Divinità (Channel Divinity 1/riposo)", "Privilegio Dominio Divino"],
            3: ["Slot Incantesimo 2° Livello"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Distruggere Non Morti (CR 1/2)"],
            6: ["Incanalare Divinità (2/riposo)", "Privilegio Dominio Divino"],
            7: ["Slot Incantesimo 4° Livello"],
            8: ["Aumento Punteggi Caratteristica (ASI)", "Distruggere Non Morti (CR 1)"],
            9: ["Slot Incantesimo 5° Livello"],
            10: ["Intervento Divino (Divine Intervention)"],
            11: ["Distruggere Non Morti (CR 2)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 7° Livello"],
            14: ["Distruggere Non Morti (CR 3)"],
            15: ["Slot Incantesimo 8° Livello"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Privilegio Dominio Divino", "Distruggere Non Morti (CR 4)"],
            18: ["Incanalare Divinità (3/riposo)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Intervento Divino Migliorato (Successo Automatico)"],
        }
    },
    "paladin": {
        "hit_die": 10,
        "features": {
            1: ["Percezione del Divino (Divine Sense)", "Imposizione delle Mani (Lay on Hands)"],
            2: ["Stile di Combattimento", "Incantesimi", "Punizione Divina (Divine Smite)"],
            3: ["Salute Divina (Divine Health)", "Giuramento Sacro (Sacred Oath)"],
            4: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            5: ["Attacco Extra (Extra Attack)"],
            6: ["Aura di Protezione (Aura of Protection +CAR a tutti i TS)"],
            7: ["Privilegio Giuramento Sacro"],
            8: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            9: ["Slot Incantesimo 3° Livello"],
            10: ["Aura di Coraggio (Aura of Courage - Immuni a Spaventato)"],
            11: ["Punizione Divina Migliorata (+1d8 radioso a ogni colpo)"],
            12: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            13: ["Slot Incantesimo 4° Livello"],
            14: ["Tocco Purificante (Cleansing Touch)"],
            15: ["Privilegio Giuramento Sacro"],
            16: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            17: ["Slot Incantesimo 5° Livello"],
            18: ["Miglioramento Auree (Raggio esteso a 9m/30ft)"],
            19: ["Aumento Punteggi Caratteristica (ASI / Talento)"],
            20: ["Campione Sacro (Privilegio Apice del Giuramento)"],
        }
    }
}

# Slot incantesimo per incantatori completi (Mago, Chierico, Druido, Bardo, Stregone)
FULL_CASTER_SLOTS = {
    1: {"1": 2},
    2: {"1": 3},
    3: {"1": 4, "2": 2},
    4: {"1": 4, "2": 3},
    5: {"1": 4, "2": 3, "3": 2},
    6: {"1": 4, "2": 3, "3": 3},
    7: {"1": 4, "2": 3, "3": 3, "4": 1},
    8: {"1": 4, "2": 3, "3": 3, "4": 2},
    9: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 1},
    10: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2},
    11: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1},
    12: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1},
    13: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1},
    14: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1},
    15: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1},
    16: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1},
    17: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 2, "6": 1, "7": 1, "8": 1, "9": 1},
    18: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 1, "7": 1, "8": 1, "9": 1},
    19: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 2, "7": 1, "8": 1, "9": 1},
    20: {"1": 4, "2": 3, "3": 3, "4": 3, "5": 3, "6": 2, "7": 2, "8": 1, "9": 1},
}


class OfflineSRD:
    _instance = None
    _spells = None
    _monsters = None
    _magic_items = None

    @classmethod
    def get_instance(cls) -> "OfflineSRD":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_spells(self) -> List[Dict[str, Any]]:
        if self._spells is None:
            path = os.path.join(SRD_DIR, "open5e_spells.json")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._spells = json.load(f)
                except Exception as e:
                    print(f"[SRD_OFFLINE] Errore caricamento open5e_spells.json: {e}")
                    self._spells = []
            else:
                self._spells = []
        return self._spells

    def _load_monsters(self) -> List[Dict[str, Any]]:
        if self._monsters is None:
            self._monsters = []
            for fname in ["open5e_monsters.json", "cc_monsters.json", "tob_monsters.json"]:
                path = os.path.join(SRD_DIR, fname)
                if os.path.isfile(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if isinstance(data, list):
                                for m in data:
                                    if isinstance(m, dict) and "source" not in m:
                                        m["source"] = fname.replace(".json", "").upper()
                                    self._monsters.append(m)
                    except Exception as e:
                        print(f"[SRD_OFFLINE] Errore caricamento {fname}: {e}")
        return self._monsters

    def search_spells(self, query: str, max_results: int = 15) -> List[Dict[str, Any]]:
        """Cerca incantesimi nei dati SRD locali supportando query in italiano o inglese."""
        if not query or not str(query).strip():
            return []
        q = str(query).strip().lower()
        # Risolvi eventuale traduzione nome
        target_en = SPELL_IT_TO_EN.get(q, q)

        spells = self._load_spells()
        candidates = []
        for s in spells:
            name = s.get("name", "")
            name_low = name.lower()
            if target_en in name_low or q in name_low:
                level_val = s.get("level_int")
                if level_val is None:
                    try:
                        level_val = int(s.get("level", 0))
                    except (ValueError, TypeError):
                        level_val = 0
                
                # Punteggio pertinenza (0 = match esatto, 1 = prefisso, 2 = sottostringa)
                score = 0 if name_low == target_en or name_low == q else (1 if name_low.startswith(target_en) or name_low.startswith(q) else 2)

                candidates.append((score, len(name), {
                    "name": name,
                    "level": level_val,
                    "time": s.get("casting_time", "1 Azione"),
                    "range": s.get("range", "9m"),
                    "desc": s.get("desc", ""),
                    "school": s.get("school", ""),
                    "duration": s.get("duration", "Istantanea"),
                    "source": "SRD 5.1 Offline"
                }))

        candidates.sort(key=lambda c: (c[0], c[1]))
        return [c[2] for c in candidates[:max_results]]

    def search_monsters(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Cerca mostri e PNG nei dati SRD locali supportando query in italiano o inglese."""
        if not query or not str(query).strip():
            return []
        q = str(query).strip().lower()
        target_en = MONSTER_IT_TO_EN.get(q, q)

        monsters = self._load_monsters()
        candidates = []
        seen = set()

        for m in monsters:
            name = m.get("name", "")
            name_low = name.lower()
            if target_en in name_low or q in name_low:
                if name_low in seen:
                    continue
                seen.add(name_low)

                hp = m.get("hit_points", 20)
                ac = m.get("armor_class", 10)
                dex = m.get("dexterity", 10)
                cr = m.get("challenge_rating", m.get("cr", "1"))
                src = m.get("source", "SRD")

                # Punteggio pertinenza (0 = match esatto, 1 = prefisso, 2 = sottostringa)
                score = 0 if name_low == target_en or name_low == q else (1 if name_low.startswith(target_en) or name_low.startswith(q) else 2)

                attrs = self.extract_attributes_from_record(m, name)

                candidates.append((score, len(name), {
                    "name": name,
                    "source": f"{src} (Offline)",
                    "summary": f"CR {cr} • CA {ac} • HP {hp}",
                    "monster_data": {
                        "name": name,
                        "hp": hp,
                        "ac": ac,
                        "dex": attrs["DES"],
                        "cr": str(cr),
                        "speed": m.get("speed", "30 ft"),
                        "attributes": attrs,
                        "actions": m.get("actions", []),
                        "special_abilities": m.get("special_abilities", []),
                        "languages": m.get("languages", ""),
                        "senses": m.get("senses", "")
                    }
                }))

        candidates.sort(key=lambda c: (c[0], c[1]))
        return [c[2] for c in candidates[:max_results]]

    def extract_attributes_from_record(self, m: Dict[str, Any], name: str = "") -> Dict[str, int]:
        return extract_and_normalize_attributes(m, name)

    def get_monster(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Restituisce il record completo del mostro (open5e / SRD / CC / TOB) per nome o query."""
        if not name_or_query or not str(name_or_query).strip():
            return None
        raw = str(name_or_query).strip()
        # Rimuove eventuali suffissi numerici di spawning (es. "Ancient Blue Dragon 2" -> "Ancient Blue Dragon")
        clean_name = re.sub(r'\s+\d+$', '', raw).strip().lower()
        target_en = MONSTER_IT_TO_EN.get(clean_name, clean_name)

        monsters = self._load_monsters()
        
        # 1. Match esatto sul nome (o traduzione inglese)
        for m in monsters:
            m_name = m.get("name", "").strip().lower()
            if m_name == clean_name or m_name == target_en:
                return m

        # 2. Match prefisso o sottostringa
        best_match = None
        best_score = 999
        for m in monsters:
            m_name = m.get("name", "").strip().lower()
            if m_name.startswith(target_en) or m_name.startswith(clean_name):
                score = len(m_name)
                if score < best_score:
                    best_score = score
                    best_match = m
            elif (target_en in m_name or clean_name in m_name) and best_match is None:
                best_match = m

        return best_match

    def get_class_level_features(self, char_class: str, level: int) -> Dict[str, Any]:
        """Restituisce privilegi e slot per il livello di una data classe core D&D 5e."""
        c_low = str(char_class).strip().lower()
        # Normalizza nome classe italiano/inglese
        for k_it, k_en in [("guerriero", "fighter"), ("barbaro", "barbarian"), ("ladro", "rogue"),
                           ("mago", "wizard"), ("chierico", "cleric"), ("paladino", "paladin"),
                           ("ranger", "ranger"), ("bardo", "bard"), ("druido", "druid"),
                           ("stregone", "sorcerer"), ("warlock", "warlock"), ("monaco", "monk")]:
            if k_it in c_low or k_en in c_low:
                c_low = k_en
                break

        prog = CLASS_PROGRESSION_TABLE.get(c_low, {})
        features = prog.get("features", {}).get(level, [])
        hit_die = prog.get("hit_die", 8)

        slots = {}
        if c_low in ["wizard", "cleric", "druid", "bard", "sorcerer"]:
            slots = FULL_CASTER_SLOTS.get(level, {})

        return {
            "class": c_low,
            "level": level,
            "hit_die": hit_die,
            "features": features,
            "spell_slots": slots,
            "proficiency_bonus": 2 + (level - 1) // 4
        }


def extract_and_normalize_attributes(source: Any = None, monster_name: str = "") -> Dict[str, int]:
    """
    Estrae e normalizza le caratteristiche di una creatura garantendo che TUTTE le chiavi
    (FOR, DES, COS, INT, SAG, CAR e sinonimi STR, DEX, CON, WIS, CHA) siano popolate
    con i valori corretti da dati esistenti, testo OCR o fallback offline SRD.
    """
    KEY_MAP = {
        "FOR": ["FOR", "STR", "strength", "forza"],
        "DES": ["DES", "DEX", "dexterity", "destrezza"],
        "COS": ["COS", "CON", "constitution", "costituzione"],
        "INT": ["INT", "intelligence", "intelligenza"],
        "SAG": ["SAG", "WIS", "wisdom", "saggezza"],
        "CAR": ["CAR", "CHA", "charisma", "carisma"]
    }

    found_stats = {}

    # 1. Se source è un dizionario (es. monster_data, full_sheet, item_data, api response)
    if isinstance(source, dict):
        attrs_dict = source.get("attributes")
        if isinstance(attrs_dict, dict) and attrs_dict:
            for stat_code, aliases in KEY_MAP.items():
                for alias in aliases:
                    if alias in attrs_dict:
                        try:
                            val = int(attrs_dict[alias])
                            if val > 0:
                                found_stats[stat_code] = val
                                break
                        except (ValueError, TypeError):
                            pass

        for stat_code, aliases in KEY_MAP.items():
            if stat_code not in found_stats:
                for alias in aliases:
                    if alias in source:
                        try:
                            val = int(source[alias])
                            if val > 0:
                                found_stats[stat_code] = val
                                break
                        except (ValueError, TypeError):
                            pass

    # 2. Se source è una stringa (es. testo PDF / OCR del blocco statistiche)
    elif isinstance(source, str) and source.strip():
        txt = source
        patterns = {
            "FOR": r'\b(?:STR|Srn|FOR|Strength)\s*[:\s]?\s*([0-9]{1,2})',
            "DES": r'\b(?:DEX|Dex|Dzx|Drx|DEx|DES|Dexterity)\s*[:\s]?\s*([0-9]{1,2})',
            "COS": r'\b(?:CON|CoH|Cott|Cor\.r|Cor|COS|Constitution)\s*[:\s]?\s*([0-9]{1,2})',
            "INT": r'\b(?:INT|lr\.rr|lrr|lrur|ltlr|lnr|Intelligence)\s*[:\s]?\s*([0-9]{1,2})',
            "SAG": r'\b(?:WIS|Wrs|Wts|SAG|Wisdom)\s*[:\s]?\s*([0-9]{1,2})',
            "CAR": r'\b(?:CHA|Cxl|Cxr|CAR|Charisma)\s*[:\s]?\s*([0-9]{1,2})'
        }
        for stat_code, pat in patterns.items():
            m = re.search(pat, txt, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                    if 1 <= val <= 35:
                        found_stats[stat_code] = val
                except (ValueError, TypeError):
                    pass

    # Se non avevamo monster_name esplicito, prova a leggerlo da source se dizionario
    if not monster_name and isinstance(source, dict):
        monster_name = str(source.get("name") or source.get("title") or "")

    # 3. Fallback intelligente su SRD offline locale:
    # Se mancano statistiche, o sono tutte a 10 (il bug segnalato), consulta il database SRD offline
    stats_all_default_ten = len(found_stats) == 6 and all(v == 10 for v in found_stats.values())
    if (len(found_stats) < 6 or stats_all_default_ten) and monster_name:
        srd_record = OfflineSRD.get_instance().get_monster(monster_name)
        if srd_record:
            srd_stats = {
                "FOR": srd_record.get("strength"),
                "DES": srd_record.get("dexterity"),
                "COS": srd_record.get("constitution"),
                "INT": srd_record.get("intelligence"),
                "SAG": srd_record.get("wisdom"),
                "CAR": srd_record.get("charisma")
            }
            for code, s_val in srd_stats.items():
                if s_val is not None:
                    try:
                        found_stats[code] = int(s_val)
                    except (ValueError, TypeError):
                        pass

    # 4. Imposta default 10 per qualsiasi caratteristica ancora non determinata
    for code in ["FOR", "DES", "COS", "INT", "SAG", "CAR"]:
        if code not in found_stats or found_stats[code] < 1:
            found_stats[code] = 10

    # 5. Restituisce il dizionario completo con sinonimi bilingue (IT/EN)
    full_attrs = {
        "FOR": found_stats["FOR"],
        "DES": found_stats["DES"],
        "COS": found_stats["COS"],
        "INT": found_stats["INT"],
        "SAG": found_stats["SAG"],
        "CAR": found_stats["CAR"],
        "STR": found_stats["FOR"],
        "DEX": found_stats["DES"],
        "CON": found_stats["COS"],
        "WIS": found_stats["SAG"],
        "CHA": found_stats["CAR"],
        "strength": found_stats["FOR"],
        "dexterity": found_stats["DES"],
        "constitution": found_stats["COS"],
        "intelligence": found_stats["INT"],
        "wisdom": found_stats["SAG"],
        "charisma": found_stats["CAR"],
    }
    return full_attrs


# Funzioni comode di modulo
def search_spells_offline(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_spells(query, max_results=max_results)

def search_monsters_offline(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_monsters(query, max_results=max_results)

def get_monster_offline(name: str) -> Optional[Dict[str, Any]]:
    return OfflineSRD.get_instance().get_monster(name)

def get_class_level_features_offline(char_class: str, level: int) -> Dict[str, Any]:
    return OfflineSRD.get_instance().get_class_level_features(char_class, level)


def format_monster_action_tooltip(action: Any, monster_name: str = "") -> str:
    """
    Formatta una stringa di ToolTip ricca e dettagliata per un'azione o attacco di un mostro/PNG,
    evidenziando Tiro per Colpire (TpC), formula e dadi danno, portata/gittata e Tiri Salvezza.
    """
    if not action:
        return "Nessuna informazione disponibile per questa azione."
        
    if isinstance(action, str):
        action_name = action.split(".")[0].strip() if "." in action else "Azione"
        desc = action.strip()
        act_dict = {"name": action_name, "desc": desc}
    elif isinstance(action, dict):
        act_dict = action
        action_name = act_dict.get("name", "Azione")
        desc = act_dict.get("desc", "")
    else:
        return str(action)

    lines = [f"⚔️ {action_name}"]
    tags = []

    # 1. Bonus al tiro per colpire
    atk_bonus = act_dict.get("attack_bonus")
    if atk_bonus is not None and atk_bonus != 0:
        val = int(atk_bonus)
        tags.append(f"🎯 TpC: +{val}" if val >= 0 else f"🎯 TpC: {val}")
    else:
        m_atk = re.search(r'([+-]\d+)\s+to\s+hit', desc, re.I)
        if m_atk:
            tags.append(f"🎯 TpC: {m_atk.group(1)}")

    # 2. Formula Danni e Tipo di Danno
    m_hit = re.search(r'Hit:\s*([0-9]+\s*\([^)]+\)[^.]+)', desc, re.I)
    if m_hit:
        dmg_clean = m_hit.group(1).strip()
        tags.append(f"💥 Danno: {dmg_clean}")
    elif act_dict.get("damage_dice"):
        d_dice = act_dict.get("damage_dice")
        d_bonus = act_dict.get("damage_bonus")
        if d_bonus:
            d_val = f"+{d_bonus}" if int(d_bonus) >= 0 else str(d_bonus)
            tags.append(f"💥 Danno: {d_dice} {d_val}")
        else:
            tags.append(f"💥 Danno: {d_dice}")
    else:
        m_takes = re.search(r'(?:taking|takes)\s+([0-9]+\s*\([^)]+\)\s*[a-zA-Z\s]+damage)', desc, re.I)
        if m_takes:
            tags.append(f"💥 Danno: {m_takes.group(1).strip()}")

    # 3. Portata / Gittata (reach / range)
    m_reach = re.search(r'reach\s+(\d+\s*(?:ft|m)\.?)', desc, re.I)
    m_range = re.search(r'range\s+(\d+(?:/\d+)?\s*(?:ft|m)\.?)', desc, re.I)
    m_area = re.search(r'(\d+[- ]foot\s*(?:line|cone|sphere|cube|radius))', desc, re.I)
    if m_reach:
        tags.append(f"📏 Portata: {m_reach.group(1)}")
    elif m_range:
        tags.append(f"🏹 Gittata: {m_range.group(1)}")
    elif m_area:
        tags.append(f"📐 Area: {m_area.group(1)}")

    # 4. Tiro Salvezza (DC / CD)
    m_dc = re.search(r'DC\s+(\d+)\s+([A-Za-z]+)\s+saving\s+throw', desc, re.I)
    if m_dc:
        stat_en = m_dc.group(2).lower()
        stat_map = {
            "strength": "FOR", "dexterity": "DES", "constitution": "COS",
            "intelligence": "INT", "wisdom": "SAG", "charisma": "CAR"
        }
        stat_label = stat_map.get(stat_en, m_dc.group(2).upper())
        tags.append(f"🛡️ TS: CD {m_dc.group(1)} {stat_label}")

    if tags:
        lines.append("  •  ".join(tags))

    if desc:
        lines.append("─────────────────────────────")
        lines.append(desc)

    return "\n".join(lines)


def normalize_ac_value(ac_data: Any, default: int = 10) -> int:
    """
    Estrae e normalizza un valore numerico intero valido per la Classe Armatura (CA).
    Gestisce formati eterogenei da API D&D 5e, compendi JSON e PDF:
    - int / float: 18 -> 18
    - list di dict: [{'type': 'natural', 'value': 22}] -> 22, [{}] -> default
    - dict: {'value': 18, 'type': 'armor'} -> 18, {'ac': 16} -> 16
    - stringhe: '18 (natural armor)' -> 18, '15' -> 15, '[{}]' -> default
    - liste vuote o annidate: [15] -> 15, [] -> default
    """
    if ac_data is None:
        return default
    if isinstance(ac_data, int):
        return ac_data
    if isinstance(ac_data, float):
        return int(ac_data)

    if isinstance(ac_data, str):
        s = ac_data.strip()
        # Prova a parsare come struttura letterale se contiene parentesi quadre/graffe
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                parsed = ast.literal_eval(s)
                return normalize_ac_value(parsed, default=default)
            except Exception:
                pass
        m = re.search(r'\b\d+\b', s)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                pass
        return default

    if isinstance(ac_data, list):
        for item in ac_data:
            val = normalize_ac_value(item, default=None)
            if val is not None:
                return val
        return default

    if isinstance(ac_data, dict):
        for key in ("value", "ac", "armor_class", "val"):
            if key in ac_data:
                val = normalize_ac_value(ac_data[key], default=None)
                if val is not None:
                    return val
        for v in ac_data.values():
            val = normalize_ac_value(v, default=None)
            if val is not None:
                return val
        return default

    return default


def normalize_speed_value(speed_data: Any, default_unit: Optional[str] = None) -> tuple:
    """
    Estrae e normalizza la velocità della creatura in:
      (speed_val: int, speed_display: str, speed_unit: str)
    - speed_val: intero pulito per la velocità base (es. 30 o 40 o 9)
    - speed_display: stringa descrittiva per tutti i movimenti (es. '40 ft • Volo 80 ft')
    - speed_unit: unità ('ft' o 'm')
    Non restituisce MAI rappresentazioni json grezze come '{}' o '[]'.
    """
    if speed_data is None:
        u = default_unit or "ft"
        return 30, f"30 {u}", u

    # Gestione stringhe
    if isinstance(speed_data, str):
        s = speed_data.strip()
        if not s or s in ("{}", "[]", "[{}]", "None"):
            u = default_unit or "ft"
            return 30, f"30 {u}", u

        # Se è una stringa che serializza una lista o dict (es. "[{}]" o "{'walk': '30 ft.'}")
        if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
            try:
                parsed = ast.literal_eval(s)
                return normalize_speed_value(parsed, default_unit=default_unit)
            except Exception:
                pass

        unit = "m" if (" m" in s.lower() or "metr" in s.lower()) else (default_unit or "ft")
        m_first = re.search(r'\b\d+\b', s)
        base_val = int(m_first.group(0)) if m_first else 30

        # Se contiene modalità di movimento o virgole
        if any(w in s.lower() for w in ("fly", "swim", "burrow", "climb", "volo", "nuoto", "scavo", "scalata", ",")):
            cleaned = s
            cleaned = re.sub(r'\bfly\b', 'Volo', cleaned, flags=re.I)
            cleaned = re.sub(r'\bswim\b', 'Nuoto', cleaned, flags=re.I)
            cleaned = re.sub(r'\bburrow\b', 'Scavo', cleaned, flags=re.I)
            cleaned = re.sub(r'\bclimb\b', 'Scalata', cleaned, flags=re.I)
            cleaned = re.sub(r'\bwalk\b', '', cleaned, flags=re.I)
            parts = [p.strip(' .,') for p in re.split(r',\s*(?![^()]*\))', cleaned) if p.strip(' .,')]
            disp = " • ".join(parts) if parts else f"{base_val} {unit}"
            return base_val, disp, unit
        else:
            return base_val, f"{base_val} {unit}", unit

    # Gestione numeri
    if isinstance(speed_data, (int, float)):
        val = int(speed_data)
        u = default_unit or ("m" if val <= 18 else "ft")
        return val, f"{val} {u}", u

    # Gestione liste
    if isinstance(speed_data, list):
        if not speed_data:
            u = default_unit or "ft"
            return 30, f"30 {u}", u
        merged = {}
        for item in speed_data:
            if isinstance(item, dict):
                merged.update(item)
            elif isinstance(item, (int, float, str)):
                return normalize_speed_value(item, default_unit=default_unit)
        if merged:
            return normalize_speed_value(merged, default_unit=default_unit)
        u = default_unit or "ft"
        return 30, f"30 {u}", u

    # Gestione dict (es. {"walk": "40 ft.", "burrow": "40 ft.", "fly": "80 ft."})
    if isinstance(speed_data, dict):
        if not speed_data:
            u = default_unit or "ft"
            return 30, f"30 {u}", u

        all_vals_str = " ".join(str(v) for v in speed_data.values()).lower()
        if " m" in all_vals_str or "metro" in all_vals_str or "metri" in all_vals_str:
            unit = "m"
        elif "ft" in all_vals_str:
            unit = "ft"
        else:
            unit = default_unit or "ft"

        walk_val = speed_data.get("walk") or speed_data.get("walking")
        base_val = 30
        if walk_val is not None:
            m = re.search(r'\d+', str(walk_val))
            if m:
                base_val = int(m.group(0))
        else:
            for k, v in speed_data.items():
                if k == "hover":
                    continue
                m = re.search(r'\d+', str(v))
                if m:
                    base_val = int(m.group(0))
                    break

        parts = []
        if walk_val is not None:
            m = re.search(r'\d+', str(walk_val))
            if m:
                parts.append(f"{m.group(0)} {unit}")
        elif not any(k in speed_data for k in ("fly", "swim", "burrow", "climb")):
            parts.append(f"{base_val} {unit}")

        for mode, lbl in [("fly", "Volo"), ("swim", "Nuoto"), ("burrow", "Scavo"), ("climb", "Scalata")]:
            if mode in speed_data:
                m = re.search(r'\d+', str(speed_data[mode]))
                if m:
                    parts.append(f"{lbl} {m.group(0)} {unit}")

        if speed_data.get("hover") is True or "hover" in str(speed_data.get("fly", "")).lower():
            parts.append("(fluttua)")

        disp = " • ".join(parts) if parts else f"{base_val} {unit}"
        return base_val, disp, unit

    u = default_unit or "ft"
    return 30, f"30 {u}", u


# -----------------------------------------------------------------------------
# FUNZIONI DI MATCHING & FILTRAGGIO RAPIDO (CR, TIPO, RARITÀ, SCUOLA)
# -----------------------------------------------------------------------------

def parse_cr_to_float(cr_val: Any) -> float:
    """Converte un Grado di Sfida (es. '1/2', '1/4', '0', 5, '17') in float."""
    if cr_val is None:
        return 0.0
    s = str(cr_val).strip()
    if "/" in s:
        parts = s.split("/")
        try:
            return float(parts[0]) / float(parts[1])
        except (ValueError, ZeroDivisionError):
            return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def match_monster_cr(cr_val: Any, cr_filter: Optional[str]) -> bool:
    """Verifica se il CR soddisfa il filtro raggruppato."""
    if not cr_filter or cr_filter in ("Tutti i CR", "All CR"):
        return True
    val = parse_cr_to_float(cr_val)
    if "0 - 1/2" in cr_filter:
        return val <= 0.5
    elif "1 - 4" in cr_filter:
        return 1.0 <= val <= 4.0
    elif "5 - 9" in cr_filter:
        return 5.0 <= val <= 9.0
    elif "10 - 14" in cr_filter:
        return 10.0 <= val <= 14.0
    elif "15 - 19" in cr_filter:
        return 15.0 <= val <= 19.0
    elif "20+" in cr_filter:
        return val >= 20.0
    return True


CREATURE_TYPE_MAP = {
    "aberrazione": ["aberration", "aberrazione"],
    "bestia": ["beast", "bestia"],
    "celestiale": ["celestial", "celestiale"],
    "costrutto": ["construct", "costrutto"],
    "drago": ["dragon", "drago"],
    "elementale": ["elemental", "elementale"],
    "fata": ["fey", "fata"],
    "gigante": ["giant", "gigante"],
    "immondo": ["fiend", "immondo", "demon", "devil"],
    "melma": ["ooze", "melma"],
    "mostruosità": ["monstrosity", "mostruosita", "mostro"],
    "non morto": ["undead", "non morto", "non-morto"],
    "pianta": ["plant", "pianta"],
    "umanoide": ["humanoid", "umanoide"],
}


def match_monster_type(raw_type: Any, type_filter: Optional[str]) -> bool:
    """Verifica se la tipologia della creatura soddisfa il filtro bilingue."""
    if not type_filter or type_filter in ("Tutti i Tipi", "All Types"):
        return True
    if raw_type is None:
        return False
    t_str = str(raw_type).strip().lower()
    f_str = type_filter.strip().lower()

    keywords = CREATURE_TYPE_MAP.get(f_str, [f_str])
    return any(k in t_str for k in keywords)


ITEM_RARITY_MAP = {
    "comune": ["common", "comune"],
    "non comune": ["uncommon", "non comune"],
    "raro": ["rare", "raro"],
    "molto raro": ["very rare", "molto raro"],
    "leggendario": ["legendary", "leggendario"],
    "artefatto": ["artifact", "artefatto"],
}


def match_item_rarity(raw_rarity: Any, rarity_filter: Optional[str]) -> bool:
    """Verifica se la rarità dell'oggetto soddisfa il filtro."""
    if not rarity_filter or rarity_filter in ("Tutte le Rarità", "All Rarities"):
        return True
    if raw_rarity is None:
        return False
    r_str = str(raw_rarity).strip().lower()
    f_str = rarity_filter.strip().lower()

    keywords = ITEM_RARITY_MAP.get(f_str, [f_str])
    return any(k in r_str for k in keywords)


ITEM_TYPE_MAP = {
    "arma": ["weapon", "arma", "spada", "arco", "pugnale", "ascia"],
    "armatura": ["armor", "armatura", "scudo", "shield"],
    "pozione": ["potion", "pozione", "olio", "elixir"],
    "pergamena": ["scroll", "pergamena"],
    "anello": ["ring", "anello"],
    "bacchetta/verga": ["wand", "rod", "staff", "bacchetta", "verga", "bastone"],
    "meraviglia": ["wondrous", "meraviglia", "oggetto meraviglioso"],
}


def match_item_type(raw_type: Any, type_filter: Optional[str]) -> bool:
    """Verifica se la categoria dell'oggetto soddisfa il filtro."""
    if not type_filter or type_filter in ("Tutti i Tipi", "All Types"):
        return True
    if raw_type is None:
        return False
    t_str = str(raw_type).strip().lower()
    f_str = type_filter.strip().lower()

    keywords = ITEM_TYPE_MAP.get(f_str, [f_str])
    return any(k in t_str for k in keywords)


SPELL_SCHOOL_MAP = {
    "abiurazione": ["abjuration", "abiurazione"],
    "ammaliamento": ["enchantment", "ammaliamento"],
    "divinazione": ["divination", "divinazione"],
    "evocazione": ["conjuration", "evocazione"],
    "illusione": ["illusion", "illusione"],
    "invocazione": ["evocation", "invocazione"],
    "necromanzia": ["necromancy", "necromanzia"],
    "trasmutazione": ["transmutation", "trasmutazione"],
}


def match_spell_school(raw_school: Any, school_filter: Optional[str]) -> bool:
    """Verifica se la scuola di magia soddisfa il filtro."""
    if not school_filter or school_filter in ("Tutte le Scuole", "All Schools"):
        return True
    if raw_school is None:
        return False
    s_str = str(raw_school).strip().lower()
    f_str = school_filter.strip().lower()

    keywords = SPELL_SCHOOL_MAP.get(f_str, [f_str])
    return any(k in s_str for k in keywords)


def match_spell_level(raw_level: Any, level_filter: Optional[str]) -> bool:
    """Verifica se il livello dell'incantesimo soddisfa il filtro."""
    if not level_filter or level_filter in ("Tutti i Livelli", "All Levels"):
        return True
    if raw_level is None:
        return False
    s_val = str(raw_level).strip().lower()
    f_val = str(level_filter).strip().lower()

    if "trucchetto" in f_val or "cantrip" in f_val or "0" in f_val:
        return s_val in ("0", "cantrip", "trucchetto") or "cantrip" in s_val or "trucchetto" in s_val

    # Estrae il numero del livello dal filtro (es. "Livello 3" -> 3)
    m_f = re.search(r'\d+', f_val)
    m_s = re.search(r'\d+', s_val)
    if m_f and m_s:
        return int(m_f.group(0)) == int(m_s.group(0))
    return f_val in s_val





