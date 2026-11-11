"""
character_schema.py - Schema canonico e normalizzatore per le schede personaggio di D&D OmniCompanion.
Unifica e garantisce la coerenza tra:
1. Oggetto 'Character' (client desktop)
2. Dizionario 'full_sheet' in 'Player' (server DM)
3. Dizionari salvati in 'client_data/characters.json' e nei file campagna/sessione.
Risolve alla radice tutti i disallineamenti di chiavi (char_class vs class_name, hp vs hp_current,
stats vs attributes, currency vs gp) garantendo retrocompatibilità al 100%.
"""

import copy
from typing import Dict, Any, Optional

# Mapping Caratteristiche IT <-> EN
STAT_IT_TO_EN = {
    "FOR": "STR",
    "DES": "DEX",
    "COS": "CON",
    "INT": "INT",
    "SAG": "WIS",
    "CAR": "CHA",
}

STAT_EN_TO_IT = {
    "STR": "FOR",
    "DEX": "DES",
    "CON": "COS",
    "INT": "INT",
    "WIS": "SAG",
    "CHA": "CAR",
}

CANONICAL_STATS_IT = ["FOR", "DES", "COS", "INT", "SAG", "CAR"]
CANONICAL_STATS_EN = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

# Mapping Valuta D&D 5e (Monete di Rame, Argento, Electrum, Oro, Platino)
COIN_KEYS_IT = ["MR", "MA", "ME", "MO", "MP"]
COIN_IT_TO_EN = {"MR": "cp", "MA": "sp", "ME": "ep", "MO": "gp", "MP": "pp"}
COIN_EN_TO_IT = {"cp": "MR", "sp": "MA", "ep": "ME", "gp": "MO", "pp": "MP"}

def calculate_modifier(score: Any) -> int:
    """Calcola il modificatore D&D 5e RAW: floor((punteggio - 10) / 2)."""
    try:
        val = int(score)
        return (val - 10) // 2
    except (ValueError, TypeError):
        return 0

def canonical_stat_name(stat: str, lang: str = "it") -> str:
    """Restituisce il nome canonico della caratteristica nella lingua richiesta ('it' o 'en')."""
    s = str(stat).strip().upper()
    if lang.lower() == "en":
        return STAT_IT_TO_EN.get(s, s if s in CANONICAL_STATS_EN else "STR")
    return STAT_EN_TO_IT.get(s, s if s in CANONICAL_STATS_IT else "FOR")

def normalize_character_dict(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalizza qualsiasi dizionario di scheda personaggio (vecchio formato, parziale o di rete)
    popolando e sincronizzando tutte le chiavi canoniche e i loro sinonimi.
    Garantisce che il dizionario contenga campi coerenti per client e server.
    """
    if not isinstance(data, dict):
        data = {}
    clean = copy.deepcopy(data)

    # 1. Nome & Identità
    clean["name"] = str(clean.get("name") or "Nuovo Personaggio").strip()
    
    # Classe: unifica char_class, class_name, character_class
    cls = (
        clean.get("char_class") or
        clean.get("class_name") or
        clean.get("character_class") or
        ""
    )
    clean["char_class"] = str(cls).strip()
    clean["class_name"] = str(cls).strip()
    clean["character_class"] = str(cls).strip()

    clean["race"] = str(clean.get("race") or "").strip()
    clean["subclass"] = str(clean.get("subclass") or "").strip()
    
    # Livello (1-20)
    try:
        lvl = int(clean.get("level") or 1)
        clean["level"] = max(1, min(20, lvl))
    except (ValueError, TypeError):
        clean["level"] = 1

    clean["background"] = str(clean.get("background") or "").strip()
    clean["alignment"] = str(clean.get("alignment") or "").strip()

    # 2. Caratteristiche (Sincronizza 'attributes' IT e 'stats' EN)
    raw_attrs = clean.get("attributes")
    raw_stats = clean.get("stats")

    norm_attrs: Dict[str, int] = {}
    norm_stats: Dict[str, int] = {}

    for it_k, en_k in STAT_IT_TO_EN.items():
        val = 10
        # Cerca valore in attributes (IT)
        if isinstance(raw_attrs, dict) and it_k in raw_attrs:
            try: val = int(raw_attrs[it_k])
            except (ValueError, TypeError): val = 10
        # O in stats (EN)
        elif isinstance(raw_stats, dict) and en_k in raw_stats:
            try: val = int(raw_stats[en_k])
            except (ValueError, TypeError): val = 10
        # O direttamente a livello radice (es. clean["FOR"] o clean["STR"])
        elif it_k in clean:
            try: val = int(clean[it_k])
            except (ValueError, TypeError): val = 10
        elif en_k in clean:
            try: val = int(clean[en_k])
            except (ValueError, TypeError): val = 10

        norm_attrs[it_k] = val
        norm_stats[en_k] = val

    clean["attributes"] = norm_attrs
    clean["stats"] = norm_stats

    # 3. Punti Ferita (Sincronizza hp_current, hp, current_hp e hp_max, max_hp)
    hp_cur_candidates = [
        clean.get("hp_current"),
        clean.get("hp"),
        clean.get("current_hp")
    ]
    hp_cur = 10
    for cand in hp_cur_candidates:
        if cand is not None:
            try:
                hp_cur = int(cand)
                break
            except (ValueError, TypeError):
                continue

    hp_max_candidates = [
        clean.get("hp_max"),
        clean.get("max_hp")
    ]
    hp_max = 10
    for cand in hp_max_candidates:
        if cand is not None:
            try:
                hp_max = int(cand)
                break
            except (ValueError, TypeError):
                continue

    # Clamping e garanzie
    hp_max = max(1, hp_max)
    hp_cur = max(0, min(hp_max, hp_cur))

    clean["hp_current"] = hp_cur
    clean["hp"] = hp_cur
    clean["current_hp"] = hp_cur

    clean["hp_max"] = hp_max
    clean["max_hp"] = hp_max

    try:
        clean["temp_hp"] = max(0, int(clean.get("temp_hp") or 0))
    except (ValueError, TypeError):
        clean["temp_hp"] = 0

    # 4. Classe Armatura (Sincronizza ac e armor_class)
    ac_val = clean.get("ac") if clean.get("ac") is not None else clean.get("armor_class", 10)
    try:
        ac_int = int(ac_val)
    except (ValueError, TypeError):
        ac_int = 10
    clean["ac"] = ac_int
    clean["armor_class"] = ac_int

    # 5. Iniziativa & Velocità & Competenza
    try:
        clean["initiative"] = int(clean.get("initiative") or 0)
    except (ValueError, TypeError):
        clean["initiative"] = 0

    speed_val = clean.get("speed")
    try:
        clean["speed"] = float(speed_val) if speed_val is not None else 9.0
    except (ValueError, TypeError):
        clean["speed"] = 9.0

    lvl = clean["level"]
    clean["proficiency_bonus"] = 2 + (lvl - 1) // 4

    # 6. Valuta (Sincronizza dict 'currency' e intero 'gp')
    curr_dict = clean.get("currency")
    if not isinstance(curr_dict, dict):
        curr_dict = {}

    norm_currency = {}
    for k in COIN_KEYS_IT:
        v = curr_dict.get(k)
        if v is None:
            en_alt = COIN_IT_TO_EN.get(k)
            v = curr_dict.get(en_alt, 0)
        try:
            norm_currency[k] = max(0, int(v or 0))
        except (ValueError, TypeError):
            norm_currency[k] = 0

    # Sincronizza 'gp' con 'MO'
    gp_direct = clean.get("gp")
    if gp_direct is not None:
        try:
            gp_int = max(0, int(gp_direct))
            if norm_currency["MO"] == 0 and gp_int > 0:
                norm_currency["MO"] = gp_int
        except (ValueError, TypeError):
            pass

    clean["currency"] = norm_currency
    clean["gp"] = norm_currency["MO"]

    # 7. Dadi Vita
    if not clean.get("hit_dice_type"):
        clean["hit_dice_type"] = "d8"
    clean["hit_dice_total"] = int(clean.get("hit_dice_total") or lvl)
    clean["hit_dice_current"] = int(clean.get("hit_dice_current") if clean.get("hit_dice_current") is not None else lvl)

    # 8. Inventario a Griglia (minimo 25 slot)
    grid = clean.get("inventory_grid")
    if not isinstance(grid, list):
        grid = [None] * 25
    else:
        while len(grid) < 25:
            grid.append(None)
    clean["inventory_grid"] = grid

    # 9. Slot Incantesimi (1..9 con max e current)
    slots = clean.get("spell_slots")
    if not isinstance(slots, dict):
        slots = {}
    norm_slots = {}
    for i in range(1, 10):
        lvl_str = str(i)
        slot_data = slots.get(lvl_str)
        if isinstance(slot_data, dict):
            s_max = slot_data.get("max", 0)
            s_cur = slot_data.get("current", s_max)
            norm_slots[lvl_str] = {"max": max(0, int(s_max or 0)), "current": max(0, int(s_cur or 0))}
        elif isinstance(slot_data, list) and len(slot_data) >= 2:
            norm_slots[lvl_str] = {"max": max(0, int(slot_data[1] or 0)), "current": max(0, int(slot_data[0] or 0))}
        else:
            norm_slots[lvl_str] = {"max": 0, "current": 0}
    clean["spell_slots"] = norm_slots

    # 10. Spellbook / Lista Incantesimi
    if not isinstance(clean.get("spellbook"), list):
        clean["spellbook"] = clean.get("spell_list", []) if isinstance(clean.get("spell_list"), list) else []

    # 11. Abilità & Competenze Tiri Salvezza
    if not isinstance(clean.get("skills"), dict):
        clean["skills"] = {}
    if not isinstance(clean.get("saving_throw_proficiencies"), list):
        clean["saving_throw_proficiencies"] = []

    # 12. Tratti, Condizioni e Risorse
    if not isinstance(clean.get("conditions"), list):
        clean["conditions"] = []

    raw_features = clean.get("features", "")
    raw_features_list = clean.get("features_list")
    if isinstance(raw_features_list, list) and len(raw_features_list) > 0:
        clean["features_list"] = raw_features_list
    elif isinstance(raw_features, list):
        clean["features_list"] = raw_features
    else:
        clean["features_list"] = []

    if isinstance(raw_features, str) and raw_features.strip():
        clean["features"] = raw_features
    elif isinstance(raw_features, list) and len(raw_features) > 0:
        clean["features"] = "\n\n".join(
            f"• {f.get('name', '')}: {f.get('desc', '')}".strip(": ") if isinstance(f, dict) else f"• {f}"
            for f in raw_features
        )
    elif len(clean["features_list"]) > 0:
        clean["features"] = "\n\n".join(
            f"• {f.get('name', '')}: {f.get('desc', '')}".strip(": ") if isinstance(f, dict) else f"• {f}"
            for f in clean["features_list"]
        )
    else:
        clean["features"] = ""

    insp = bool(clean.get("has_inspiration", clean.get("inspiration", False)))
    clean["inspiration"] = insp
    clean["has_inspiration"] = insp
    if not isinstance(clean.get("death_saves"), dict):
        clean["death_saves"] = {"successes": 0, "failures": 0}

    # 13. Multiclasse & Risorse Speciali 5e (Portento, Fortunato, Tenacia Implacabile)
    raw_classes = clean.get("classes")
    if isinstance(raw_classes, dict) and raw_classes:
        norm_classes = {}
        for c_name, c_lvl in raw_classes.items():
            if c_name:
                try:
                    norm_classes[str(c_name).strip()] = max(1, int(c_lvl))
                except (ValueError, TypeError):
                    pass
        if norm_classes:
            clean["classes"] = norm_classes
            total_c_lvl = sum(norm_classes.values())
            if total_c_lvl >= 1:
                clean["level"] = max(1, min(20, total_c_lvl))
                clean["proficiency_bonus"] = 2 + (clean["level"] - 1) // 4
    else:
        primary_cls = clean.get("char_class", "").split("/")[0].strip()
        if primary_cls:
            clean["classes"] = {primary_cls: clean["level"]}
        else:
            clean["classes"] = {}

    if not isinstance(clean.get("portent_dice"), list):
        clean["portent_dice"] = []
    try:
        clean["lucky_points"] = max(0, int(clean.get("lucky_points") or 0))
    except (ValueError, TypeError):
        clean["lucky_points"] = 0
    clean["relentless_endurance_used"] = bool(clean.get("relentless_endurance_used", False))

    return clean


# Tabella Slot Incantesimo Multiclasse (PHB p. 165)
MULTICLASS_SPELL_SLOTS_TABLE = {
    1:  {1: 2},
    2:  {1: 3},
    3:  {1: 4, 2: 2},
    4:  {1: 4, 2: 3},
    5:  {1: 4, 2: 3, 3: 2},
    6:  {1: 4, 2: 3, 3: 3},
    7:  {1: 4, 2: 3, 3: 3, 4: 1},
    8:  {1: 4, 2: 3, 3: 3, 4: 2},
    9:  {1: 4, 2: 3, 3: 3, 4: 3, 5: 1},
    10: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2},
    11: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    12: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1},
    13: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    14: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1},
    15: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    16: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1},
    17: {1: 4, 2: 3, 3: 3, 4: 3, 5: 2, 6: 1, 7: 1, 8: 1, 9: 1},
    18: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 1, 7: 1, 8: 1, 9: 1},
    19: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 1, 8: 1, 9: 1},
    20: {1: 4, 2: 3, 3: 3, 4: 3, 5: 3, 6: 2, 7: 2, 8: 1, 9: 1},
}


def check_class_multiclass_prereq(class_name: str, attrs: Dict[str, int]) -> bool:
    """Verifica i prerequisiti di caratteristica 5e RAW (PHB p. 163) per una singola classe."""
    c_low = str(class_name or "").strip().lower()
    str_v = int(attrs.get("FOR", attrs.get("STR", 10)))
    dex_v = int(attrs.get("DES", attrs.get("DEX", 10)))
    int_v = int(attrs.get("INT", 10))
    wis_v = int(attrs.get("SAG", attrs.get("WIS", 10)))
    cha_v = int(attrs.get("CAR", attrs.get("CHA", 10)))

    if any(k in c_low for k in ("barbaro", "barbarian")):
        return str_v >= 13
    if any(k in c_low for k in ("bardo", "bard", "stregone", "sorcerer", "warlock")):
        return cha_v >= 13
    if any(k in c_low for k in ("chierico", "cleric", "druido", "druid")):
        return wis_v >= 13
    if any(k in c_low for k in ("guerriero", "fighter")):
        return str_v >= 13 or dex_v >= 13
    if any(k in c_low for k in ("monaco", "monk", "ranger")):
        return dex_v >= 13 and wis_v >= 13
    if any(k in c_low for k in ("paladino", "paladin")):
        return str_v >= 13 and cha_v >= 13
    if any(k in c_low for k in ("ladro", "rogue")):
        return dex_v >= 13
    if any(k in c_low for k in ("mago", "wizard", "artefice", "artificer")):
        return int_v >= 13
    return True


def check_multiclass_prerequisites(character_or_dict: Any, target_class: str) -> tuple:
    """
    Verifica i prerequisiti di Multiclasse D&D 5e (PHB p. 163):
    Per qualificarsi in una nuova classe, il personaggio deve soddisfare i prerequisiti
    di punteggio di caratteristica sia per la classe attuale sia per la nuova classe.
    Ritorna: (ok: bool, messaggio: str)
    """
    if isinstance(character_or_dict, dict):
        attrs = character_or_dict.get("attributes", {})
        cur_classes = list((character_or_dict.get("classes") or {}).keys())
        if not cur_classes and character_or_dict.get("char_class"):
            cur_classes = [character_or_dict["char_class"]]
    else:
        attrs = getattr(character_or_dict, "attributes", {})
        cur_classes = list((getattr(character_or_dict, "classes", None) or {}).keys())
        if not cur_classes and getattr(character_or_dict, "char_class", ""):
            cur_classes = [getattr(character_or_dict, "char_class")]

    target_norm = str(target_class or "").strip()
    # Se sta salendo di livello in una classe che possiede già, non serve il controllo multiclasse
    if any(target_norm.lower() == str(c).strip().lower() for c in cur_classes):
        return True, "Avanzamento nella classe già posseduta."

    for existing_cls in cur_classes:
        if not check_class_multiclass_prereq(existing_cls, attrs):
            return False, f"Prerequisiti di caratteristica (min 13) non soddisfatti per la classe attuale '{existing_cls}' (PHB p. 163)."

    if not check_class_multiclass_prereq(target_norm, attrs):
        return False, f"Prerequisiti di caratteristica (min 13) non soddisfatti per la nuova classe '{target_norm}' (PHB p. 163)."

    return True, "Prerequisiti Multiclasse soddisfatti."


def calculate_multiclass_spell_slots(classes_dict: Dict[str, int], subclass_str: str = "") -> Dict[str, Dict[str, int]]:
    """
    Calcola gli slot incantesimo totali per un personaggio (singola classe o multiclasse)
    secondo le regole D&D 5e RAW (PHB p. 164-165), combinando Incantesimi e Magia del Patto.
    """
    eff_caster_level = 0
    warlock_level = 0
    sub_low = str(subclass_str or "").lower()

    for cls_name, lvl in (classes_dict or {}).items():
        c_low = str(cls_name).strip().lower()
        c_lvl = max(0, int(lvl or 0))
        if c_lvl <= 0:
            continue
        if any(k in c_low for k in ("bardo", "bard", "chierico", "cleric", "druido", "druid", "mago", "wizard", "stregone", "sorcerer")):
            eff_caster_level += c_lvl
        elif any(k in c_low for k in ("paladino", "paladin", "ranger")):
            # In singola classe Paladino/Ranger ottengono incantesimi dal liv. 2; in multiclasse contano metà per difetto
            if len(classes_dict) == 1 and c_lvl == 1:
                eff_caster_level += 0
            else:
                eff_caster_level += (c_lvl // 2)
        elif any(k in c_low for k in ("artefice", "artificer")):
            eff_caster_level += ((c_lvl + 1) // 2)
        elif any(k in c_low for k in ("guerriero", "fighter", "ladro", "rogue")):
            if any(k in sub_low for k in ("cavaliere mistico", "eldritch knight", "mistificatore arcano", "arcane trickster")):
                eff_caster_level += (c_lvl // 3)
        elif "warlock" in c_low:
            warlock_level += c_lvl

    eff_caster_level = min(20, eff_caster_level)
    base_slots = MULTICLASS_SPELL_SLOTS_TABLE.get(eff_caster_level, {})

    result = {}
    for s_lvl in range(1, 10):
        max_s = int(base_slots.get(s_lvl, 0))
        result[str(s_lvl)] = {"max": max_s, "current": max_s}

    # Magia del Patto (Warlock) si somma agli slot del livello del patto (max 5° livello)
    if warlock_level > 0:
        pact_slot_lvl = min(5, (warlock_level + 1) // 2)
        pact_count = 1 if warlock_level == 1 else (2 if warlock_level <= 10 else (3 if warlock_level <= 16 else 4))
        k_str = str(pact_slot_lvl)
        result[k_str]["max"] += pact_count
        result[k_str]["current"] += pact_count

    return result


