"""
common/subclass_and_race_rules.py - Motore puro-Python D&D 5e (PHB / XGtE / TCE) per:
- Tratti Razziali meccanici (Brave Halfling, Gnome Cunning, Fey Ancestry, Dwarven Resilience,
  Resistenze Razziali implicite, Armatura Naturale Tortle CA 17, Corporatura Possente 2x, Halfling Nimbleness)
- Talenti mancanti (Observant +5 passivo, Elven Accuracy 3° d20, Crusher, Piercer, Slasher,
  Skulker, Dungeon Delver, Mobile/Swashbuckler no-OA)
- Privilegi attivi e passivi delle Sottoclassi mancanti across tutte le 12+1 classi
  (Berserker, Zealot, Lore, Valor, Nature, Trickery, Devotion, Vengeance, Ancients, Gloom Stalker,
  Hunter, Swashbuckler, Assassin, Arcane Trickster, Draconic, Divine Soul, Archfey, GOO, Hexblade,
  Conjuration, Enchantment, Illusion, Necromancy, Transmutation, War Magic, Open Hand, Shadow, Artificer Flash of Genius).
"""

from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from common.dnd5e_tables import (
    entity_find_resource,
    entity_get_class_level,
    entity_get_total_level,
    entity_has_keyword,
    entity_spend_resource,
)


# ==============================================================================
# HELPER INTERNI D'ENTITÀ (Senza duplicare common.feats_and_classes)
# ==============================================================================

def _sheet(entity: Any) -> Dict[str, Any]:
    if isinstance(entity, dict):
        return entity
    fs = getattr(entity, "full_sheet", None)
    return fs if isinstance(fs, dict) else {}


def _race_str(entity: Any) -> str:
    sh = _sheet(entity)
    return str(sh.get("race") or getattr(entity, "race", "") or "").strip().lower()


def _subrace_str(entity: Any) -> str:
    sh = _sheet(entity)
    return str(sh.get("subrace") or getattr(entity, "subrace", "") or "").strip().lower()


def _subclass_text(entity: Any) -> str:
    sh = _sheet(entity)
    parts: List[str] = []
    for src in (
        sh.get("subclass"),
        getattr(entity, "subclass", None),
        sh.get("features"),
        getattr(entity, "features", None),
    ):
        if isinstance(src, str) and src.strip():
            parts.append(src.lower())
        elif isinstance(src, list):
            parts.extend(str(x).lower() for x in src)
    subs = sh.get("subclasses") if isinstance(sh.get("subclasses"), dict) else getattr(entity, "subclasses", None)
    if isinstance(subs, dict):
        parts.extend(str(v).lower() for v in subs.values() if v)
    return " | ".join(parts)


def _has_subclass(entity: Any, *keywords: str) -> bool:
    txt = _subclass_text(entity)
    if any(k.lower() in txt for k in keywords if k):
        return True
    return entity_has_keyword(entity, *keywords)


def _attr_mod(entity: Any, stat: str, default: int = 10) -> int:
    from common.item_modifiers import get_effective_attribute_from_dict
    try:
        val = int(get_effective_attribute_from_dict(entity, stat))
    except Exception:
        val = default
    return (val - 10) // 2


def _pb(entity: Any) -> int:
    lvl = max(1, int(entity_get_total_level(entity) or 1))
    return ((lvl - 1) // 4) + 2


def _has_condition(entity: Any, *tokens: str) -> bool:
    conds = getattr(entity, "conditions", None)
    if conds is None:
        conds = _sheet(entity).get("conditions", [])
    joined = " ".join(str(c).lower() for c in (conds or []))
    return any(t.lower() in joined for t in tokens)


# ==============================================================================
# 1. TRATTI RAZZIALI MECCANICI (PHB / VGtM / MPMM)
# ==============================================================================

def get_racial_save_adv_reasons(
    entity: Any,
    save_stat: str,
    is_magic: bool = False,
    effect_tags: Tuple[str, ...] = (),
) -> Dict[str, Any]:
    """
    Valuta tutti i vantaggi/immunità razziali ai Tiri Salvezza (PHB):
    - Halfling (Coraggioso / Brave): Vantaggio vs Spaventato (Frightened)
    - Gnomo (Astuzia Gnomesca / Gnome Cunning): Vantaggio su INT/SAG/CAR contro magia
    - Elfo / Mezzelfo (Retaggio Fatato / Fey Ancestry): Vantaggio vs Affascinato (Charmed) + Immunità Sonno magico
    - Nano (Resilienza Nanica / Dwarven Resilience): Vantaggio vs Veleno (Poison)
    - Yuan-Ti / Satiro (Resistenza alla Magia): Vantaggio contro tutti gli incantesimi/effetti magici
    """
    race = _race_str(entity)
    sub = _subrace_str(entity)
    tags_low = " ".join(str(t).lower() for t in (effect_tags or ())).strip()
    stat_up = str(save_stat or "").strip().upper()[:3]

    adv = False
    reasons: List[str] = []
    magic_sleep_immune = False

    if "halfling" in race or entity_has_keyword(entity, "coraggioso", "brave"):
        if any(k in tags_low for k in ("fright", "spavent", "fear", "paura")):
            adv = True
            reasons.append("Coraggioso (Halfling)")

    if "gnom" in race or entity_has_keyword(entity, "astuzia gnomesca", "gnome cunning"):
        if (is_magic or any(k in tags_low for k in ("magic", "magia", "spell", "incantesim"))) and stat_up in ("INT", "SAG", "WIS", "CAR", "CHA"):
            adv = True
            reasons.append("Astuzia Gnomesca")

    if any(k in race for k in ("elf", "drow", "eladrin", "shadar-kai")) or entity_has_keyword(entity, "retaggio fatato", "fey ancestry"):
        magic_sleep_immune = True
        if any(k in tags_low for k in ("charm", "affascinat", "ammali", "fey")):
            adv = True
            reasons.append("Retaggio Fatato")

    if any(k in race for k in ("nan", "dwarf")) or entity_has_keyword(entity, "resilienza nanica", "dwarven resilience"):
        if any(k in tags_low for k in ("poison", "velen", "avvelen")):
            adv = True
            reasons.append("Resilienza Nanica")

    if any(k in race or k in sub for k in ("yuan-ti", "satyr", "satiro")) or entity_has_keyword(entity, "resistenza alla magia", "magic resistance"):
        if is_magic or any(k in tags_low for k in ("magic", "magia", "spell", "incantesim")):
            adv = True
            reasons.append("Resistenza alla Magia")

    return {
        "advantage": adv,
        "reasons": reasons,
        "magic_sleep_immune": magic_sleep_immune,
    }


_DRAGONBORN_ANCESTRY_DAMAGE: Dict[str, str] = {
    "rosso": "fuoco", "red": "fuoco", "oro": "fuoco", "gold": "fuoco", "ottone": "fuoco", "brass": "fuoco",
    "bianco": "freddo", "white": "freddo", "argento": "freddo", "silver": "freddo",
    "blu": "fulmine", "blue": "fulmine", "bronzo": "fulmine", "bronze": "fulmine",
    "nero": "acido", "black": "acido", "rame": "acido", "copper": "acido",
    "verde": "veleno", "green": "veleno",
}


def get_implicit_racial_resistances(entity: Any) -> Set[str]:
    """Restituisce i tipi di danno (IT+EN normalizzati) per cui la razza conferisce Resistenza innata."""
    race = _race_str(entity)
    sub = _subrace_str(entity)
    sh = _sheet(entity)
    feats = " ".join(str(x).lower() for x in (sh.get("features") if isinstance(sh.get("features"), list) else [sh.get("features", "")]))
    res: Set[str] = set()

    if any(k in race for k in ("nan", "dwarf")) or entity_has_keyword(entity, "resilienza nanica", "dwarven resilience"):
        res.update({"veleno", "poison"})

    if "tiefling" in race or entity_has_keyword(entity, "resistenza infernale", "hellish resistance"):
        res.update({"fuoco", "fire"})

    if "aasimar" in race or entity_has_keyword(entity, "resistenza celestiale", "celestial resistance"):
        res.update({"necrotico", "necrotic", "radiante", "radiant"})

    if any(k in race for k in ("triton", "goliath")):
        if "goliath" in race or entity_has_keyword(entity, "nato tra i monti", "mountain born"):
            res.update({"freddo", "cold"})
        if "triton" in race:
            res.update({"freddo", "cold"})

    if any(k in race for k in ("genasi",)) and any(k in sub or k in race for k in ("fuoco", "fire")):
        res.update({"fuoco", "fire"})
    if any(k in race for k in ("genasi",)) and any(k in sub or k in race for k in ("acqua", "water")):
        res.update({"acido", "acid"})

    if any(k in race for k in ("dragonid", "dragonborn")):
        blob = f"{race} {sub} {feats} {sh.get('draconic_ancestry', '')}".lower()
        matched_it = None
        for color, dmg_it in _DRAGONBORN_ANCESTRY_DAMAGE.items():
            if color in blob:
                matched_it = dmg_it
                break
        if matched_it == "fuoco":
            res.update({"fuoco", "fire"})
        elif matched_it == "freddo":
            res.update({"freddo", "cold"})
        elif matched_it == "fulmine":
            res.update({"fulmine", "lightning"})
        elif matched_it == "acido":
            res.update({"acido", "acid"})
        elif matched_it == "veleno":
            res.update({"veleno", "poison"})

    if any(k in race or k in sub for k in ("kalashtar", "gith")):
        res.update({"psichico", "psychic"})
    if any(k in race or k in sub for k in ("yuan-ti",)):
        # PHB/VGtM/MPMM immunity/resistance vs poison
        res.update({"veleno", "poison"})

    return res


def apply_tortle_natural_armor(entity: Any, current_ac: int, shield_bonus: int = 0) -> Tuple[int, str]:
    """Tortle Natural Armor: CA base 17 (senza modificatore DES) + eventuale scudo."""
    race = _race_str(entity)
    if "tortle" in race or entity_has_keyword(entity, "corazza naturale tortle", "natural armor 17"):
        tortle_ac = 17 + max(0, int(shield_bonus or 0))
        if tortle_ac >= current_ac:
            return tortle_ac, f"Corazza Naturale Tortle (17 + scudo {shield_bonus})"
    return current_ac, ""


def get_powerful_build_multiplier(entity: Any) -> float:
    """Corporatura Possente (Goliath, Firbolg, Orco puro, Bugbear, Loxodon, Centauro, Minotauro): capacità di carico x2."""
    race = _race_str(entity)
    if entity_has_keyword(entity, "corporatura possente", "powerful build"):
        return 2.0
    if any(k in race for k in ("goliath", "firbolg", "bugbear", "loxodon", "centaur", "minotaur")):
        return 2.0
    if ("orc" in race or "orco" in race) and "mezz" not in race and "half" not in race:
        return 2.0
    return 1.0


def has_halfling_nimbleness(entity: Any) -> bool:
    """Agilità Halfling (PHB p. 28): consente di attraversare lo spazio di creature di una taglia superiore."""
    race = _race_str(entity)
    return "halfling" in race or entity_has_keyword(entity, "agilità halfling", "halfling nimbleness")


# ==============================================================================
# 2. TALENTI MANCANTI (PHB / XGtE / TCE)
# ==============================================================================

def get_passive_observant_bonus(entity: Any, skill_key: str) -> int:
    """Osservatore (Observant, PHB p. 168): +5 a Percezione Passiva e Indagare Passivo."""
    if not entity_has_keyword(entity, "osservatore", "observant"):
        return 0
    sk = str(skill_key or "").strip().lower()
    if any(k in sk for k in ("percez", "percept", "indag", "investig")):
        return 5
    return 0


def get_dungeon_delver_bonuses(entity: Any) -> Dict[str, Any]:
    """Esploratore di Dungeon (PHB p. 166): Vantaggio porte segrete, Vantaggio TS trappole, Resistenza danni trappole."""
    has = entity_has_keyword(entity, "esploratore di dungeon", "dungeon delver")
    return {
        "has_feat": has,
        "secret_door_adv": has,
        "trap_save_adv": has,
        "trap_damage_resistance": has,
    }


def check_elven_accuracy_eligible(attacker: Any, has_advantage: bool, stat_used: str = "DES") -> bool:
    """Precisione Elfica (XGtE p. 74): con Vantaggio su DES/INT/SAG/CAR, tira un 3° d20."""
    if not has_advantage:
        return False
    if not entity_has_keyword(attacker, "precisione elfica", "elven accuracy"):
        return False
    st = str(stat_used or "").strip().upper()[:3]
    return st in ("DES", "DEX", "INT", "SAG", "WIS", "CAR", "CHA")


def has_skulker_hide_on_miss(attacker: Any) -> bool:
    """Esploratore Furtivo (Skulker, PHB p. 170): mancare con un attacco a distanza mentre si è nascosti non rivela la posizione."""
    return entity_has_keyword(attacker, "esploratore furtivo", "skulker")


def apply_crusher_piercer_slasher_on_hit(
    attacker: Any,
    target: Any,
    damage_type: str,
    damage_rolls: Optional[List[int]] = None,
    die_sides: int = 8,
    is_crit: bool = False,
) -> Dict[str, Any]:
    """
    TCE p. 79-81: Applica gli effetti 1/turno e su Critico di Crusher, Piercer e Slasher.
    Usa `attacker.turn_feat_used` (resettato ad ogni nuovo turno dell'attaccante).
    """
    dt = str(damage_type or "").lower()
    used = getattr(attacker, "turn_feat_used", None)
    if not isinstance(used, dict):
        used = {}
        try:
            attacker.turn_feat_used = used
        except Exception:
            pass

    out: Dict[str, Any] = {
        "push_hexes": 0,
        "crusher_crit_adv": False,
        "piercer_reroll_delta": 0,
        "piercer_extra_crit_die": 0,
        "slasher_slow_ft": 0,
        "slasher_crit_disadv": False,
        "notes": [],
    }

    # CRUSHER (Frantumatore): Contundenti
    if any(k in dt for k in ("contundent", "bludgeon")) and entity_has_keyword(attacker, "frantumatore", "crusher"):
        if not used.get("crusher"):
            used["crusher"] = True
            out["push_hexes"] = 1
            out["notes"].append("💥 Frantumatore: bersaglio spinto di 5 ft (1 hex)!")
        if is_crit and target is not None:
            out["crusher_crit_adv"] = True
            try:
                target.crusher_crit_vulnerable = True
            except Exception:
                pass
            out["notes"].append("💥 Frantumatore Critico: gli attacchi contro il bersaglio hanno Vantaggio fino al tuo prossimo turno!")

    # PIERCER (Perforatore): Perforanti
    if any(k in dt for k in ("perforant", "pierc")) and entity_has_keyword(attacker, "perforatore", "piercer"):
        if not used.get("piercer") and damage_rolls:
            low = min(damage_rolls)
            if low < die_sides:
                reroll = random.randint(1, max(4, int(die_sides)))
                used["piercer"] = True
                if reroll > low:
                    out["piercer_reroll_delta"] = reroll - low
                    out["notes"].append(f"🎯 Perforatore: ritira dado minimo {low}→{reroll} (+{reroll - low})")
        if is_crit:
            extra = random.randint(1, max(4, int(die_sides)))
            out["piercer_extra_crit_die"] = extra
            out["notes"].append(f"🎯 Perforatore Critico: +1 dado extra (+{extra} danni)")

    # SLASHER (Fendente): Taglienti
    if any(k in dt for k in ("taglient", "slash")) and entity_has_keyword(attacker, "fendente", "slasher"):
        if not used.get("slasher") and target is not None:
            used["slasher"] = True
            out["slasher_slow_ft"] = 10
            try:
                target.slasher_slow_ft = 10
            except Exception:
                pass
            out["notes"].append("⚔️ Fendente: velocità del bersaglio ridotta di 10 ft fino al tuo prossimo turno!")
        if is_crit and target is not None:
            out["slasher_crit_disadv"] = True
            try:
                target.slasher_crit_disadvantage = True
            except Exception:
                pass
            out["notes"].append("⚔️ Fendente Critico: il bersaglio ha Svantaggio ai TxC fino al tuo prossimo turno!")

    return out


def register_melee_attack_no_oa(attacker: Any, target: Any) -> bool:
    """
    Mobile (PHB p. 168) / Swashbuckler Fancy Footwork (XGtE p. 47):
    Dopo aver effettuato un attacco in mischia contro una creatura, essa non può compiere
    Attacchi di Opportunità contro di te per il resto del turno (a prescindere dal colpire).
    """
    if not attacker or not target:
        return False
    swash = entity_get_class_level(attacker, "ladro", "rogue") >= 3 and _has_subclass(attacker, "spadaccino", "swashbuckler")
    mob = entity_has_keyword(attacker, "mobile", "mobilità")
    if not (swash or mob):
        return False
    no_oa = getattr(attacker, "no_oa_targets_this_turn", None)
    if not isinstance(no_oa, set):
        no_oa = set()
        try:
            attacker.no_oa_targets_this_turn = no_oa
        except Exception:
            return False
    t_name = getattr(target, "name", "")
    if t_name:
        no_oa.add(t_name)
    return True


def has_no_oa_against(mover: Any, reactor: Any) -> bool:
    """Verifica se `reactor` è bloccato dal fare OA contro `mover` in questo turno."""
    no_oa = getattr(mover, "no_oa_targets_this_turn", None)
    if isinstance(no_oa, set) and getattr(reactor, "name", "") in no_oa:
        return True
    if getattr(reactor, "open_hand_no_reactions", False):
        return True
    return False


# ==============================================================================
# 3. SOTTOCLASSI: PASSIVI INIZIATIVA / TXC / DANNI / TS / DIFESA
# ==============================================================================

def get_subclass_initiative_bonus(entity: Any) -> Tuple[int, List[str]]:
    """
    Bonus all'Iniziativa da sottoclassi:
    - Ranger Gloom Stalker (XGtE p. 42) Lv 3+: +mod SAG
    - Ladro Swashbuckler (XGtE p. 47) Lv 3+: +mod CAR
    - Mago War Magic (XGtE p. 59) / Chronurgy Lv 2+: +mod INT
    """
    bonus = 0
    notes: List[str] = []

    if entity_get_class_level(entity, "ranger") >= 3 and _has_subclass(entity, "gloom stalker", "oscurità", "tenebre"):
        w = _attr_mod(entity, "SAG")
        bonus += w
        notes.append(f"Gloom Stalker ({w:+d})")

    if entity_get_class_level(entity, "ladro", "rogue") >= 3 and _has_subclass(entity, "spadaccino", "swashbuckler"):
        c = _attr_mod(entity, "CAR")
        bonus += c
        notes.append(f"Swashbuckler ({c:+d})")

    if entity_get_class_level(entity, "mago", "wizard") >= 2 and _has_subclass(entity, "war magic", "magia della guerra", "cronurg", "chronurg"):
        i = _attr_mod(entity, "INT")
        bonus += i
        notes.append(f"Tactical Wit ({i:+d})")

    return bonus, notes


def get_subclass_attack_mods(
    attacker: Any,
    target: Any,
    game_state: Any = None,
    is_melee: bool = True,
    distance_hexes: int = 1,
) -> Dict[str, Any]:
    """Restituisce modificatori al TxC da privilegi di sottoclasse e condizioni tattiche di talento."""
    bonus = 0
    adv = False
    disadv = False
    crit_min = 20
    auto_crit_on_hit = False
    swash_1v1_sneak = False
    notes: List[str] = []

    t_name = getattr(target, "name", "") if target else ""

    # Crusher crit vulnerability / Slasher crit disadvantage sul bersaglio
    if target is not None and getattr(target, "crusher_crit_vulnerable", False):
        adv = True
        notes.append("Frantumatore Critico (Vantaggio)")
    if getattr(attacker, "slasher_crit_disadvantage", False):
        disadv = True
        notes.append("Fendente Critico (Svantaggio)")

    # Paladino Devozione - Arma Sacra (+CAR al TxC)
    if getattr(attacker, "sacred_weapon_active", False):
        cha_b = max(1, _attr_mod(attacker, "CAR"))
        bonus += cha_b
        notes.append(f"Arma Sacra (+{cha_b})")

    # Paladino Vendetta - Voto di Inimicizia (Vantaggio)
    if t_name and getattr(attacker, "vow_of_enmity_target", "") == t_name:
        adv = True
        notes.append("Voto di Inimicizia (Vantaggio)")

    # Warlock Hexblade's Curse (Critico 19-20)
    if t_name and getattr(attacker, "hexblade_curse_target", "") == t_name:
        crit_min = min(crit_min, 19)
        notes.append("Maledizione Hexblade (Crit 19-20)")

    # Monaco Via dell'Ombra - Passo d'Ombra (Vantaggio prossimo attacco in mischia)
    if is_melee and getattr(attacker, "shadow_step_advantage", False):
        adv = True
        attacker.shadow_step_advantage = False
        notes.append("Passo d'Ombra (Vantaggio)")

    # Ladro Assassino Lv 3+: Vantaggio vs chi non ha ancora agito, Crit automatico vs Sorpreso
    if entity_get_class_level(attacker, "ladro", "rogue") >= 3 and _has_subclass(attacker, "assassin"):
        if target is not None:
            if getattr(target, "is_surprised", False) or _has_condition(target, "sorpres", "surpris"):
                auto_crit_on_hit = True
                adv = True
                notes.append("Assassino (Critico Automatico vs Sorpreso)")
            elif not getattr(target, "has_acted_in_combat", True):
                adv = True
                notes.append("Assassino (Vantaggio vs bersaglio che non ha ancora agito)")

    # Ladro Swashbuckler Lv 3+: Rakish Audacity (Sneak Attack 1v1 in mischia se nessuna altra creatura entro 1 hex dall'attaccante)
    if is_melee and distance_hexes <= 1 and entity_get_class_level(attacker, "ladro", "rogue") >= 3 and _has_subclass(attacker, "spadaccino", "swashbuckler"):
        if game_state and target is not None and getattr(attacker, "position", None) and getattr(target, "position", None):
            from common.hex_utils import Hex, grid_distance_3d
            gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
            a_hex = Hex(attacker.position[0], attacker.position[1])
            others_near = False
            for other in getattr(game_state, "players", []):
                if other is attacker or other is target or getattr(other, "hp", 0) <= 0:
                    continue
                if getattr(other, "position", None):
                    if grid_distance_3d(a_hex, Hex(other.position[0], other.position[1]), getattr(attacker, "elevation", 0), getattr(other, "elevation", 0), grid_type=gtype) <= 1.01:
                        others_near = True
                        break
            if not others_near and not disadv:
                swash_1v1_sneak = True
                notes.append("Audacia Spavalda (Attacco Furtivo 1v1)")
        else:
            swash_1v1_sneak = True

    return {
        "attack_bonus": bonus,
        "advantage": adv,
        "disadvantage": disadv,
        "crit_threshold": crit_min,
        "auto_crit": auto_crit_on_hit,
        "swashbuckler_sneak": swash_1v1_sneak,
        "notes": notes,
    }


def get_subclass_damage_mods(
    attacker: Any,
    target: Any,
    damage_type: str = "",
    is_spell: bool = False,
    is_cantrip: bool = False,
    is_weapon_attack: bool = True,
    round_number: int = 1,
) -> Dict[str, Any]:
    """
    Restituisce dadi bonus / bonus flat ai danni da Sottoclassi:
    - Barbaro Zelota Lv 3+ (Furia Divina: +1d6 + floor(barb/2) radiante/necrotico 1/turno in Ira)
    - Ranger Gloom Stalker Lv 3+ (Imboscata Letale: +1d8 al round 1)
    - Ranger Cacciatore Lv 3+ (Sterminatore di Colossi: +1d8 vs bersaglio ferito 1/turno)
    - Warlock Hexblade's Curse (+PB danni su bersaglio maledetto)
    - Stregone Draconico Lv 6+ (+mod CAR su incantesimi dell'elemento draconico)
    - Chierico Luce/Arcana Lv 8+ (+mod SAG sui trucchetti)
    - Chierico Guerra/Tempesta/Natura/Vita/Forgia Lv 8+/14+ (Colpo Divino: +1d8/+2d8 su arma 1/turno)
    """
    used = getattr(attacker, "turn_feat_used", None)
    if not isinstance(used, dict):
        used = {}
        try:
            attacker.turn_feat_used = used
        except Exception:
            pass

    flat_bonus = 0
    dice_formulas: List[Tuple[str, str]] = []  # (formula, damage_type)
    notes: List[str] = []

    t_name = getattr(target, "name", "") if target else ""

    # Warlock Hexblade's Curse (+PB danni)
    if t_name and getattr(attacker, "hexblade_curse_target", "") == t_name:
        pb = _pb(attacker)
        flat_bonus += pb
        notes.append(f"Hexblade's Curse (+{pb})")

    if is_weapon_attack:
        # Barbaro Zelota Lv 3+ - Furia Divina (1/turno in Ira)
        barb_lvl = entity_get_class_level(attacker, "barbar", "barbarian")
        if barb_lvl >= 3 and getattr(attacker, "is_raging", False) and _has_subclass(attacker, "zelota", "zealot"):
            if not used.get("divine_fury"):
                used["divine_fury"] = True
                extra_flat = barb_lvl // 2
                flat_bonus += extra_flat
                dice_formulas.append(("1d6", "radiante"))
                notes.append(f"Furia Divina Zelota (+1d6+{extra_flat})")

        # Ranger Gloom Stalker Lv 3+ - Dread Ambusher (Round 1)
        ranger_lvl = entity_get_class_level(attacker, "ranger")
        if ranger_lvl >= 3 and round_number == 1 and _has_subclass(attacker, "gloom stalker", "oscurità", "tenebre"):
            if not used.get("dread_ambusher_dmg"):
                used["dread_ambusher_dmg"] = True
                dice_formulas.append(("1d8", damage_type or "perforante"))
                notes.append("Imboscata Letale (+1d8)")

        # Ranger Hunter Lv 3+ - Sterminatore di Colossi (bersaglio sotto max HP, 1/turno)
        if ranger_lvl >= 3 and target is not None and getattr(target, "hp", 1) < getattr(target, "max_hp", 1) and _has_subclass(attacker, "cacciatore", "hunter", "coloss"):
            if not used.get("colossus_slayer"):
                used["colossus_slayer"] = True
                dice_formulas.append(("1d8", damage_type or "tagliente"))
                notes.append("Sterminatore di Colossi (+1d8)")

        # Chierico Lv 8+/14+ - Colpo Divino (1/turno)
        cleric_lvl = entity_get_class_level(attacker, "chierico", "cleric")
        if cleric_lvl >= 8 and _has_subclass(attacker, "guerra", "war", "tempesta", "tempest", "natura", "nature", "vita", "life", "forgia", "forge", "colpo divino", "divine strike"):
            if not used.get("divine_strike"):
                used["divine_strike"] = True
                d_str = "2d8" if cleric_lvl >= 14 else "1d8"
                dt_sub = "radiante" if _has_subclass(attacker, "vita", "life") else ("fuoco" if _has_subclass(attacker, "forgia", "forge") else ("fulmine" if _has_subclass(attacker, "tempesta", "tempest") else (damage_type or "radiante")))
                dice_formulas.append((d_str, dt_sub))
                notes.append(f"Colpo Divino (+{d_str} {dt_sub})")

    if is_spell:
        # Stregone Draconico Lv 6+ (+CAR a incantesimi dell'elemento draconico)
        sorc_lvl = entity_get_class_level(attacker, "stregone", "sorcerer")
        if sorc_lvl >= 6 and _has_subclass(attacker, "draconic", "dracon"):
            sh = _sheet(attacker)
            elem_hint = str(sh.get("draconic_element") or sh.get("draconic_ancestry") or _subclass_text(attacker)).lower()
            dt_low = str(damage_type or "").lower()
            elem_ok = (not dt_low) or any(pair[0] in elem_hint and pair[1] in dt_low for pair in (
                ("fuoco", "fuoc"), ("fire", "fire"), ("freddo", "fredd"), ("cold", "cold"),
                ("fulmin", "fulm"), ("lightn", "lightn"), ("acid", "acid"), ("velen", "velen"), ("poison", "poison"),
            ))
            if elem_ok and not used.get("elemental_affinity"):
                used["elemental_affinity"] = True
                cha_b = max(1, _attr_mod(attacker, "CAR"))
                flat_bonus += cha_b
                notes.append(f"Affinità Elementale Draconica (+{cha_b})")

        # Chierico Luce/Arcana/Tomba Lv 8+ - Potent Spellcasting (+SAG sui trucchetti)
        if is_cantrip and entity_get_class_level(attacker, "chierico", "cleric") >= 8 and _has_subclass(attacker, "luce", "light", "conoscenza", "knowledge", "arcana", "tomba", "grave", "potente", "potent spellcasting"):
            wis_b = max(1, _attr_mod(attacker, "SAG"))
            flat_bonus += wis_b
            notes.append(f"Incantatore Potente (+{wis_b})")

    return {
        "flat_bonus": flat_bonus,
        "dice_formulas": dice_formulas,
        "notes": notes,
    }


def get_subclass_save_mods(
    defender: Any,
    caster_or_attacker: Any = None,
    save_stat: str = "SAG",
    is_spell: bool = False,
    effect_tags: Tuple[str, ...] = (),
    game_state: Any = None,
) -> Dict[str, Any]:
    """
    Restituisce immunità/vantaggi/svantaggi su TS da Sottoclassi:
    - Barbaro Berserker Lv 6+: Ira Incosciente (Immune a Affascinato/Spaventato in Ira)
    - Paladino Devozione Lv 7+: Aura di Devozione (Immune a Affascinato entro 10/30 ft)
    - Ladro Mistificatore Arcano Lv 9+: Imboscata Magica (Bersaglio ha Svantaggio al TS se l'attaccante è Nascosto)
    """
    tags_low = " ".join(str(t).lower() for t in (effect_tags or ())).strip()
    immune = False
    adv = False
    disadv = False
    notes: List[str] = []

    if getattr(defender, "is_raging", False) and entity_get_class_level(defender, "barbar", "barbarian") >= 6 and _has_subclass(defender, "berserker"):
        if any(k in tags_low for k in ("charm", "affascinat", "fright", "spavent", "fear")):
            immune = True
            notes.append("Ira Incosciente (Berserker Lv6+: Immune)")

    if any(k in tags_low for k in ("charm", "affascinat")) and has_paladin_aura_of_devotion(defender, game_state):
        immune = True
        notes.append("Aura di Devozione (Immune ad Affascinato)")

    if is_spell and caster_or_attacker is not None:
        if entity_get_class_level(caster_or_attacker, "ladro", "rogue") >= 9 and _has_subclass(caster_or_attacker, "mistificat", "arcane trickster"):
            if getattr(caster_or_attacker, "is_hidden", False) or _has_condition(caster_or_attacker, "nascos", "hidden"):
                disadv = True
                notes.append("Imboscata Magica (Ladro Lv9+: Svantaggio al TS)")

    return {"immune": immune, "advantage": adv, "disadvantage": disadv, "notes": notes}


def has_paladin_aura_of_devotion(target_player: Any, game_state: Any) -> bool:
    """Paladino Devozione Lv 7+ (PHB p. 86): alleati entro 10/30 ft immuni ad Affascinato."""
    if not target_player:
        return False
    if entity_get_class_level(target_player, "paladin", "paladino") >= 7 and _has_subclass(target_player, "devozion", "devotion") and getattr(target_player, "hp", 0) > 0:
        return True
    if not game_state:
        return False
    t_pos = getattr(target_player, "position", None)
    tgt_p = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
    from common.hex_utils import Hex, grid_distance_3d
    gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    for p in getattr(game_state, "players", []):
        pal_lvl = entity_get_class_level(p, "paladin", "paladino")
        if pal_lvl < 7 or getattr(p, "hp", 0) <= 0 or not _has_subclass(p, "devozion", "devotion"):
            continue
        if bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None)) != tgt_p:
            continue
        radius = 6.0 if pal_lvl >= 18 else 2.0
        if p is target_player:
            return True
        if t_pos and getattr(p, "position", None):
            if grid_distance_3d(Hex(p.position[0], p.position[1]), Hex(t_pos[0], t_pos[1]), getattr(p, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=gtype) <= radius:
                return True
    return False


def has_aura_of_warding_spell_resistance(target_player: Any, game_state: Any) -> bool:
    """Paladino Antichi Lv 7+ (PHB p. 87): alleati entro 10/30 ft hanno Resistenza ai danni da incantesimo."""
    if not target_player:
        return False
    if entity_get_class_level(target_player, "paladin", "paladino") >= 7 and _has_subclass(target_player, "antich", "ancients") and getattr(target_player, "hp", 0) > 0:
        return True
    if not game_state:
        return False
    t_pos = getattr(target_player, "position", None)
    tgt_p = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
    from common.hex_utils import Hex, grid_distance_3d
    gtype = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
    for p in getattr(game_state, "players", []):
        pal_lvl = entity_get_class_level(p, "paladin", "paladino")
        if pal_lvl < 7 or getattr(p, "hp", 0) <= 0 or not _has_subclass(p, "antich", "ancients"):
            continue
        if bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None)) != tgt_p:
            continue
        radius = 6.0 if pal_lvl >= 18 else 2.0
        if p is target_player:
            return True
        if t_pos and getattr(p, "position", None):
            if grid_distance_3d(Hex(p.position[0], p.position[1]), Hex(t_pos[0], t_pos[1]), getattr(p, "elevation", 0), getattr(target_player, "elevation", 0), grid_type=gtype) <= radius:
                return True
    return False


def apply_grim_harvest_on_kill(attacker: Any, victim: Any, spell_level: int, spell_school: str = "") -> int:
    """Mago Necromanzia Lv 2+ (PHB p. 118): Uccidendo una creatura con incantesimo Lv 1+, cura 2*lvl (o 3*lvl se Necromanzia)."""
    if not attacker or not victim or spell_level <= 0 or getattr(victim, "hp", 1) > 0:
        return 0
    if entity_get_class_level(attacker, "mago", "wizard") < 2 or not _has_subclass(attacker, "necroman"):
        return 0
    v_type = str(getattr(victim, "creature_type", "") or _sheet(victim).get("creature_type", "")).lower()
    if any(k in v_type for k in ("non morto", "undead", "costrutto", "construct")):
        return 0
    mult = 3 if "necrom" in str(spell_school or "").lower() else 2
    heal = mult * int(spell_level)
    cur_hp = int(getattr(attacker, "hp", 0) or 0)
    max_hp = int(getattr(attacker, "max_hp", cur_hp) or cur_hp)
    new_hp = min(max_hp, cur_hp + heal)
    attacker.hp = new_hp
    return max(0, new_hp - cur_hp)


# ==============================================================================
# 4. PRIVILEGI ATTIVI DI SOTTOCLASSE
# ==============================================================================

def handle_subclass_active_power(
    player: Any,
    power_id: str,
    game_state: Any = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Risolve i privilegi attivi di sottoclasse e restituisce dict {ok, log, broadcast}.
    """
    params = params if isinstance(params, dict) else {}
    pid = str(power_id or "").strip().lower()
    target_name = str(params.get("target") or params.get("target_name") or "").strip()
    target = game_state.get_player(target_name) if (game_state and target_name and hasattr(game_state, "get_player")) else None

    if pid == "frenzy_attack":
        if entity_get_class_level(player, "barbar", "barbarian") < 3 or not _has_subclass(player, "berserker"):
            return {"ok": False, "log": "Richiede Barbaro Berserker Lv 3+."}
        if not getattr(player, "is_raging", False):
            return {"ok": False, "log": "Frenesia richiede che tu sia in Ira."}
        if not getattr(player, "has_bonus_action", True):
            return {"ok": False, "log": "Azione Bonus già consumata."}
        player.has_bonus_action = False
        player.frenzy_exhaustion_pending = True
        return {
            "ok": True,
            "log": f"🪓 [FRENESIA - {player.name}] Effettua 1 attacco extra con Azione Bonus (1 livello di Indebolimento al termine dell'Ira).",
        }

    if pid == "cutting_words":
        bard_lvl = entity_get_class_level(player, "bardo", "bard")
        if bard_lvl < 3 or not _has_subclass(player, "sapienz", "lore"):
            return {"ok": False, "log": "Richiede Bardo Collegio della Sapienza Lv 3+."}
        ok, cur, mx = entity_spend_resource(player, ("ispirazione", "bardic inspiration", "bardic_inspiration"), 1)
        if not ok:
            return {"ok": False, "log": f"Nessun uso di Ispirazione Bardica disponibile ({cur}/{mx})."}
        die = 6 if bard_lvl < 5 else (8 if bard_lvl < 10 else (10 if bard_lvl < 15 else 12))
        roll = random.randint(1, die)
        if target is not None:
            target.cutting_words_penalty = roll
        return {
            "ok": True,
            "roll": roll,
            "log": f"🎭 [PAROLE TAGLIENTI] {player.name} spende 1 Ispirazione ({cur}/{mx}) in Reazione: -{roll} (1d{die}) al tiro di {target_name or 'bersaglio'}!",
        }

    if pid == "combat_inspiration":
        bard_lvl = entity_get_class_level(player, "bardo", "bard")
        if bard_lvl < 3 or not _has_subclass(player, "valor"):
            return {"ok": False, "log": "Richiede Bardo Collegio del Valore Lv 3+."}
        die = 6 if bard_lvl < 5 else (8 if bard_lvl < 10 else (10 if bard_lvl < 15 else 12))
        roll = random.randint(1, die)
        mode = str(params.get("mode", "damage")).lower()
        return {
            "ok": True,
            "roll": roll,
            "log": f"🛡️ [ISPIRAZIONE IN COMBATTIMENTO] {target_name or player.name} applica +{roll} (1d{die}) {'alla CA in Reazione' if 'ac' in mode else 'ai danni con arma'}!",
        }

    if pid in ("invoke_duplicity", "sacred_weapon", "vow_of_enmity"):
        # Tutti consumano Incanalare Divinità (1/riposo breve+)
        ok, cur, mx = entity_spend_resource(player, ("incanalare", "channel divinity", "channel_divinity"), 1)
        if not ok:
            return {"ok": False, "log": f"Usi di Incanalare Divinità esauriti ({cur}/{mx})."}
        if pid == "invoke_duplicity":
            player.duplicity_active = True
            return {"ok": True, "log": f"🪞 [INVOCARE DUPLICITÀ] {player.name} evoca un duplicato illusorio per 1 min ({cur}/{mx} CD)."}
        if pid == "sacred_weapon":
            player.sacred_weapon_active = True
            cha_b = max(1, _attr_mod(player, "CAR"))
            return {"ok": True, "log": f"✨ [ARMA SACRA] {player.name} infonde l'arma: +{cha_b} al TxC ed emette luce intensa ({cur}/{mx} CD)."}
        if pid == "vow_of_enmity":
            if not target_name:
                return {"ok": False, "log": "Specifica un bersaglio per Voto di Inimicizia."}
            player.vow_of_enmity_target = target_name
            return {"ok": True, "log": f"⚔️ [VOTO DI INIMICIZIA] {player.name} giura inimicizia contro {target_name}: Vantaggio ai TxC per 1 min ({cur}/{mx} CD)."}

    if pid == "hexblade_curse":
        if entity_get_class_level(player, "warlock") < 1 or not _has_subclass(player, "hexblade", "lama dell'ombra"):
            return {"ok": False, "log": "Richiede Warlock Lama dell'Ombra (Hexblade)."}
        if getattr(player, "hexblade_curse_used", False):
            return {"ok": False, "log": "Maledizione Hexblade già usata (si ricarica con Riposo Breve)."}
        if not target_name:
            return {"ok": False, "log": "Seleziona un bersaglio per Maledizione Hexblade."}
        player.hexblade_curse_used = True
        player.hexblade_curse_target = target_name
        return {"ok": True, "log": f"🗡️ [MALEDIZIONE HEXBLADE] {player.name} maledice {target_name}: +{_pb(player)} danni e Critico 19-20!"}

    if pid == "fey_presence":
        if entity_get_class_level(player, "warlock") < 1 or not _has_subclass(player, "archfey", "signore fatato"):
            return {"ok": False, "log": "Richiede Warlock Signore Fatato (Archfey)."}
        if getattr(player, "fey_presence_used", False):
            return {"ok": False, "log": "Presenza Fatata già usata (Riposo Breve)."}
        player.fey_presence_used = True
        effect = str(params.get("effect", "Affascinato (Charmed)"))
        dc = 8 + _pb(player) + _attr_mod(player, "CAR")
        return {"ok": True, "dc": dc, "log": f"🧚 [PRESENZA FATATA] {player.name} proietta un cubo di 10 ft: TS SAG CD {dc} o {effect} fino al termine del prossimo turno!"}

    if pid == "misty_escape":
        if entity_get_class_level(player, "warlock") < 6:
            return {"ok": False, "log": "Richiede Warlock Archfey Lv 6+."}
        if getattr(player, "misty_escape_used", False):
            return {"ok": False, "log": "Fuga Velata già usata (Riposo Breve)."}
        player.misty_escape_used = True
        return {"ok": True, "log": f"🌫️ [FUGA VELATA] {player.name} diventa Invisibile e si teletrasporta fino a 60 ft in Reazione!"}

    if pid == "entropic_ward":
        if entity_get_class_level(player, "warlock") < 6:
            return {"ok": False, "log": "Richiede Warlock Grande Antico Lv 6+."}
        if getattr(player, "entropic_ward_used", False):
            return {"ok": False, "log": "Interdizione Entropica già usata (Riposo Breve)."}
        player.entropic_ward_used = True
        return {"ok": True, "log": f"🌀 [INTERDIZIONE ENTROPICA] {player.name} impone Svantaggio all'attacco in arrivo (Vantaggio al tuo prossimo attacco se manca)!"}

    if pid == "shadow_step":
        if entity_get_class_level(player, "monaco", "monk") < 6 or not _has_subclass(player, "ombra", "shadow"):
            return {"ok": False, "log": "Richiede Monaco Via dell'Ombra Lv 6+."}
        if not getattr(player, "has_bonus_action", True):
            return {"ok": False, "log": "Azione Bonus già consumata."}
        player.has_bonus_action = False
        player.shadow_step_advantage = True
        return {"ok": True, "log": f"🌑 [PASSO D'OMBRA] {player.name} si teletrasporta fino a 60 ft da ombra a ombra: Vantaggio al prossimo attacco in mischia questo turno!"}

    if pid == "open_hand_technique":
        if entity_get_class_level(player, "monaco", "monk") < 3 or not _has_subclass(player, "mano aperta", "open hand"):
            return {"ok": False, "log": "Richiede Monaco Via della Mano Aperta Lv 3+."}
        mode = str(params.get("mode", "prone")).lower()
        dc = 8 + _pb(player) + _attr_mod(player, "SAG")
        if mode in ("no_reactions", "no_reazioni") and target is not None:
            target.open_hand_no_reactions = True
            return {"ok": True, "log": f"✋ [MANO APERTA] {target_name} non può effettuare Reazioni fino al termine del prossimo turno di {player.name}!"}
        if mode == "push":
            return {"ok": True, "dc": dc, "log": f"✋ [MANO APERTA] {target_name or 'Bersaglio'}: TS FOR CD {dc} o spinto di 15 ft!"}
        return {"ok": True, "dc": dc, "log": f"✋ [MANO APERTA] {target_name or 'Bersaglio'}: TS DES CD {dc} o cade Prono!"}

    if pid == "benign_transposition":
        if entity_get_class_level(player, "mago", "wizard") < 6 or not _has_subclass(player, "evocazion", "conjur"):
            return {"ok": False, "log": "Richiede Mago Scuola di Evocazione (Conjuration) Lv 6+."}
        if getattr(player, "benign_transposition_used", False):
            return {"ok": False, "log": "Trasposizione Benigna già usata (si ricarica con Riposo Lungo o incantesimo di Conjuration Lv1+)."}
        player.benign_transposition_used = True
        return {"ok": True, "log": f"✨ [TRASPOSIZIONE BENIGNA] {player.name} si teletrasporta di 30 ft (o scambia posto con {target_name or 'un alleato consenziente'})!"}

    if pid == "hypnotic_gaze":
        if entity_get_class_level(player, "mago", "wizard") < 2 or not _has_subclass(player, "ammaliamento", "enchant"):
            return {"ok": False, "log": "Richiede Mago Scuola di Ammaliamento Lv 2+."}
        dc = 8 + _pb(player) + _attr_mod(player, "INT")
        return {"ok": True, "dc": dc, "log": f"👁️ [SGUARDO IPNOTICO] {target_name or 'Bersaglio entro 5 ft'}: TS SAG CD {dc} o Affascinato, Velocità 0 e Incapacitato!"}

    if pid == "illusory_self":
        if entity_get_class_level(player, "mago", "wizard") < 10 or not _has_subclass(player, "illusion"):
            return {"ok": False, "log": "Richiede Mago Scuola di Illusione Lv 10+."}
        if getattr(player, "illusory_self_used", False):
            return {"ok": False, "log": "Sé Illusorio già usato (Riposo Breve)."}
        player.illusory_self_used = True
        return {"ok": True, "log": f"🎭 [SÉ ILLUSORIO] {player.name} interpone un duplicato illusorio: l'attacco contro di te manca automaticamente!"}

    if pid == "transmuters_stone":
        if entity_get_class_level(player, "mago", "wizard") < 6 or not _has_subclass(player, "trasmut", "transmut"):
            return {"ok": False, "log": "Richiede Mago Scuola di Trasmutazione Lv 6+."}
        benefit = str(params.get("benefit", "Competenza TS COS")).strip()
        player.transmuters_stone_benefit = benefit
        return {"ok": True, "log": f"💎 [PIETRA DEL TRASMUTATORE] {player.name} forgia la pietra conferendo: {benefit}."}

    if pid == "flash_of_genius":
        if entity_get_class_level(player, "artefice", "artificer") < 7:
            return {"ok": False, "log": "Richiede Artefice Lv 7+."}
        int_b = max(1, _attr_mod(player, "INT"))
        res = entity_find_resource(player, "lampo di genio", "flash of genius")
        if res is None:
            fs = _sheet(player)
            cl = fs.get("custom_resources") if isinstance(fs, dict) and isinstance(fs.get("custom_resources"), list) else getattr(player, "custom_resources", None)
            if not isinstance(cl, list):
                cl = []
                if isinstance(fs, dict) and fs is not player:
                    fs["custom_resources"] = cl
                else:
                    player.custom_resources = cl
            cl.append({"name": "Lampo di Genio (Flash of Genius)", "current": int_b, "max": int_b, "reset_on": "long"})
        ok, cur, mx = entity_spend_resource(player, ("lampo di genio", "flash of genius"), 1)
        if not ok:
            return {"ok": False, "log": f"Usi di Lampo di Genio esauriti ({cur}/{mx})."}
        return {"ok": True, "bonus": int_b, "log": f"⚡ [LAMPO DI GENIO] {player.name} aggiunge +{int_b} alla prova o al TS di {target_name or player.name} ({cur}/{mx})!"}

    return {"ok": False, "log": f"Privilegio sottoclasse '{pid}' non riconosciuto."}
