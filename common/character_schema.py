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

    return clean

