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

                candidates.append((score, len(name), {
                    "name": name,
                    "source": f"{src} (Offline)",
                    "summary": f"CR {cr} • CA {ac} • HP {hp}",
                    "monster_data": {
                        "name": name,
                        "hp": hp,
                        "ac": ac,
                        "dex": dex,
                        "cr": str(cr),
                        "speed": m.get("speed", "30 ft")
                    }
                }))

        candidates.sort(key=lambda c: (c[0], c[1]))
        return [c[2] for c in candidates[:max_results]]

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


# Funzioni comode di modulo
def search_spells_offline(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_spells(query, max_results=max_results)

def search_monsters_offline(query: str, max_results: int = 20) -> List[Dict[str, Any]]:
    return OfflineSRD.get_instance().search_monsters(query, max_results=max_results)

def get_class_level_features_offline(char_class: str, level: int) -> Dict[str, Any]:
    return OfflineSRD.get_instance().get_class_level_features(char_class, level)

