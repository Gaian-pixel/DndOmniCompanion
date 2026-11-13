"""
common/item_modifiers.py - Calcolo automatico e unificato dei modificatori degli oggetti (D&D 5e RAW).

Gestisce:
- Armature magiche (+1, +2, +3, Piastre Naniche, Scaglie di Drago, ecc.) ed estrazione CA base e destrezza
- Scudi normali e magici (+1, +2, +3)
- Oggetti meravigliosi, anelli e mantelli (Anello/Mantello di Protezione, Bracciali della Difesa, Veste dell'Arcimago)
- Statistiche alterate (Guanti della Forza dell'Orco, Fascia dell'Intelletto, Amuleto della Salute, Cinture dei Giganti, Tomi/Manuali)
- Tiri salvezza, CD Incantesimi, Bonus Attacco Magico, Velocità
- Armi magiche (+1, +2, +3, Spada del Sole, Holy Avenger, Vorpal, ecc.)
"""

import re
from typing import Dict, Any, List, Tuple, Optional

from common.dnd5e_tables import entity_has_keyword, entity_get_class_level, entity_get_total_level


STAT_MAP = {
    "STR": "FOR", "STRENGTH": "FOR", "FORZA": "FOR", "FOR": "FOR",
    "DEX": "DES", "DEXTERITY": "DES", "DESTREZZA": "DES", "DES": "DES",
    "CON": "COS", "CONSTITUTION": "COS", "COSTITUZIONE": "COS", "COS": "COS",
    "INT": "INT", "INTELLIGENCE": "INT", "INTELLIGENZA": "INT",
    "WIS": "SAG", "WISDOM": "SAG", "SAGGEZZA": "SAG", "SAG": "SAG",
    "CHA": "CAR", "CHARISMA": "CAR", "CARISMA": "CAR", "CAR": "CAR",
    "HON": "ONO", "HONOR": "ONO", "ONORE": "ONO", "ONO": "ONO",
    "SAN": "SAN", "SANITY": "SAN", "SANITÀ": "SAN", "SANITA": "SAN",
}


def canonical_stat_key(stat_name: str) -> str:
    """Restituisce la chiave canonica (FOR, DES, COS, INT, SAG, CAR, ONO, SAN)."""
    if not stat_name:
        return "FOR"
    return STAT_MAP.get(str(stat_name).strip().upper(), "FOR")


def extract_magic_bonus(text: str) -> int:
    """
    Estrae il bonus magico (+1, +2, +3, +4, +5) dal nome o dalla descrizione di un oggetto.
    Esempio:
    'Armatura a Piastre +3' -> 3
    'Scudo +2' -> 2
    'Spada Lunga +1' -> 1
    """
    if not text or not isinstance(text, str):
        return 0
    # Cerca pattern espliciti tipo +1, +2, +3 isolati o prima di parole chiave
    match = re.search(r'(?:^|[^\w])\+([1-5])(?:\b|[^\w]|$)', text)
    if match:
        try:
            return int(match.group(1))
        except (ValueError, TypeError):
            pass
    return 0


def detect_armor_properties(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rileva le proprietà difensive 5e RAW di un'armatura o scudo (base CA, destrezza permessa, bonus magico).
    """
    res = {
        "is_armor": False,
        "is_shield": False,
        "category": None,      # "heavy", "medium", "light", "shield"
        "base_ac": 10,
        "max_dex": None,        # None = illimitato, 0 = pesante, 2 = media
        "magic_bonus": 0,
        "stealth_disadv": False
    }
    if not item or not isinstance(item, dict):
        return res

    iname = str(item.get("name", "")).lower().strip()
    itype = str(item.get("type", "")).lower().strip()
    desc = str(item.get("desc", "")).lower()

    # Escludi consumabili, pergamene, pozioni, anelli, armi, vestiario comune (stivali/guanti/mantelli)
    non_armor_types = (
        "pozione", "potion", "pergamena", "scroll", "consumabile", "consumable",
        "arma", "weapon", "anello", "ring", "bacchetta", "wand", "verga", "rod",
        "bastone", "staff", "valuta", "currency", "munizioni", "ammunition",
        "oggetto meraviglioso", "wondrous item", "meraviglioso"
    )
    if itype in non_armor_types:
        return res
    non_armor_keywords = (
        "pergamena", "scroll", "pozione", "potion", "spilla", "brooch",
        "stivali", "boots", "guanti", "gloves", "gauntlets", "mantello", "cloak",
        "anello ", "ring of", "cintura", "belt", "amuleto", "amulet",
        "fascia", "headband", "bracciali", "bracers", "veste", "robe",
        "tomo", "tome", "manuale", "manual", "otre", "waterskin", "zaino", "backpack"
    )
    if any(k in iname for k in non_armor_keywords):
        return res

    # 1. Riconoscimento Scudo
    if "scudo" in iname or "shield" in iname or itype in ("scudo", "shield"):
        res["is_shield"] = True
        res["category"] = "shield"
        res["base_ac"] = 2
        # Bonus magico esplicito o da nome/descrizione
        magic_b = 0
        if "magic_bonus" in item:
            try: magic_b = max(magic_b, int(item["magic_bonus"]))
            except Exception: pass
        if "bonus_ac" in item:
            try: magic_b = max(magic_b, int(item["bonus_ac"]))
            except Exception: pass
        if "bonus" in item:
            try: magic_b = max(magic_b, int(item["bonus"]))
            except Exception: pass
        if magic_b == 0:
            magic_b = extract_magic_bonus(iname)
        if magic_b == 0:
            # Per uno scudo, "+2 CA" è la dicitura base di uno scudo standard (PHB).
            # Cerchiamo bonus magici espliciti (es. '+1 magico', 'bonus magico di +2', '+3 addizionale alla CA')
            m = re.search(r'(?:bonus magico|magico di|ulteriore|bonus aggiuntivo|bonus di)\s*\+([1-5])', desc)
            if m:
                try: magic_b = int(m.group(1))
                except Exception: pass
            else:
                m2 = re.search(r'\+([1-5])\s*(?:magico|magica|extra|addizionale)', desc)
                if m2:
                    try: magic_b = int(m2.group(1))
                    except Exception: pass
        res["magic_bonus"] = magic_b
        return res

    # 2. Riconoscimento Armatura
    is_armor_candidate = (
        itype in ("armatura", "armor") or
        any(k in iname for k in [
            "armatura", "armor", "cuoio", "leather", "corazza", "giaco", 
            "maglia", "chain", "piastre", "plate", "imbottita", "padded", 
            "scaglie", "scale", "pettorale", "breastplate", "strisce", 
            "splint", "corazza ad anelli", "ring mail", "pelle", "hide"
        ])
    )
    if not is_armor_candidate:
        return res

    res["is_armor"] = True

    # Rilevamento categoria e CA base da tabella ufficiale 5e RAW (PHB p. 145)
    # --- Pesante (Heavy Armor): Des = 0 ---
    if any(k in iname for k in ["armatura a piastre", "piastre complete", "full plate", "completa", "piastre naniche", "dwarven plate"]) or (iname in ("piastre", "plate")):
        res["category"] = "heavy"
        res["base_ac"] = 18
        res["max_dex"] = 0
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["corazza a strisce", "strisce", "splint"]):
        res["category"] = "heavy"
        res["base_ac"] = 17
        res["max_dex"] = 0
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["cotta di maglia", "chain mail"]):
        res["category"] = "heavy"
        res["base_ac"] = 16
        res["max_dex"] = 0
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["corazza ad anelli", "anelli", "ring mail"]):
        res["category"] = "heavy"
        res["base_ac"] = 14
        res["max_dex"] = 0
        res["stealth_disadv"] = True

    # --- Media (Medium Armor): Des max = 2 ---
    elif any(k in iname for k in ["mezza armatura", "half plate"]):
        res["category"] = "medium"
        res["base_ac"] = 15
        res["max_dex"] = 2
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["pettorale", "corazza pettorale", "breastplate"]):
        res["category"] = "medium"
        res["base_ac"] = 14
        res["max_dex"] = 2
    elif any(k in iname for k in ["scaglie", "corazza a scaglie", "scale mail", "scaglie di drago", "dragon scale"]):
        res["category"] = "medium"
        res["base_ac"] = 14
        res["max_dex"] = 2
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["giaco di maglia", "giaco elfico", "elven chain", "giaco", "chain shirt"]):
        res["category"] = "medium"
        res["base_ac"] = 13
        res["max_dex"] = 2
    elif any(k in iname for k in ["pelle", "armatura di pelle", "hide"]):
        res["category"] = "medium"
        res["base_ac"] = 12
        res["max_dex"] = 2

    # --- Leggera (Light Armor): Des completa ---
    elif any(k in iname for k in ["cuoio borchiato", "borchiato", "studded leather", "studded"]):
        res["category"] = "light"
        res["base_ac"] = 12
        res["max_dex"] = None
    elif any(k in iname for k in ["imbottita", "padded"]):
        res["category"] = "light"
        res["base_ac"] = 11
        res["max_dex"] = None
        res["stealth_disadv"] = True
    elif any(k in iname for k in ["cuoio", "leather"]):
        res["category"] = "light"
        res["base_ac"] = 11
        res["max_dex"] = None
    else:
        # Se presente ac_base esplicito
        exp_base = item.get("ac_base", item.get("base_ac"))
        if exp_base is not None:
            try:
                res["base_ac"] = int(exp_base)
            except (ValueError, TypeError):
                res["base_ac"] = 11
        else:
            res["base_ac"] = 11
        res["category"] = "medium"
        res["max_dex"] = 2

    # Calcolo bonus magico armatura
    magic_b = 0
    if "magic_bonus" in item:
        try: magic_b = max(magic_b, int(item["magic_bonus"]))
        except Exception: pass
    if "bonus_ac" in item:
        try: magic_b = max(magic_b, int(item["bonus_ac"]))
        except Exception: pass
    if "bonus" in item:
        try: magic_b = max(magic_b, int(item["bonus"]))
        except Exception: pass

    # Armature celebri 5e
    if any(k in iname for k in ["piastre naniche", "dwarven plate"]):
        magic_b = max(magic_b, 2)
    elif any(k in iname for k in ["scaglie di drago", "dragon scale", "giaco elfico", "elven chain"]):
        magic_b = max(magic_b, 1)
    elif any(k in iname for k in ["armatura demoniaca", "demon armor"]):
        magic_b = max(magic_b, 1)

    if magic_b == 0:
        magic_b = extract_magic_bonus(iname)

    if magic_b == 0:
        m = re.search(r'\+([1-5])\s*(?:alla\s*)?(?:ca|ac|armatura|classe armatura)\b', desc)
        if m:
            try: magic_b = int(m.group(1))
            except Exception: pass

    res["magic_bonus"] = magic_b
    return res


def _is_tome_or_manual(iname: str) -> bool:
    return any(k in iname for k in [
        "tomo della comprensione", "tome of understanding",
        "tomo del chiaro pensiero", "tome of clear thought",
        "tomo della leadership", "tome of leadership",
        "manuale della salute", "manual of bodily health",
        "manuale dell'esercizio fisico", "manual of gainful exercise",
        "manuale dei movimenti rapidi", "manual of quickness of action"
    ])


def _get_char_field(character_or_dict: Any, attr: str, default: Any = None) -> Any:
    if isinstance(character_or_dict, dict):
        return character_or_dict.get(attr, default)
    sheet = getattr(character_or_dict, "full_sheet", None)
    if isinstance(sheet, dict) and attr in sheet:
        return sheet.get(attr, default)
    if hasattr(character_or_dict, attr):
        return getattr(character_or_dict, attr)
    if isinstance(sheet, dict):
        return sheet.get(attr, default)
    return default


def calculate_character_item_modifiers(character_or_dict: Any) -> Dict[str, Any]:
    """
    Analizza tutti gli oggetti nell'inventario di un personaggio (o dizionario),
    calcolando tutti i modificatori attivi (equipaggiati o sintonizzati).
    """
    def _get(attr, default=None):
        return _get_char_field(character_or_dict, attr, default)

    inventory = _get("inventory_grid", []) or []
    char_class = str(_get("char_class", "")).lower()
    subclass = str(_get("subclass", "")).lower()
    level = int(_get("level", 1) or 1)
    backpack_dropped = bool(_get("backpack_dropped", False))

    # Limite sintonizzazioni (5e RAW: 3 standard, fino a 6 per Artefice)
    max_attune = 3
    if "artefice" in char_class or "artificer" in char_class:
        max_attune = 6 if level >= 18 else (5 if level >= 14 else (4 if level >= 10 else 3))

    equipped_armor_item = None
    equipped_armor_props = None
    equipped_shield_item = None
    equipped_shield_props = None

    attuned_items = []
    seen_attuned_names = set()
    active_non_attuned_items = []

    stowed_containers = {"bag_of_holding", "haversack", "mount"}

    # Scansione inventario
    for it in inventory:
        if not it or not isinstance(it, dict):
            continue
        container = str(it.get("container") or "backpack").strip().lower()
        if container in stowed_containers:
            continue
        if container == "backpack" and backpack_dropped:
            continue

        is_equipped = (container == "equipped")
        is_attuned = bool(it.get("attuned", False))
        iname_norm = str(it.get("name", "")).strip().lower()

        if is_equipped:
            # Rileva se armatura o scudo
            props = detect_armor_properties(it)
            if props["is_shield"]:
                if equipped_shield_item is None or (
                    props["base_ac"] + props["magic_bonus"] >
                    equipped_shield_props["base_ac"] + equipped_shield_props["magic_bonus"]
                ):
                    equipped_shield_item = it
                    equipped_shield_props = props
            elif props["is_armor"]:
                if equipped_armor_item is None or (
                    props["base_ac"] + props["magic_bonus"] >
                    equipped_armor_props["base_ac"] + equipped_armor_props["magic_bonus"]
                ):
                    equipped_armor_item = it
                    equipped_armor_props = props
            elif not is_attuned and (_is_tome_or_manual(iname_norm) or it.get("requires_attunement") is False):
                active_non_attuned_items.append(it)

        if is_attuned:
            # D&D 5e RAW (PHB p. 138 / DMG p. 252): non ci si può sintonizzare con più copie dello stesso oggetto
            if len(attuned_items) < max_attune:
                if not iname_norm or iname_norm not in seen_attuned_names:
                    if iname_norm:
                        seen_attuned_names.add(iname_norm)
                    attuned_items.append(it)

    # Struttura dei risultati
    modifiers = {
        # Armatura e Scudo
        "equipped_armor": equipped_armor_item,
        "armor_props": equipped_armor_props,
        "equipped_shield": equipped_shield_item,
        "shield_props": equipped_shield_props,
        "has_shield": equipped_shield_item is not None,
        "shield_total_ac": (equipped_shield_props["base_ac"] + equipped_shield_props["magic_bonus"]) if equipped_shield_props else 0,
        
        # Bonus generici (Wondrous items / Attuned)
        "bonus_ac": 0,
        "bonus_saves": 0,
        "set_stats": {},
        "bonus_stats": {},
        "bonus_speed": 0,
        "bonus_spell_dc": 0,
        "bonus_spell_attack": 0,
        "special_ac_base": None,    # es. Veste dell'Arcimago (Base 15 + Des)
        
        # Metadati
        "attuned_items": attuned_items,
        "attuned_count": len(attuned_items),
        "max_attunement": max_attune,
        "active_bonuses_summary": []
    }

    # Analisi degli oggetti attivi (sintonizzati + oggetti equipaggiati senza sintonia come Tomi/Manuali)
    seen_active_names = set()
    for item in (attuned_items + active_non_attuned_items):
        iname = str(item.get("name", "")).lower().strip()
        desc = str(item.get("desc", "")).lower()

        if iname:
            if iname in seen_active_names:
                continue
            seen_active_names.add(iname)

        item_armor_props = detect_armor_properties(item)
        is_same_as_equipped_armor = (equipped_armor_item is not None and item is equipped_armor_item)
        is_same_as_equipped_shield = (equipped_shield_item is not None and item is equipped_shield_item)

        # Un'armatura o uno scudo non attualmente equipaggiati come primari non conferiscono alcun bonus
        if item_armor_props["is_armor"] and not is_same_as_equipped_armor:
            continue
        if item_armor_props["is_shield"] and not is_same_as_equipped_shield:
            continue

        # 1. Stat Setters (D&D 5e RAW)
        if any(k in iname for k in ["guanti della forza dell'orco", "gauntlets of ogre power"]):
            modifiers["set_stats"]["FOR"] = max(modifiers["set_stats"].get("FOR", 0), 19)
            modifiers["active_bonuses_summary"].append("FOR=19")
        elif any(k in iname for k in ["fascia dell'intelletto", "headband of intellect"]):
            modifiers["set_stats"]["INT"] = max(modifiers["set_stats"].get("INT", 0), 19)
            modifiers["active_bonuses_summary"].append("INT=19")
        elif any(k in iname for k in ["amuleto della salute", "amulet of health"]):
            modifiers["set_stats"]["COS"] = max(modifiers["set_stats"].get("COS", 0), 19)
            modifiers["active_bonuses_summary"].append("COS=19")
        elif any(k in iname for k in ["mano di vecna", "hand of vecna"]):
            modifiers["set_stats"]["FOR"] = max(modifiers["set_stats"].get("FOR", 0), 20)
            modifiers["active_bonuses_summary"].append("FOR=20")
        elif "cintura della forza dei giganti" in iname or ("belt" in iname and "giant strength" in iname):
            if any(k in iname for k in ["tempesta", "storm"]):
                b_str = 29
            elif any(k in iname for k in ["nuvole", "cloud"]):
                b_str = 27
            elif any(k in iname for k in ["fuoco", "fire"]):
                b_str = 25
            elif any(k in iname for k in ["pietra", "gelo", "frost", "stone"]):
                b_str = 23
            else:
                b_str = 21  # Collina
            modifiers["set_stats"]["FOR"] = max(modifiers["set_stats"].get("FOR", 0), b_str)
            modifiers["active_bonuses_summary"].append(f"FOR={b_str}")

        # Proprietà esplicite set_stat
        for stat_k in ("str", "dex", "con", "int", "wis", "cha"):
            field = f"set_{stat_k}"
            if field in item:
                canon = canonical_stat_key(stat_k)
                try:
                    s_val = int(item[field])
                    modifiers["set_stats"][canon] = max(modifiers["set_stats"].get(canon, 0), s_val)
                    modifiers["active_bonuses_summary"].append(f"{canon}={s_val}")
                except Exception:
                    pass

        # 2. Stat Adders (+2 Tomi, Manuali o bonus_stats)
        handled_stats = False
        for stat_k in ("str", "dex", "con", "int", "wis", "cha"):
            field = f"bonus_{stat_k}"
            if field in item:
                canon = canonical_stat_key(stat_k)
                try:
                    b_val = int(item[field])
                    modifiers["bonus_stats"][canon] = modifiers["bonus_stats"].get(canon, 0) + b_val
                    handled_stats = True
                except Exception:
                    pass
        if "bonus_stats" in item and isinstance(item["bonus_stats"], dict):
            for sk, sv in item["bonus_stats"].items():
                canon = canonical_stat_key(sk)
                try:
                    modifiers["bonus_stats"][canon] = modifiers["bonus_stats"].get(canon, 0) + int(sv)
                    handled_stats = True
                except Exception:
                    pass

        if not handled_stats:
            if any(k in iname for k in ["tomo della comprensione", "tome of understanding"]):
                modifiers["bonus_stats"]["SAG"] = modifiers["bonus_stats"].get("SAG", 0) + 2
            elif any(k in iname for k in ["tomo del chiaro pensiero", "tome of clear thought"]):
                modifiers["bonus_stats"]["INT"] = modifiers["bonus_stats"].get("INT", 0) + 2
            elif any(k in iname for k in ["tomo della leadership", "tome of leadership"]):
                modifiers["bonus_stats"]["CAR"] = modifiers["bonus_stats"].get("CAR", 0) + 2
            elif any(k in iname for k in ["manuale della salute", "manual of bodily health"]):
                modifiers["bonus_stats"]["COS"] = modifiers["bonus_stats"].get("COS", 0) + 2
            elif any(k in iname for k in ["manuale dell'esercizio fisico", "manual of gainful exercise"]):
                modifiers["bonus_stats"]["FOR"] = modifiers["bonus_stats"].get("FOR", 0) + 2
            elif any(k in iname for k in ["manuale dei movimenti rapidi", "manual of quickness of action"]):
                modifiers["bonus_stats"]["DES"] = modifiers["bonus_stats"].get("DES", 0) + 2

        # 3. Oggetti difensivi e CA
        handled_ac = False
        if not is_same_as_equipped_armor and not is_same_as_equipped_shield:
            # Proprietà esplicita bonus_ac
            if "bonus_ac" in item:
                try:
                    modifiers["bonus_ac"] += int(item["bonus_ac"])
                    handled_ac = True
                except Exception:
                    pass
            elif "ac_bonus" in item:
                try:
                    modifiers["bonus_ac"] += int(item["ac_bonus"])
                    handled_ac = True
                except Exception:
                    pass

            if not handled_ac:
                if any(k in iname for k in ["anello di protezione", "mantello della protezione", "ring of protection", "cloak of protection"]):
                    modifiers["bonus_ac"] += 1
                    handled_ac = True
                elif any(k in iname for k in ["bracciali della difesa", "bracers of defense"]):
                    # D&D 5e RAW: +2 CA SOLO se NON si indossa armatura e NON si usa scudo
                    if equipped_armor_item is None and equipped_shield_item is None:
                        modifiers["bonus_ac"] += 2
                    handled_ac = True
                elif any(k in iname for k in ["bastone del potere", "staff of power"]):
                    modifiers["bonus_ac"] += 2
                    handled_ac = True
                elif any(k in iname for k in ["veste dell'arcimago", "robe of the archmagi"]):
                    # Base AC 15 + Des se senz'armatura
                    modifiers["special_ac_base"] = 15
                    handled_ac = True
                elif any(k in iname for k in ["difensore", "defender"]):
                    # Spada Difensore (può allocare bonus alla CA)
                    pass
                else:
                    # Regex descrizione es. '+1 alla CA'
                    ac_m = re.search(r'\+([1-5])\s*(?:alla\s*)?(?:ca|ac|armatura|classe armatura)\b', desc)
                    if ac_m:
                        try:
                            modifiers["bonus_ac"] += int(ac_m.group(1))
                            handled_ac = True
                        except Exception:
                            pass

        # 4. Tiri Salvezza
        handled_saves = False
        if "bonus_saves" in item:
            try:
                modifiers["bonus_saves"] += int(item["bonus_saves"])
                handled_saves = True
            except Exception:
                pass
        elif "save_bonus" in item:
            try:
                modifiers["bonus_saves"] += int(item["save_bonus"])
                handled_saves = True
            except Exception:
                pass

        if not handled_saves:
            if any(k in iname for k in ["anello di protezione", "mantello della protezione", "ring of protection", "cloak of protection", "pietra della buona fortuna", "luckstone", "stone of good luck"]):
                modifiers["bonus_saves"] += 1
            elif any(k in iname for k in ["bastone del potere", "staff of power", "veste dell'arcimago", "robe of the archmagi"]):
                modifiers["bonus_saves"] += 2
            else:
                s_m = re.search(r'\+([1-5])\s*(?:a\s*tutti\s*i\s*)?(?:tiri\s*salvezza|ts|saving\s*throws)\b', desc)
                if s_m:
                    try:
                        modifiers["bonus_saves"] += int(s_m.group(1))
                    except Exception:
                        pass

        # 5. Magia: CD e Attacco Incantesimi
        handled_spell_dc = False
        handled_spell_atk = False
        if "bonus_spell_dc" in item:
            try:
                modifiers["bonus_spell_dc"] += int(item["bonus_spell_dc"])
                handled_spell_dc = True
            except Exception:
                pass
        if "bonus_spell_attack" in item:
            try:
                modifiers["bonus_spell_attack"] += int(item["bonus_spell_attack"])
                handled_spell_atk = True
            except Exception:
                pass

        # Oggetti magici ufficiali focalizzatori (+1, +2, +3)
        if not handled_spell_dc and not handled_spell_atk:
            if any(k in iname for k in [
                "verga del custode del patto", "rod of the pact keeper",
                "amuleto del devoto", "amulet of the devout",
                "grimorio arcano", "arcane grimoire",
                "fiala del sangue", "bloodwell vial",
                "falce lunare", "moon sickle",
                "tamburo del ritmo", "rhythm maker's drum"
            ]):
                m_bonus = extract_magic_bonus(iname) or 1
                modifiers["bonus_spell_dc"] += m_bonus
                modifiers["bonus_spell_attack"] += m_bonus
            elif any(k in iname for k in ["bacchetta del mago da guerra", "wand of the war mage"]):
                m_bonus = extract_magic_bonus(iname) or 1
                modifiers["bonus_spell_attack"] += m_bonus
            elif any(k in iname for k in ["veste dell'arcimago", "robe of the archmagi"]):
                modifiers["bonus_spell_dc"] += 2
                modifiers["bonus_spell_attack"] += 2
            elif any(k in iname for k in ["bastone del potere", "staff of power"]):
                # D&D 5e RAW (DMG p. 202): +2 agli attacchi con incantesimi (non alla CD)
                modifiers["bonus_spell_attack"] += 2

        # 6. Velocità
        if "bonus_speed" in item:
            try: modifiers["bonus_speed"] += int(item["bonus_speed"])
            except Exception: pass
        elif any(k in iname for k in ["stivali della velocit", "boots of speed"]):
            pass

    return modifiers


def get_effective_attribute_from_dict(character_or_dict: Any, stat_name: str, mods: Optional[Dict[str, Any]] = None) -> int:
    """
    Restituisce il punteggio effettivo di una caratteristica (es. FOR, DES, COS, INT, SAG, CAR)
    su un oggetto Character o dizionario full_sheet, considerando set_stats e bonus_stats degli oggetti.
    """
    def _get(attr, default=None):
        return _get_char_field(character_or_dict, attr, default)

    if mods is None:
        mods = calculate_character_item_modifiers(character_or_dict)

    canon = canonical_stat_key(stat_name)
    base = 10
    attrs = _get("attributes", {})
    if isinstance(attrs, dict):
        if canon in attrs:
            try:
                base = int(attrs[canon])
            except (ValueError, TypeError):
                base = 10
        else:
            for k, v in attrs.items():
                if canonical_stat_key(k) == canon:
                    try:
                        base = int(v)
                    except (ValueError, TypeError):
                        base = 10
                    break
    if canon in mods["set_stats"]:
        base = max(base, mods["set_stats"][canon])
    if canon in mods["bonus_stats"]:
        base += mods["bonus_stats"][canon]
    return base


def get_effective_save_bonus_from_dict(character_or_dict: Any, stat_name: str, mods: Optional[Dict[str, Any]] = None) -> int:
    """
    Calcola il bonus totale di Tiro Salvezza per una caratteristica su un oggetto Character o dizionario full_sheet,
    includendo il modificatore effettivo (con oggetti come Guanti dell'Orco/Amuleto Salute), la competenza
    e i bonus ai tiri salvezza da oggetti (Anello/Mantello Protezione, Pietra Buona Fortuna, Bastone del Potere).
    """
    def _get(attr, default=None):
        return _get_char_field(character_or_dict, attr, default)

    if mods is None:
        mods = calculate_character_item_modifiers(character_or_dict)

    canon = canonical_stat_key(stat_name)

    # Supporto esplicito per mostri con dizionario saving_throws (es. {"SAG": "+5"} o {"WIS": 5})
    st_dict = _get("saving_throws", None)
    if isinstance(st_dict, dict) and st_dict:
        for k, v in st_dict.items():
            if canonical_stat_key(k) == canon and v is not None and str(v).strip() != "":
                try:
                    explicit_val = int(str(v).replace("+", "").strip())
                    return explicit_val + mods.get("bonus_saves", 0)
                except (ValueError, TypeError):
                    pass

    eff_score = get_effective_attribute_from_dict(character_or_dict, canon, mods=mods)
    mod = (eff_score - 10) // 2

    profs = _get("saving_throw_proficiencies", None)
    # Ladro Lv 15+ Mente Sfuggente (Slippery Mind, PHB p. 96): competenza ai TS su Saggezza
    if str(stat_name or "").upper().strip() in ("SAG", "WIS", "SAGGEZZA", "WISDOM"):
        if entity_get_class_level(character_or_dict, "ladro", "rogue") >= 15 or entity_has_keyword(character_or_dict, "mente sfuggente", "slippery mind"):
            if isinstance(profs, (list, tuple, set)):
                if not any(str(x).upper().strip() in ("SAG", "WIS", "SAGGEZZA", "WISDOM") for x in profs):
                    profs = list(profs) + ["SAG"]
            elif profs is None:
                profs = ["SAG"]
    if not isinstance(profs, (list, tuple, set)):
        profs = st_dict if isinstance(st_dict, (list, tuple, set)) else []
    norm_profs = {canonical_stat_key(p) for p in profs if p}

    if canon in norm_profs:
        lvl_raw = _get("level", _get("cr", 1))
        try:
            lvl = max(1, int(float(str(lvl_raw).split("/")[0]) if "/" in str(lvl_raw) else float(lvl_raw or 1)))
        except (ValueError, TypeError):
            lvl = 1
        prof_bonus = ((lvl - 1) // 4) + 2
        mod += prof_bonus
    else:
        # Anima di Diamante (Monaco Liv 14+, PHB p. 79): competenza in TUTTI i Tiri Salvezza
        try:
            monk_lvl = entity_get_class_level(character_or_dict, "monaco", "monk")
            if monk_lvl >= 14 or entity_has_keyword(character_or_dict, "anima di diamante", "diamond soul"):
                tot_lvl = entity_get_total_level(character_or_dict)
                mod += ((max(1, tot_lvl) - 1) // 4) + 2
        except Exception:
            pass

    return mod + mods.get("bonus_saves", 0)


def is_item_cursed(item_dict: Any) -> bool:
    """Ritorna True se un oggetto è maledetto e la maledizione non è stata rimossa (DMG p. 138)."""
    if not item_dict or not isinstance(item_dict, dict):
        return False
    if item_dict.get("curse_lifted", False):
        return False
    if item_dict.get("cursed") or item_dict.get("is_cursed"):
        return True
    txt = f"{item_dict.get('name', '')} {item_dict.get('desc', '')}".lower()
    return "maledett" in txt or "cursed" in txt


def can_unattune_item(item_dict: Any) -> Tuple[bool, str]:
    """
    DMG p. 138: Non è possibile interrompere volontariamente la sintonia con un oggetto maledetto
    finché la maledizione non viene spezzata (es. con Rimuovi Maledizione).
    """
    if is_item_cursed(item_dict):
        iname = item_dict.get("name", "Oggetto Maledetto")
        return False, f"'{iname}' è MALEDETTO: impossibile rimuoverne la sintonia senza Rimuovi Maledizione (Remove Curse)!"
    return True, "Sintonia terminabile."


def lift_curse_on_inventory(character_or_dict: Any, target_item_name: Optional[str] = None) -> List[str]:
    """
    Rimuove la maledizione dagli oggetti nell'inventario di un personaggio o Player.
    Ritorna la lista dei nomi degli oggetti liberati dalla maledizione.
    """
    lifted = []
    inv = _get_char_field(character_or_dict, "inventory_grid", None)
    if not isinstance(inv, list):
        return lifted
    t_low = str(target_item_name or "").strip().lower()
    for it in inv:
        if not it or not isinstance(it, dict):
            continue
        if t_low and t_low not in str(it.get("name", "")).lower():
            continue
        if is_item_cursed(it):
            it["curse_lifted"] = True
            it["cursed"] = False
            lifted.append(it.get("name", "Oggetto Maledetto"))
    return lifted


def _has_fighting_style_defense(features_str: str) -> bool:
    """
    Verifica se il personaggio possiede effettivamente lo Stile di Combattimento: Difesa (+1 CA con armatura),
    evitando falsi positivi da 'Difesa Senz'Armatura', descrizioni generali di classe o incantesimi.
    """
    if not features_str:
        return False
    # Rimuovi le occorrenze note che NON sono lo Stile di Combattimento Difesa
    cleaned = re.sub(r"difesa\s+senz['’]?armatura", "", features_str)
    cleaned = re.sub(r"unarmored\s+defense", "", cleaned)
    cleaned = re.sub(r"scudo\s+per\s+la\s+difesa", "", cleaned)
    cleaned = re.sub(r"difesa\s+contro\s+attacchi\s+multipli", "", cleaned)
    cleaned = re.sub(r"multiattack\s+defense", "", cleaned)
    cleaned = re.sub(r"difesa\s+seducente", "", cleaned)
    cleaned = re.sub(r"beguiling\s+defenses", "", cleaned)
    # Rimuovi la riga descrittiva generica dell'elenco di tutti gli stili in classes_data.py
    # (che elenca tiro, difesa, duello, ecc. nello stesso blocco)
    if ("tiro:" in cleaned and "duello:" in cleaned) or ("archery" in cleaned and "dueling" in cleaned):
        cleaned = re.sub(r"[•\-*]\s*difesa\s*:\s*bonus\s+permanente[^\n]*", "", cleaned)
        cleaned = re.sub(r"defense\s*\(\+1\s*ac\)\s*,?", "", cleaned)
    return bool(re.search(r"\b(?:difesa|defense)\b", cleaned))


def compute_effective_ac(character_or_dict: Any) -> int:
    """
    Calcola la Classe Armatura (CA) finale totale di un personaggio considerando:
    - Armatura indossata (base + modificatore destrezza + bonus magico dell'armatura)
    - Difesa senz'armatura (Monaco, Barbaro, Resilienza Draconica, Veste dell'Arcimago)
    - Stile di Combattimento Difesa (+1 se indossa un'armatura)
    - Scudo equipaggiato (base +2 + bonus magico dello scudo)
    - Oggetti meravigliosi, anelli, mantelli e sintonizzazioni (Anello Protezione, Bracciali Difesa, ecc.)
    """
    def _get(attr, default=None):
        return _get_char_field(character_or_dict, attr, default)

    mods = calculate_character_item_modifiers(character_or_dict)

    # Modificatori di caratteristica effettivi (considerando set_stats e bonus_stats)
    def _effective_mod(stat_name: str) -> int:
        eff_val = get_effective_attribute_from_dict(character_or_dict, stat_name, mods=mods)
        return (eff_val - 10) // 2

    des_mod = _effective_mod("DES")
    cos_mod = _effective_mod("COS")
    sag_mod = _effective_mod("SAG")

    armor_item = mods["equipped_armor"]
    armor_props = mods["armor_props"]
    shield_item = mods["equipped_shield"]
    has_shield = (shield_item is not None)

    char_cls = str(_get("char_class", "")).lower()
    subclass = str(_get("subclass", "")).lower()

    features_raw = _get("features", [])
    if isinstance(features_raw, str):
        features_str = features_raw.lower()
    elif isinstance(features_raw, (list, tuple, set)):
        features_str = " ".join(str(f).lower() for f in features_raw)
    else:
        features_str = ""
    features_list_raw = _get("features_list", [])
    if isinstance(features_list_raw, list) and features_list_raw:
        fl_str = " ".join(
            f"{f.get('name', '')} {f.get('desc', '')}".lower() if isinstance(f, dict) else str(f).lower()
            for f in features_list_raw
        )
        features_str = f"{features_str} {fl_str}".strip()

    if armor_item and armor_props:
        # Calcolo destrezza applicabile
        max_dex = armor_props["max_dex"]
        # Talento Maestro delle Armature Medie (PHB p. 168): max +3 DES con armature medie
        if max_dex == 2 and entity_has_keyword(character_or_dict, "maestro delle armature medie", "medium armor master"):
            max_dex = 3
        if max_dex is None:
            dex_allowed = des_mod
        elif max_dex == 0:
            dex_allowed = 0
        else:
            dex_allowed = min(max_dex, des_mod)

        # Base armatura + bonus magico armatura (+1, +2, +3, ecc.)
        base_ac = armor_props["base_ac"] + armor_props["magic_bonus"] + dex_allowed

        # Stile di Combattimento Difesa: +1 CA mentre si indossa un'armatura
        if _has_fighting_style_defense(features_str):
            base_ac += 1
    else:
        # Difesa senz'armatura (D&D 5e RAW: in multiclasse NON si cumulano né si riottengono dopo la prima, PHB p. 164)
        classes_dict = _get("classes", {})
        ordered_classes = [str(k).lower() for k in classes_dict.keys()] if isinstance(classes_dict, dict) and classes_dict else [char_cls]
        first_unarmored_source = None
        for cls_entry in ordered_classes:
            if "monaco" in cls_entry or "monk" in cls_entry:
                first_unarmored_source = "monk"
                break
            if "barbaro" in cls_entry or "barbarian" in cls_entry:
                first_unarmored_source = "barbarian"
                break
        if first_unarmored_source is None:
            if "monaco" in char_cls or "monk" in char_cls:
                first_unarmored_source = "monk"
            elif "barbaro" in char_cls or "barbarian" in char_cls:
                first_unarmored_source = "barbarian"

        if mods["special_ac_base"] is not None:
            # Es. Veste dell'Arcimago: 15 + Des
            base_ac = mods["special_ac_base"] + des_mod
        elif first_unarmored_source == "monk":
            # 10 + Des + Sag (solo se NON si usa uno scudo, PHB p. 78)
            base_ac = 10 + des_mod + (sag_mod if not has_shield else 0)
        elif first_unarmored_source == "barbarian":
            # 10 + Des + Cos (può usare uno scudo, PHB p. 48)
            base_ac = 10 + des_mod + cos_mod
        elif "dracon" in subclass or "draconic" in subclass:
            # Resilienza Draconica (Stregone, PHB p. 102): 13 + Des
            base_ac = 13 + des_mod
        else:
            base_ac = 10 + des_mod

        from common.subclass_and_race_rules import apply_tortle_natural_armor
        base_ac, _ = apply_tortle_natural_armor(character_or_dict, base_ac, shield_bonus=0)

    # Scudo: +2 base + bonus magico scudo
    if has_shield:
        base_ac += mods["shield_total_ac"]

    # Oggetti meravigliosi, anelli, mantelli (+1 CA Anello di Protezione, +2 Bracciali della Difesa, ecc.)
    final_ac = base_ac + mods["bonus_ac"]
    # Talento Combattente a Due Armi (Dual Wielder, PHB p. 165): +1 CA mentre si impugna un'arma da mischia in ciascuna mano (senza scudo)
    if not shield_item and entity_has_keyword(character_or_dict, "combattente a due armi", "dual wielder"):
        is_dw = bool(_get("dual_wielding", False))
        if not is_dw:
            inv_items = _get("inventory", []) or []
            eq_melee = 0
            for it in inv_items:
                if isinstance(it, dict) and it.get("equipped") and not it.get("is_shield"):
                    it_cat = str(it.get("category", "") or it.get("type", "")).lower()
                    it_name = str(it.get("name", "")).lower()
                    if any(k in it_cat or k in it_name for k in ("spada", "ascia", "pugnale", "mazza", "martello", "lancia", "stocco", "scimitarra", "flagello", "piccone", "sword", "axe", "dagger", "mace", "hammer", "spear", "rapier", "scimitar", "weapon", "arma")) and not any(rk in it_name for rk in ("arco", "balestra", "fionda", "cerbottana", "bow", "crossbow", "sling", "blowgun", "scudo", "shield")):
                        eq_melee += 1
            if eq_melee >= 2:
                is_dw = True
        if is_dw:
            final_ac += 1
    return final_ac


def detect_item_charges_defaults(item_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rileva o inizializza i valori predefiniti D&D 5e RAW per le cariche di un oggetto magico
    (es. Bastone del Potere, Bacchetta delle Palle di Fuoco, Bacchetta dei Dardi Incantati).
    Ritorna un dizionario con 'charges_max', 'charges_current', 'recharge_dice'.
    """
    if not isinstance(item_dict, dict):
        return {"charges_max": 0, "charges_current": 0, "recharge_dice": ""}

    if "charges_max" in item_dict and int(item_dict.get("charges_max") or 0) > 0:
        c_max = int(item_dict["charges_max"])
        c_cur = int(item_dict.get("charges_current", c_max))
        rec = str(item_dict.get("recharge_dice", "1d6+1"))
        return {"charges_max": c_max, "charges_current": max(0, min(c_max, c_cur)), "recharge_dice": rec}

    iname = str(item_dict.get("name", "")).strip().lower()
    desc = str(item_dict.get("desc", "")).strip().lower()

    res = {"charges_max": 0, "charges_current": 0, "recharge_dice": ""}
    if any(k in iname for k in ("bastone dei magi", "staff of the magi")):
        res = {"charges_max": 50, "charges_current": 50, "recharge_dice": "4d6+2"}
    elif any(k in iname for k in ("bastone del potere", "staff of power")):
        res = {"charges_max": 20, "charges_current": 20, "recharge_dice": "2d8+4"}
    elif any(k in iname for k in (
        "bastone della guarigione", "staff of healing",
        "bastone dei boschi", "staff of the woodlands",
        "bastone del fuoco", "staff of fire",
        "bastone del gelo", "staff of frost",
        "bastone dello sciame", "staff of swarming insects"
    )):
        res = {"charges_max": 10, "charges_current": 10, "recharge_dice": "1d6+4"}
    elif any(k in iname for k in (
        "bacchetta delle palle di fuoco", "wand of fireballs",
        "bacchetta dei fulmini", "wand of lightning bolts",
        "bacchetta dei dardi incantati", "wand of magic missiles",
        "bacchetta della paralisi", "wand of paralysis",
        "bacchetta delle ragnatele", "wand of web",
        "bacchetta della paura", "wand of fear",
        "bacchetta di metamorfosi", "wand of polymorph"
    )):
        res = {"charges_max": 7, "charges_current": 7, "recharge_dice": "1d6+1"}
    elif any(k in iname for k in ("anello dell'ariete", "ring of the ram")):
        res = {"charges_max": 3, "charges_current": 3, "recharge_dice": "1d3"}
    else:
        # Fallback regex sulla descrizione es. "ha 7 cariche" o "has 10 charges"
        m = re.search(r'\b(\d+)\s*(?:cariche|charges)\b', desc)
        if m:
            c_max = int(m.group(1))
            rec_m = re.search(r'(\d+d\d+(?:\s*\+\s*\d+)?)', desc)
            rec = rec_m.group(1).replace(" ", "") if rec_m else "1d6+1"
            res = {"charges_max": c_max, "charges_current": c_max, "recharge_dice": rec}

    if res["charges_max"] > 0:
        item_dict.setdefault("charges_max", res["charges_max"])
        item_dict.setdefault("charges_current", res["charges_current"])
        item_dict.setdefault("recharge_dice", res["recharge_dice"])
    return res


def use_item_charge_dict(item_dict: Dict[str, Any], cost: int = 1) -> tuple:
    """
    Spende 'cost' cariche da un oggetto magico (5e RAW).
    Se l'oggetto scende a 0 cariche, effettua il tiro di 1d20 previsto dalla DMG (p. 141):
    con un risultato di 1, avvisa del rischio di esaurimento/sbriciolamento in cenere.
    Ritorna: (success: bool, message: str)
    """
    if not isinstance(item_dict, dict):
        return False, "Oggetto non valido."
    if item_dict.get("magic_destroyed"):
        return False, f"'{item_dict.get('name', 'Oggetto')}' ha perso la sua magia / è sbriciolato (DMG p. 141)."
    defaults = detect_item_charges_defaults(item_dict)
    if "charges_max" not in item_dict and defaults["charges_max"] > 0:
        item_dict["charges_max"] = defaults["charges_max"]
        item_dict["charges_current"] = defaults["charges_current"]
        item_dict["recharge_dice"] = defaults["recharge_dice"]

    c_max = int(item_dict.get("charges_max") or 0)
    if c_max <= 0:
        return False, f"'{item_dict.get('name', 'Oggetto')}' non possiede cariche magiche."

    c_cur = int(item_dict.get("charges_current", c_max))
    cost = max(1, int(cost))
    if c_cur < cost:
        return False, f"Cariche insufficienti su '{item_dict.get('name', 'Oggetto')}' ({c_cur}/{c_max} disponibili, richieste {cost})."

    item_dict["charges_current"] = c_cur - cost
    rem = item_dict["charges_current"]
    name = item_dict.get("name", "Oggetto Magico")
    msg = f"⚡ Usate {cost} carica/he di **{name}** (Cariche rimaste: **{rem}/{c_max}**)."

    if rem == 0:
        from common.dice import roll_dice
        d20_res = roll_dice("1d20")["total"]
        no_destr = bool(item_dict.get("no_destroy_on_zero", False))
        if d20_res == 1 and not no_destr:
            item_dict["magic_destroyed"] = True
            item_dict["charges_max"] = 0
            item_dict["charges_current"] = 0
            item_dict["attuned"] = False
            if "sbriciolat" not in str(name).lower() and "senza magia" not in str(name).lower():
                item_dict["name"] = f"{name} [Senza Magia]"
            msg += f" 💥 **ULTIMA CARICA SPESA (1d20 = 1)!** Secondo il DMG (p. 141), **{name}** perde per sempre la sua magia / si sbriciola in cenere!"
        else:
            msg += f" (Ultima carica spesa: tiro conservazione 1d20 = {d20_res}, l'oggetto resta intatto)."

    return True, msg


def recharge_item_dict(item_dict: Dict[str, Any]) -> Optional[str]:
    """
    Ricarica un oggetto magico all'alba / al termine di un Riposo Lungo (5e RAW).
    Ritorna una stringa di riepilogo se l'oggetto ha recuperato cariche, altrimenti None.
    """
    if not isinstance(item_dict, dict):
        return None
    if item_dict.get("magic_destroyed"):
        return None
    defaults = detect_item_charges_defaults(item_dict)
    if "charges_max" not in item_dict and defaults["charges_max"] > 0:
        item_dict["charges_max"] = defaults["charges_max"]
        item_dict["charges_current"] = defaults["charges_current"]
        item_dict["recharge_dice"] = defaults["recharge_dice"]

    c_max = int(item_dict.get("charges_max") or 0)
    if c_max <= 0:
        return None
    c_cur = int(item_dict.get("charges_current", c_max))
    if c_cur >= c_max:
        return None

    rec_formula = str(item_dict.get("recharge_dice") or defaults.get("recharge_dice") or "1d6+1").strip().lower()
    if rec_formula in ("all", "tutte", "max"):
        gained = c_max - c_cur
        item_dict["charges_current"] = c_max
        return f"✨ **{item_dict.get('name', 'Oggetto')}** recupera tutte le cariche ({c_max}/{c_max})."

    from common.dice import roll_dice
    try:
        rolled = max(1, int(roll_dice(rec_formula)["total"]))
    except Exception:
        rolled = 1
    new_cur = min(c_max, c_cur + rolled)
    actual_gain = new_cur - c_cur
    item_dict["charges_current"] = new_cur
    return f"✨ **{item_dict.get('name', 'Oggetto')}** recupera +{actual_gain} cariche all'alba [{rec_formula} = {rolled}] ({new_cur}/{c_max})."

