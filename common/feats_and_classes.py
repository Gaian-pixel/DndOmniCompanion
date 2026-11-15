"""
common/feats_and_classes.py - Motore puro-Python D&D 5e (PHB / XGtE / TCE) per:
- Talenti (Feats) mancanti: Dual Wielder, Medium Armor Master, Heavy Armor Master,
  Mounted Combatant, Savage Attacker, Defensive Duelist, Grappler, Mage Slayer, Skulker,
  Tavern Brawler, Polearm Master, Great Weapon Master, Lucky.
- Privilegi di classe e sottoclasse PHB per tutte le 12 classi (Primal Champion cap 24,
  Fast Movement, Persistent Rage, Survivor, Purity of Body, Divine Health, Slippery Mind,
  Elusive, Arcane Ward, Sculpt Spells, Dark One's Blessing, Unarmored Movement, Jack of All Trades, ecc.).
- Competenze Armature/Armi/Strumenti & penalità (PHB p. 144), Sinergie Strumenti (XGtE),
  Requisiti e Riposo Breve di Sintonia (DMG p. 136-138), Armatura nel Sonno (XGtE p. 77),
  Componenti Materiali costose/consumate e Durata Concentrazione in round.
"""

from __future__ import annotations

import math
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from common.dnd5e_tables import entity_get_class_level, entity_get_total_level, entity_has_keyword


def _entity_sheet(entity: Any) -> Dict[str, Any]:
    if isinstance(entity, dict):
        return entity
    fs = getattr(entity, "full_sheet", None)
    return fs if isinstance(fs, dict) else {}


def _entity_attr_val(entity: Any, stat: str, default: int = 10) -> int:
    from common.item_modifiers import get_effective_attribute_from_dict
    try:
        return int(get_effective_attribute_from_dict(entity, stat))
    except Exception:
        return default


def _entity_attr_mod(entity: Any, stat: str, default: int = 10) -> int:
    return (_entity_attr_val(entity, stat, default) - 10) // 2


def _entity_pb(entity: Any) -> int:
    lvl = max(1, int(entity_get_total_level(entity) or 1))
    return ((lvl - 1) // 4) + 2


# ==============================================================================
# 1. COMPETENZE ARMATURE / ARMI / STRUMENTI & PENALITA' (PHB p. 144, XGtE p. 78)
# ==============================================================================

def _normalize_armor_category(armor_cat_or_name: str) -> Optional[str]:
    s = str(armor_cat_or_name or "").strip().lower()
    if not s:
        return None
    if s in ("light", "leggera") or any(k in s for k in ("cuoio", "leather", "imbottita", "padded")):
        return "light"
    if s in ("medium", "media") or any(k in s for k in ("pelle", "hide", "giaco", "chain shirt", "scaglie", "scale", "pettorale", "breastplate", "mezza armatura", "half plate")):
        return "medium"
    if s in ("heavy", "pesante") or any(k in s for k in ("anelli", "ring mail", "cotta di maglia", "chain mail", "strisce", "splint", "piastre", "plate")):
        return "heavy"
    if s in ("shield", "scudo"):
        return "shield"
    return None


def get_entity_armor_proficiencies(entity: Any) -> set:
    """Restituisce l'insieme {'light', 'medium', 'heavy', 'shield'} posseduto dall'entità."""
    from common.character_schema import compute_character_proficiencies
    sheet = _entity_sheet(entity)
    classes = sheet.get("classes") if isinstance(sheet.get("classes"), dict) else {}
    char_cls = str(sheet.get("char_class") or sheet.get("class") or getattr(entity, "char_class", "") or "")
    race = str(sheet.get("race") or getattr(entity, "race", "") or "")
    subclass = str(sheet.get("subclass") or getattr(entity, "subclass", "") or "")
    feats_raw = sheet.get("features") or getattr(entity, "features", "") or ""
    profs = set()

    # Da classi base e sottoclassi note
    if classes or char_cls:
        prof_arg = sheet if isinstance(sheet, dict) and (sheet.get("classes") or sheet.get("char_class")) else {
            "classes": classes,
            "char_class": char_cls,
            "race": race,
            "subrace": sheet.get("subrace") or getattr(entity, "subrace", ""),
            "subclass": subclass,
            "feats": sheet.get("feats") or getattr(entity, "feats", []),
            "features": feats_raw,
        }
        c_profs = compute_character_proficiencies(prof_arg)
        for p in c_profs.get("armor", []):
            cat = _normalize_armor_category(p)
            if cat:
                profs.add(cat)
    # Sottoclassi speciali con competenze armatura (Valore Bardo, Lama Cantante, Domini Chierico)
    sub_low = subclass.lower()
    if any(k in sub_low for k in ("valore", "valor", "spade", "swords")):
        profs.update({"medium", "shield"} if "valore" in sub_low or "valor" in sub_low else {"medium"})
    if any(k in sub_low for k in ("guerra", "war", "tempesta", "tempest", "vita", "life", "natura", "nature", "forgia", "forge", "ordine", "order")):
        if entity_get_class_level(entity, "chierico", "cleric") > 0:
            profs.add("heavy")
    if any(k in sub_low for k in ("cantore", "bladesing")):
        profs.add("light")

    # Talenti armatura (Lightly/Moderately/Heavily Armored) e lista esplicita
    if entity_has_keyword(entity, "corazza leggera", "lightly armored"):
        profs.add("light")
    if entity_has_keyword(entity, "corazza media", "moderately armored"):
        profs.update({"medium", "shield"})
    if entity_has_keyword(entity, "corazza pesante", "heavily armored"):
        profs.add("heavy")

    raw_armor_profs = (sheet.get("proficiencies") or {}).get("armor", []) if isinstance(sheet.get("proficiencies"), dict) else []
    for rp in (raw_armor_profs or []):
        rl = str(rp).lower()
        if "tutte" in rl or "all" in rl:
            profs.update({"light", "medium", "heavy", "shield"})
        else:
            c = _normalize_armor_category(rl)
            if c:
                profs.add(c)
    return profs


def get_armor_nonproficiency_penalties(entity: Any) -> Dict[str, Any]:
    """
    PHB p. 144: Se indossi un'armatura o uno scudo senza competenza:
    - Svantaggio a prove di caratteristica, TS e TxC su Forza o Destrezza
    - Impossibile lanciare incantesimi.
    """
    from common.item_modifiers import calculate_character_item_modifiers
    mods = calculate_character_item_modifiers(entity)
    eq_armor = mods.get("equipped_armor")
    has_shield = bool(mods.get("has_shield", False))
    if not eq_armor and not has_shield:
        return {"non_proficient": False, "disadvantage_str_dex": False, "cannot_cast_spells": False, "missing": [], "str_speed_penalty": 0}

    # Un NPC/Mostro privo di classe PC non va penalizzato sulla propria armatura naturale/da statblock
    if getattr(entity, "is_monster", False):
        return {"non_proficient": False, "disadvantage_str_dex": False, "cannot_cast_spells": False, "missing": [], "str_speed_penalty": 0}
    sheet = _entity_sheet(entity)
    has_pc_class = bool(sheet.get("classes") or sheet.get("char_class") or sheet.get("class") or getattr(entity, "char_class", ""))
    if not has_pc_class and not getattr(entity, "is_party_member", False):
        return {"non_proficient": False, "disadvantage_str_dex": False, "cannot_cast_spells": False, "missing": [], "str_speed_penalty": 0}

    profs = get_entity_armor_proficiencies(entity)
    missing = []
    eq_cat = _normalize_armor_category((eq_armor or {}).get("category") or (eq_armor or {}).get("name", "")) if eq_armor else None
    if eq_cat and eq_cat not in profs:
        missing.append(eq_cat)
    if has_shield and "shield" not in profs:
        missing.append("shield")

    # Requisito Forza Armatura Pesante (PHB p. 144-145): -10 ft velocità (salvo Nano / Stivali Elfi-Salto)
    str_pen = 0
    if eq_cat == "heavy" and eq_armor:
        aname = str(eq_armor.get("name", "")).lower()
        req_str = 15 if any(k in aname for k in ("piastre", "plate", "strisce", "splint")) else (13 if any(k in aname for k in ("cotta di maglia", "chain mail")) else 0)
        if req_str > 0 and _entity_attr_val(entity, "FOR", 10) < req_str:
            race = str(sheet.get("race") or getattr(entity, "race", "") or "").lower()
            if "nano" not in race and "dwarf" not in race and not entity_has_keyword(entity, "stivali dello slancio", "boots of striding"):
                str_pen = 10

    non_prof = len(missing) > 0
    return {
        "non_proficient": non_prof,
        "disadvantage_str_dex": non_prof,
        "cannot_cast_spells": non_prof,
        "missing": missing,
        "str_speed_penalty": str_pen,
    }


def is_proficient_with_weapon(entity: Any, weapon_name: str, weapon_props: Optional[List[str]] = None) -> bool:
    """Verifica la competenza con l'arma specifica per il bonus di competenza al TxC (PHB p. 146)."""
    sheet = _entity_sheet(entity)
    if not sheet and not getattr(entity, "char_class", ""):
        return True
    if not (sheet.get("classes") or sheet.get("char_class") or sheet.get("class") or getattr(entity, "char_class", "")):
        return True

    if entity_has_keyword(entity, "maestro d'armi", "weapon master"):
        return True
    w_low = str(weapon_name or "").lower()
    if any(k in w_low for k in ("senz'armi", "unarmed")):
        return True
    if any(k in w_low for k in ("improvvisat", "improvised")):
        return entity_has_keyword(entity, "attaccabrighe", "tavern brawler")

    from common.character_schema import compute_character_proficiencies
    prof_arg = sheet if isinstance(sheet, dict) and (sheet.get("classes") or sheet.get("char_class")) else {
        "classes": sheet.get("classes") if isinstance(sheet.get("classes"), dict) else {},
        "char_class": str(sheet.get("char_class") or sheet.get("class") or getattr(entity, "char_class", "") or ""),
        "race": str(sheet.get("race") or getattr(entity, "race", "") or ""),
        "subrace": str(sheet.get("subrace") or getattr(entity, "subrace", "") or ""),
        "subclass": str(sheet.get("subclass") or getattr(entity, "subclass", "") or ""),
        "feats": sheet.get("feats") or getattr(entity, "feats", []),
        "features": sheet.get("features") or getattr(entity, "features", ""),
    }
    c_profs = compute_character_proficiencies(prof_arg)
    w_profs = [str(w).lower() for w in c_profs.get("weapons", [])]
    raw_ep = (sheet.get("proficiencies") or {}).get("weapons", []) if isinstance(sheet.get("proficiencies"), dict) else []
    for ew in (raw_ep or []):
        ewl = str(ew).lower()
        if ewl and ewl not in w_profs:
            w_profs.append(ewl)
    if any("tutte" in wp or "all" in wp or "marziali" in wp or "martial" in wp for wp in w_profs):
        return True

    martial_kws = (
        "spada lunga", "longsword", "spadone", "greatsword", "stocco", "rapier", "scimitar",
        "spada corta", "shortsword", "bipenne", "greataxe", "ascia da battaglia", "battleaxe",
        "alabarda", "halberd", "falcione", "glaive", "picca", "pike", "maglio", "maul",
        "martello da guerra", "warhammer", "frusta", "whip", "arco lungo", "longbow",
        "balestra pesante", "heavy crossbow", "balestra a mano", "hand crossbow", "tridente", "trident",
    )
    is_martial = any(k in w_low for k in martial_kws) or any("martial" in str(p).lower() or "marziale" in str(p).lower() for p in (weapon_props or []))
    if not is_martial and any("semplici" in wp or "simple" in wp for wp in w_profs):
        return True
    return any(wp in w_low or w_low in wp for wp in w_profs if len(wp) >= 3)


TOOL_SKILL_SYNERGIES_XGTE: Dict[str, Tuple[str, ...]] = {
    "indagare": ("arnesi da scasso", "thieves' tools", "kit da falsario", "forgery kit"),
    "investigare": ("arnesi da scasso", "thieves' tools", "kit da falsario", "forgery kit"),
    "investigation": ("arnesi da scasso", "thieves' tools", "kit da falsario", "forgery kit"),
    "medicina": ("kit da erborista", "herbalism kit", "borse da guaritore"),
    "medicine": ("herbalism kit", "kit da erborista"),
    "natura": ("kit da erborista", "herbalism kit", "kit da avvelenatore", "poisoner's kit"),
    "nature": ("herbalism kit", "kit da erborista", "poisoner's kit", "kit da avvelenatore"),
    "arcano": ("scorte da alchimista", "alchemist's supplies", "calligraf"),
    "arcana": ("alchemist's supplies", "scorte da alchimista"),
    "fuga": ("arnesi da scasso", "thieves' tools"),
    "inganno": ("kit da camuffamento", "disguise kit", "kit da falsario", "forgery kit"),
    "deception": ("disguise kit", "kit da camuffamento", "forgery kit", "kit da falsario"),
    "furtività": ("kit da camuffamento", "disguise kit", "calzolaio", "cobbler's tools"),
    "stealth": ("disguise kit", "kit da camuffamento", "cobbler's tools", "calzolaio"),
    "sopravvivenza": ("strumenti da cartografo", "cartographer's tools", "navigatore", "navigator's tools"),
    "survival": ("cartographer's tools", "strumenti da cartografo", "navigator's tools"),
    "storia": ("strumenti da fabbro", "smith's tools", "muratore", "mason's tools", "intagliatore"),
    "history": ("smith's tools", "strumenti da fabbro", "mason's tools"),
}


def check_tool_synergy_xgte(entity: Any, skill_name: str, tool_name: Optional[str] = None) -> bool:
    """XGtE p. 78-85: Se competente sia nell'abilità sia nello strumento correlato, conferisce Vantaggio."""
    sheet = _entity_sheet(entity)
    skills = sheet.get("skills", {}) or {}
    profs = sheet.get("proficiencies", {}) or {}
    tool_list = [str(t).lower() for t in (profs.get("tools", []) if isinstance(profs, dict) else [])]
    if not tool_list:
        return False

    s_low = str(skill_name or "").strip().lower()
    skill_prof = False
    for k, v in skills.items():
        if s_low and (s_low in str(k).lower() or str(k).lower() in s_low):
            try:
                if int(v or 0) >= 1:
                    skill_prof = True
                    break
            except (ValueError, TypeError):
                pass
    if not skill_prof:
        return False

    if tool_name:
        t_low = str(tool_name).strip().lower()
        return any(t_low in t or t in t_low for t in tool_list)

    matched_tools = TOOL_SKILL_SYNERGIES_XGTE.get(s_low, ())
    return any(any(mt in t for mt in matched_tools) for t in tool_list)


# ==============================================================================
# 2. SINTONIA PREREQUISITI & RIPOSO BREVE (DMG p. 136-138) + ARMATURA SONNO (XGtE)
# ==============================================================================

_CLASS_NAME_ALIASES: Dict[str, Tuple[str, ...]] = {
    "barbaro": ("barbaro", "barbarian"), "barbarian": ("barbaro", "barbarian"),
    "bardo": ("bardo", "bard"), "bard": ("bardo", "bard"),
    "chierico": ("chierico", "cleric"), "cleric": ("chierico", "cleric"),
    "druido": ("druido", "druid"), "druid": ("druido", "druid"),
    "guerriero": ("guerriero", "fighter"), "fighter": ("guerriero", "fighter"),
    "ladro": ("ladro", "rogue"), "rogue": ("ladro", "rogue"),
    "mago": ("mago", "wizard"), "wizard": ("mago", "wizard"),
    "monaco": ("monaco", "monk"), "monk": ("monaco", "monk"),
    "paladino": ("paladino", "paladin"), "paladin": ("paladino", "paladin"),
    "ranger": ("ranger",),
    "stregone": ("stregone", "sorcerer"), "sorcerer": ("stregone", "sorcerer"),
    "warlock": ("warlock",),
    "artefice": ("artefice", "artificer"), "artificer": ("artefice", "artificer"),
}


def check_attunement_prerequisites(character: Any, item: Dict[str, Any]) -> Tuple[bool, str]:
    """
    DMG p. 136-138: Verifica i prerequisiti di sintonia (classe, incantatore, allineamento).
    Artefice Lv 14+ (Magic Item Savant) e Ladro Furfante Lv 13+ (Use Magic Device) ignorano i prerequisiti!
    """
    if not isinstance(item, dict):
        return True, ""

    # Ladro Furfante Lv 13+ (Use Magic Device) / Artefice Lv 14+ (Magic Item Savant)
    sub_low = str(_entity_sheet(character).get("subclass") or getattr(character, "subclass", "") or "").lower()
    rogue_lvl = entity_get_class_level(character, "ladro", "rogue")
    art_lvl = entity_get_class_level(character, "artefice", "artificer")
    if (rogue_lvl >= 13 and ("furfante" in sub_low or "thief" in sub_low)) or art_lvl >= 14:
        return True, ""
    if entity_has_keyword(character, "usare oggetti magici", "use magic device", "esperto di oggetti magici", "magic item savant"):
        return True, ""

    req_parts = [
        str(item.get("requires_attunement") or ""),
        str(item.get("attunement_prereq") or ""),
        str(item.get("attunement_requirements") or ""),
        str(item.get("desc") or ""),
    ]
    if item.get("attuned_class"):
        req_parts.append(f"requires attunement by a {item.get('attuned_class')}")
    req_txt = " ".join(req_parts).lower()

    if "sintonia" not in req_txt and "attunement" not in req_txt:
        return True, ""

    # Prerequisito incantatore ("spellcaster" / "incantatore")
    if re.search(r"(?:by a|da parte di un)\s+(?:spellcaster|incantatore)", req_txt) or "requires attunement by a spellcaster" in req_txt:
        sh = _entity_sheet(character)
        has_slots = any(
            (sl.get("max", 0) > 0 if isinstance(sl, dict) else False)
            for sl in (sh.get("spell_slots") or getattr(character, "spell_slots", {}) or {}).values()
        )
        pact = sh.get("pact_slots") or getattr(character, "pact_slots", {}) or {}
        has_pact = isinstance(pact, dict) and pact.get("max", 0) > 0
        is_caster_class = any(
            entity_get_class_level(character, *als) > 0
            for als in (("mago", "wizard"), ("chierico", "cleric"), ("druido", "druid"), ("bardo", "bard"), ("stregone", "sorcerer"), ("warlock",), ("paladino", "paladin"), ("ranger",), ("artefice", "artificer"))
        )
        if not (has_slots or has_pact or is_caster_class or entity_has_keyword(character, "incantesimi", "spellcasting", "magia del patto", "pact magic")):
            return False, f"'{item.get('name', 'Oggetto')}' richiede la sintonia da parte di un Incantatore (DMG p. 136)."

    # Prerequisito classe ("by a wizard", "da un paladino", ecc.)
    req_classes = []
    m_req = re.search(r"(?:requires attunement|richiede sintonia)[^.\n;]{0,120}", req_txt)
    if m_req:
        snippet = m_req.group(0)
        for cname, aliases in _CLASS_NAME_ALIASES.items():
            if re.search(rf"\b{re.escape(cname)}\b", snippet):
                req_classes.append(aliases)
        if req_classes:
            if not any(entity_get_class_level(character, *als) > 0 for als in req_classes):
                return False, f"'{item.get('name', 'Oggetto')}' richiede una classe specifica per la sintonia ({m_req.group(0)})."

        # Prerequisito allineamento
        align = str(_entity_sheet(character).get("alignment") or getattr(character, "alignment", "") or "").lower()
        if align:
            if any(w in snippet for w in ("buon", "good")) and not any(w in align for w in ("buon", "good")):
                return False, f"'{item.get('name', 'Oggetto')}' richiede allineamento Buono."
            if any(w in snippet for w in ("malvag", "evil")) and not any(w in align for w in ("malvag", "evil")):
                return False, f"'{item.get('name', 'Oggetto')}' richiede allineamento Malvagio."
            if any(w in snippet for w in ("legal", "lawful")) and not any(w in align for w in ("legal", "lawful")):
                return False, f"'{item.get('name', 'Oggetto')}' richiede allineamento Legale."
            if any(w in snippet for w in ("caotic", "chaotic")) and not any(w in align for w in ("caotic", "chaotic")):
                return False, f"'{item.get('name', 'Oggetto')}' richiede allineamento Caotico."

    return True, ""


def attune_item_short_rest(character: Any, item_idx: int) -> Tuple[bool, str]:
    """DMG p. 138: Sintonizza un oggetto durante un Riposo Breve (1 oggetto per riposo)."""
    inv = getattr(character, "inventory_grid", None)
    if not isinstance(inv, list):
        inv = _entity_sheet(character).get("inventory_grid")
    if not isinstance(inv, list) or not (0 <= item_idx < len(inv)) or not isinstance(inv[item_idx], dict):
        return False, "Oggetto non valido in inventario."
    item = inv[item_idx]
    ok_p, err_p = check_attunement_prerequisites(character, item)
    if not ok_p:
        return False, err_p

    art_lvl = entity_get_class_level(character, "artefice", "artificer")
    max_att = 6 if art_lvl >= 18 else (5 if art_lvl >= 14 else (4 if art_lvl >= 10 else 3))
    cur_att = [it for it in inv if isinstance(it, dict) and it.get("attuned")]
    if len(cur_att) >= max_att:
        return False, f"Limite sintonizzazioni raggiunto ({len(cur_att)}/{max_att})."

    iname = str(item.get("name", "")).strip().lower()
    if any(str(it.get("name", "")).strip().lower() == iname for it in cur_att if it is not item):
        return False, "Non puoi sintonizzarti con due copie dello stesso oggetto (DMG p. 138)."

    item["attuned"] = True
    return True, f"🔮 Sintonia completata durante il Riposo Breve con '{item.get('name', 'Oggetto')}'."


def evaluate_armor_sleep(entity: Any, game_state: Any = None) -> Dict[str, Any]:
    """
    XGtE p. 77 (Regola Opzionale DM opt_armor_sleep_xge):
    Dormire con armatura Media o Pesante limita il recupero di Dadi Vita a 1/4 del totale (min 1)
    e impedisce di ridurre il livello di Indebolimento (Exhaustion).
    """
    opt_on = False
    if game_state and isinstance(getattr(game_state, "automation_settings", None), dict):
        opt_on = bool(game_state.automation_settings.get("opt_armor_sleep_xge", False))
    elif getattr(entity, "sleeping_in_armor", False):
        opt_on = True
    if not opt_on:
        return {"penalized": False, "hd_fraction": 0.5, "blocks_exhaustion_recovery": False, "note": ""}

    from common.item_modifiers import calculate_character_item_modifiers
    mods = calculate_character_item_modifiers(entity)
    eq_armor = mods.get("equipped_armor") or {}
    cat = str(eq_armor.get("category") or "").lower()
    if not eq_armor and isinstance(getattr(entity, "sleeping_in_armor", None), str):
        cat = str(entity.sleeping_in_armor).lower()
    if cat in ("medium", "media", "heavy", "pesante") or getattr(entity, "sleeping_in_armor", False) is True:
        return {
            "penalized": True,
            "hd_fraction": 0.25,
            "blocks_exhaustion_recovery": True,
            "note": f"🛡️ Riposo in armatura {cat or 'media/pesante'} (XGtE p. 77): recuperi solo 1/4 dei Dadi Vita (min 1) e l'Indebolimento non cala.",
        }
    return {"penalized": False, "hd_fraction": 0.5, "blocks_exhaustion_recovery": False, "note": ""}


# ==============================================================================
# 3. TALENTI 5e (FEATS - PHB p. 165-170) & APPLICATORI DI COMBATTIMENTO
# ==============================================================================

def get_heavy_armor_master_reduction(entity: Any, damage_type: str, is_magical: bool = False) -> int:
    """Maestria nelle Armature Pesanti (PHB p. 167): -3 ai danni contundenti/perforanti/taglienti non magici in armatura pesante."""
    if is_magical:
        return 0
    if not entity_has_keyword(entity, "maestria nelle armature pesanti", "heavy armor master"):
        return 0
    dt = str(damage_type or "").lower()
    if not any(k in dt for k in ("taglient", "slashing", "perforant", "piercing", "contundent", "bludgeoning")):
        return 0
    from common.item_modifiers import calculate_character_item_modifiers
    eq_armor = calculate_character_item_modifiers(entity).get("equipped_armor")
    if eq_armor and _normalize_armor_category(eq_armor.get("category") or eq_armor.get("name", "")) == "heavy":
        return 3
    return 0


def check_defensive_duelist_bonus(entity: Any) -> int:
    """Duellante Difensivo (PHB p. 165): con arma accurata, +Bonus Competenza alla CA in reazione."""
    if not entity_has_keyword(entity, "duellante difensivo", "defensive duelist"):
        return 0
    return _entity_pb(entity)


def apply_savage_attacker_roll(formula: str, is_crit: bool = False) -> Tuple[int, str]:
    """Attaccante Selvaggio (PHB p. 169): 1/turno tira due volte i dadi danno in mischia e prendi il totale maggiore."""
    from common.dice import roll_dice
    r1 = roll_dice(formula, is_crit=is_crit)
    r2 = roll_dice(formula, is_crit=is_crit)
    best = r1 if r1["total"] >= r2["total"] else r2
    return best["total"], f" [🪓 Attaccante Selvaggio: max({r1['total']}, {r2['total']})={best['total']}]"


def spend_lucky_point(entity: Any, reason: str = "Tiro di dado") -> Tuple[bool, int, str]:
    """Talento Fortunato (Lucky, PHB p. 167): spende 1/3 Punti Fortuna per tirare un d20 extra."""
    if not entity_has_keyword(entity, "fortunato", "lucky"):
        return False, 0, "Richiede il talento Fortunato (Lucky)."
    from common.dnd5e_tables import entity_spend_resource, entity_find_resource
    res = entity_find_resource(entity, "fortunato", "lucky", "punti fortuna")
    if res is None:
        sheet = _entity_sheet(entity)
        cl = getattr(entity, "custom_resources", None)
        if cl is None and isinstance(sheet, dict):
            cl = sheet.setdefault("custom_resources", [])
        if isinstance(cl, list):
            cl.append({"name": "Punti Fortuna (Lucky)", "current": 3, "max": 3, "reset_on": "long"})
    ok, cur, mx = entity_spend_resource(entity, ("fortunato", "lucky", "punti fortuna"), 1)
    if not ok:
        return False, 0, f"Punti Fortuna esauriti ({cur}/{mx})."
    roll = random.randint(1, 20)
    return True, roll, f"🍀 [FORTUNATO] {getattr(entity, 'name', 'PG')} spende 1 Punto Fortuna ({cur}/{mx}) su {reason}: nuovo d20 = {roll}!"


# ==============================================================================
# 4. INCANTESIMI: COMPONENTI MATERIALI, DURATA CONCENTRAZIONE E METAMAGIA
# ==============================================================================

def parse_spell_duration_rounds(duration_str: str) -> Optional[int]:
    """Converte la durata 5e ('1 minuto', '10 minutes', '1 ora', '1 round') in numero di round da 6 sec."""
    s = str(duration_str or "").strip().lower()
    if not s or any(k in s for k in ("istant", "instant")):
        return 0
    m = re.search(r"(\d+)\s*(round|turn|minut|minute|ora|ore|hour)", s)
    if not m:
        return None
    val = int(m.group(1))
    unit = m.group(2)
    if unit.startswith(("round", "turn")):
        return val
    if unit.startswith("minut"):
        return val * 10
    if unit.startswith(("or", "hour")):
        return val * 600
    return None


def check_spell_material_components(entity: Any, spell: Dict[str, Any]) -> Tuple[bool, bool, int, str]:
    """
    PHB p. 203: Verifica componenti materiali con costo in MO o consumati.
    Ritorna: (ok, is_consumed, gp_cost, note)
    """
    mat = str(spell.get("material", "") or spell.get("materials", "") or spell.get("desc", "")).lower()
    comps = str(spell.get("components", "") or "").upper()
    if "M" not in comps and not spell.get("material"):
        return True, False, 0, ""

    m_cost = re.search(r"(\d[\d\.,]*)\s*(?:mo|gp|monete d['’]oro|gold pieces?)", mat)
    if not m_cost:
        return True, False, 0, ""

    raw_num = m_cost.group(1).replace(".", "").replace(",", "")
    try:
        gp_cost = int(raw_num)
    except ValueError:
        gp_cost = 0
    is_consumed = any(k in mat for k in ("consuma", "consum", "si distrugge", "destroyed"))

    if gp_cost <= 0:
        return True, is_consumed, 0, ""

    sheet = _entity_sheet(entity)
    inv = getattr(entity, "inventory_grid", None) or sheet.get("inventory_grid", []) or []
    # Cerca componente specifico o valore in inventario/oro disponibile
    curr = getattr(entity, "currency", None) or sheet.get("currency", {}) or {}
    try:
        gp_avail = int(curr.get("gp", 0) or 0) + int(curr.get("pp", 0) or 0) * 10
    except (ValueError, TypeError):
        gp_avail = 0

    has_matching_item = any(
        isinstance(it, dict) and (float(it.get("value_gp", 0) or 0) >= gp_cost or str(gp_cost) in str(it.get("desc", "")).lower())
        for it in inv
    )
    if has_matching_item or gp_avail >= gp_cost:
        return True, is_consumed, gp_cost, f" [💎 Componente da {gp_cost} mo{' (consumato)' if is_consumed else ''}]"
    return False, is_consumed, gp_cost, f"⚠️ Componente materiale richiesto: valore minimo {gp_cost} MO (non trovato nello zaino/borsello)."


# ==============================================================================
# 5. PRIVILEGI DI CLASSE PHB AGGIUNTIVI (ALL 12 CLASSES)
# ==============================================================================

def get_entity_speed_bonus_ft(entity: Any) -> int:
    """
    Calcola i bonus passivi di velocità PHB (esclusa l'armatura/ingombro):
    - Barbaro Lv 5+: Movimento Veloce (+10 ft senza armatura pesante)
    - Monaco Lv 2+: Movimento Senz'Armatura (+10..+30 ft senza armatura né scudo)
    - Talento Mobile (+10 ft)
    """
    from common.item_modifiers import calculate_character_item_modifiers
    mods = calculate_character_item_modifiers(entity)
    eq_armor = mods.get("equipped_armor")
    has_shield = bool(mods.get("has_shield", False))
    armor_cat = _normalize_armor_category((eq_armor or {}).get("category") or (eq_armor or {}).get("name", "")) if eq_armor else ""

    bonus = 0
    barb_lvl = entity_get_class_level(entity, "barbar", "barbarian")
    if barb_lvl >= 5 and armor_cat != "heavy":
        bonus += 10

    monk_lvl = entity_get_class_level(entity, "monaco", "monk")
    if monk_lvl >= 2 and eq_armor is None and not has_shield:
        bonus += 10 if monk_lvl < 6 else (15 if monk_lvl < 10 else (20 if monk_lvl < 14 else (25 if monk_lvl < 18 else 30)))

    if entity_has_keyword(entity, "mobile", "mobilità"):
        bonus += 10
    return bonus


def get_jack_or_remarkable_bonus(entity: Any, stat: str, is_proficient: bool = False) -> int:
    """Bardo Lv 2+ Tuttofare (Jack of All Trades, ogni abilità/Iniziativa) o Campione Lv 7+ Atleta Straordinario (FOR/DES/COS)."""
    if is_proficient:
        return 0
    pb = _entity_pb(entity)
    bard_lvl = entity_get_class_level(entity, "bardo", "bard")
    if bard_lvl >= 2 or entity_has_keyword(entity, "tuttofare", "jack of all trades"):
        return pb // 2
    sub_low = str(_entity_sheet(entity).get("subclass") or getattr(entity, "subclass", "") or "").lower()
    if entity_get_class_level(entity, "guerriero", "fighter") >= 7 and ("campione" in sub_low or "champion" in sub_low):
        if str(stat or "").upper() in ("FOR", "STR", "DES", "DEX", "COS", "CON", "INIT"):
            return math.ceil(pb / 2)
    return 0


def init_or_get_arcane_ward_hp(entity: Any) -> int:
    """Mago Abiurazione Lv 2+ (PHB p. 115): Interdizione Arcana = 2 * livello Mago + mod INT."""
    wiz_lvl = entity_get_class_level(entity, "mago", "wizard")
    sheet = _entity_sheet(entity)
    sub_low = str(sheet.get("subclass") or getattr(entity, "subclass", "") or "").lower()
    if wiz_lvl < 2 or not ("abiur" in sub_low or "abjur" in sub_low or entity_has_keyword(entity, "interdizione arcana", "arcane ward")):
        return 0
    max_w = max(1, (2 * wiz_lvl) + _entity_attr_mod(entity, "INT"))
    cur = getattr(entity, "arcane_ward_hp", None)
    if cur is None and isinstance(sheet, dict):
        cur = sheet.get("arcane_ward_hp", None)
    if cur is None:
        cur = max_w
    cur_i = max(0, min(max_w, int(cur or 0)))
    try:
        entity.arcane_ward_hp = cur_i
    except Exception:
        pass
    if isinstance(sheet, dict):
        sheet["arcane_ward_hp"] = cur_i
    return cur_i


def consume_arcane_ward_hp(entity: Any, incoming_damage: int) -> Tuple[int, int]:
    """Assorbe i danni con Interdizione Arcana prima dei PV. Ritorna (danno_residuo, assorbito)."""
    if incoming_damage <= 0:
        return incoming_damage, 0
    ward = init_or_get_arcane_ward_hp(entity)
    if ward <= 0:
        return incoming_damage, 0
    absorbed = min(ward, int(incoming_damage))
    rem = int(incoming_damage) - absorbed
    new_ward = ward - absorbed
    try:
        entity.arcane_ward_hp = new_ward
    except Exception:
        pass
    sheet = _entity_sheet(entity)
    if isinstance(sheet, dict):
        sheet["arcane_ward_hp"] = new_ward
    return rem, absorbed


def recharge_arcane_ward_hp(entity: Any, spell_level: int) -> int:
    """Lanciando un incantesimo di Abiurazione di 1°+ liv., Interdizione Arcana recupera 2*livello PV."""
    if spell_level <= 0:
        return 0
    wiz_lvl = entity_get_class_level(entity, "mago", "wizard")
    sheet = _entity_sheet(entity)
    sub_low = str(sheet.get("subclass") or getattr(entity, "subclass", "") or "").lower()
    if wiz_lvl < 2 or not ("abiur" in sub_low or "abjur" in sub_low or entity_has_keyword(entity, "interdizione arcana", "arcane ward")):
        return 0
    max_w = max(1, (2 * wiz_lvl) + _entity_attr_mod(entity, "INT"))
    cur = init_or_get_arcane_ward_hp(entity)
    new_w = min(max_w, cur + (2 * int(spell_level)))
    try:
        entity.arcane_ward_hp = new_w
    except Exception:
        pass
    if isinstance(sheet, dict):
        sheet["arcane_ward_hp"] = new_w
    return new_w - cur


def apply_dark_ones_blessing(attacker: Any, victim: Any, game_state: Any = None) -> int:
    """Warlock Immondo Lv 1+ (PHB p. 109): Uccidere un nemico ostile conferisce Temp HP = mod CAR + liv. Warlock."""
    if not attacker or not victim or getattr(victim, "hp", 1) > 0:
        return 0
    war_lvl = entity_get_class_level(attacker, "warlock")
    sub_low = str(_entity_sheet(attacker).get("subclass") or getattr(attacker, "subclass", "") or "").lower()
    if war_lvl >= 1 and (any(k in sub_low for k in ("immondo", "fiend")) or entity_has_keyword(attacker, "benedizione dell'oscuro", "dark one's blessing")):
        gain = max(1, _entity_attr_mod(attacker, "CAR") + war_lvl)
        from server.rules.reaction_magic import apply_temp_hp
        new_t, _ = apply_temp_hp(attacker, gain, game_state)
        return new_t
    return 0


def get_destroy_undead_cr_threshold(cleric_lvl: int) -> float:
    """Chierico Lv 5+ (PHB p. 59): Distruggere Non Morti per GS."""
    if cleric_lvl >= 17:
        return 4.0
    if cleric_lvl >= 14:
        return 3.0
    if cleric_lvl >= 11:
        return 2.0
    if cleric_lvl >= 8:
        return 1.0
    if cleric_lvl >= 5:
        return 0.5
    return -1.0


def has_paladin_aura_of_courage(target_player: Any, game_state: Any) -> bool:
    """Paladino Lv 10+ (PHB p. 85): gli alleati entro 10/30 ft non possono essere Spaventati."""
    if not target_player or not game_state:
        return False
    t_pos = getattr(target_player, "position", None)
    tgt_p = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
    from common.hex_utils import Hex, grid_distance_3d
    gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    for p in getattr(game_state, "players", []):
        pal_lvl = entity_get_class_level(p, "paladin", "paladino")
        if pal_lvl < 10 or getattr(p, "hp", 0) <= 0:
            continue
        conds = [str(c).lower() for c in getattr(p, "conditions", [])]
        if any(ic in conds for ic in ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "stordito", "pietrificato", "morto")):
            continue
        p_party = bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None))
        if p_party != tgt_p:
            continue
        radius = 6.0 if pal_lvl >= 18 else 2.0
        if p.name == target_player.name:
            return True
        if t_pos and getattr(p, "position", None):
            d = grid_distance_3d(Hex(p.position[0], p.position[1]), Hex(t_pos[0], t_pos[1]), getattr(p, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=gtype)
            if d <= radius:
                return True
    return False


# ==============================================================================
# 4. PREREQUISITI TALENTI, HALF-FEAT & RESILIENT (PHB p. 165-170 / XGtE / TCE)
# ==============================================================================

HALF_FEAT_SPECS: Dict[Tuple[str, ...], Dict[str, Any]] = {
    ("resilient", "resiliente"): {"stats": ("FOR", "DES", "COS", "INT", "SAG", "CAR"), "grants_save_prof": True},
    ("heavy armor master", "armature pesanti"): {"stats": ("FOR",), "grants_save_prof": False},
    ("observant", "osservatore"): {"stats": ("INT", "SAG"), "grants_save_prof": False},
    ("keen mind", "mente acuta"): {"stats": ("INT",), "grants_save_prof": False},
    ("actor", "attore"): {"stats": ("CAR",), "grants_save_prof": False},
    ("athlete", "atleta"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
    ("tavern brawler", "rissaiolo", "attaccabrighe"): {"stats": ("FOR", "COS"), "grants_save_prof": False},
    ("fey touched", "toccato dalle fate"): {"stats": ("INT", "SAG", "CAR"), "grants_save_prof": False},
    ("shadow touched", "toccato dall'ombra"): {"stats": ("INT", "SAG", "CAR"), "grants_save_prof": False},
    ("telekinetic", "telecinetico"): {"stats": ("INT", "SAG", "CAR"), "grants_save_prof": False},
    ("telepathic", "telepatico"): {"stats": ("INT", "SAG", "CAR"), "grants_save_prof": False},
    ("chef", "cuoco"): {"stats": ("COS", "SAG"), "grants_save_prof": False},
    ("crusher", "frantumatore"): {"stats": ("FOR", "COS"), "grants_save_prof": False},
    ("piercer", "perforatore"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
    ("slasher", "squartatore"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
    ("elven accuracy", "precisione elfica"): {"stats": ("DES", "INT", "SAG", "CAR"), "grants_save_prof": False},
    ("lightly armored", "corazza leggera"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
    ("moderately armored", "corazza media"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
    ("heavily armored", "corazza pesante"): {"stats": ("FOR",), "grants_save_prof": False},
    ("weapon master", "maestro d'armi"): {"stats": ("FOR", "DES"), "grants_save_prof": False},
}


def get_half_feat_spec(feat_name: str) -> Optional[Dict[str, Any]]:
    """Restituisce la specifica {stats, grants_save_prof} se il talento è un Half-Feat (+1 caratteristica)."""
    low = str(feat_name or "").strip().lower()
    if not low:
        return None
    for keys, spec in HALF_FEAT_SPECS.items():
        if any(k in low for k in keys):
            return dict(spec)
    return None


def get_feat_ability_choices(feat_name: str) -> Tuple[str, ...]:
    """Restituisce le caratteristiche ammissibili (IT canonical) per un Half-Feat, o () se non applicabile."""
    spec = get_half_feat_spec(feat_name)
    return tuple(spec.get("stats", ())) if spec else ()


def entity_can_cast_spell(entity: Any, include_pact: bool = True) -> bool:
    """Verifica se l'entità possiede la capacità di lanciare almeno un incantesimo (Spellcasting / Pact Magic / Innate)."""
    sheet = _entity_sheet(entity)
    full_caster_keys = (
        ("mago", "wizard"),
        ("stregone", "sorcerer"),
        ("chierico", "cleric"),
        ("druido", "druid"),
        ("bardo", "bard"),
        ("artefice", "artificer"),
    )
    for keys in full_caster_keys:
        if entity_get_class_level(entity, *keys) >= 1:
            return True
    if include_pact and entity_get_class_level(entity, "warlock") >= 1:
        return True
    if entity_get_class_level(entity, "paladino", "paladin") >= 2:
        return True
    if entity_get_class_level(entity, "ranger") >= 2:
        return True

    sub_low = str(sheet.get("subclass") or getattr(entity, "subclass", "") or "").lower()
    subclasses_map = sheet.get("subclasses") if isinstance(sheet.get("subclasses"), dict) else getattr(entity, "subclasses", {}) or {}
    sub_blob = f"{sub_low} {' '.join(str(v).lower() for v in subclasses_map.values())}" if isinstance(subclasses_map, dict) else sub_low
    if entity_get_class_level(entity, "guerriero", "fighter") >= 3 and any(k in sub_blob for k in ("cavaliere mistico", "eldritch knight")):
        return True
    if entity_get_class_level(entity, "ladro", "rogue") >= 3 and any(k in sub_blob for k in ("mistificatore arcano", "arcane trickster")):
        return True

    slots = sheet.get("spell_slots") if isinstance(sheet.get("spell_slots"), dict) else getattr(entity, "spell_slots", {})
    if isinstance(slots, dict):
        for s_val in slots.values():
            mx = s_val.get("max", 0) if isinstance(s_val, dict) else (s_val[1] if isinstance(s_val, list) and len(s_val) >= 2 else 0)
            try:
                if int(mx or 0) > 0:
                    return True
            except (TypeError, ValueError):
                pass

    if include_pact:
        pact = sheet.get("pact_slots") if isinstance(sheet.get("pact_slots"), dict) else getattr(entity, "pact_slots", {})
        if isinstance(pact, dict):
            try:
                if int(pact.get("max", 0) or 0) > 0:
                    return True
            except (TypeError, ValueError):
                pass

    spellbook = sheet.get("spellbook") if isinstance(sheet.get("spellbook"), list) else getattr(entity, "spellbook", [])
    if isinstance(spellbook, list) and len(spellbook) > 0:
        return True

    if entity_has_keyword(
        entity,
        "spellcasting",
        "pact magic",
        "magia del patto",
        "iniziato alla magia",
        "magic initiate",
        "toccato dalle fate",
        "fey touched",
        "toccato dall'ombra",
        "shadow touched",
    ):
        return True
    return False


def entity_has_martial_weapon_proficiency(entity: Any) -> bool:
    """Verifica se l'entità ha competenza con almeno un'arma marziale (PHB / TCE Fighting Initiate)."""
    from common.character_schema import compute_character_proficiencies
    sheet = _entity_sheet(entity)
    prof_arg = sheet if isinstance(sheet, dict) and (sheet.get("classes") or sheet.get("char_class") or sheet.get("race")) else {
        "classes": getattr(entity, "classes", {}) if isinstance(getattr(entity, "classes", None), dict) else {},
        "char_class": str(getattr(entity, "char_class", "") or ""),
        "race": str(getattr(entity, "race", "") or ""),
        "subrace": str(getattr(entity, "subrace", "") or ""),
        "subclass": str(getattr(entity, "subclass", "") or ""),
        "feats": getattr(entity, "feats", []) or [],
        "features": getattr(entity, "features", "") or "",
    }
    w_profs = [str(w).lower() for w in compute_character_proficiencies(prof_arg).get("weapons", [])]
    explicit_list = sheet.get("weapon_proficiencies") if isinstance(sheet.get("weapon_proficiencies"), list) else getattr(entity, "weapon_proficiencies", [])
    nested_list = (sheet.get("proficiencies") or {}).get("weapons", []) if isinstance(sheet.get("proficiencies"), dict) else []
    for ew in list(explicit_list or []) + list(nested_list or []):
        ewl = str(ew).strip().lower()
        if ewl:
            w_profs.append(ewl)

    martial_markers = (
        "marzial", "martial", "tutte", "all",
        "spada lunga", "longsword", "spada corta", "shortsword", "stocco", "rapier",
        "scimitarra", "scimitar", "spadone", "greatsword", "ascia da battaglia", "battleaxe",
        "bipenne", "greataxe", "martello da guerra", "warhammer", "arco lungo", "longbow",
    )
    if any(any(m in wp for m in martial_markers) for wp in w_profs):
        return True
    sub_low = str(sheet.get("subclass") or getattr(entity, "subclass", "") or "").lower()
    if any(k in sub_low for k in ("valore", "valor", "spade", "swords", "guerra", "war", "tempesta", "tempest", "lama del patto", "hexblade", "kensei")):
        return True
    return False


def check_feat_prerequisites(entity: Any, feat_name_or_dict: Any) -> Tuple[bool, str]:
    """Valida i prerequisiti di un Talento 5e (incantesimi, caratteristiche >= 13, competenze, razza)."""
    from common.srd_offline import STANDARD_5E_FEATS_CATALOG
    prereq = ""
    if isinstance(feat_name_or_dict, dict):
        prereq = str(feat_name_or_dict.get("prerequisite", "") or "").strip()
    else:
        fname = str(feat_name_or_dict or "").strip()
        for entry in STANDARD_5E_FEATS_CATALOG:
            if entry.get("name", "").lower() == fname.lower():
                prereq = str(entry.get("prerequisite", "") or "").strip()
                break

    low = prereq.lower().strip()
    if not low or low in ("nessuno", "none", "-", "n/a"):
        return True, ""

    # 1. Prerequisiti incantesimi / Magia del Patto
    if any(k in low for k in ("incantesim", "spell", "magia del patto", "pact magic")):
        if not entity_can_cast_spell(entity, include_pact=True):
            return False, f"Prerequisito mancante: {prereq}"

    # 2. Prerequisiti punteggio caratteristica
    if ("intelligenza o saggezza" in low or "intelligence or wisdom" in low) and "13" in low:
        if _entity_attr_val(entity, "INT", 10) < 13 and _entity_attr_val(entity, "SAG", 10) < 13:
            return False, f"Richiede INT o SAG >= 13 (attuali: INT {_entity_attr_val(entity, 'INT', 10)}, SAG {_entity_attr_val(entity, 'SAG', 10)})."
    elif ("destrezza 13" in low or "dexterity 13" in low) and _entity_attr_val(entity, "DES", 10) < 13:
        return False, f"Richiede DES >= 13 (attuale: {_entity_attr_val(entity, 'DES', 10)})."
    elif ("forza 13" in low or "strength 13" in low) and _entity_attr_val(entity, "FOR", 10) < 13:
        return False, f"Richiede FOR >= 13 (attuale: {_entity_attr_val(entity, 'FOR', 10)})."
    elif ("carisma 13" in low or "charisma 13" in low) and _entity_attr_val(entity, "CAR", 10) < 13:
        return False, f"Richiede CAR >= 13 (attuale: {_entity_attr_val(entity, 'CAR', 10)})."

    # 3. Prerequisiti competenze armature / armi marziali
    armor_profs = get_entity_armor_proficiencies(entity)
    if ("armature pesanti" in low or "heavy armor" in low) and "heavy" not in armor_profs:
        return False, "Richiede competenza nelle armature pesanti."
    if ("armature medie" in low or "medium armor" in low) and "medium" not in armor_profs:
        return False, "Richiede competenza nelle armature medie."
    if ("armature leggere" in low or "light armor" in low) and "light" not in armor_profs:
        return False, "Richiede competenza nelle armature leggere."
    if ("arma marziale" in low or "martial weapon" in low) and not entity_has_martial_weapon_proficiency(entity):
        return False, "Richiede competenza in almeno un'arma marziale."

    # 4. Prerequisiti razziali
    sheet = _entity_sheet(entity)
    race_low = str(sheet.get("race") or getattr(entity, "race", "") or "").lower()
    if "elfo" in low or "mezzelfo" in low or "elf" in low:
        if not any(rk in race_low for rk in ("elf", "drow")):
            return False, "Richiede razza Elfo o Mezzelfo."
    if "halfling" in low and "halfling" not in race_low:
        return False, "Richiede razza Halfling."

    return True, ""


def apply_half_feat_bonus(character_or_dict: Any, feat_name: str, chosen_stat: Optional[str] = None) -> Dict[str, Any]:
    """Applica il +1 di un Half-Feat (+ eventuale competenza TS per Resiliente) e calcola PF retroattivi COS."""
    from common.character_schema import STAT_IT_TO_EN, canonical_stat_name
    spec = get_half_feat_spec(feat_name)
    if not spec:
        return {"applied": False, "stat": None, "old_val": None, "new_val": None, "save_prof_added": None, "retro_hp": 0}

    allowed = list(spec.get("stats", ()))
    is_dict = isinstance(character_or_dict, dict)
    attrs = character_or_dict.setdefault("attributes", {}) if is_dict else getattr(character_or_dict, "attributes", None)
    if not isinstance(attrs, dict):
        return {"applied": False, "stat": None, "old_val": None, "new_val": None, "save_prof_added": None, "retro_hp": 0}

    stat_it = canonical_stat_name(str(chosen_stat or ""), "it") if chosen_stat else ""
    if stat_it not in allowed:
        stat_it = next((s for s in allowed if int(attrs.get(s, 10) or 10) < 20), allowed[0])

    barb_lvl = entity_get_class_level(character_or_dict, "barbar", "barbarian")
    cap = 24 if (barb_lvl >= 20 and stat_it in ("FOR", "COS")) else 20
    old_val = int(attrs.get(stat_it, 10) or 10)
    new_val = min(cap, old_val + 1)
    attrs[stat_it] = new_val
    if is_dict and isinstance(character_or_dict.get("stats"), dict):
        en_k = STAT_IT_TO_EN.get(stat_it, stat_it)
        character_or_dict["stats"][en_k] = new_val

    lvl = max(1, int((character_or_dict.get("level", 1) if is_dict else getattr(character_or_dict, "level", 1)) or 1))
    retro_hp = 0
    if stat_it == "COS":
        delta_mod = (new_val - 10) // 2 - (old_val - 10) // 2
        if delta_mod > 0:
            retro_hp = lvl * delta_mod
            if is_dict:
                character_or_dict["hp_max"] = int(character_or_dict.get("hp_max", 10) or 10) + retro_hp
                character_or_dict["hp_current"] = int(character_or_dict.get("hp_current", 10) or 10) + retro_hp
            else:
                character_or_dict.hp_max = int(getattr(character_or_dict, "hp_max", 10) or 10) + retro_hp
                character_or_dict.hp_current = int(getattr(character_or_dict, "hp_current", 10) or 10) + retro_hp

    save_prof_added = None
    if spec.get("grants_save_prof"):
        if is_dict:
            profs = character_or_dict.setdefault("saving_throw_proficiencies", [])
        else:
            profs = getattr(character_or_dict, "saving_throw_proficiencies", None)
            if not isinstance(profs, list):
                profs = []
                setattr(character_or_dict, "saving_throw_proficiencies", profs)
        existing_canon = {canonical_stat_name(str(p), "it") for p in profs if p}
        if stat_it not in existing_canon:
            profs.append(stat_it)
            save_prof_added = stat_it

    return {
        "applied": True,
        "stat": stat_it,
        "old_val": old_val,
        "new_val": new_val,
        "save_prof_added": save_prof_added,
        "retro_hp": retro_hp,
    }
