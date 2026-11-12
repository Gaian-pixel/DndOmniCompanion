"""
common/dnd5e_tables.py - Dati canonici D&D 5e (PHB, DMG, MM) e utility condivise.

Contiene:
- Rilevamento centralizzato di privilegi, talenti, tratti di mostro e livelli di classe
- Calcolatori PHB (Salto, Soffocamento/Apnea, Destrezza subacquea, Talenti)
- Regole e tabelle DMG (Varianti Riposo, Punti Incantesimo, Shock Sistemico / Danno Massiccio,
  Ferite Permanenti, Follia Breve/Lunga/Indefinita, Veleni, Malattie, CA/PF/Soglia Oggetti,
  Complicazioni Inseguimento)
"""

import random
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# RILEVAMENTO CENTRALIZZATO PRIVILEGI, TALENTI, TRATTI E CLASSI
# ==============================================================================

def _extract_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    val = getattr(obj, key, None)
    if val is not None:
        return val
    fs = getattr(obj, "full_sheet", None)
    if isinstance(fs, dict):
        return fs.get(key, default)
    return default


def get_entity_text_blobs(entity: Any) -> Dict[str, str]:
    """Estrae stringhe lowercase normalizzate per class, subclass, race, type, features, feats, traits, conditions."""
    if entity is None:
        return {
            "class": "", "subclass": "", "race": "", "type": "",
            "features": "", "feats": "", "traits": "", "conditions": "", "all": ""
        }

    def _flatten(val: Any) -> str:
        if not val:
            return ""
        if isinstance(val, str):
            return val
        if isinstance(val, dict):
            return f"{val.get('name', '')} {val.get('desc', '')} {val.get('title', '')}"
        if isinstance(val, (list, tuple, set)):
            parts = []
            for item in val:
                if isinstance(item, dict):
                    parts.append(f"{item.get('name', '')} {item.get('desc', '')} {item.get('title', '')}")
                else:
                    parts.append(str(item))
            return " ".join(parts)
        return str(val)

    fs = entity if isinstance(entity, dict) else (getattr(entity, "full_sheet", None) or {})
    if not isinstance(fs, dict):
        fs = {}

    cls_s = str(_extract_attr_or_key(entity, "char_class", "") or fs.get("char_class", "") or fs.get("class_name", "")).lower()
    sub_s = str(_extract_attr_or_key(entity, "subclass", "") or fs.get("subclass", "")).lower()
    race_s = str(_extract_attr_or_key(entity, "race", "") or fs.get("race", "")).lower()
    type_s = str(_extract_attr_or_key(entity, "type", "") or fs.get("type", "") or fs.get("creature_type", "")).lower()

    feat_parts = [
        _flatten(_extract_attr_or_key(entity, "features", "")),
        _flatten(_extract_attr_or_key(entity, "features_list", "")),
        _flatten(fs.get("features", "")),
        _flatten(fs.get("features_list", "")),
    ]
    feats_list_parts = [
        _flatten(_extract_attr_or_key(entity, "feats", "")),
        _flatten(fs.get("feats", "")),
    ]
    traits_parts = [
        _flatten(_extract_attr_or_key(entity, "traits", "")),
        _flatten(_extract_attr_or_key(entity, "special_abilities", "")),
        _flatten(fs.get("traits", "")),
        _flatten(fs.get("special_abilities", "")),
    ]
    cond_parts = [
        _flatten(_extract_attr_or_key(entity, "conditions", "")),
        _flatten(fs.get("conditions", "")),
        _flatten(_extract_attr_or_key(entity, "active_effects", "")),
        _flatten(fs.get("active_effects", "")),
    ]

    f_str = " ".join(p for p in feat_parts if p).lower()
    feats_str = " ".join(p for p in feats_list_parts if p).lower()
    tr_str = " ".join(p for p in traits_parts if p).lower()
    cd_str = " ".join(p for p in cond_parts if p).lower()
    all_str = " ".join(x for x in (cls_s, sub_s, race_s, type_s, f_str, feats_str, tr_str, cd_str) if x)

    return {
        "class": cls_s,
        "subclass": sub_s,
        "race": race_s,
        "type": type_s,
        "features": f_str,
        "feats": feats_str,
        "traits": tr_str,
        "conditions": cd_str,
        "all": all_str,
    }


def entity_has_keyword(entity: Any, *keywords: str) -> bool:
    """Ritorna True se almeno una keyword compare nei privilegi, talenti, tratti, razza o sottoclasse dell'entità."""
    if not entity or not keywords:
        return False
    blobs = get_entity_text_blobs(entity)
    haystack = blobs["all"]
    return any(str(k).lower() in haystack for k in keywords if k)


def entity_get_class_level(entity: Any, *class_aliases: str) -> int:
    """Restituisce il livello nella classe specificata (supportando multiclasse e alias IT/EN)."""
    if not entity or not class_aliases:
        return 0
    aliases = tuple(str(a).lower() for a in class_aliases)
    fs = entity if isinstance(entity, dict) else (getattr(entity, "full_sheet", None) or {})
    classes = _extract_attr_or_key(entity, "classes", None)
    if not isinstance(classes, dict) and isinstance(fs, dict):
        classes = fs.get("classes")
    if isinstance(classes, dict) and classes:
        best = 0
        for cname, clvl in classes.items():
            c_low = str(cname).lower()
            if any(a in c_low for a in aliases):
                try:
                    best = max(best, int(clvl or 0))
                except (ValueError, TypeError):
                    pass
        if best > 0:
            return best

    cls_s = str(
        _extract_attr_or_key(entity, "char_class", "")
        or (fs.get("char_class", "") if isinstance(fs, dict) else "")
        or _extract_attr_or_key(entity, "class", "")
        or (fs.get("class", "") if isinstance(fs, dict) else "")
    ).lower()
    if any(a in cls_s for a in aliases):
        lvl_raw = _extract_attr_or_key(entity, "level", None)
        if lvl_raw is None and isinstance(fs, dict):
            lvl_raw = fs.get("level", 1)
        try:
            return max(1, int(lvl_raw or 1))
        except (ValueError, TypeError):
            return 1
    return 0


def entity_get_total_level(entity: Any) -> int:
    """Restituisce il livello totale dell'entità (sommando le multiclasse o fallback su level)."""
    if not entity:
        return 1
    fs = entity if isinstance(entity, dict) else (getattr(entity, "full_sheet", None) or {})
    classes = _extract_attr_or_key(entity, "classes", None)
    if not isinstance(classes, dict) and isinstance(fs, dict):
        classes = fs.get("classes")
    if isinstance(classes, dict) and classes:
        tot = 0
        for v in classes.values():
            try:
                tot += max(0, int(v or 0))
            except (ValueError, TypeError):
                pass
        if tot > 0:
            return min(20, tot)
    try:
        lvl = int(_extract_attr_or_key(entity, "level", None) or (fs.get("level", 1) if isinstance(fs, dict) else 1) or 1)
        return max(1, lvl)
    except (ValueError, TypeError):
        return 1


def entity_get_effective_attr(entity: Any, stat_it: str) -> int:
    """Restituisce il punteggio di caratteristica effettivo da Character/Player/dict."""
    from common.item_modifiers import get_effective_attribute_from_dict
    return get_effective_attribute_from_dict(entity, stat_it)


def entity_get_attr_mod(entity: Any, stat_it: str) -> int:
    """Restituisce il modificatore di caratteristica effettivo floor((score - 10)/2)."""
    return (entity_get_effective_attr(entity, stat_it) - 10) // 2


def entity_find_resource(entity: Any, *keywords: str) -> Optional[Dict[str, Any]]:
    """Trova la prima risorsa in custom_resources il cui nome contiene una delle keyword."""
    if not entity or not keywords:
        return None
    kws = tuple(str(k).lower() for k in keywords)
    for source in (entity, getattr(entity, "full_sheet", None) if not isinstance(entity, dict) else None):
        if source is None:
            continue
        res_list = source.get("custom_resources") if isinstance(source, dict) else getattr(source, "custom_resources", None)
        if isinstance(res_list, list):
            for r in res_list:
                if isinstance(r, dict):
                    rname = str(r.get("name", "")).lower()
                    if any(k in rname for k in kws):
                        return r
    return None


def entity_spend_resource(entity: Any, keywords: Tuple[str, ...], amount: int = 1) -> Tuple[bool, int, int]:
    """
    Consuma `amount` unità da una risorsa trovata per keyword sia su `entity` sia su `entity.full_sheet`.
    Ritorna (ok, nuovo_current, max_val).
    """
    r_main = entity_find_resource(entity, *keywords)
    if r_main is None:
        return False, 0, 0
    cur = int(r_main.get("current", 0) or 0)
    mx = int(r_main.get("max", cur) or 0)
    if cur < amount:
        return False, cur, mx
    new_cur = max(0, cur - amount)
    r_main["current"] = new_cur

    # Sincronizza anche eventuale replica dentro full_sheet
    if not isinstance(entity, dict) and isinstance(getattr(entity, "full_sheet", None), dict):
        fs_res = entity.full_sheet.get("custom_resources")
        if isinstance(fs_res, list):
            target_name = str(r_main.get("name", "")).lower()
            for r in fs_res:
                if isinstance(r, dict) and str(r.get("name", "")).lower() == target_name:
                    r["current"] = new_cur
    return True, new_cur, mx


# ==============================================================================
# CALCOLATORI PHB (SALTO, APNEA/SOFFOCAMENTO, TALENTI)
# ==============================================================================

PHB_FEATS_CATALOG: Dict[str, Dict[str, str]] = {
    "Sentinella (Sentinel)": {
        "aliases": "sentinella sentinel",
        "desc": "I tuoi Attacchi d'Opportunità riducono a 0 m la velocità del bersaglio per il resto del turno; ignora l'azione Disimpegno."
    },
    "Maestro d'Armi Astate (Polearm Master)": {
        "aliases": "maestro d'armi astate polearm master",
        "desc": "Azione Bonus 1d4 contundente con l'estremità opposta di falcione/alabarda/bastone; provoca AdO quando un nemico entra nella tua portata."
    },
    "Incantatore da Guerra (War Caster)": {
        "aliases": "incantatore da guerra war caster",
        "desc": "Vantaggio ai Tiri Salvezza su Costituzione per mantenere la Concentrazione; lanci incantesimi come AdO."
    },
    "Robusto (Tough)": {
        "aliases": "robusto tough",
        "desc": "I tuoi Punti Ferita Massimi aumentano di +2 per ogni livello raggiunto."
    },
    "Allerta (Alert)": {
        "aliases": "allerta alert",
        "desc": "+5 all'Iniziativa; non puoi essere Sorpreso finché sei cosciente; creature nascoste non hanno vantaggio contro di te."
    },
    "Resiliente (Resilient)": {
        "aliases": "resiliente resilient",
        "desc": "+1 a una caratteristica scelta e competenza nei suoi Tiri Salvezza."
    },
    "Adepto Elementale (Elemental Adept)": {
        "aliases": "adepto elementale elemental adept",
        "desc": "I tuoi incantesimi di un elemento scelto (Fuoco/Freddo/Fulmine/Acido/Tuono) ignorano la Resistenza e trattano gli 1 sui dadi danno come 2."
    },
    "Esperto di Balestre (Crossbow Expert)": {
        "aliases": "esperto di balestre crossbow expert",
        "desc": "Ignori la proprietà Ricarica; nessuna penalità di svantaggio a 1,5 m (5 ft) da nemici con attacchi a distanza; attacco bonus con balestra a mano."
    },
    "Cecchino Magico (Spell Sniper)": {
        "aliases": "cecchino magico spell sniper",
        "desc": "Portata doppia per incantesimi con tiro per colpire; ignora Mezza e Tre Quarti Copertura; nessun svantaggio a 1,5 m da nemici con incantesimi."
    },
    "Guaritore (Healer)": {
        "aliases": "guaritore healer",
        "desc": "Con un Kit da Guaritore puoi curare 1d6 + 4 + livello PF (1 volta per riposo breve/lungo per creatura)."
    },
    "Condottiero Ispiratore (Inspiring Leader)": {
        "aliases": "condottiero ispiratore inspiring leader",
        "desc": "Con un discorso di 10 minuti conferisci PF Temporanei pari a Livello + mod CAR fino a 6 alleati (1/riposo breve/lungo)."
    },
    "Fortunato (Lucky)": {
        "aliases": "fortunato lucky",
        "desc": "3 Punti Fortuna per riposo lungo per aggiungere/ritirare un d20."
    },
}


def calculate_jump_distances(str_score: int, running_start: bool = True) -> Dict[str, Any]:
    """Calcola Salto in Lungo e Salto in Alto secondo PHB p. 182."""
    try:
        score = max(1, int(str_score or 10))
    except (ValueError, TypeError):
        score = 10
    mod = (score - 10) // 2
    factor = 1.0 if running_start else 0.5
    long_ft = round(score * factor, 1)
    high_ft = round(max(0.0, (3 + mod) * factor), 1)
    long_m = round(long_ft * 0.3, 1)
    high_m = round(high_ft * 0.3, 1)
    return {
        "str_score": score,
        "str_mod": mod,
        "running_start": bool(running_start),
        "long_jump_ft": long_ft,
        "long_jump_m": long_m,
        "high_jump_ft": high_ft,
        "high_jump_m": high_m,
        "reach_up_ft": round(high_ft * 1.5, 1),  # approx with arms
    }


def get_breath_hold_rounds(con_mod: int) -> int:
    """
    PHB p. 183: Una creatura può trattenere il respiro per 1 + mod COS minuti (1 minuto = 10 round),
    con un minimo di 30 secondi (5 round).
    """
    minutes = 1 + int(con_mod or 0)
    if minutes < 1:
        return 5  # 30 secondi
    return minutes * 10


def get_suffocation_rounds(con_mod: int) -> int:
    """PHB p. 183: Dopo aver esaurito il respiro sopravvive per un numero di round pari a mod COS (minimo 1)."""
    return max(1, int(con_mod or 0))


# ==============================================================================
# PUNTI INCANTESIMO (DMG p. 288-289) & VARIANTI DI RIPOSO (DMG p. 267)
# ==============================================================================

SPELL_POINTS_BY_LEVEL: Dict[int, int] = {
    1: 4, 2: 6, 3: 14, 4: 17, 5: 27,
    6: 32, 7: 38, 8: 44, 9: 57, 10: 64,
    11: 73, 12: 73, 13: 83, 14: 83, 15: 94,
    16: 94, 17: 107, 18: 114, 19: 123, 20: 133,
}

SPELL_POINT_COST: Dict[int, int] = {
    1: 2, 2: 3, 3: 5, 4: 6, 5: 7, 6: 9, 7: 10, 8: 11, 9: 13
}

REST_VARIANTS: Dict[str, Dict[str, Any]] = {
    "standard": {
        "label": "Standard (1h Breve / 8h Lungo)",
        "short_hours": 1.0,
        "long_hours": 8.0,
    },
    "epic_heroism": {
        "label": "Eroismo Epico DMG p.267 (5 min Breve / 1h Lungo)",
        "short_hours": 5.0 / 60.0,
        "long_hours": 1.0,
    },
    "gritty_realism": {
        "label": "Realismo Crudo DMG p.267 (8h Breve / 7 giorni Lungo)",
        "short_hours": 8.0,
        "long_hours": 168.0,
    },
}


def calculate_spell_points_max(character_or_dict: Any) -> int:
    """Calcola il totale massimo di Spell Points (DMG p. 288) escludendo la Magia del Patto."""
    fs = character_or_dict if isinstance(character_or_dict, dict) else (getattr(character_or_dict, "full_sheet", None) or {})
    classes = _extract_attr_or_key(character_or_dict, "classes", None)
    if not isinstance(classes, dict) and isinstance(fs, dict):
        classes = fs.get("classes")
    if not isinstance(classes, dict) or not classes:
        c_name = str(_extract_attr_or_key(character_or_dict, "char_class", "") or "").strip()
        lvl = entity_get_total_level(character_or_dict)
        classes = {c_name: lvl} if c_name else {}

    sub_low = str(_extract_attr_or_key(character_or_dict, "subclass", "") or "").lower()
    eff_lvl = 0
    for cname, clvl in classes.items():
        c_low = str(cname).lower()
        l_val = max(0, int(clvl or 0))
        if l_val <= 0:
            continue
        if any(k in c_low for k in ("bardo", "bard", "chierico", "cleric", "druido", "druid", "mago", "wizard", "stregone", "sorcerer")):
            eff_lvl += l_val
        elif any(k in c_low for k in ("paladino", "paladin", "ranger")):
            if len(classes) == 1 and l_val == 1:
                eff_lvl += 0
            else:
                eff_lvl += (l_val // 2)
        elif any(k in c_low for k in ("artefice", "artificer")):
            eff_lvl += ((l_val + 1) // 2)
        elif any(k in c_low for k in ("guerriero", "fighter", "ladro", "rogue")):
            if any(k in sub_low for k in ("cavaliere mistico", "eldritch knight", "mistificatore arcano", "arcane trickster")):
                eff_lvl += (l_val // 3)
    eff_lvl = min(20, eff_lvl)
    return int(SPELL_POINTS_BY_LEVEL.get(eff_lvl, 0))


# ==============================================================================
# TABELLE OPZIONALI DMG (DANNO MASSICCIO, FERITE PERMANENTI, FOLLIA, VELENI, MALATTIE, OGGETTI, INSEGUIMENTI)
# ==============================================================================

SYSTEM_SHOCK_TABLE: Dict[int, Dict[str, str]] = {
    1:  {"effect": "Crolla a 0 PF", "condition": "Incosciente", "desc": "La creatura crolla a 0 Punti Ferita."},
    2:  {"effect": "Crolla a 0 PF (Stabile)", "condition": "Incosciente", "desc": "Crolla a 0 PF ma è stabile."},
    3:  {"effect": "Crolla a 0 PF (Stabile)", "condition": "Incosciente", "desc": "Crolla a 0 PF ma è stabile."},
    4:  {"effect": "Stordito (1 turno)", "condition": "Stordito", "desc": "È Stordito fino alla fine del proprio prossimo turno."},
    5:  {"effect": "Stordito (1 turno)", "condition": "Stordito", "desc": "È Stordito fino alla fine del proprio prossimo turno."},
    6:  {"effect": "Nessuna Reazione + Svantaggio", "condition": "Shock Sistemico", "desc": "Non può usare reazioni e subisce Svantaggio a tiri per colpire e prove di caratteristica fino alla fine del proprio prossimo turno."},
    7:  {"effect": "Nessuna Reazione + Svantaggio", "condition": "Shock Sistemico", "desc": "Non può usare reazioni e subisce Svantaggio a tiri per colpire e prove di caratteristica fino alla fine del proprio prossimo turno."},
    8:  {"effect": "Nessuna Reazione", "condition": "Shock Lieve", "desc": "Non può effettuare reazioni fino alla fine del proprio prossimo turno."},
    9:  {"effect": "Nessuna Reazione", "condition": "Shock Lieve", "desc": "Non può effettuare reazioni fino alla fine del proprio prossimo turno."},
    10: {"effect": "Nessuna Reazione", "condition": "Shock Lieve", "desc": "Non può effettuare reazioni fino alla fine del proprio prossimo turno."},
}


def roll_system_shock(roll_val: Optional[int] = None) -> Dict[str, Any]:
    r = int(roll_val) if roll_val is not None else random.randint(1, 10)
    r = max(1, min(10, r))
    entry = dict(SYSTEM_SHOCK_TABLE[r])
    entry["roll"] = r
    return entry


LINGERING_INJURIES_TABLE: List[Tuple[int, int, str, str]] = [
    (1, 1, "Perdita di un Occhio", "Svantaggio alle prove di Percezione basate sulla vista e agli attacchi a distanza."),
    (2, 2, "Perdita di un Braccio o Mano", "Non puoi impugnare oggetti a due mani né usare un secondo oggetto."),
    (3, 3, "Perdita di un Piede o Gamba", "Velocità dimezzata; cadi Prono dopo l'azione Scatto se fallisci TS DES CD 10."),
    (4, 4, "Zoppia Grave", "Velocità ridotta di 1,5 m (5 ft); cadi Prono dopo Scatto senza bastone/stampella."),
    (5, 7, "Ferita Interna", "Quando compi un'azione, supera TS COS CD 15 o perdi l'azione e subisci 1d6 danni."),
    (8, 10, "Costole Rotte", "Come Ferita Interna, ma CD 10 su Costituzione."),
    (11, 13, "Cicatrice Orribile", "Svantaggio a Persuasione, Vantaggio a Intimidire."),
    (14, 16, "Ferita Infetta", "I tuoi Punti Ferita massimi calano di 1 ogni 24 ore finché la ferita non viene curata."),
    (17, 20, "Cicatrice Minore", "Nessun effetto meccanico negativo."),
]


def roll_lingering_injury(roll_val: Optional[int] = None) -> Dict[str, Any]:
    r = int(roll_val) if roll_val is not None else random.randint(1, 20)
    r = max(1, min(20, r))
    for lo, hi, name, desc in LINGERING_INJURIES_TABLE:
        if lo <= r <= hi:
            return {"roll": r, "name": name, "desc": desc}
    return {"roll": r, "name": "Cicatrice Minore", "desc": "Nessun effetto meccanico."}


SHORT_TERM_MADNESS: List[Tuple[int, int, str]] = [
    (1, 20, "La creatura si ritira in se stessa ed è Paralizzata per la durata (1d10 minuti)."),
    (21, 30, "La creatura diventa Incapacitata e trascorre il tempo ridendo, piangendo o urlando."),
    (31, 40, "Spaventata: deve usare ogni azione per fuggire dalla fonte della paura."),
    (41, 50, "Balbettio incontrollabile: incapace di parlare o lanciare incantesimi verbali."),
    (51, 60, "Deve usare la propria azione ogni round per attaccare la creatura più vicina."),
    (61, 70, "Allucinazioni vivide: svantaggio alle prove di caratteristica."),
    (71, 75, "Fa tutto ciò che le viene detto che sembri non suicida."),
    (76, 80, "Impulso irrefrenabile di mangiare oggetti non commestibili (terra, melma, ecc.)."),
    (81, 90, "La creatura è Stordita."),
    (91, 100, "La creatura perde conoscenza (Incosciente)."),
]

LONG_TERM_MADNESS: List[Tuple[int, int, str]] = [
    (1, 10, "Compulsione a ripetere azioni (lavarsi mani, contare, pregare) subendo svantaggio."),
    (11, 20, "Allucinazioni intense: svantaggio alle prove basate su Saggezza e Carisma."),
    (21, 30, "Paranoia estrema: nessuna creatura è alleata; svantaggio a CAR."),
    (31, 40, "Disgusto verso ciò che tocca; subisce nausea o svantaggio agli attacchi."),
    (41, 45, "Delirio mistico di onnipotenza (CAR +1, ma rifiuta aiuto)."),
    (46, 55, "Amnesia selettiva di identità e amici recenti."),
    (56, 75, "Tremore continuo: svantaggio a prove e attacchi basati su Forza e Destrezza."),
    (76, 85, "Cecità o sordità isterica parziale/totale."),
    (86, 95, "Furia incontrollata: in combattimento attacca finché un nemico è a terra."),
    (96, 100, "Catatonia: Incosciente ma svegliabile con scosse o danni."),
]

INDEFINITE_MADNESS: List[Tuple[int, int, str]] = [
    (1, 15, "'Essere ubriaco o stordito mi mantiene lucido' (Difetto Indefinito)."),
    (16, 25, "'Tengo qualsiasi cosa trovi, potrebbe servirmi'."),
    (26, 30, "'Cerco di sembrare più simile possibile a chi rispetto'."),
    (31, 35, "'Sono convinto che la verità sia nascosta in ogni testo che trovo'."),
    (36, 45, "'C'è un solo modo per risolvere i problemi: la forza bruta'."),
    (46, 55, "'Non sopporto che qualcuno si avvicini senza avvertirmi'."),
    (56, 70, "'Credo di non poter mai morire davvero'."),
    (71, 80, "'Tutte le figure d'autorità stanno cospirando contro di me'."),
    (81, 90, "'Sono un'arma vivente, chiunque mi ostacoli va abbattuto'."),
    (91, 100, "'Non ricordo nulla di ciò che ho fatto nell'ultimo mese, ma sorrido lo stesso'."),
]


def roll_madness(tier: str = "short", roll_val: Optional[int] = None) -> Dict[str, Any]:
    r = int(roll_val) if roll_val is not None else random.randint(1, 100)
    r = max(1, min(100, r))
    t_low = str(tier or "short").lower()
    if "long" in t_low or "lunga" in t_low:
        tbl = LONG_TERM_MADNESS
        dur = f"{random.randint(1, 10) * 10} ore"
        title = "Follia a Lungo Termine"
    elif "indef" in t_low or "perm" in t_low:
        tbl = INDEFINITE_MADNESS
        dur = "Finché curata"
        title = "Follia Indefinita"
    else:
        tbl = SHORT_TERM_MADNESS
        dur = f"{random.randint(1, 10)} minuti"
        title = "Follia a Breve Termine"
    effect_text = tbl[-1][2]
    for lo, hi, desc in tbl:
        if lo <= r <= hi:
            effect_text = desc
            break
    return {"roll": r, "tier": title, "duration": dur, "desc": effect_text}


DMG_POISONS: Dict[str, Dict[str, Any]] = {
    "Sangue d'Assassino (Assassin's Blood)": {"type": "Ingestione", "dc": 10, "stat": "COS", "dmg": "1d12 Veleno", "condition": "Avvelenato (24h)", "half_on_save": True},
    "Fumi d'Othur Bruciato (Burnt Othur Fumes)": {"type": "Inalazione", "dc": 13, "stat": "COS", "dmg": "3d6 Veleno", "condition": "Avvelenato (+1d6/turno fino a 3 TS)", "half_on_save": False},
    "Muco di Vermeiena (Carrion Crawler Mucus)": {"type": "Contatto", "dc": 13, "stat": "COS", "dmg": "0", "condition": "Avvelenato e Paralizzato (1 min)", "half_on_save": False},
    "Veleno Drow (Drow Poison)": {"type": "Ferita", "dc": 13, "stat": "COS", "dmg": "0", "condition": "Avvelenato (1h; Incosciente se fallisce di >=5)", "half_on_save": False},
    "Essenza d'Etere (Essence of Ether)": {"type": "Inalazione", "dc": 15, "stat": "COS", "dmg": "0", "condition": "Avvelenato e Incosciente (8h)", "half_on_save": False},
    "Malizia (Malice)": {"type": "Inalazione", "dc": 15, "stat": "COS", "dmg": "0", "condition": "Avvelenato e Accecato (1h)", "half_on_save": False},
    "Lacrime di Mezzanotte (Midnight Tears)": {"type": "Ingestione", "dc": 17, "stat": "COS", "dmg": "9d6 Veleno", "condition": "Colpisce a mezzanotte", "half_on_save": True},
    "Olio di Taggit (Oil of Taggit)": {"type": "Contatto", "dc": 13, "stat": "COS", "dmg": "0", "condition": "Avvelenato e Incosciente (24h)", "half_on_save": False},
    "Tintura Pallida (Pale Tincture)": {"type": "Ingestione", "dc": 16, "stat": "COS", "dmg": "1d6 Veleno", "condition": "Avvelenato (danno ogni 24h fino a 7 TS riusciti)", "half_on_save": False},
    "Veleno di Verme Purpureo (Purple Worm Poison)": {"type": "Ferita", "dc": 19, "stat": "COS", "dmg": "12d6 Veleno", "condition": "Nessuna condizione aggiuntiva", "half_on_save": True},
    "Veleno di Serpente (Serpent Venom)": {"type": "Ferita", "dc": 11, "stat": "COS", "dmg": "3d6 Veleno", "condition": "Nessuna", "half_on_save": True},
    "Torpore (Torpor)": {"type": "Ingestione", "dc": 15, "stat": "COS", "dmg": "0", "condition": "Avvelenato e Incapacitato (4d6 ore)", "half_on_save": False},
    "Siero della Verità (Truth Serum)": {"type": "Ingestione", "dc": 11, "stat": "COS", "dmg": "0", "condition": "Avvelenato (incapace di mentire 1h)", "half_on_save": False},
    "Veleno di Viverna (Wyvern Poison)": {"type": "Ferita", "dc": 15, "stat": "COS", "dmg": "7d6 Veleno", "condition": "Nessuna", "half_on_save": True},
}

DMG_DISEASES: Dict[str, Dict[str, Any]] = {
    "Febbre della Risata (Cackle Fever)": {"dc": 13, "stat": "COS", "desc": "+1 Livello di Sfinimento + 1d10 Psichici su fallimento (3 TS per guarire)."},
    "Peste delle Fogne (Sewer Plague)": {"dc": 11, "stat": "COS", "desc": "+1 Livello di Sfinimento; recupera solo metà PF dai Dadi Vita e riposi lunghi."},
    "Marciume Oculare (Sight Rot)": {"dc": 15, "stat": "COS", "desc": "Penalità -1 cumulativa alla vista fino ad Accecato al giorno 5 (curabile con Ristorare Inferiore/magia)."},
}

OBJECT_MATERIALS_AC: Dict[str, int] = {
    "Stoffa / Carta / Corda": 11,
    "Cristallo / Vetro / Ghiaccio": 13,
    "Legno / Osso": 15,
    "Pietra": 17,
    "Ferro / Acciaio": 19,
    "Mithral": 21,
    "Adamantio": 23,
}

OBJECT_SIZE_HP: Dict[str, Tuple[int, int]] = {
    "Minuscolo (Tiny)": (2, 5),      # fragile, resiliente
    "Piccolo (Small)": (3, 10),
    "Medio (Medium)": (4, 18),
    "Grande (Large)": (5, 27),
    "Enorme (Huge)": (10, 50),
}


def evaluate_object_damage(raw_damage: int, damage_type: str, damage_threshold: int = 0) -> Tuple[int, str]:
    """
    Valuta il danno contro un oggetto secondo DMG p. 246-247:
    - Oggetti sono immuni ai danni da Veleno e Psichico.
    - Se ha Soglia di Danno (damage_threshold > 0), qualsiasi danno totale inferiore alla soglia è ridotto a 0.
    """
    dt = str(damage_type or "").lower()
    if any(k in dt for k in ("veleno", "poison", "psichico", "psychic")):
        return 0, f"Immunità Oggetto ({damage_type})"
    dmg = max(0, int(raw_damage or 0))
    thresh = max(0, int(damage_threshold or 0))
    if thresh > 0 and dmg < thresh:
        return 0, f"Danno {dmg} < Soglia di Danno ({thresh}) -> 0 danni!"
    return dmg, f"{dmg} danni all'oggetto"


CHASE_COMPLICATIONS_URBAN: List[Tuple[int, int, str]] = [
    (1, 1, "Un grosso ostacolo (barile/carro) blocca la via: Acrobazia CD 15 o terreno difficile per 3 m."),
    (2, 2, "Una folla blocca la strada: Atletica o Intimidire CD 10 o terreno difficile per 3 m."),
    (3, 3, "Una grande finestra di vetro sbarra il passaggio: TS DES CD 10 o 1d4 taglienti e cadi Prono."),
    (4, 4, "Un labirinto di vicoli e casse: TS INT CD 10 per orientarti o perdi 3 m di movimento."),
    (5, 5, "Pozza d'olio/fango scivolosa: TS DES CD 10 o cadi Prono."),
    (6, 6, "Un cane da guardia aggressivo/animale randagio abbaia e attacca chi passa (CA 12, +3 TxC, 1d4+1)."),
    (7, 7, "Una corda stesa o carrucola penzola all'altezza del collo: TS DES CD 10 o 1d4 contundenti e Prono."),
    (8, 8, "Una guardia cittadina ordina l'alt e cerca di afferrarti (+3 Lotta)."),
    (9, 9, "Un mendicante o venditore ambulante ti ostacola chiedendo aiuto: Carisma CD 10 o terreno difficile."),
    (10, 10, "Un edificio in ristrutturazione lascia cadere calcinacci: TS DES CD 12 o 2d4 contundenti."),
    (11, 20, "Nessuna complicazione in questo turno."),
]


def roll_chase_complication(roll_val: Optional[int] = None) -> Dict[str, Any]:
    r = int(roll_val) if roll_val is not None else random.randint(1, 20)
    r = max(1, min(20, r))
    for lo, hi, desc in CHASE_COMPLICATIONS_URBAN:
        if lo <= r <= hi:
            return {"roll": r, "desc": desc, "has_complication": r <= 10}
    return {"roll": r, "desc": "Nessuna complicazione in questo turno.", "has_complication": False}


def get_max_free_dashes(con_mod: int) -> int:
    """DMG p. 252: Durante un Inseguimento puoi usare Scatto gratis 3 + mod COS volte (min 0)."""
    return max(0, 3 + int(con_mod or 0))
