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

# Dizionario traduzione oggetti magici ed equipaggiamento più comuni Italiano -> Inglese
ITEM_IT_TO_EN = {
    "pozione di guarigione": "potion of healing",
    "pozione di cura": "potion of healing",
    "pozione di guarigione maggiore": "potion of greater healing",
    "pozione di guarigione superiore": "potion of greater healing",
    "pozione di guarigione suprema": "potion of supreme healing",
    "pozione di volo": "potion of flying",
    "pozione di invisibilità": "potion of invisibility",
    "pozione di invisibilita": "potion of invisibility",
    "pozione di velocità": "potion of speed",
    "pozione di velocita": "potion of speed",
    "pozione di eroismo": "potion of heroism",
    "pozione di forza del gigante": "potion of giant strength",
    "pozione di resistenza": "potion of resistance",
    "borsa conservante": "bag of holding",
    "zaino pratico di heward": "handy haversack",
    "zaino pratico": "handy haversack",
    "mantello della protezione": "cloak of protection",
    "mantello elfico": "cloak of elvenkind",
    "mantello dello spostamento": "cloak of displacement",
    "stivali elfici": "boots of elvenkind",
    "stivali della velocità": "boots of speed",
    "stivali della levitazione": "boots of levitation",
    "stivali alati": "winged boots",
    "anello di protezione": "ring of protection",
    "anello dell'invisibilità": "ring of invisibility",
    "anello di accumulo degli incantesimi": "ring of spell storing",
    "anello della rigenerazione": "ring of regeneration",
    "amuleto della salute": "amulet of health",
    "fascia dell'intelletto": "headband of intellect",
    "guanti del potere orchesco": "gauntlets of ogre power",
    "cintura della forza dei giganti": "belt of giant strength",
    "bacchetta dei dardi incantati": "wand of magic missiles",
    "bacchetta delle palle di fuoco": "wand of fireballs",
    "bacchetta dell'individuazione del magico": "wand of magic detection",
    "bastone del potere": "staff of power",
    "bastone dei maghi": "staff of the magi",
    "bastone della guarigione": "staff of healing",
    "spada vorpal": "vorpal sword",
    "spada fiammeggiante": "flame tongue",
    "lingua di fuoco": "flame tongue",
    "lama del gelo": "frost brand",
    "vendicatore sacro": "holy avenger",
    "lama della fortuna": "luck blade",
    "pugnale del veleno": "dagger of venom",
    "giavellotto del fulmine": "javelin of lightning",
    "scudo di mithral": "mithral armor",
    "armatura di mithral": "mithral armor",
    "armatura di adamantio": "adamantine armor",
    "pergamena magica": "spell scroll",
    "pergamena di incantesimo": "spell scroll",
    "pergamena di volo": "spell scroll",
    "scopa volante": "broom of flying",
    "tappeto volante": "carpet of flying",
    "sfera di annientamento": "sphere of annihilation",
    "mazzo delle molte cose": "deck of many things",
    "pietra di ioun": "ioun stone",
    "occhiali della notte": "goggles of night",
    "corda dell'intreccio": "rope of entanglement",
    "corda della scalata": "rope of climbing",
    "decanter dell'acqua infinita": "decanter of endless water",
    "collana delle palle di fuoco": "necklace of fireballs",
    "perla del potere": "pearl of power",
    "bracciali della difesa": "bracers of defense",
    "elmo della telepatia": "helm of telepathy",
    "elmo del teletrasporto": "helm of teleportation",
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

    def _load_magic_items(self) -> List[Dict[str, Any]]:
        if self._magic_items is None:
            path = os.path.join(SRD_DIR, "open5e_magicitems.json")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._magic_items = json.load(f)
                except Exception as e:
                    print(f"[SRD_OFFLINE] Errore caricamento open5e_magicitems.json: {e}")
                    self._magic_items = []
            else:
                self._magic_items = []
        return self._magic_items

    def get_magic_item(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Cerca un oggetto magico nel database SRD offline supportando nomi in italiano o inglese."""
        if not name_or_query or not str(name_or_query).strip():
            return None
        q = str(name_or_query).strip().lower()
        # Rimuovi eventuale bonus finale generico per lookup (es. "Spada Lunga +1" -> "weapon, +1")
        target_en = ITEM_IT_TO_EN.get(q, q)
        if target_en == q:
            for k_it, k_en in ITEM_IT_TO_EN.items():
                if k_it in q:
                    target_en = k_en
                    break
            if re.search(r'\+[123]\b', q):
                num_m = re.search(r'\+([123])\b', q)
                b_num = num_m.group(1) if num_m else "1"
                if any(w in q for w in ["spada", "ascia", "arco", "pugnale", "martello", "mazza", "lancia", "balestra", "arma"]):
                    target_en = f"weapon, +{b_num}"
                elif any(w in q for w in ["armatura", "corazza", "cotta"]):
                    target_en = f"armor, +{b_num}"
                elif "scudo" in q:
                    target_en = f"shield, +{b_num}"

        items = self._load_magic_items()
        for it in items:
            it_name = str(it.get("name", "")).strip().lower()
            if it_name == q or it_name == target_en:
                return it

        best_match = None
        best_len = 999
        for it in items:
            it_name = str(it.get("name", "")).strip().lower()
            if it_name.startswith(target_en) or it_name.startswith(q):
                if len(it_name) < best_len:
                    best_len = len(it_name)
                    best_match = it
            elif (target_en in it_name or q in it_name) and best_match is None:
                best_match = it
        return best_match

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

def get_all_monsters_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_monsters())

def get_all_spells_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_spells())

def get_all_magic_items_offline() -> List[Dict[str, Any]]:
    return list(OfflineSRD.get_instance()._load_magic_items())

def get_class_level_features_offline(char_class: str, level: int) -> Dict[str, Any]:
    return OfflineSRD.get_instance().get_class_level_features(char_class, level)


# Mappe inverse Inglese -> Italiano per visualizzazione e ricerca bilingue
SPELL_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in SPELL_IT_TO_EN.items():
    if _en_v not in SPELL_EN_TO_IT:
        SPELL_EN_TO_IT[_en_v] = _it_k.title()

MONSTER_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in MONSTER_IT_TO_EN.items():
    if _en_v not in MONSTER_EN_TO_IT:
        MONSTER_EN_TO_IT[_en_v] = _it_k.title()

ITEM_EN_TO_IT: Dict[str, str] = {}
for _it_k, _en_v in ITEM_IT_TO_EN.items():
    if _en_v not in ITEM_EN_TO_IT:
        ITEM_EN_TO_IT[_en_v] = _it_k.title()


def get_italian_translation(name_en: str, category: str = "") -> Optional[str]:
    """Restituisce la traduzione italiana di un nome inglese SRD se presente nei dizionari."""
    if not name_en:
        return None
    low = str(name_en).strip().lower()
    cat_l = str(category).lower()
    if "incantesim" in cat_l or "spell" in cat_l:
        if low in SPELL_EN_TO_IT:
            return SPELL_EN_TO_IT[low]
    if "mostr" in cat_l or "png" in cat_l or "npc" in cat_l:
        if low in MONSTER_EN_TO_IT:
            return MONSTER_EN_TO_IT[low]
    if any(k in cat_l for k in ("oggett", "equip", "arm", "pozion")):
        if low in ITEM_EN_TO_IT:
            return ITEM_EN_TO_IT[low]
    return SPELL_EN_TO_IT.get(low) or ITEM_EN_TO_IT.get(low) or MONSTER_EN_TO_IT.get(low)


def get_bilingual_label(name: str, category: str = "") -> str:
    """Restituisce l'etichetta bilingue es. 'Fireball (Palla Di Fuoco)' se esiste traduzione."""
    if not name:
        return ""
    it_name = get_italian_translation(name, category)
    if it_name and it_name.lower() != name.strip().lower() and it_name.lower() not in name.strip().lower():
        return f"{name} ({it_name})"
    return name


def match_bilingual_search(item: Dict[str, Any], search_text: str, category: str = "") -> bool:
    """
    Verifica se `item` corrisponde a `search_text` cercando in:
    - nome originale (EN o IT)
    - traduzione italiana/inglese dai dizionari SRD
    - tipo, scuola, rarità, parole chiave, sommario
    """
    if not search_text:
        return True
    q = search_text.strip().lower()
    if not q:
        return True

    name = str(item.get("name") or item.get("title") or "").strip()
    name_l = name.lower()
    if q in name_l:
        return True

    # Traduzione diretta della query IT -> EN
    q_en_candidates = set()
    for d in (SPELL_IT_TO_EN, MONSTER_IT_TO_EN, ITEM_IT_TO_EN):
        if q in d:
            q_en_candidates.add(d[q])
        for k_it, v_en in d.items():
            if q in k_it:
                q_en_candidates.add(v_en)
    for q_en in q_en_candidates:
        if q_en in name_l:
            return True

    # Traduzione del nome dell'elemento EN -> IT
    it_trans = get_italian_translation(name, category)
    if it_trans and q in it_trans.lower():
        return True

    # Campi secondari (keywords, summary, type, school, rarity, category)
    kws = [str(k).lower() for k in item.get("keywords", [])]
    if any(q in k for k in kws):
        return True
    for field in ("summary", "type", "school", "rarity", "category", "manual_name"):
        val = item.get(field)
        if isinstance(val, dict):
            val = val.get("name", "")
        if val and q in str(val).lower():
            return True
    return False


# Catalogo standard 5e SRD Offline per Armi, Armature, Pozioni, Regole e Classi
STANDARD_5E_EQUIPMENT_CATALOG: List[Dict[str, Any]] = [
    # Armi da Mischia e a Distanza
    {"name": "Spada Lunga (Longsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "15 mo", "weight": 3.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 tagliente (Versatile 1d10). Peso: 3 lbs."},
    {"name": "Spadone (Greatsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 6.0, "damage": {"damage_dice": "2d6", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 2d6 tagliente (Pesante, Due Mani). Peso: 6 lbs."},
    {"name": "Spada Corta (Shortsword)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale da mischia. Danno: 1d6 perforante (Accurata, Leggera). Peso: 2 lbs."},
    {"name": "Stocco (Rapier)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "25 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale da mischia. Danno: 1d8 perforante (Accurata). Peso: 2 lbs."},
    {"name": "Scimitarra (Scimitar)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "25 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d6 tagliente (Accurata, Leggera). Peso: 3 lbs."},
    {"name": "Ascia Bipenne (Greataxe)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "30 mo", "weight": 7.0, "damage": {"damage_dice": "1d12", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d12 tagliente (Pesante, Due Mani). Peso: 7 lbs."},
    {"name": "Ascia da Battaglia (Battleaxe)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 4.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 tagliente (Versatile 1d10). Peso: 4 lbs."},
    {"name": "Martello da Guerra (Warhammer)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "15 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Contundente"}}, "desc": "Arma marziale da mischia. Danno: 1d8 contundente (Versatile 1d10). Peso: 2 lbs."},
    {"name": "Maglio (Maul)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "damage": {"damage_dice": "2d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma marziale da mischia. Danno: 2d6 contundente (Pesante, Due Mani). Peso: 10 lbs."},
    {"name": "Alabarda (Halberd)", "type": "Arma da Mischia Marziale", "rarity": "Comune", "cost": "20 mo", "weight": 6.0, "damage": {"damage_dice": "1d10", "damage_type": {"name": "Tagliente"}}, "desc": "Arma marziale da mischia. Danno: 1d10 tagliente (Pesante, Portata, Due Mani). Peso: 6 lbs."},
    {"name": "Pugnale (Dagger)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "2 mo", "weight": 1.0, "damage": {"damage_dice": "1d4", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia. Danno: 1d4 perforante (Accurata, Leggera, Lancio 6/18m). Peso: 1 lb."},
    {"name": "Mazza (Mace)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "5 mo", "weight": 4.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma semplice da mischia. Danno: 1d6 contundente. Peso: 4 lbs."},
    {"name": "Bastone Ferrato (Quarterstaff)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "2 ma", "weight": 4.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Contundente"}}, "desc": "Arma semplice da mischia. Danno: 1d6 contundente (Versatile 1d8). Peso: 4 lbs."},
    {"name": "Lancia (Spear)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "1 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia. Danno: 1d6 perforante (Lancio 6/18m, Versatile 1d8). Peso: 3 lbs."},
    {"name": "Giavellotto (Javelin)", "type": "Arma da Mischia Semplice", "rarity": "Comune", "cost": "5 ma", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice da mischia/lancio. Danno: 1d6 perforante (Lancio 9/36m). Peso: 2 lbs."},
    {"name": "Arco Lungo (Longbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 2.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d8 perforante (Munizioni 45/180m, Pesante, Due Mani). Peso: 2 lbs."},
    {"name": "Arco Corto (Shortbow)", "type": "Arma a Distanza Semplice", "rarity": "Comune", "cost": "25 mo", "weight": 2.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice a distanza. Danno: 1d6 perforante (Munizioni 24/96m, Due Mani). Peso: 2 lbs."},
    {"name": "Balestra Leggera (Light Crossbow)", "type": "Arma a Distanza Semplice", "rarity": "Comune", "cost": "25 mo", "weight": 5.0, "damage": {"damage_dice": "1d8", "damage_type": {"name": "Perforante"}}, "desc": "Arma semplice a distanza. Danno: 1d8 perforante (Munizioni 24/96m, Ricarica, Due Mani). Peso: 5 lbs."},
    {"name": "Balestra Pesante (Heavy Crossbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "50 mo", "weight": 18.0, "damage": {"damage_dice": "1d10", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d10 perforante (Munizioni 30/120m, Pesante, Ricarica, Due Mani). Peso: 18 lbs."},
    {"name": "Balestra a Mano (Hand Crossbow)", "type": "Arma a Distanza Marziale", "rarity": "Comune", "cost": "75 mo", "weight": 3.0, "damage": {"damage_dice": "1d6", "damage_type": {"name": "Perforante"}}, "desc": "Arma marziale a distanza. Danno: 1d6 perforante (Munizioni 9/36m, Leggera, Ricarica). Peso: 3 lbs."},
    # Armature e Scudi
    {"name": "Armatura di Cuoio (Leather Armor)", "type": "Armatura Leggera", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "desc": "Armatura leggera. CA: 11 + modificatore di Destrezza."},
    {"name": "Armatura di Cuoio Borchiato (Studded Leather)", "type": "Armatura Leggera", "rarity": "Comune", "cost": "45 mo", "weight": 13.0, "desc": "Armatura leggera. CA: 12 + modificatore di Destrezza."},
    {"name": "Giaco di Maglia (Chain Shirt)", "type": "Armatura Media", "rarity": "Comune", "cost": "50 mo", "weight": 20.0, "desc": "Armatura media. CA: 13 + modificatore di Destrezza (max +2)."},
    {"name": "Cotta a Scaglie (Scale Mail)", "type": "Armatura Media", "rarity": "Comune", "cost": "50 mo", "weight": 45.0, "desc": "Armatura media. CA: 14 + modificatore di Destrezza (max +2). Svantaggio a Furtività."},
    {"name": "Mezza Armatura (Half Plate)", "type": "Armatura Media", "rarity": "Comune", "cost": "750 mo", "weight": 40.0, "desc": "Armatura media. CA: 15 + modificatore di Destrezza (max +2). Svantaggio a Furtività."},
    {"name": "Cotta di Maglia (Chain Mail)", "type": "Armatura Pesante", "rarity": "Comune", "cost": "75 mo", "weight": 55.0, "desc": "Armatura pesante. CA: 16 (Richiede FOR 13, Svantaggio a Furtività)."},
    {"name": "Armatura a Piastre (Plate Armor)", "type": "Armatura Pesante", "rarity": "Comune", "cost": "1500 mo", "weight": 65.0, "desc": "Armatura pesante. CA: 18 (Richiede FOR 15, Svantaggio a Furtività)."},
    {"name": "Scudo (Shield)", "type": "Armatura (Scudo)", "rarity": "Comune", "cost": "10 mo", "weight": 6.0, "desc": "Scudo in legno o metallo. Conferisce +2 alla Classe Armatura quando impugnato."},
    # Pozioni
    {"name": "Pozione di Guarigione (Potion of Healing)", "type": "Pozione", "rarity": "Comune", "cost": "50 mo", "weight": 0.5, "desc": "Bevi questa fiala di liquido rosso per recuperare 2d4 + 2 Punti Ferita (1 Azione)."},
    {"name": "Pozione di Guarigione Maggiore (Potion of Greater Healing)", "type": "Pozione", "rarity": "Non Comune", "cost": "150 mo", "weight": 0.5, "desc": "Recuperi 4d4 + 4 Punti Ferita quando bevi questa pozione."},
    {"name": "Pozione di Guarigione Superiore (Potion of Superior Healing)", "type": "Pozione", "rarity": "Raro", "cost": "500 mo", "weight": 0.5, "desc": "Recuperi 8d4 + 8 Punti Ferita quando bevi questa pozione."},
    {"name": "Pozione di Guarigione Suprema (Potion of Supreme Healing)", "type": "Pozione", "rarity": "Molto Raro", "cost": "1350 mo", "weight": 0.5, "desc": "Recuperi 10d4 + 20 Punti Ferita quando bevi questa pozione."},
    {"name": "Antidoto (Antitoxin)", "type": "Pozione", "rarity": "Comune", "cost": "50 mo", "weight": 0.1, "desc": "Chi beve questa fiala ottiene vantaggio ai tiri salvezza contro il veleno per 1 ora."},
    # Attrezzi ed Equipaggiamento d'Avventura
    {"name": "Zaino da Esploratore (Explorer's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "10 mo", "weight": 10.0, "desc": "Contiene sacco a pelo, acciarino, 10 torce, 10 razioni, borraccia e 15m di corda di canapa."},
    {"name": "Zaino da Scassinatore (Burglar's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "16 mo", "weight": 12.0, "desc": "Contiene piede di porco, martello, 10 chiodi, 5 candele, acciarino, 5 razioni, borraccia e 15m di corda."},
    {"name": "Zaino da Studioso (Scholar's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "40 mo", "weight": 10.0, "desc": "Contiene libro di nozioni, inchiostro, penna d'oca, 10 fogli di pergamena, razioni e borraccia."},
    {"name": "Zaino da Sacerdote (Priest's Pack)", "type": "Equipaggiamento (Zaino)", "rarity": "Comune", "cost": "19 mo", "weight": 10.0, "desc": "Contiene coperta, 10 candele, acciarino, incensiere, vesti da cerimonia, 2 razioni e borraccia."},
    {"name": "Strumenti da Scasso (Thieves' Tools)", "type": "Strumenti", "rarity": "Comune", "cost": "25 mo", "weight": 1.0, "desc": "Include lima, grimaldelli, specchietto, pinze. Necessario per scassinare serrature e disattivare trappole."},
    {"name": "Borsa da Guaritore (Healer's Kit)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "5 mo", "weight": 3.0, "desc": "10 usi. Spendendo 1 uso ed 1 Azione puoi stabilizzare una creatura a 0 PF senza prova di Medicina."},
    {"name": "Corda di Canapa 15m (Hempen Rope)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "1 mo", "weight": 10.0, "desc": "Corda da 15 metri (50 ft), 2 PF, può essere spezzata con una prova di Forza CD 17."},
    {"name": "Torcia (Torch)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "1 mr", "weight": 1.0, "desc": "Brucia per 1 ora proiettando luce intensa nel raggio di 6m e luce fioca per altri 6m."},
    {"name": "Lanterna Schermabile (Hooded Lantern)", "type": "Equipaggiamento", "rarity": "Comune", "cost": "5 mo", "weight": 2.0, "desc": "Proietta luce intensa per 9m e luce fioca per altri 9m per 6 ore con una fiaschetta d'olio."},
]


STANDARD_5E_RULES_CATALOG: List[Dict[str, Any]] = [
    {"name": "Azioni in Combattimento (Actions in Combat)", "category": "Regole", "type": "Combattimento", "desc": "Durante il tuo turno puoi muoverti e compiere un'Azione:\n• Attacco: effettua un attacco in mischia o a distanza.\n• Lanciare un Incantesimo: tempo di lancio 1 azione.\n• Scatto (Dash): raddoppia il movimento per il turno.\n• Disimpegno (Disengage): il tuo movimento non provoca attacchi d'opportunità.\n• Schivata (Dodge): gli attacchi contro di te hanno svantaggio e hai vantaggio ai TS su Destrezza.\n• Aiuto (Help): dai vantaggio alla prossima prova o attacco di un alleato.\n• Nascondersi (Hide): effettua una prova di Furtività.\n• Preparare (Ready): prepara un'azione in risposta a un innesco usando la Reazione."},
    {"name": "Condizioni D&D 5e (Conditions)", "category": "Regole", "type": "Condizioni", "desc": "Riepilogo rapido delle condizioni:\n• Accecato (Blinded): fallisce prove basate sulla vista, attacchi con svantaggio, attacchi subiti con vantaggio.\n• Affascinato (Charmed): non può attaccare chi l'ha affascinato; questi ha vantaggio alle prove sociali.\n• Afferrato (Grappled): velocità 0.\n• Avvelenato (Poisoned): svantaggio ai tiri per colpire e alle prove di caratteristica.\n• Incosciente (Unconscious): incapacitato, prono, fallisce TS FOR/DES, attacchi subiti con vantaggio e critico automatico entro 1.5m.\n• Invisibile (Invisible): attacchi con vantaggio, attacchi subiti con svantaggio.\n• Paralizzato (Paralyzed): incapacitato, fallisce TS FOR/DES, critico automatico entro 1.5m.\n• Prono (Prone): svantaggio agli attacchi; attacchi subiti entro 1.5m hanno vantaggio, oltre 1.5m svantaggio.\n• Stordito (Stunned): incapacitato, fallisce TS FOR/DES, attacchi subiti con vantaggio.\n• Trattenuto (Restrained): velocità 0, attacchi con svantaggio, attacchi subiti con vantaggio, svantaggio ai TS DES."},
    {"name": "Riposo Breve e Riposo Lungo (Resting)", "category": "Regole", "type": "Avventura", "desc": "• Riposo Breve (Short Rest): almeno 1 ora di inattività leggera. Puoi spendere Dadi Vita (fino al tuo livello) aggiungendo il modificatore di Costituzione per recuperare Punti Ferita.\n• Riposo Lungo (Long Rest): almeno 8 ore. Recuperi tutti i Punti Ferita perduti, tutti gli slot incantesimo e fino a metà dei tuoi Dadi Vita totali (minimo 1), oltre a ridurre l'Indebolimento di 1 livello."},
    {"name": "Tiri Salvezza contro Morte (Death Saving Throws)", "category": "Regole", "type": "Combattimento", "desc": "Quando inizi il turno a 0 PF, tiri 1d20 senza modificatori:\n• 10 o più: 1 Successo (al 3° successo sei stabile a 0 PF).\n• 9 o meno: 1 Fallimento (al 3° fallimento il personaggio muore).\n• 1 Naturale: conta come 2 fallimenti.\n• 20 Naturale: recuperi immediatamente 1 Punto Ferita e torni cosciente!"},
    {"name": "Copertura e Terreno Difficile (Cover & Terrain)", "category": "Regole", "type": "Combattimento", "desc": "• Mezza Copertura (Half Cover): +2 a CA e ai Tiri Salvezza su Destrezza.\n• Tre Quarti di Copertura (Three-Quarters Cover): +5 a CA e ai Tiri Salvezza su Destrezza.\n• Copertura Totale (Total Cover): non può essere bersagliato direttamente da un attacco o incantesimo.\n• Terreno Difficile: ogni metro di movimento costa 1 metro extra (2x costo movimento)."},
    {"name": "Vantaggio e Svantaggio (Advantage & Disadvantage)", "category": "Regole", "type": "Meccaniche Base", "desc": "• Vantaggio: tiri 2d20 e usi il risultato più alto.\n• Svantaggio: tiri 2d20 e usi il risultato più basso.\n• Se hai sia vantaggio che svantaggio (indipendentemente da quanti), si annullano a vicenda e tiri 1d20 normale."},
    {"name": "Concentrazione sugli Incantesimi (Concentration)", "category": "Regole", "type": "Magia", "desc": "Se subisci danni mentre mantieni la concentrazione su un incantesimo, devi superare un Tiro Salvezza su Costituzione con CD pari a 10 o alla metà del danno subito (qualunque sia più alta). Puoi concentrarti su un solo incantesimo alla volta."},
]


def get_all_equipment_offline(category: str = "Equipaggiamento") -> List[Dict[str, Any]]:
    """Restituisce il catalogo offline per Equipaggiamento, Armi o Pozioni combinato con SRD Magic Items."""
    cat_l = str(category).lower()
    results = []
    seen = set()

    for it in STANDARD_5E_EQUIPMENT_CATALOG:
        t_low = str(it.get("type", "")).lower()
        if "armi" in cat_l and "arma" not in t_low and "weapon" not in t_low:
            continue
        if "pozion" in cat_l and "pozion" not in t_low and "potion" not in t_low:
            continue
        copy_it = dict(it)
        copy_it["source"] = "SRD 5e"
        results.append(copy_it)
        seen.add(copy_it["name"].lower())

    for mit in get_all_magic_items_offline():
        m_type = str(mit.get("type", "")).lower()
        m_name = str(mit.get("name", ""))
        if "armi" in cat_l and "weapon" not in m_type:
            continue
        if "pozion" in cat_l and "potion" not in m_type:
            continue
        if m_name.lower() not in seen:
            seen.add(m_name.lower())
            results.append(mit)

    return results


def get_all_rules_offline() -> List[Dict[str, Any]]:
    """Restituisce le voci del compendio per le Regole D&D 5e offline."""
    return [dict(r) for r in STANDARD_5E_RULES_CATALOG]


def get_all_classes_offline() -> List[Dict[str, Any]]:
    """Restituisce le schede di progressione 1-20 delle classi D&D 5e."""
    class_names_it = {
        "fighter": "Guerriero (Fighter)",
        "barbarian": "Barbaro (Barbarian)",
        "rogue": "Ladro (Rogue)",
        "wizard": "Mago (Wizard)",
        "cleric": "Chierico (Cleric)",
        "paladin": "Paladino (Paladin)",
        "ranger": "Ranger",
        "bard": "Bardo (Bard)",
        "druid": "Druido (Druid)",
        "monk": "Monaco (Monk)",
        "sorcerer": "Stregone (Sorcerer)",
        "warlock": "Warlock",
    }
    out = []
    for c_key, c_data in CLASS_PROGRESSION_TABLE.items():
        title = class_names_it.get(c_key, c_key.title())
        hd = c_data.get("hit_die", 8)
        feats_map = c_data.get("features", {})
        lines = [f"🎲 Dado Vita: d{hd} per livello", ""]
        for lvl in sorted(feats_map.keys()):
            f_list = ", ".join(feats_map[lvl])
            lines.append(f"• Livello {lvl}: {f_list}")
        out.append({
            "name": title,
            "category": "Classi",
            "type": f"Dado Vita d{hd}",
            "desc": "\n".join(lines),
            "source": "SRD 5e",
        })
    return out


def get_all_traits_offline() -> List[Dict[str, Any]]:
    """Restituisce l'elenco dei privilegi di classe e tratti razziali 5e offline."""
    traits = []
    seen = set()
    for c_key, c_data in CLASS_PROGRESSION_TABLE.items():
        for lvl, f_list in c_data.get("features", {}).items():
            for feat in f_list:
                if feat.lower() in seen or "asi" in feat.lower():
                    continue
                seen.add(feat.lower())
                traits.append({
                    "name": feat,
                    "category": "Tratti",
                    "type": f"{c_key.title()} (Liv. {lvl})",
                    "desc": f"Privilegio di classe {c_key.title()} sbloccato al Livello {lvl}.",
                    "source": "SRD 5e",
                })
    return traits


def resolve_compendium_item(raw_entry: str, default_qty: int = 1) -> Dict[str, Any]:
    """
    Risolve una stringa di oggetto (es. '2x Pozione di Guarigione', 'Spada Lunga +1', 'Corda di Canapa')
    interrogando nell'ordine:
    1. Compendio Custom (srd_data/custom_compendium.json)
    2. Compendio SRD Offline (srd_data/open5e_magicitems.json)
    3. Catalogo Equipaggiamento Standard 5e (common/starter_equipment.py)
    Restituisce un dizionario strutturato pronto per l'inventario VTT e la distribuzione del loot.
    """
    from common.starter_equipment import (
        lookup_standard_weight,
        DEFAULT_CAMPAIGN_STARTER_KIT,
        STARTER_PACK_CONTENTS,
        CLASS_STARTING_KITS,
    )

    s = str(raw_entry or "").strip().strip('"\'')
    qty = default_qty
    # Estrai prefisso o suffisso quantità: "2x Pozione", "3 Pozioni", "Pozione (x2)"
    m_pre = re.match(r'^(\d+)\s*[xX]\s*(.+)$', s)
    m_suf = re.match(r'^(.+?)\s*\(\s*[xX]?(\d+)\s*\)$', s)
    if m_pre:
        qty = max(1, int(m_pre.group(1)))
        s = m_pre.group(2).strip().strip('"\'')
    elif m_suf:
        qty = max(1, int(m_suf.group(2)))
        s = m_suf.group(1).strip().strip('"\'')

    clean_low = s.lower()

    # 1. Cerca nel Compendio Custom (custom_compendium.json)
    custom_path = os.path.join(SRD_DIR, "custom_compendium.json")
    if os.path.isfile(custom_path):
        try:
            with open(custom_path, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            for cat in ("Oggetti Magici", "Equipaggiamento", "Armi", "Pozioni"):
                for cit in cdata.get(cat, []):
                    cname = str(cit.get("name") or cit.get("title") or "").strip()
                    if cname.lower() == clean_low:
                        w = cit.get("weight")
                        try:
                            w = float(w) if w is not None else lookup_standard_weight(cname)
                        except (ValueError, TypeError):
                            w = lookup_standard_weight(cname)
                        return {
                            "name": cname,
                            "qty": qty,
                            "type": cit.get("type") or cat,
                            "weight": w,
                            "rarity": cit.get("rarity", "Comune"),
                            "desc": cit.get("desc", ""),
                            "attuned": False,
                            "from_compendium": True,
                            "compendium_source": "Compendio Custom",
                        }
        except Exception:
            pass

    # 2. Cerca nel Compendio SRD Offline (open5e_magicitems.json)
    srd_it = OfflineSRD.get_instance().get_magic_item(s)
    if srd_it:
        raw_type = str(srd_it.get("type", "Oggetto Magico"))
        type_it = "Oggetto Magico"
        rt_low = raw_type.lower()
        if "potion" in rt_low or "pozion" in clean_low:
            type_it = "Pozione"
        elif "scroll" in rt_low or "pergamen" in clean_low:
            type_it = "Pergamena"
        elif "weapon" in rt_low or any(w in clean_low for w in ["spada", "ascia", "arco", "pugnale", "martello", "lancia"]):
            type_it = "Arma"
        elif "armor" in rt_low or "armatura" in clean_low or "corazza" in clean_low:
            type_it = "Armatura"
        elif "shield" in rt_low or "scudo" in clean_low:
            type_it = "Scudo"

        w = lookup_standard_weight(s)
        if w <= 0.0:
            w = 0.5 if type_it in ("Pozione", "Pergamena") else 1.0

        return {
            "name": s,
            "srd_name": srd_it.get("name", s),
            "qty": qty,
            "type": type_it,
            "weight": w,
            "rarity": srd_it.get("rarity", "Non Comune"),
            "desc": srd_it.get("desc", ""),
            "requires_attunement": bool(srd_it.get("requires_attunement")),
            "attuned": False,
            "from_compendium": True,
            "compendium_source": "SRD 5.1",
        }

    # 3. Cerca nel Catalogo Equipaggiamento Standard 5e (starter_equipment.py)
    std_catalog: List[Dict[str, Any]] = []
    std_catalog.extend(DEFAULT_CAMPAIGN_STARTER_KIT)
    for p_list in STARTER_PACK_CONTENTS.values():
        std_catalog.extend(p_list)
    for k_data in CLASS_STARTING_KITS.values():
        std_catalog.extend(k_data.get("inventory", []))

    for std_it in std_catalog:
        std_name = str(std_it.get("name", "")).strip()
        if std_name.lower() == clean_low or clean_low in std_name.lower():
            w = std_it.get("weight", 0.0) or lookup_standard_weight(std_name)
            return {
                "name": s if std_name.lower() != clean_low else std_name,
                "qty": qty,
                "type": std_it.get("type", "Equipaggiamento"),
                "weight": float(w),
                "rarity": "Comune",
                "desc": std_it.get("desc", ""),
                "attuned": False,
                "from_compendium": True,
                "compendium_source": "Equipaggiamento 5e",
            }

    # 4. Fallback se il nome corrisponde a un peso standard 5e (es. "Spada Lunga", "Corda di Seta", "Torcia")
    std_w = lookup_standard_weight(s)
    inferred_type = "Equipaggiamento"
    if any(k in clean_low for k in ["spada", "ascia", "pugnale", "arco", "balestra", "martello", "mazza", "lancia", "giavellotto", "stocco", "scimitarra", "alabarda"]):
        inferred_type = "Arma"
    elif any(k in clean_low for k in ["armatura", "corazza", "cotta", "giaco"]):
        inferred_type = "Armatura"
    elif "scudo" in clean_low:
        inferred_type = "Scudo"
    elif "pozion" in clean_low or "elisir" in clean_low or "antidoto" in clean_low:
        inferred_type = "Pozione"
    elif "pergamen" in clean_low:
        inferred_type = "Pergamena"

    return {
        "name": s,
        "qty": qty,
        "type": inferred_type,
        "weight": std_w,
        "rarity": "Comune",
        "desc": "Oggetto standard D&D 5e." if std_w > 0 else "",
        "attuned": False,
        "from_compendium": bool(std_w > 0),
        "compendium_source": "Equipaggiamento 5e" if std_w > 0 else "Personalizzato",
    }


def parse_loot_specification(raw_loot: Any) -> Dict[str, Any]:
    """
    Analizza una specifica di loot DndScript (es. '100 mo, 50 ma, 2x Pozione di Cura, Spada Lunga +1')
    separando le valute (MR, MA, ME, MO, MP) e risolvendo ciascun oggetto nel Compendio.
    """
    currency = {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0}
    resolved_items: List[Dict[str, Any]] = []

    if not raw_loot:
        return {"currency": currency, "items": resolved_items}

    if isinstance(raw_loot, list):
        tokens = [str(x).strip() for x in raw_loot if str(x).strip()]
    else:
        tokens = [t.strip() for t in str(raw_loot).split(",") if t.strip()]

    coin_patterns = [
        ("MP", r"^(\d+)\s*(?:mp|pp|monete\s+d['i]\s*platino|platino)$"),
        ("ME", r"^(\d+)\s*(?:me|ep|monete\s+d['i]\s*electrum|electrum|electro)$"),
        ("MA", r"^(\d+)\s*(?:ma|sp|monete\s+d['i]\s*argento|argento)$"),
        ("MR", r"^(\d+)\s*(?:mr|cp|monete\s+di\s*rame|rame)$"),
        ("MO", r"^(\d+)\s*(?:mo|gp|monete\s+d['i]\s*oro|oro)$"),
    ]

    for tok in tokens:
        clean_tok = tok.strip().strip('"\'')
        if not clean_tok:
            continue
        matched_coin = False
        for c_code, pat in coin_patterns:
            m = re.match(pat, clean_tok, re.IGNORECASE)
            if m:
                currency[c_code] += int(m.group(1))
                matched_coin = True
                break
        if not matched_coin:
            resolved_items.append(resolve_compendium_item(clean_tok))

    return {"currency": currency, "items": resolved_items}


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


def normalize_size_value(size_data: Any) -> int:
    """Converte la taglia D&D 5e (stringa o numero) nel numero di esagoni/caselle (size) del token."""
    if isinstance(size_data, (int, float)):
        return max(1, int(size_data))
    s = str(size_data or "").strip().lower()
    if any(k in s for k in ("gargantuan", "mastodontic", "colossal")):
        return 4
    if any(k in s for k in ("huge", "enorme")):
        return 3
    if any(k in s for k in ("large", "grande")):
        return 2
    # Tiny, Small, Medium, Piccola, Media -> 1 esagono
    return 1


def normalize_damage_list(damage_data: Any) -> List[str]:
    """Converte resistenze, immunità o vulnerabilità (lista o stringa) in lista normalizzata di tipi di danno."""
    if not damage_data:
        return []
    result = []
    if isinstance(damage_data, list):
        for item in damage_data:
            if isinstance(item, str):
                for sub in re.split(r'[,;]|(?:\band\b)|(?:\be\b)', item):
                    clean = sub.strip().lower()
                    if clean and clean not in result:
                        result.append(clean)
            elif isinstance(item, dict) and "name" in item:
                clean = str(item["name"]).strip().lower()
                if clean and clean not in result:
                    result.append(clean)
    elif isinstance(damage_data, str):
        for sub in re.split(r'[,;]|(?:\band\b)|(?:\be\b)', damage_data):
            clean = sub.strip().lower()
            if clean and clean not in result:
                result.append(clean)
    return result


def extract_legendary_stats(mdata: Dict[str, Any]) -> tuple:
    """Estrae (legendary_resistances, legendary_actions, has_lair) da dizionario o statblock di una creatura."""
    if not isinstance(mdata, dict):
        return 0, 0, False
    
    # 1. Legendary Resistances (es. 3/Day)
    leg_res = 0
    abilities = mdata.get("special_abilities") or mdata.get("features") or []
    if isinstance(abilities, list):
        for ab in abilities:
            ab_name = ab.get("name", "") if isinstance(ab, dict) else str(ab)
            ab_desc = ab.get("desc", "") if isinstance(ab, dict) else ""
            if "legendary resistance" in ab_name.lower() or "resistenza leggendaria" in ab_name.lower():
                m_count = re.search(r'\((\d+)\s*/\s*(?:day|giorno)\)', ab_name, re.IGNORECASE)
                if not m_count:
                    m_count = re.search(r'\((\d+)\s*/\s*(?:day|giorno)\)', ab_desc, re.IGNORECASE)
                leg_res = int(m_count.group(1)) if m_count else 3
                break

    # 2. Legendary Actions (di norma 3 azioni per round per creature leggendarie)
    leg_actions = mdata.get("legendary_actions") or []
    leg_act_count = 3 if (isinstance(leg_actions, list) and len(leg_actions) > 0) else 0

    # 3. Lair Actions
    has_lair = bool(mdata.get("lair_actions") or "lair_actions" in mdata)
    if not has_lair and isinstance(abilities, list):
        for ab in abilities:
            t = str(ab).lower()
            if "lair action" in t or "azione della tana" in t:
                has_lair = True
                break

    return leg_res, leg_act_count, has_lair


def extract_darkvision_flag(mdata: Dict[str, Any]) -> bool:
    """Verifica se una creatura possiede Scurovisione dai sensi o tratti."""
    if not isinstance(mdata, dict):
        return False
    senses = str(mdata.get("senses", "")).lower()
    if "darkvision" in senses or "scurovisione" in senses:
        return True
    traits = mdata.get("special_abilities") or mdata.get("features") or []
    if isinstance(traits, list):
        for t in traits:
            text = str(t).lower()
            if "darkvision" in text or "scurovisione" in text:
                return True
    return False


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





