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
from typing import Dict, Any, Optional, Tuple, List

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
    if not isinstance(clean.get("subclasses"), dict):
        clean["subclasses"] = {}
    
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

    # 5b. PHB: Ladro Lv 15+ Mente Sfuggente (Slippery Mind -> Competenza TS SAG)
    #     e Barbaro Lv 20 Campione Primordiale (+4 FOR/+4 COS fino a 24, una tantum)
    _cls_map = clean.get("classes") if isinstance(clean.get("classes"), dict) else {}
    if not _cls_map and clean.get("char_class"):
        _cls_map = {str(clean.get("char_class")): int(clean.get("level", 1) or 1)}
    _rogue_lvl = sum(int(v or 0) for k, v in _cls_map.items() if "ladr" in str(k).lower() or "rogue" in str(k).lower())
    _barb_lvl = sum(int(v or 0) for k, v in _cls_map.items() if "barbar" in str(k).lower())
    if _rogue_lvl >= 15:
        _profs_upper = {str(p).upper() for p in clean["saving_throw_proficiencies"]}
        if "SAG" not in _profs_upper and "WIS" not in _profs_upper:
            clean["saving_throw_proficiencies"].append("SAG")
    if _barb_lvl >= 20 and not clean.get("primal_champion_applied"):
        clean["primal_champion_applied"] = True
        for _it_k, _en_k in (("FOR", "STR"), ("COS", "CON")):
            _cur_v = int(clean["attributes"].get(_it_k, clean["stats"].get(_en_k, 10)) or 10)
            _new_v = min(24, _cur_v + 4)
            clean["attributes"][_it_k] = _new_v
            clean["stats"][_en_k] = _new_v

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
    clean["arcane_recovery_used"] = bool(clean.get("arcane_recovery_used", False))

    # 14. Risorse e Privilegi di Classe Specifici 5e RAW
    # Forma Selvatica (Wild Shape - Druido PHB p. 66)
    ws = clean.get("wild_shape")
    if not isinstance(ws, dict):
        ws = {
            "active": False,
            "beast_name": "",
            "beast_hp": 0,
            "beast_max_hp": 0,
            "original_attributes": {},
            "original_ac": clean.get("ac", 10),
            "original_speed": clean.get("speed", 30)
        }
    else:
        ws.setdefault("active", False)
        ws.setdefault("beast_name", "")
        ws.setdefault("beast_hp", 0)
        ws.setdefault("beast_max_hp", 0)
        ws.setdefault("original_attributes", {})
        ws.setdefault("original_ac", clean.get("ac", 10))
        ws.setdefault("original_speed", clean.get("speed", 30))
    clean["wild_shape"] = ws

    # Punti Stregoneria (Fonte di Magia - Stregone PHB p. 101)
    cls_str_low = str(clean.get("char_class", "")).lower()
    sub_str_low = str(clean.get("subclass", "")).lower()
    classes_map = clean.get("classes", {})
    sorc_lvl = 0
    for c_k, c_v in classes_map.items():
        if any(k in str(c_k).lower() for k in ("stregone", "sorcerer")):
            sorc_lvl = max(sorc_lvl, int(c_v))
    if sorc_lvl == 0 and any(k in cls_str_low for k in ("stregone", "sorcerer")):
        sorc_lvl = clean["level"]

    if sorc_lvl >= 2:
        sp_max = max(sorc_lvl, int(clean.get("sorcery_points_max") or sorc_lvl))
        raw_sp_cur = clean.get("sorcery_points_current")
        raw_sp_max = clean.get("sorcery_points_max")
        if raw_sp_cur is None or (raw_sp_cur == 0 and (raw_sp_max is None or raw_sp_max == 0)):
            sp_cur = sp_max
        else:
            sp_cur = int(raw_sp_cur)
        clean["sorcery_points_max"] = sp_max
        clean["sorcery_points_current"] = max(0, min(sp_max, sp_cur))
    else:
        clean["sorcery_points_max"] = int(clean.get("sorcery_points_max") or 0)
        clean["sorcery_points_current"] = int(clean.get("sorcery_points_current") or 0)

    # Dadi di Superiorità (Maestro della Battaglia - Guerriero PHB p. 73)
    is_battlemaster = any(k in sub_str_low for k in ("maestro della battaglia", "battle master", "battlemaster"))
    if is_battlemaster:
        f_lvl = clean["level"]
        for c_k, c_v in classes_map.items():
            if any(k in str(c_k).lower() for k in ("guerriero", "fighter")):
                f_lvl = int(c_v)
        sup_max = 4 if f_lvl < 7 else (5 if f_lvl < 15 else 6)
        sup_die = "d8" if f_lvl < 10 else ("d10" if f_lvl < 18 else "d12")
        raw_sup_cur = clean.get("superiority_dice_current")
        raw_sup_max = clean.get("superiority_dice_max")
        if raw_sup_cur is None or (raw_sup_cur == 0 and (raw_sup_max is None or raw_sup_max == 0)):
            sup_cur = sup_max
        else:
            sup_cur = int(raw_sup_cur)
        clean["superiority_dice_max"] = sup_max
        clean["superiority_dice_current"] = max(0, min(sup_max, sup_cur))
        clean["superiority_die_type"] = sup_die
    else:
        clean["superiority_dice_max"] = int(clean.get("superiority_dice_max") or 0)
        clean["superiority_dice_current"] = int(clean.get("superiority_dice_current") or 0)
        clean["superiority_die_type"] = clean.get("superiority_die_type", "d8")

    # Punti Incantesimo Opzionali (Spell Points - DMG p. 288)
    from common.dnd5e_tables import calculate_spell_points_max
    sp_opt_max = calculate_spell_points_max(clean)
    if sp_opt_max > 0:
        raw_opt_cur = clean.get("spell_points_current")
        raw_opt_max = clean.get("spell_points_max")
        if raw_opt_cur is None or (raw_opt_cur == 0 and (raw_opt_max is None or raw_opt_max == 0)):
            opt_cur = sp_opt_max
        else:
            opt_cur = int(raw_opt_cur or 0)
        clean["spell_points_max"] = sp_opt_max
        clean["spell_points_current"] = max(0, min(sp_opt_max, opt_cur))
    else:
        clean["spell_points_max"] = int(clean.get("spell_points_max") or 0)
        clean["spell_points_current"] = int(clean.get("spell_points_current") or 0)

    if not isinstance(clean.get("feats"), list):
        clean["feats"] = []

    # 15. Slot Magia del Patto (Warlock) separati dagli slot Incantesimi (PHB p. 164)
    raw_pact = clean.get("pact_slots")
    calc_pact = calculate_pact_magic_slots(clean.get("classes", {}))
    if isinstance(raw_pact, dict) and (raw_pact.get("max", 0) or calc_pact["max"] == 0):
        p_max = max(0, int(raw_pact.get("max", 0) or 0))
        p_cur = max(0, min(p_max, int(raw_pact.get("current", p_max) if raw_pact.get("current") is not None else p_max)))
        p_lvl = max(0, min(5, int(raw_pact.get("level", calc_pact.get("level", 1) if p_max > 0 else 0) or 0)))
        if calc_pact["max"] > p_max:
            p_max = calc_pact["max"]
            p_lvl = calc_pact["level"]
            p_cur = min(p_max, max(0, p_cur))
        clean["pact_slots"] = {"max": p_max, "current": p_cur, "level": p_lvl}
    else:
        clean["pact_slots"] = dict(calc_pact)

    # 16. Competenze Armature, Armi e Strumenti derivate (PHB p. 164 Multiclasse & Razze/Sottoclassi)
    computed_profs = compute_character_proficiencies(clean)
    for pk, sk in (("armor", "armor_proficiencies"), ("weapons", "weapon_proficiencies"), ("tools", "tool_proficiencies")):
        existing_list = clean.get(sk)
        if not isinstance(existing_list, list):
            existing_list = []
        merged = list(dict.fromkeys([str(x) for x in existing_list if x] + computed_profs[pk]))
        clean[sk] = merged

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


def filter_non_stacking_multiclass_features(character_or_dict: Any, new_features: List[str]) -> Tuple[List[str], List[str]]:
    """
    PHB p. 164 Regole Multiclasse di non-cumulabilità:
    - Attacco Extra (base): non si somma tra due classi diverse (solo Guerriero 11/20 sblocca 3°/4° attacco).
    - Difesa Senza Armatura: se già posseduta (Barbaro o Monaco), una seconda fonte non sostituisce la prima.
    - Incanalare Divinità: non aggiunge usi extra rispetto al massimo singolo (nota informativa).
    Ritorna: (filtered_features, skipped_notes)
    """
    is_d = isinstance(character_or_dict, dict)
    raw_txt = (character_or_dict.get("features", "") if is_d else getattr(character_or_dict, "features", "")) or ""
    flist = (character_or_dict.get("features_list", []) if is_d else getattr(character_or_dict, "features_list", [])) or []
    blob = (str(raw_txt) + " " + " ".join(str(x.get("name", "")) for x in flist if isinstance(x, dict))).lower()

    has_extra_attack = ("attacco extra" in blob or "extra attack" in blob)
    has_unarmored = ("difesa senza armatura" in blob or "unarmored defense" in blob)

    kept: List[str] = []
    notes: List[str] = []
    for fname in (new_features or []):
        f_low = str(fname or "").lower()
        is_upgraded_fighter_ea = any(k in f_low for k in ("(2)", "(3)", "2 attacchi extra", "3 attacchi extra", "three attacks", "four attacks"))
        if ("attacco extra" in f_low or "extra attack" in f_low) and has_extra_attack and not is_upgraded_fighter_ea:
            notes.append(f"{fname} (Già posseduto da altra classe — non si somma, PHB p. 164)")
            continue
        if ("difesa senza armatura" in f_low or "unarmored defense" in f_low) and has_unarmored:
            notes.append(f"{fname} (Già posseduta — non cumulabile in multiclasse, PHB p. 164)")
            continue
        kept.append(fname)
    return kept, notes


def calculate_pact_magic_slots(classes_dict: Dict[str, int]) -> Dict[str, int]:
    """Calcola separatamente gli slot di Magia del Patto del Warlock (ricarica a Riposo Breve, PHB p. 106/164)."""
    warlock_level = 0
    for cls_name, lvl in (classes_dict or {}).items():
        if "warlock" in str(cls_name or "").strip().lower():
            warlock_level += max(0, int(lvl or 0))
    if warlock_level <= 0:
        return {"max": 0, "current": 0, "level": 0}
    pact_slot_lvl = min(5, (warlock_level + 1) // 2)
    pact_count = 1 if warlock_level == 1 else (2 if warlock_level <= 10 else (3 if warlock_level <= 16 else 4))
    return {"max": pact_count, "current": pact_count, "level": pact_slot_lvl}


def calculate_multiclass_spell_slots(classes_dict: Dict[str, int], subclass_str: str = "", include_pact: bool = False) -> Dict[str, Dict[str, int]]:
    """
    Calcola gli slot incantesimo tradizionali (Incantesimi / Riposo Lungo) per un personaggio
    secondo le regole D&D 5e RAW (PHB p. 164-165), mantenendo separata la Magia del Patto Warlock.
    """
    eff_caster_level = 0
    sub_low = str(subclass_str or "").lower()

    for cls_name, lvl in (classes_dict or {}).items():
        c_low = str(cls_name).strip().lower()
        c_lvl = max(0, int(lvl or 0))
        if c_lvl <= 0 or "warlock" in c_low:
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

    eff_caster_level = min(20, eff_caster_level)
    base_slots = MULTICLASS_SPELL_SLOTS_TABLE.get(eff_caster_level, {})

    result = {}
    for s_lvl in range(1, 10):
        max_s = int(base_slots.get(s_lvl, 0))
        result[str(s_lvl)] = {"max": max_s, "current": max_s}

    if include_pact:
        pact = calculate_pact_magic_slots(classes_dict)
        if pact["max"] > 0 and str(pact["level"]) in result:
            result[str(pact["level"])]["max"] += pact["max"]
            result[str(pact["level"])]["current"] += pact["max"]

    return result


# Tabella Competenze Iniziali vs Multiclasse (PHB p. 45-119, p. 164)
_CLASS_START_PROFS = {
    "barbar": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "bard": {"armor": ["light"], "weapons": ["simple", "hand crossbow", "longsword", "rapier", "shortsword"], "tools": ["Strumento Musicale"]},
    "chieric": {"armor": ["light", "medium", "shields"], "weapons": ["simple"], "tools": []},
    "cleric": {"armor": ["light", "medium", "shields"], "weapons": ["simple"], "tools": []},
    "druid": {"armor": ["light", "medium", "shields"], "weapons": ["club", "dagger", "dart", "javelin", "mace", "quarterstaff", "scimitar", "sickle", "sling", "spear"], "tools": ["Borsa da Erborista"]},
    "guerrier": {"armor": ["light", "medium", "heavy", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "fighter": {"armor": ["light", "medium", "heavy", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "monac": {"armor": [], "weapons": ["simple", "shortsword"], "tools": ["Strumento Artigiano o Musicale"]},
    "monk": {"armor": [], "weapons": ["simple", "shortsword"], "tools": ["Strumento Artigiano o Musicale"]},
    "paladin": {"armor": ["light", "medium", "heavy", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "ranger": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "ladr": {"armor": ["light"], "weapons": ["simple", "hand crossbow", "longsword", "rapier", "shortsword"], "tools": ["Arnesi da Scasso"]},
    "rogue": {"armor": ["light"], "weapons": ["simple", "hand crossbow", "longsword", "rapier", "shortsword"], "tools": ["Arnesi da Scasso"]},
    "stregon": {"armor": [], "weapons": ["dagger", "dart", "sling", "quarterstaff", "light crossbow"], "tools": []},
    "sorcerer": {"armor": [], "weapons": ["dagger", "dart", "sling", "quarterstaff", "light crossbow"], "tools": []},
    "warlock": {"armor": ["light"], "weapons": ["simple"], "tools": []},
    "mag": {"armor": [], "weapons": ["dagger", "dart", "sling", "quarterstaff", "light crossbow"], "tools": []},
    "wizard": {"armor": [], "weapons": ["dagger", "dart", "sling", "quarterstaff", "light crossbow"], "tools": []},
    "artef": {"armor": ["light", "medium", "shields"], "weapons": ["simple"], "tools": ["Arnesi da Scasso", "Arnesi da Inventore"]},
    "artificer": {"armor": ["light", "medium", "shields"], "weapons": ["simple"], "tools": ["Arnesi da Scasso", "Arnesi da Inventore"]},
}

_CLASS_MULTICLASS_PROFS = {
    "barbar": {"armor": ["shields"], "weapons": ["simple", "martial"], "tools": []},
    "bard": {"armor": ["light"], "weapons": [], "tools": ["Strumento Musicale"]},
    "chieric": {"armor": ["light", "medium", "shields"], "weapons": [], "tools": []},
    "cleric": {"armor": ["light", "medium", "shields"], "weapons": [], "tools": []},
    "druid": {"armor": ["light", "medium", "shields"], "weapons": [], "tools": []},
    "guerrier": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "fighter": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "monac": {"armor": [], "weapons": ["simple", "shortsword"], "tools": []},
    "monk": {"armor": [], "weapons": ["simple", "shortsword"], "tools": []},
    "paladin": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "ranger": {"armor": ["light", "medium", "shields"], "weapons": ["simple", "martial"], "tools": []},
    "ladr": {"armor": ["light"], "weapons": [], "tools": ["Arnesi da Scasso"]},
    "rogue": {"armor": ["light"], "weapons": [], "tools": ["Arnesi da Scasso"]},
    "warlock": {"armor": ["light"], "weapons": ["simple"], "tools": []},
    "artef": {"armor": ["light", "medium", "shields"], "weapons": [], "tools": ["Arnesi da Scasso"]},
    "artificer": {"armor": ["light", "medium", "shields"], "weapons": [], "tools": ["Arnesi da Scasso"]},
}


def compute_character_proficiencies(char_or_dict: Any) -> Dict[str, list]:
    """Calcola competenze in armature, armi e strumenti (Classe iniziale, Multiclasse PHB p.164, Sottoclasse, Razza, Talenti)."""
    def _g(k, default=None):
        if isinstance(char_or_dict, dict):
            return char_or_dict.get(k, default)
        return getattr(char_or_dict, k, default)

    armor = set()
    weapons = set()
    tools = []

    classes = _g("classes", {})
    if not isinstance(classes, dict) or not classes:
        cls_primary = str(_g("char_class", "") or "").split("/")[0].strip()
        classes = {cls_primary: int(_g("level", 1) or 1)} if cls_primary else {}

    for idx, cls_name in enumerate(classes.keys()):
        c_low = str(cls_name or "").lower()
        table = _CLASS_START_PROFS if idx == 0 else _CLASS_MULTICLASS_PROFS
        for key, profs in table.items():
            if key in c_low:
                armor.update(profs["armor"])
                weapons.update(profs["weapons"])
                for tl in profs["tools"]:
                    if tl not in tools:
                        tools.append(tl)
                break

    sub_low = str(_g("subclass", "") or "").lower()
    if any(k in sub_low for k in ("vita", "life", "tempesta", "tempest", "guerra", "war", "natura", "nature", "forgia", "forge", "ordine", "order")):
        armor.update(["light", "medium", "heavy"])
        if any(k in sub_low for k in ("tempesta", "tempest", "guerra", "war")):
            weapons.add("martial")
    if any(k in sub_low for k in ("valore", "valor", "lama", "swords", "hexblade", "lama maledetta")):
        armor.update(["medium", "shields"])
        weapons.add("martial")
    if any(k in sub_low for k in ("cantore della lama", "bladesing")):
        armor.add("light")

    race_low = str(_g("race", "") or "").lower()
    subrace_low = str(_g("subrace", "") or "").lower()
    if "nano" in race_low or "dwarf" in race_low:
        weapons.update(["battleaxe", "handaxe", "light hammer", "warhammer"])
        if "montagn" in race_low or "mountain" in race_low or "montagn" in subrace_low or "mountain" in subrace_low:
            armor.update(["light", "medium"])
    if "elf" in race_low or "drow" in race_low:
        if "drow" in race_low or "drow" in subrace_low or "oscuro" in subrace_low:
            weapons.update(["rapier", "shortsword", "hand crossbow"])
        else:
            weapons.update(["longsword", "shortsword", "shortbow", "longbow"])
    if "hobgoblin" in race_low:
        armor.add("light")

    feats = _g("feats", []) or []
    feat_txt = " ".join(str(f.get("name", f) if isinstance(f, dict) else f).lower() for f in feats)
    feat_txt += " " + str(_g("features", "") or "").lower()
    if "lightly armored" in feat_txt or "armature leggere" in feat_txt:
        armor.add("light")
    if "moderately armored" in feat_txt or "armature medie" in feat_txt:
        armor.update(["medium", "shields"])
    if "heavily armored" in feat_txt or "armature pesanti" in feat_txt:
        armor.add("heavy")
    if "weapon master" in feat_txt or "maestro d'armi" in feat_txt:
        weapons.add("martial")

    return {"armor": sorted(armor), "weapons": sorted(weapons), "tools": tools}


def consume_spell_or_pact_slot(sheet_or_char: Any, min_level: int, prefer_pact: bool = True) -> Tuple[bool, str]:
    """Consuma uno slot Incantesimo o Magia del Patto di livello >= min_level (PHB p. 164)."""
    lvl_req = max(1, min(9, int(min_level or 1)))
    is_dict = isinstance(sheet_or_char, dict)
    pact = sheet_or_char.get("pact_slots") if is_dict else getattr(sheet_or_char, "pact_slots", None)
    slots = sheet_or_char.get("spell_slots") if is_dict else getattr(sheet_or_char, "spell_slots", None)

    def _try_pact():
        if isinstance(pact, dict) and pact.get("current", 0) > 0 and pact.get("level", 0) >= lvl_req:
            pact["current"] -= 1
            return True, f"Slot Patto Warlock (Lv {pact['level']}°, rimasti {pact['current']}/{pact['max']})"
        return False, ""

    def _try_standard():
        if isinstance(slots, dict):
            for s_lvl in range(lvl_req, 10):
                s_info = slots.get(str(s_lvl))
                if isinstance(s_info, dict) and s_info.get("current", 0) > 0:
                    s_info["current"] -= 1
                    return True, f"Slot Incantesimo {s_lvl}° livello (rimasti {s_info['current']}/{s_info.get('max', 0)})"
                elif isinstance(s_info, list) and len(s_info) >= 2 and s_info[0] > 0:
                    s_info[0] -= 1
                    return True, f"Slot Incantesimo {s_lvl}° livello (rimasti {s_info[0]}/{s_info[1]})"
        return False, ""

    if prefer_pact:
        ok, msg = _try_pact()
        if ok:
            return True, msg
        return _try_standard()
    else:
        ok, msg = _try_standard()
        if ok:
            return True, msg
        return _try_pact()


