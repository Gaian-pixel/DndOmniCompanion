# -*- coding: utf-8 -*-
"""
D&D 5e DMG & XGtE Optional Systems Engine (server/dm_dmg_systems.py).

Implements complete, pure-Python + server-integrated mechanics for:
1. DMG p. 274 Monster Creation & Challenge Rating (CR) Calculator
2. DMG p. 250 Handling Mobs (attackers-needed-per-hit table)
3. DMG p. 140 Mixing Potions (Miscibility d100 table) & Spell Scroll Mishaps
4. DMG p. 244-245 Social Interaction (Attitudes & DC thresholds) & DMG p. 93 NPC Loyalty
5. DMG p. 119 / Saltmarsh Naval & Vehicles (Hull/Sails/Helm HP & Damage Threshold)
6. DMG p. 105-112 Wilderness Navigation, Foraging & Environmental Hazards
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple


# ==============================================================================
# 1. DMG p. 274 MONSTER CR CALCULATOR
# ==============================================================================

# (cr_str, cr_val, prof, ac, hp_min, hp_max, atk, dpr_min, dpr_max, save_dc, xp)
DMG_CR_TABLE: List[Tuple[str, float, int, int, int, int, int, int, int, int, int]] = [
    ("0", 0.0, 2, 13, 1, 6, 3, 0, 1, 13, 10),
    ("1/8", 0.125, 2, 13, 7, 35, 3, 2, 3, 13, 25),
    ("1/4", 0.25, 2, 13, 36, 49, 3, 4, 5, 13, 50),
    ("1/2", 0.5, 2, 13, 50, 70, 3, 6, 8, 13, 100),
    ("1", 1.0, 2, 13, 71, 85, 3, 9, 14, 13, 200),
    ("2", 2.0, 2, 13, 86, 100, 3, 15, 20, 13, 450),
    ("3", 3.0, 2, 13, 101, 115, 4, 21, 26, 13, 700),
    ("4", 4.0, 2, 14, 116, 130, 5, 27, 32, 14, 1100),
    ("5", 5.0, 3, 15, 131, 145, 6, 33, 38, 15, 1800),
    ("6", 6.0, 3, 15, 146, 160, 6, 39, 44, 15, 2300),
    ("7", 7.0, 3, 15, 161, 175, 6, 45, 50, 15, 2900),
    ("8", 8.0, 3, 16, 176, 190, 7, 51, 56, 16, 3900),
    ("9", 9.0, 4, 16, 191, 205, 7, 57, 62, 16, 5000),
    ("10", 10.0, 4, 17, 206, 220, 7, 63, 68, 16, 5900),
    ("11", 11.0, 4, 17, 221, 235, 8, 69, 74, 17, 7200),
    ("12", 12.0, 4, 17, 236, 250, 8, 75, 80, 17, 8400),
    ("13", 13.0, 5, 18, 251, 265, 8, 81, 86, 18, 10000),
    ("14", 14.0, 5, 18, 266, 280, 8, 87, 92, 18, 11500),
    ("15", 15.0, 5, 18, 281, 295, 8, 93, 98, 18, 13000),
    ("16", 16.0, 5, 18, 296, 310, 9, 99, 104, 18, 15000),
    ("17", 17.0, 6, 19, 311, 325, 10, 105, 110, 19, 18000),
    ("18", 18.0, 6, 19, 326, 340, 10, 111, 116, 19, 20000),
    ("19", 19.0, 6, 19, 341, 355, 10, 117, 122, 19, 22000),
    ("20", 20.0, 6, 19, 356, 400, 10, 123, 140, 19, 25000),
    ("21", 21.0, 7, 19, 401, 445, 11, 141, 158, 20, 33000),
    ("22", 22.0, 7, 19, 446, 490, 11, 159, 176, 20, 41000),
    ("23", 23.0, 7, 19, 491, 535, 11, 177, 194, 20, 50000),
    ("24", 24.0, 7, 19, 536, 580, 12, 195, 212, 21, 62000),
    ("25", 25.0, 8, 19, 581, 625, 12, 213, 230, 21, 75000),
    ("26", 26.0, 8, 19, 626, 670, 12, 231, 248, 21, 90000),
    ("27", 27.0, 8, 19, 671, 715, 13, 249, 266, 22, 105000),
    ("28", 28.0, 8, 19, 716, 760, 13, 267, 284, 22, 120000),
    ("29", 29.0, 9, 19, 761, 805, 13, 285, 302, 22, 135000),
    ("30", 30.0, 9, 19, 806, 850, 14, 303, 320, 23, 155000),
]


def _find_hp_row_index(effective_hp: float) -> int:
    hp = max(1, int(round(effective_hp)))
    for idx, row in enumerate(DMG_CR_TABLE):
        if hp <= row[5]:
            return idx
    return len(DMG_CR_TABLE) - 1


def _find_dpr_row_index(effective_dpr: float) -> int:
    dpr = max(0, int(round(effective_dpr)))
    for idx, row in enumerate(DMG_CR_TABLE):
        if dpr <= row[8]:
            return idx
    return len(DMG_CR_TABLE) - 1


def _closest_cr_index(avg_cr_val: float) -> int:
    best_idx = 0
    best_dist = 999.0
    for idx, row in enumerate(DMG_CR_TABLE):
        dist = abs(row[1] - avg_cr_val)
        if dist < best_dist - 1e-9:
            best_dist = dist
            best_idx = idx
        elif abs(dist - best_dist) <= 1e-9:
            # Tie goes to higher CR (standard 5e round-nearest-up at half step)
            best_idx = idx
    return best_idx


def calculate_monster_cr_dmg(
    hp: int,
    ac: int,
    dpr: float,
    attack_bonus: int = 3,
    save_dc: Optional[int] = None,
    use_save_dc: bool = False,
    has_resistances: bool = False,
    has_immunities: bool = False,
    effective_ac_bonus: int = 0,
    effective_hp_bonus: int = 0,
    magic_resistance: bool = False,
    save_proficiencies: int = 0,
    flying_low_cr_ranged: bool = False,
) -> Dict[str, Any]:
    """Calculate Defensive CR, Offensive CR, Final CR and XP using DMG p. 274-281."""
    base_hp = max(1, int(hp))
    # First-pass expected CR from raw HP to select resistance/immunity multiplier tier
    rough_row = DMG_CR_TABLE[_find_hp_row_index(base_hp)]
    rough_cr = rough_row[1]

    hp_mult = 1.0
    if has_immunities:
        if rough_cr <= 10.0:
            hp_mult = 2.0
        elif rough_cr <= 16.0:
            hp_mult = 1.5
        else:
            hp_mult = 1.25
    elif has_resistances:
        if rough_cr <= 4.0:
            hp_mult = 2.0
        elif rough_cr <= 10.0:
            hp_mult = 1.5
        elif rough_cr <= 16.0:
            hp_mult = 1.25
        else:
            hp_mult = 1.0

    effective_hp = int(round(base_hp * hp_mult + effective_hp_bonus))
    def_idx = _find_hp_row_index(effective_hp)
    target_ac = DMG_CR_TABLE[def_idx][3]

    eff_ac = int(ac) + int(effective_ac_bonus)
    if magic_resistance:
        eff_ac += 2
    if flying_low_cr_ranged and DMG_CR_TABLE[def_idx][1] <= 10.0:
        eff_ac += 2
    if save_proficiencies >= 5:
        eff_ac += 4
    elif save_proficiencies >= 3:
        eff_ac += 2

    ac_diff = eff_ac - target_ac
    ac_shift = int(ac_diff / 2)  # truncates toward zero: +/-1 at +/-2, etc.
    adj_def_idx = max(0, min(len(DMG_CR_TABLE) - 1, def_idx + ac_shift))
    def_cr_val = DMG_CR_TABLE[adj_def_idx][1]
    def_cr_str = DMG_CR_TABLE[adj_def_idx][0]

    off_idx = _find_dpr_row_index(dpr)
    if use_save_dc and save_dc is not None:
        target_dc = DMG_CR_TABLE[off_idx][9]
        off_diff = int(save_dc) - target_dc
    else:
        target_atk = DMG_CR_TABLE[off_idx][6]
        off_diff = int(attack_bonus) - target_atk
    off_shift = int(off_diff / 2)
    adj_off_idx = max(0, min(len(DMG_CR_TABLE) - 1, off_idx + off_shift))
    off_cr_val = DMG_CR_TABLE[adj_off_idx][1]
    off_cr_str = DMG_CR_TABLE[adj_off_idx][0]

    avg_cr = (def_cr_val + off_cr_val) / 2.0
    final_idx = _closest_cr_index(avg_cr)
    final_row = DMG_CR_TABLE[final_idx]

    return {
        "effective_hp": effective_hp,
        "hp_multiplier": hp_mult,
        "effective_ac": eff_ac,
        "defensive_cr": def_cr_str,
        "defensive_cr_value": def_cr_val,
        "offensive_cr": off_cr_str,
        "offensive_cr_value": off_cr_val,
        "final_cr": final_row[0],
        "final_cr_value": final_row[1],
        "proficiency_bonus": final_row[2],
        "xp": final_row[10],
    }


# ==============================================================================
# 2. DMG p. 250 HANDLING MOBS
# ==============================================================================

def _attackers_needed_for_roll(d20_needed: int) -> int:
    """Return DMG p. 250 number of attackers required for 1 hit."""
    if d20_needed <= 5:
        return 1
    if d20_needed <= 12:
        return 2
    if d20_needed <= 14:
        return 3
    if d20_needed <= 16:
        return 4
    if d20_needed <= 18:
        return 5
    if d20_needed == 19:
        return 10
    return 20


def resolve_mob_attack(
    num_attackers: int,
    attack_bonus: int,
    target_ac: int,
    damage_per_hit: int = 0,
    advantage: bool = False,
    disadvantage: bool = False,
) -> Dict[str, Any]:
    """Compute guaranteed hits and damage for a mob using DMG p. 250."""
    n = max(0, int(num_attackers))
    needed_raw = int(target_ac) - int(attack_bonus)
    if advantage and not disadvantage:
        needed_raw -= 5
    elif disadvantage and not advantage:
        needed_raw += 5
    d20_needed = max(1, min(20, needed_raw))
    per_hit = _attackers_needed_for_roll(d20_needed)
    hits = n // per_hit if per_hit > 0 else 0
    total_damage = max(0, hits * max(0, int(damage_per_hit)))
    return {
        "num_attackers": n,
        "d20_needed": d20_needed,
        "attackers_per_hit": per_hit,
        "hits": hits,
        "damage_per_hit": max(0, int(damage_per_hit)),
        "total_damage": total_damage,
    }


# ==============================================================================
# 3. DMG p. 140 MIXING POTIONS & SPELL SCROLL MISHAPS
# ==============================================================================

def roll_potion_miscibility(d100_roll: Optional[int] = None) -> Dict[str, Any]:
    """Resolve mixing two potions using DMG p. 140 Potion Miscibility table."""
    roll = int(d100_roll) if d100_roll is not None else random.randint(1, 100)
    roll = max(1, min(100, roll))
    if roll == 1:
        explosion_self = sum(random.randint(1, 10) for _ in range(6))
        explosion_aoe = random.randint(1, 10)
        return {
            "roll": roll,
            "code": "EXPLOSION",
            "self_damage": explosion_self,
            "aoe_5ft_damage": explosion_aoe,
            "summary": (
                f"Esplosione alchemica (d100={roll})! {explosion_self} danni da forza al bevitore, "
                f"{explosion_aoe} entro 1,5m; entrambe le pozioni distrutte."
            ),
        }
    if roll <= 8:
        return {
            "roll": roll,
            "code": "POISON",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Veleno letale (d100={roll}): la mistura si trasforma in un veleno a scelta del DM.",
        }
    if roll <= 15:
        return {
            "roll": roll,
            "code": "BOTH_NULLIFIED",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Neutralizzate (d100={roll}): entrambe le pozioni perdono ogni effetto.",
        }
    if roll <= 25:
        return {
            "roll": roll,
            "code": "ONE_NULLIFIED",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Parziale (d100={roll}): una pozione perde l'effetto, l'altra funziona normalmente.",
        }
    if roll <= 35:
        return {
            "roll": roll,
            "code": "HALVED",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Dimezzate (d100={roll}): entrambe le pozioni hanno durata ed effetti numerici dimezzati.",
        }
    if roll <= 90:
        return {
            "roll": roll,
            "code": "NORMAL",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Compatibili (d100={roll}): la mistura produce normalmente l'effetto di entrambe le pozioni.",
        }
    if roll <= 99:
        return {
            "roll": roll,
            "code": "ONE_DOUBLED",
            "self_damage": 0,
            "aoe_5ft_damage": 0,
            "summary": f"Potenziata (d100={roll}): una pozione raddoppia durata/effetti numerici; l'altra agisce normalmente.",
        }
    return {
        "roll": roll,
        "code": "PERMANENT",
        "self_damage": 0,
        "aoe_5ft_damage": 0,
        "summary": f"Alchimia Straordinaria (d100={roll})! Funziona una sola pozione ma il suo effetto è PERMANENTE.",
    }


def resolve_spell_scroll_use(
    spell_level: int,
    on_class_list: bool,
    max_castable_level: int,
    caster_ability_mod: int = 0,
    check_roll: Optional[int] = None,
    mishap_save_mod: int = 0,
    mishap_save_roll: Optional[int] = None,
    mishap_table_roll: Optional[int] = None,
    trigger_mishap_on_fail: bool = True,
) -> Dict[str, Any]:
    """Resolve DMG p. 200 Spell Scroll activation + DMG p. 140 Scroll Mishap."""
    lvl = max(0, int(spell_level))
    if not on_class_list:
        return {
            "success": False,
            "unintelligible": True,
            "scroll_consumed": False,
            "check_dc": None,
            "check_total": None,
            "mishap": None,
            "summary": "La pergamena è incomprensibile: non appartiene alla lista incantesimi della tua classe.",
        }

    if lvl <= int(max_castable_level):
        return {
            "success": True,
            "unintelligible": False,
            "scroll_consumed": True,
            "check_dc": None,
            "check_total": None,
            "mishap": None,
            "summary": f"Pergamena di  livello {lvl} lanciata senza prova!",
        }

    dc = 10 + lvl
    d20 = int(check_roll) if check_roll is not None else random.randint(1, 20)
    total = d20 + int(caster_ability_mod)
    if total >= dc:
        return {
            "success": True,
            "unintelligible": False,
            "scroll_consumed": True,
            "check_dc": dc,
            "check_total": total,
            "mishap": None,
            "summary": f"Prova caratteristica {total} (d20={d20}{caster_ability_mod:+d}) vs CD {dc}: pergamena lanciata con successo!",
        }

    mishap_info: Optional[Dict[str, Any]] = None
    if trigger_mishap_on_fail:
        save_d20 = int(mishap_save_roll) if mishap_save_roll is not None else random.randint(1, 20)
        save_total = save_d20 + int(mishap_save_mod)
        if save_total < 10:
            m_roll = int(mishap_table_roll) if mishap_table_roll is not None else random.randint(1, 6)
            m_roll = max(1, min(6, m_roll))
            if m_roll == 1:
                dmg = sum(random.randint(1, 6) for _ in range(max(1, lvl)))
                mishap_desc = f"Impeto di forza magica: {dmg} danni da forza all'incantatore!"
            elif m_roll == 2:
                dmg = 0
                mishap_desc = "Bersaglio deviato: l'incantesimo colpisce l'incantatore o un alleato casuale entro 9m."
            elif m_roll == 3:
                dmg = 0
                mishap_desc = "Punto sbagliato: l'effetto si sprigiona in una direzione/luogo casuale nel raggio."
            elif m_roll == 4:
                dmg = 0
                mishap_desc = "Effetto bizzarro innocuo: l'energia si manifesta in modo caotico (scintille, suoni, colore)."
            elif m_roll == 5:
                dmg = 0
                mishap_desc = "Sbalzo planare: incantatore e creature entro 3m trasportati sul Piano Astrale fino a fine prossimo turno."
            else:
                dmg = 0
                mishap_desc = "Incantesimo ritardato: si attiva automaticamente in un momento casuale entro 1d12 ore."
            mishap_info = {
                "save_total": save_total,
                "table_roll": m_roll,
                "damage": dmg,
                "description": mishap_desc,
            }

    msg = f"Prova fallita {total} vs CD {dc}: pergamena sprecata."
    if mishap_info:
        msg += f" Incidente (TS SAG {mishap_info['save_total']} < 10, d6={mishap_info['table_roll']}): {mishap_info['description']}"
    return {
        "success": False,
        "unintelligible": False,
        "scroll_consumed": True,
        "check_dc": dc,
        "check_total": total,
        "mishap": mishap_info,
        "summary": msg,
    }


# ==============================================================================
# 4. DMG p. 244-245 SOCIAL INTERACTION & DMG p. 93 NPC LOYALTY
# ==============================================================================

_SOCIAL_OUTCOMES: Dict[str, List[Tuple[int, str, str]]] = {
    "friendly": [
        (20, "SIGNIFICANT_RISK", "Accetta un rischio o sacrificio significativo per aiutare il gruppo."),
        (10, "MINOR_RISK", "Accetta un rischio o sacrificio minore per aiutare."),
        (0, "HELPS_NO_RISK", "Fa ciò che gli viene chiesto senza assumersi rischi o sacrifici."),
    ],
    "indifferent": [
        (20, "MINOR_RISK", "Accetta un rischio o sacrificio minore per aiutare."),
        (10, "HELPS_NO_RISK", "Fa ciò che gli viene chiesto purché non comporti rischi o sacrifici."),
        (0, "NEUTRAL_NO_HELP", "Non offre alcun aiuto ma non ostacola il gruppo."),
    ],
    "hostile": [
        (20, "HELPS_NO_RISK", "Aiuta quanto richiesto purché senza rischi o sacrifici personali."),
        (10, "NEUTRAL_NO_HELP", "Non offre aiuto ma evita di arrecare danno."),
        (0, "OPPOSES", "Si oppone agli avventurieri e può rischiare per danneggiarli."),
    ],
}


def resolve_social_check(attitude: str, total_check: int) -> Dict[str, Any]:
    """Resolve DMG p. 245 Charisma check threshold by initial attitude."""
    norm = str(attitude or "indifferent").strip().lower()
    if norm in ("amichevole", "friendly"):
        norm = "friendly"
    elif norm in ("ostile", "hostile"):
        norm = "hostile"
    else:
        norm = "indifferent"

    val = int(total_check)
    for min_dc, code, desc in _SOCIAL_OUTCOMES[norm]:
        if val >= min_dc:
            return {
                "attitude": norm,
                "check_total": val,
                "threshold_met": min_dc,
                "outcome_code": code,
                "description": desc,
            }
    # Below DC 0
    return {
        "attitude": norm,
        "check_total": val,
        "threshold_met": None,
        "outcome_code": "WORSENS_OPPOSES",
        "description": "Reazione negativa o ostile: l'atteggiamento peggiora o rifiuta categoricamente.",
    }


def adjust_npc_loyalty(current_loyalty: int, delta: int) -> Dict[str, Any]:
    """Adjust DMG p. 93 NPC loyalty (0..20) and evaluate betrayal/cohesion tier."""
    new_val = max(0, min(20, int(current_loyalty) + int(delta)))
    if new_val <= 0:
        tier = "DISLOYAL_BETRAYS"
        desc = "Lealtà 0: il seguace tradisce o abbandona il gruppo appena possibile."
    elif new_val <= 10:
        tier = "TENSE"
        desc = f"Lealtà {new_val}/20 (Fragile): potrebbe disertare sotto forte pressione o pericolo."
    else:
        tier = "LOYAL"
        desc = f"Lealtà {new_val}/20 (Fedele): disposto anche a rischiare per il gruppo."
    return {"loyalty": new_val, "tier": tier, "description": desc}


# ==============================================================================
# 5. DMG p. 119 / SALTMARSH VEHICLES & NAVAL COMBAT
# ==============================================================================

VEHICLE_TEMPLATES_DMG: Dict[str, Dict[str, Any]] = {
    "rowboat": {
        "name": "Barca a Remi",
        "hull_hp": 50,
        "hull_ac": 11,
        "damage_threshold": 0,
        "sails_hp": 25,
        "sails_ac": 12,
        "helm_hp": 25,
        "helm_ac": 12,
        "speed_ft": 15,
        "mph": 1.5,
        "crew_min": 1,
    },
    "keelboat": {
        "name": "Battello Fluviale",
        "hull_hp": 100,
        "hull_ac": 15,
        "damage_threshold": 10,
        "sails_hp": 50,
        "sails_ac": 12,
        "helm_hp": 35,
        "helm_ac": 15,
        "speed_ft": 20,
        "mph": 1.0,
        "crew_min": 1,
    },
    "longship": {
        "name": "Nave Lunga",
        "hull_hp": 300,
        "hull_ac": 15,
        "damage_threshold": 15,
        "sails_hp": 100,
        "sails_ac": 12,
        "helm_hp": 50,
        "helm_ac": 16,
        "speed_ft": 40,
        "mph": 3.0,
        "crew_min": 20,
    },
    "sailing_ship": {
        "name": "Veliero",
        "hull_hp": 300,
        "hull_ac": 15,
        "damage_threshold": 15,
        "sails_hp": 100,
        "sails_ac": 12,
        "helm_hp": 50,
        "helm_ac": 18,
        "speed_ft": 35,
        "mph": 2.0,
        "crew_min": 15,
    },
    "warship": {
        "name": "Nave da Guerra",
        "hull_hp": 500,
        "hull_ac": 15,
        "damage_threshold": 20,
        "sails_hp": 100,
        "sails_ac": 12,
        "helm_hp": 50,
        "helm_ac": 18,
        "speed_ft": 35,
        "mph": 2.5,
        "crew_min": 30,
    },
    "galley": {
        "name": "Galea",
        "hull_hp": 500,
        "hull_ac": 15,
        "damage_threshold": 20,
        "sails_hp": 150,
        "sails_ac": 12,
        "helm_hp": 60,
        "helm_ac": 18,
        "speed_ft": 40,
        "mph": 4.0,
        "crew_min": 40,
    },
    "airship": {
        "name": "Aeronave",
        "hull_hp": 300,
        "hull_ac": 13,
        "damage_threshold": 0,
        "sails_hp": 100,
        "sails_ac": 12,
        "helm_hp": 50,
        "helm_ac": 16,
        "speed_ft": 60,
        "mph": 8.0,
        "crew_min": 10,
    },
    "carriage": {
        "name": "Carrozza / Carro",
        "hull_hp": 100,
        "hull_ac": 15,
        "damage_threshold": 5,
        "sails_hp": 30,  # Wheels/Axles
        "sails_ac": 13,
        "helm_hp": 25,
        "helm_ac": 14,
        "speed_ft": 30,
        "mph": 3.0,
        "crew_min": 1,
    },
}


def create_vehicle_state(template_key: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
    """Create a stateful DMG p. 119 vehicle dictionary."""
    tpl = VEHICLE_TEMPLATES_DMG.get(str(template_key).lower(), VEHICLE_TEMPLATES_DMG["sailing_ship"])
    return {
        "template": str(template_key).lower(),
        "name": custom_name or tpl["name"],
        "damage_threshold": tpl["damage_threshold"],
        "speed_ft": tpl["speed_ft"],
        "base_speed_ft": tpl["speed_ft"],
        "mph": tpl["mph"],
        "crew_current": tpl["crew_min"],
        "crew_min": tpl["crew_min"],
        "hull": {"hp": tpl["hull_hp"], "max_hp": tpl["hull_hp"], "ac": tpl["hull_ac"]},
        "sails": {"hp": tpl["sails_hp"], "max_hp": tpl["sails_hp"], "ac": tpl["sails_ac"]},
        "helm": {"hp": tpl["helm_hp"], "max_hp": tpl["helm_hp"], "ac": tpl["helm_ac"]},
        "sinking": False,
        "immobilized": False,
        "unsteerable": False,
    }


def apply_vehicle_damage(vehicle: Dict[str, Any], raw_damage: int, component: str = "hull") -> Dict[str, Any]:
    """Apply damage to hull/sails/helm respecting DMG p. 119 Damage Threshold."""
    comp = str(component or "hull").lower()
    if comp not in ("hull", "sails", "helm"):
        comp = "hull"
    dmg = max(0, int(raw_damage))
    threshold = int(vehicle.get("damage_threshold", 0)) if comp == "hull" else 0
    if dmg < threshold:
        return {
            "component": comp,
            "raw_damage": dmg,
            "damage_taken": 0,
            "blocked_by_threshold": True,
            "remaining_hp": vehicle[comp]["hp"],
            "status_note": f"Soglia Danno ({threshold}) assorbe l'impatto su {comp}: 0 danni!",
        }

    target = vehicle[comp]
    target["hp"] = max(0, int(target["hp"]) - dmg)
    notes: List[str] = []
    if vehicle["sails"]["hp"] == 0:
        vehicle["speed_ft"] = max(0, int(vehicle.get("base_speed_ft", 30)) // 2)
        notes.append("Vele/Ruote distrutte (velocità dimezzata)")
    if vehicle["helm"]["hp"] == 0:
        vehicle["unsteerable"] = True
        notes.append("Timone distrutto (ingovernabile)")
    if vehicle["hull"]["hp"] == 0:
        vehicle["sinking"] = True
        vehicle["immobilized"] = True
        notes.append("Scafo sfondato (sta affondando / distrutto)")

    return {
        "component": comp,
        "raw_damage": dmg,
        "damage_taken": dmg,
        "blocked_by_threshold": False,
        "remaining_hp": target["hp"],
        "status_note": "; ".join(notes) if notes else f"{comp} ridotto a {target['hp']}/{target['max_hp']} PF.",
    }


# ==============================================================================
# 6. DMG p. 105-112 WILDERNESS NAVIGATION, FORAGING & HAZARDS
# ==============================================================================

TERRAIN_NAVIGATION_FORAGE_DMG: Dict[str, Dict[str, Any]] = {
    "grassland": {"name": "Prateria / Campi / Strade", "nav_dc": 5, "forage_dc": 10},
    "forest": {"name": "Foresta / Giungla / Colline", "nav_dc": 15, "forage_dc": 10},
    "jungle": {"name": "Giungla Fitta", "nav_dc": 15, "forage_dc": 10},
    "coast": {"name": "Costa", "nav_dc": 10, "forage_dc": 10},
    "mountain": {"name": "Montagna", "nav_dc": 15, "forage_dc": 15},
    "swamp": {"name": "Palude / Acquitrino", "nav_dc": 15, "forage_dc": 15},
    "arctic": {"name": "Artico / Ghiacciai", "nav_dc": 15, "forage_dc": 20},
    "desert": {"name": "Deserto", "nav_dc": 10, "forage_dc": 20},
    "underdark": {"name": "Sottosuolo / Caverne", "nav_dc": 15, "forage_dc": 20},
}


def resolve_wilderness_travel_checks(
    terrain: str,
    nav_roll_total: int,
    forage_roll_total: int,
    wis_mod: int = 0,
    pace: str = "normal",
    has_ranger_natural_explorer: bool = False,
) -> Dict[str, Any]:
    """Resolve DMG p. 111 Navigation & Foraging checks."""
    t = TERRAIN_NAVIGATION_FORAGE_DMG.get(str(terrain).lower(), TERRAIN_NAVIGATION_FORAGE_DMG["forest"])
    pace_norm = str(pace or "normal").lower()
    pace_mod = 5 if pace_norm == "slow" else (-5 if pace_norm == "fast" else 0)

    eff_nav = int(nav_roll_total) + pace_mod
    lost = (eff_nav < t["nav_dc"]) and not has_ranger_natural_explorer

    if pace_norm == "fast":
        can_forage = False
        forage_success = False
        food_lb = 0
        water_gal = 0
    else:
        can_forage = True
        forage_success = int(forage_roll_total) >= t["forage_dc"]
        mult = 2 if has_ranger_natural_explorer else 1
        food_lb = max(0, (random.randint(1, 6) + int(wis_mod)) * mult) if forage_success else 0
        water_gal = max(0, (random.randint(1, 6) + int(wis_mod)) * mult) if forage_success else 0

    return {
        "terrain": t["name"],
        "pace": pace_norm,
        "nav_dc": t["nav_dc"],
        "effective_nav_roll": eff_nav,
        "got_lost": lost,
        "can_forage": can_forage,
        "forage_dc": t["forage_dc"],
        "forage_success": forage_success,
        "food_pounds": food_lb,
        "water_gallons": water_gal,
    }


def resolve_wilderness_hazard(
    hazard_type: str,
    save_total: Optional[int] = None,
    d20_roll: Optional[int] = None,
) -> Dict[str, Any]:
    """Resolve DMG p. 105 / 110 Wilderness Hazards."""
    hz = str(hazard_type or "").lower()
    roll_val = int(save_total) if save_total is not None else (int(d20_roll) if d20_roll is not None else random.randint(1, 20))
    if hz in ("razorvine", "rovo_tagliente"):
        saved = roll_val >= 10
        dmg = 0 if saved else random.randint(1, 10)
        return {"hazard": "Rovo Tagliente", "save_dc": 10, "saved": saved, "damage": dmg, "damage_type": "slashing"}
    if hz in ("brown_mold", "muffa_bruna"):
        raw = sum(random.randint(1, 10) for _ in range(4))
        saved = roll_val >= 12
        dmg = raw // 2 if saved else raw
        return {"hazard": "Muffa Bruna", "save_dc": 12, "saved": saved, "damage": dmg, "damage_type": "cold"}
    if hz in ("green_slime", "melma_verde"):
        saved = roll_val >= 10
        dmg = 0 if saved else random.randint(1, 10)
        return {"hazard": "Melma Verde", "save_dc": 10, "saved": saved, "damage": dmg, "damage_type": "acid"}
    if hz in ("quicksand", "sabbie_mobili"):
        sink_ft = random.randint(1, 4) + 1
        escape_dc = 10 + sink_ft
        saved = roll_val >= escape_dc
        return {"hazard": "Sabbie Mobili", "save_dc": escape_dc, "sink_ft": sink_ft, "saved": saved, "damage": 0, "damage_type": "none"}
    if hz in ("frigid_water", "acqua_gelida"):
        saved = roll_val >= 10
        return {"hazard": "Acqua Gelida", "save_dc": 10, "saved": saved, "exhaustion_gained": 0 if saved else 1, "damage": 0, "damage_type": "none"}
    # thin_ice
    saved = roll_val >= 10
    return {"hazard": "Ghiaccio Sottile", "save_dc": 10, "saved": saved, "damage": 0, "damage_type": "none"}
