"""
server/dm_optional_tools.py
Motore centralizzato per Regole Opzionali DMG, XGtE & TCE selezionabili dal DM:
- Effetti meccanici concreti e cura delle Ferite Permanenti (Lingering Injuries DMG p. 272)
- Morale Mostri e PNG (DMG p. 273)
- Punti Eroe (Hero Points DMG p. 264)
- Direzione Tattica / Facing (DMG p. 252)
- Paura e Orrore (Fear & Horror DMG p. 266)
- Impulsi Curativi (Healing Surges DMG p. 266)
- Varianti Iniziativa: Squadra / Side & Fattore Velocita' / Speed Factor (DMG p. 270)
- Raccolta Veleni (Poison Harvesting DMG p. 258)
- Trappole Complesse a Iniziativa 20/10 (XGtE p. 118-123 / DMG)
- Armi d'Assedio (Siege Equipment DMG p. 255-256)
- Oggetti Magici Senzienti & Conflitti Ego (DMG p. 214-216)
- Proprieta' Artefatti (Benefiche/Deteriori Minori & Maggiori DMG p. 219-221)
- Seguaci (Sidekicks TCE), Bastioni/Roccaforti (DMG p. 127), Fama (Renown) e Pieta' (Piety)
"""

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from common.dice import roll_dice
from common.dnd5e_tables import (
    DMG_POISONS,
    entity_get_attr_mod,
    entity_get_effective_attr,
    entity_get_total_level,
    roll_madness,
)
from common.item_modifiers import get_effective_attribute_from_dict, get_effective_save_bonus_from_dict
from common.network_utils import broadcast, send_message
from common.protocol import make_chat_broadcast, make_error_reply, make_game_state, make_player_stats_update


def _opt_enabled(game_state: Any, key: str, default: bool = False) -> bool:
    if not game_state:
        return default
    settings = getattr(game_state, "automation_settings", None)
    if isinstance(settings, dict):
        return bool(settings.get(key, default))
    return default


def _sync_conds(entity: Any) -> None:
    if isinstance(getattr(entity, "full_sheet", None), dict):
        entity.full_sheet["conditions"] = list(getattr(entity, "conditions", []) or [])


# ==============================================================================
# 1. FERITE PERMANENTI (LINGERING INJURIES DMG p. 272) - PENALITA' & CURA
# ==============================================================================

def get_lingering_injury_penalties(entity: Any) -> Dict[str, Any]:
    """Analizza le ferite permanenti attive sull'entita' e restituisce i modificatori meccanici."""
    out: Dict[str, Any] = {
        "speed_halved": False,
        "speed_penalty_ft": 0,
        "dash_fall_prone": False,
        "dash_prone_dc": 0,
        "no_two_handed": False,
        "ranged_attack_disadvantage": False,
        "sight_perception_disadvantage": False,
        "blinded": False,
        "festering_wound": False,
        "internal_injury_dc": 0,
    }
    if not entity:
        return out
    inj_list: List[Any] = []
    injuries = getattr(entity, "injuries", None)
    if isinstance(injuries, list):
        inj_list.extend(injuries)
    for fx in (getattr(entity, "active_effects", None) or []):
        if isinstance(fx, dict) and fx.get("lingering_injury"):
            inj_list.append(fx)
    if not inj_list:
        return out
    eye_count = 0
    for inj in inj_list:
        name = str(inj.get("name", inj) if isinstance(inj, dict) else inj).lower()
        if any(k in name for k in ("occhio", "eye")):
            eye_count += 1
            out["ranged_attack_disadvantage"] = True
            out["sight_perception_disadvantage"] = True
        if any(k in name for k in ("mano", "braccio", "hand", "arm")):
            out["no_two_handed"] = True
        if any(k in name for k in ("piede", "gamba", "foot", "leg")):
            out["speed_halved"] = True
            out["dash_fall_prone"] = True
        if any(k in name for k in ("zopp", "limp")):
            out["speed_penalty_ft"] = max(out["speed_penalty_ft"], 5)
            out["dash_prone_dc"] = max(out["dash_prone_dc"], 10)
        if any(k in name for k in ("infett", "festering")):
            out["festering_wound"] = True
        if any(k in name for k in ("intern", "internal")):
            out["internal_injury_dc"] = 15
    if eye_count >= 2:
        out["blinded"] = True
    return out


def cure_lingering_injury(target: Any, method: str = "regenerate", injury_name: Optional[str] = None) -> Tuple[bool, str]:
    """Cura ferite permanenti secondo DMG p. 272 (Rigenerazione, Ristorare, Cure Magiche o Medicina CD 15)."""
    raw_inj = getattr(target, "injuries", None) if target else None
    raw_fx = getattr(target, "active_effects", None) if target else None
    has_inj = isinstance(raw_inj, list) and len(raw_inj) > 0
    has_fx_inj = isinstance(raw_fx, list) and any(isinstance(fx, dict) and fx.get("lingering_injury") for fx in raw_fx)
    if not target or (not has_inj and not has_fx_inj):
        return False, f"{getattr(target, 'name', 'Bersaglio')} non ha ferite permanenti attive."
    m_low = str(method or "regenerate").lower()
    cured: List[str] = []
    remaining: List[Any] = []
    for inj in (raw_inj or []):
        iname = str(inj.get("name", inj) if isinstance(inj, dict) else inj)
        ilow = iname.lower()
        if injury_name and injury_name.lower() not in ilow:
            remaining.append(inj)
            continue
        is_missing_limb = any(k in ilow for k in ("occhio", "eye", "mano", "braccio", "hand", "arm", "piede", "gamba", "foot", "leg"))
        if "regenerate" in m_low or "rigenera" in m_low:
            cured.append(iname)
        elif "greater" in m_low or "superiore" in m_low or not is_missing_limb:
            if not is_missing_limb or ("regenerate" in m_low):
                cured.append(iname)
            else:
                remaining.append(inj)
        else:
            remaining.append(inj)
    if isinstance(raw_inj, list):
        target.injuries = remaining
    if has_fx_inj:
        kept_fx = []
        for fx in raw_fx:
            if not (isinstance(fx, dict) and fx.get("lingering_injury")):
                kept_fx.append(fx)
                continue
            iname = str(fx.get("name", "Ferita"))
            ilow = iname.lower()
            if injury_name and injury_name.lower() not in ilow:
                kept_fx.append(fx)
                continue
            is_missing_limb = any(k in ilow for k in ("occhio", "eye", "mano", "braccio", "hand", "arm", "piede", "gamba", "foot", "leg"))
            if "regenerate" in m_low or "rigenera" in m_low or ("greater" in m_low and not is_missing_limb) or not is_missing_limb:
                cured.append(iname)
            else:
                kept_fx.append(fx)
        target.active_effects = kept_fx
    if cured and hasattr(target, "conditions") and isinstance(target.conditions, list):
        cured_tags = {f"Ferita: {c}" for c in cured}
        target.conditions = [c for c in target.conditions if c not in cured_tags]
        _sync_conds(target)
    if cured:
        return True, f"🩹 [CURA FERITA DMG] {', '.join(cured)} rimossa da {target.name}!"
    return False, "Questo metodo non può rigenerare arti o occhi mancanti (serve Rigenerazione)."


def tick_festering_wounds_24h(game_state: Any) -> List[str]:
    """DMG p. 272: Ferite Infette riducono i PF Max di 1 ogni 24 ore."""
    logs: List[str] = []
    if not game_state:
        return logs
    for p in list(getattr(game_state, "players", [])):
        pen = get_lingering_injury_penalties(p)
        if pen.get("festering_wound") and getattr(p, "max_hp", 1) > 0:
            p.max_hp = max(0, int(p.max_hp) - 1)
            if p.hp > p.max_hp:
                p.hp = p.max_hp
            if isinstance(getattr(p, "full_sheet", None), dict):
                p.full_sheet["hp_max"] = p.max_hp
                p.full_sheet["hp_current"] = p.hp
            logs.append(f"🦠 [FERITA INFETTA] {p.name} perde 1 PF Max (nuovo max: {p.max_hp}).")
    return logs


# ==============================================================================
# 2. MORALE MOSTRI E PNG (DMG p. 273)
# ==============================================================================

def evaluate_morale_checks(game_state: Any, trigger_reason: str = "casualties", forced_save_roll: Optional[int] = None) -> List[str]:
    """
    DMG p. 273: Quando il leader cade, metà nemici sono sconfitti, o un mostro solitario scende <=50% PF,
    i nemici effettuano un TS Saggezza CD 10 o sono Spaventati / in rotta.
    """
    if not _opt_enabled(game_state, "opt_morale", False):
        return []
    hostiles = [
        p for p in getattr(game_state, "players", [])
        if getattr(p, "in_combat", True)
        and not getattr(p, "is_party_member", False)
        and getattr(p, "conn", None) is None
    ]
    if not hostiles:
        return []

    dead_or_down = [h for h in hostiles if getattr(h, "hp", 1) <= 0]
    alive = [h for h in hostiles if getattr(h, "hp", 0) > 0]
    if not alive:
        return []

    should_check = (trigger_reason == "manual")
    if trigger_reason == "leader_down":
        should_check = True
    elif len(hostiles) > 1 and len(dead_or_down) >= (len(hostiles) / 2.0):
        should_check = True
    elif len(hostiles) == 1 and alive[0].hp <= (max(1, alive[0].max_hp) / 2.0):
        should_check = True

    if not should_check:
        return []

    msgs: List[str] = []
    for npc in alive:
        if getattr(npc, "_morale_broken", False) or getattr(npc, "_morale_passed_once", False):
            continue
        conds_low = [str(c).lower() for c in getattr(npc, "conditions", [])]
        if any("spaventat" in c or "fright" in c or "morale" in c for c in conds_low):
            npc._morale_broken = True
            continue
        wis_save = get_effective_save_bonus_from_dict(npc, "SAG")
        if forced_save_roll is not None:
            r_tot = int(forced_save_roll) + wis_save
        else:
            r_tot = roll_dice(f"1d20{'+' if wis_save >= 0 else ''}{wis_save}")["total"]
        if r_tot < 10:
            npc._morale_broken = True
            if not hasattr(npc, "conditions") or not isinstance(npc.conditions, list):
                npc.conditions = []
            if "Spaventato (Morale Rotto)" not in npc.conditions:
                npc.conditions.append("Spaventato (Morale Rotto)")
            _sync_conds(npc)
            m = f"🏳️ [MORALE DMG p.273] {npc.name} fallisce TS SAG {r_tot} < CD 10: il morale si spezza (Spaventato / in fuga)!"
            msgs.append(m)
            broadcast(game_state, make_player_stats_update(npc.name, npc.hp, npc.max_hp, npc.initiative, npc.conditions, getattr(npc, "temp_hp", 0)))
        else:
            npc._morale_passed_once = True
            msgs.append(f"🛡️ [MORALE DMG p.273] {npc.name} supera TS SAG {r_tot} >= CD 10 e mantiene la posizione.")

    for m in msgs:
        broadcast(game_state, make_chat_broadcast("Sistema", m))
        if hasattr(game_state, "log_dm_message"):
            game_state.log_dm_message(f"[DMG_OPT] {m}")
    return msgs


# ==============================================================================
# 3. PUNTI EROE (HERO POINTS DMG p. 264)
# ==============================================================================

def get_hero_points_max(entity: Any) -> int:
    return 5 + (entity_get_total_level(entity) // 2)


def ensure_hero_points(entity: Any, reset: bool = False) -> int:
    mx = get_hero_points_max(entity)
    cur = getattr(entity, "hero_points", None)
    if reset or cur is None:
        entity.hero_points = mx
    else:
        entity.hero_points = max(0, min(mx, int(cur)))
    if isinstance(getattr(entity, "full_sheet", None), dict):
        entity.full_sheet["hero_points"] = entity.hero_points
    return int(entity.hero_points)


def handle_spend_hero_point(actor: Any, mode: str, game_state: Any) -> Tuple[bool, str]:
    if not _opt_enabled(game_state, "opt_hero_points", False):
        return False, "La regola opzionale Punti Eroe (DMG p. 264) è disabilitata dal Master."
    cur = ensure_hero_points(actor, reset=False)
    if cur <= 0:
        return False, f"{actor.name} non ha Punti Eroe disponibili!"
    actor.hero_points = cur - 1
    if isinstance(getattr(actor, "full_sheet", None), dict):
        actor.full_sheet["hero_points"] = actor.hero_points

    m_low = str(mode or "roll_bonus").lower()
    if m_low in ("death_save", "stabilize", "stabilizza"):
        actor.death_save_failures = 0
        if getattr(actor, "hp", 0) <= 0:
            actor.hp = 0
            if "Stabilizzato" not in getattr(actor, "conditions", []):
                actor.conditions.append("Stabilizzato")
            _sync_conds(actor)
        msg = f"🌟 [PUNTO EROE DMG p.264] {actor.name} spende 1 Punto Eroe ({actor.hero_points} rimasti) per trasformare il TS Morte in SUCCESSO / stabilizzarsi!"
    else:
        bonus_r = roll_dice("1d6")["total"]
        actor.pending_hero_bonus = bonus_r
        msg = f"🌟 [PUNTO EROE DMG p.264] {actor.name} spende 1 Punto Eroe ({actor.hero_points} rimasti) e aggiunge +1d6 ({bonus_r}) al tiro!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


# ==============================================================================
# 4. DIREZIONE TATTICA / FACING (DMG p. 252)
# ==============================================================================

def _pos_to_xy(pos: Any, grid_type: str = "hex") -> Tuple[float, float]:
    if not pos or len(pos) < 2:
        return 0.0, 0.0
    q, r = float(pos[0]), float(pos[1])
    if grid_type == "square":
        return q, r
    x = math.sqrt(3.0) * (q + r / 2.0)
    y = 1.5 * r
    return x, y


def update_facing_from_move(entity: Any, from_pos: Any, to_pos: Any, grid_type: str = "hex") -> Optional[float]:
    if not entity or not from_pos or not to_pos or list(from_pos) == list(to_pos):
        return getattr(entity, "facing", None)
    x1, y1 = _pos_to_xy(from_pos, grid_type)
    x2, y2 = _pos_to_xy(to_pos, grid_type)
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        return getattr(entity, "facing", None)
    angle = math.degrees(math.atan2(dy, dx)) % 360.0
    entity.facing = round(angle, 1)
    return entity.facing


def evaluate_facing_attack(attacker: Any, defender: Any, grid_type: str = "hex") -> Dict[str, Any]:
    """
    DMG p. 252:
    - Front arc (<=60° dal vettore facing del difensore): scudo attivo
    - Flank arc (60°..120°): scudo del lato coperto ignorato
    - Rear arc (>120°): scudo ignorato + Vantaggio all'attaccante
    """
    out = {"arc": "front", "ignore_shield": False, "grant_advantage": False}
    f_deg = getattr(defender, "facing", None)
    a_pos = getattr(attacker, "position", None)
    d_pos = getattr(defender, "position", None)
    if f_deg is None or not a_pos or not d_pos or list(a_pos) == list(d_pos):
        return out
    dx_a, dy_a = _pos_to_xy(a_pos, grid_type)
    dx_d, dy_d = _pos_to_xy(d_pos, grid_type)
    vx, vy = dx_a - dx_d, dy_a - dy_d
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return out
    att_angle = math.degrees(math.atan2(vy, vx)) % 360.0
    diff = abs((att_angle - float(f_deg) + 180.0) % 360.0 - 180.0)
    if diff > 120.0:
        out["arc"] = "rear"
        out["ignore_shield"] = True
        out["grant_advantage"] = True
    elif diff > 60.0:
        out["arc"] = "flank"
        out["ignore_shield"] = True
    return out


# ==============================================================================
# 5. PAURA E ORRORE (FEAR & HORROR DMG p. 266) & IMPULSI CURATIVI (DMG p. 266)
# ==============================================================================

def handle_fear_or_horror_save(target: Any, kind: str, dc: int, game_state: Any, forced_roll: Optional[int] = None) -> Tuple[bool, str]:
    if not _opt_enabled(game_state, "opt_fear_horror", False):
        return False, "La regola opzionale Paura e Orrore (DMG p. 266) è disabilitata dal Master."
    k_low = str(kind or "fear").lower()
    stat = "SAG" if k_low == "fear" else ("SAN" if _opt_enabled(game_state, "opt_honor_sanity", False) else "CAR")
    mod = get_effective_save_bonus_from_dict(target, stat)
    roll_tot = int(forced_roll) + mod if forced_roll is not None else roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")["total"]
    passed = roll_tot >= int(dc)

    if k_low == "fear":
        if passed:
            msg = f"😨 [PAURA DMG p.266] {target.name} supera TS {stat} {roll_tot} >= CD {dc}!"
        else:
            if "Spaventato" not in target.conditions:
                target.conditions.append("Spaventato")
            _sync_conds(target)
            msg = f"😱 [PAURA DMG p.266] {target.name} fallisce TS {stat} {roll_tot} < CD {dc} ed è SPAVENTATO!"
    else:
        if passed:
            msg = f"🕯️ [ORRORE DMG p.266] {target.name} supera TS {stat} {roll_tot} >= CD {dc}!"
        else:
            mad = roll_madness("short")
            if not isinstance(getattr(target, "madness_effects", None), list):
                target.madness_effects = []
            target.madness_effects.append(mad)
            tag = f"{mad['tier']} ({mad['duration']})"
            if tag not in target.conditions:
                target.conditions.append(tag)
            _sync_conds(target)
            msg = f"🧠 [ORRORE DMG p.266] {target.name} fallisce TS {stat} {roll_tot} < CD {dc} -> {mad['tier']}: {mad['desc']}"

    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


def handle_healing_surge(actor: Any, count: int, game_state: Any) -> Tuple[bool, str]:
    """DMG p. 266: Usa un'Azione per spendere fino a metà Dadi Vita e curarsi subito."""
    if not _opt_enabled(game_state, "opt_healing_surges", False):
        return False, "Gli Impulsi Curativi (DMG p. 266) sono disabilitati dal Master."
    fs = getattr(actor, "full_sheet", None)
    if not isinstance(fs, dict):
        fs = {}
        actor.full_sheet = fs
    max_hd = max(1, int(fs.get("hit_dice_max", entity_get_total_level(actor)) or 1))
    cur_hd = int(fs.get("hit_dice_current", max_hd) if fs.get("hit_dice_current") is not None else max_hd)
    req = max(1, min(max(1, max_hd // 2), int(count or 1), cur_hd))
    if cur_hd <= 0:
        return False, f"{actor.name} non ha Dadi Vita rimasti per l'Impulso Curativo!"

    hd_type = str(fs.get("hit_dice_type", "d8") or "d8").lower()
    if "d" not in hd_type:
        hd_type = "d8"
    die_sides = int("".join(ch for ch in hd_type.split("d")[-1] if ch.isdigit()) or 8)
    con_mod = entity_get_attr_mod(actor, "COS")
    total_heal = sum(max(1, random.randint(1, die_sides) + con_mod) for _ in range(req))

    fs["hit_dice_current"] = cur_hd - req
    old_hp = actor.hp
    actor.hp = min(actor.max_hp, max(0, actor.hp) + total_heal)
    fs["hp_current"] = actor.hp
    if actor.hp > 0 and "Incosciente" in getattr(actor, "conditions", []):
        actor.conditions = [c for c in actor.conditions if c not in ("Incosciente", "Stabilizzato")]
        _sync_conds(actor)
    if getattr(game_state, "combat_active", False):
        actor.has_acted_this_turn = True

    msg = f"💚 [IMPULSO CURATIVO DMG p.266] {actor.name} spende {req}d{die_sides} Dadi Vita ({fs['hit_dice_current']}/{max_hd} rimasti) e recupera {actor.hp - old_hp} PF ({actor.hp}/{actor.max_hp})!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(actor.name, actor.hp, actor.max_hp, actor.initiative, actor.conditions, getattr(actor, "temp_hp", 0)))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


# ==============================================================================
# 6. VARIANTI INIZIATIVA DMG p. 270 (SIDE & SPEED FACTOR)
# ==============================================================================

def compute_speed_factor_modifier(entity: Any, declared_action: Optional[str] = None) -> int:
    """DMG p. 270: Modificatore Speed Factor in base a Taglia e Azione Dichiarata."""
    raw_sz = getattr(entity, "size", 1)
    if isinstance(raw_sz, str):
        sz_map = {"minuscola": 0, "tiny": 0, "piccola": 0, "small": 0, "media": 1, "medium": 1, "grande": 2, "large": 2, "enorme": 3, "huge": 3, "mastodontica": 4, "gargantuan": 4}
        sz = sz_map.get(raw_sz.strip().lower(), 1)
    else:
        try:
            sz = int(raw_sz or 1)
        except (ValueError, TypeError):
            sz = 1
    size_mod = 0
    if sz >= 3:
        size_mod = -5   # Enorme / Gargantuesca
    elif sz == 2:
        size_mod = -2   # Grande
    elif sz <= 0:
        size_mod = 2    # Piccola / Minuscola

    if declared_action is None:
        fs = getattr(entity, "full_sheet", None)
        declared_action = (fs.get("speed_factor_action") if isinstance(fs, dict) else None) or getattr(entity, "speed_factor_action", "melee")
    act = str(declared_action or "melee").lower()
    act_mod = 0
    if "heavy" in act or "pesante" in act or "loading" in act or "carica" in act:
        act_mod = -2
    elif "light" in act or "leggera" in act or "finesse" in act or "accurata" in act:
        act_mod = 2
    elif "ranged" in act or "distanza" in act:
        act_mod = -5
    elif "spell" in act or "incant" in act:
        lvl = 1
        for tok in act.split():
            if tok.isdigit():
                lvl = int(tok)
                break
        act_mod = -lvl
    return size_mod + act_mod


def apply_initiative_variant(game_state: Any, side_rolls: Optional[Tuple[int, int]] = None) -> List[str]:
    """Applica l'eventuale variante d'Iniziativa DMG attiva su GameState.automation_settings."""
    if not game_state:
        return []
    iv = (getattr(game_state, "automation_settings", {}) or {}).get("opt_init_variant", "standard")
    in_c = [p for p in getattr(game_state, "players", []) if getattr(p, "in_combat", True)]
    if not in_c:
        return []
    logs: List[str] = []
    if iv == "side":
        r_party = side_rolls[0] if side_rolls else roll_dice("1d20")["total"]
        r_enemies = side_rolls[1] if side_rolls else roll_dice("1d20")["total"]
        game_state.side_initiative_rolls = {"party": r_party, "enemies": r_enemies}
        for p in in_c:
            is_party = bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None))
            p.initiative = r_party if is_party else r_enemies
        logs.append(f"🎲 [INIZIATIVA DI SQUADRA DMG p.270] Eroi: {r_party} | Nemici: {r_enemies}")
    elif iv == "speed_factor":
        for p in in_c:
            decl = getattr(p, "speed_factor_declared_action", None) or getattr(p, "speed_factor_action", "melee")
            sf_mod = compute_speed_factor_modifier(p, decl)
            dex_mod = entity_get_attr_mod(p, "DES")
            p.initiative = roll_dice("1d20")["total"] + dex_mod + sf_mod
        logs.append("⚡ [FATTORE VELOCITA' DMG p.270] Iniziativa ricalcolata per taglia e azione dichiarata!")
    game_state.players.sort(key=lambda p: (getattr(p, "in_combat", True), getattr(p, "initiative", 0)), reverse=True)
    return logs


# ==============================================================================
# 7. RACCOLTA VELENI, TRAPPOLE COMPLESSE, ARMI D'ASSEDIO, SENZIENTI, ARTEFATTI
# ==============================================================================

def handle_harvest_poison(actor: Any, target_name: str, poison_name: str, game_state: Any, forced_roll: Optional[int] = None) -> Tuple[bool, str]:
    """DMG p. 258: Estrazione veleno (CD 20 Natura o Strumenti Avvelenatore; fallire >=5 avvelena)."""
    int_mod = entity_get_attr_mod(actor, "INT")
    pb = ((entity_get_total_level(actor) - 1) // 4) + 2
    sheet = getattr(actor, "full_sheet", {}) or {}
    skills = [str(s).lower() for s in (sheet.get("skills", []) or [])]
    has_prof = any("natura" in s or "nature" in s or "avvelen" in s or "poison" in s for s in skills)
    bonus = int_mod + (pb if has_prof else 0)
    raw = int(forced_roll) if forced_roll is not None else roll_dice("1d20")["total"]
    tot = raw + bonus

    if hasattr(game_state, "advance_game_time"):
        game_state.advance_game_time(minutes=random.randint(1, 6))

    if tot >= 20:
        p_key = poison_name or "Veleno Base (Basic Poison)"
        if not isinstance(sheet, dict):
            sheet = {}
            actor.full_sheet = sheet
        inv = sheet.setdefault("inventory", [])
        inv.append({
            "name": f"Veleno Raccolto: {p_key}",
            "type": "Consumabile",
            "qty": 1,
            "weight": 0.5,
            "desc": f"Estratto da {target_name or 'creatura velenosa'} (DMG p. 258).",
        })
        msg = f"🧪 [RACCOLTA VELENO DMG p.258] {actor.name} supera CD 20 ({tot}) ed estrae 1 dose di '{p_key}'!"
    elif tot <= 15:
        from server.rules.combat import apply_damage
        dmg = roll_dice("2d6")["total"]
        apply_damage(actor, dmg, damage_type="Veleno", game_state=game_state)
        if "Avvelenato" not in actor.conditions:
            actor.conditions.append("Avvelenato")
        _sync_conds(actor)
        msg = f"☠️ [RACCOLTA VELENO FALLITA] {actor.name} ottiene {tot} (scarto >=5 sotto CD 20) e si espone al veleno (-{dmg} PF, Avvelenato)!"
    else:
        msg = f"❌ [RACCOLTA VELENO] {actor.name} fallisce CD 20 ({tot}): la sacca di veleno si danneggia senza effetto."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


def register_complex_trap(game_state: Any, trap_data: Dict[str, Any]) -> Dict[str, Any]:
    if not hasattr(game_state, "active_complex_traps") or not isinstance(game_state.active_complex_traps, list):
        game_state.active_complex_traps = []
    trap = {
        "id": trap_data.get("id") or f"trap_{len(game_state.active_complex_traps) + 1}",
        "name": trap_data.get("name", "Lame Rotanti del Corridoio"),
        "initiative": int(trap_data.get("initiative", 20) or 20),
        "save_stat": str(trap_data.get("save_stat", "DES")).upper(),
        "dc": int(trap_data.get("dc", 15) or 15),
        "damage_formula": str(trap_data.get("damage_formula", "2d10")),
        "damage_type": str(trap_data.get("damage_type", "Tagliente")),
        "disarm_dc": int(trap_data.get("disarm_dc", 16) or 16),
        "disarm_progress": 0,
        "disarm_required": int(trap_data.get("disarm_required", 2) or 2),
        "active": True,
    }
    game_state.active_complex_traps.append(trap)
    return trap


def trigger_complex_traps_at_round_start(game_state: Any, init_band: int = 20) -> List[str]:
    """Attiva Trappole Complesse a Iniziativa 20 o 10 contro i combattenti attivi."""
    traps = getattr(game_state, "active_complex_traps", None)
    if not traps or not isinstance(traps, list):
        return []
    targets = [p for p in getattr(game_state, "players", []) if getattr(p, "in_combat", True) and getattr(p, "hp", 0) > 0]
    if not targets:
        return []
    from server.rules.combat import apply_damage
    logs: List[str] = []
    for t in traps:
        if not t.get("active", True) or int(t.get("initiative", 20)) != int(init_band):
            continue
        stat = t.get("save_stat", "DES")
        dc = int(t.get("dc", 15))
        dmg_f = t.get("damage_formula", "2d10")
        dmg_type = t.get("damage_type", "Tagliente")
        hit_summary = []
        for p in targets:
            mod = get_effective_save_bonus_from_dict(p, stat)
            sv = roll_dice(f"1d20{'+' if mod >= 0 else ''}{mod}")["total"]
            raw = roll_dice(dmg_f)["total"]
            app_d = raw // 2 if sv >= dc else raw
            fin, _, _, _ = apply_damage(p, app_d, damage_type=dmg_type, game_state=game_state)
            hit_summary.append(f"{p.name}: -{fin}{' (dimezz.)' if sv >= dc else ''}")
        msg = f"⚙️ [TRAPPOLA COMPLESSA Init {init_band} - {t['name']} CD {dc} {stat}] " + ", ".join(hit_summary)
        logs.append(msg)
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        if hasattr(game_state, "log_dm_message"):
            game_state.log_dm_message(f"[TRAP] {msg}")
    return logs


SIEGE_EQUIPMENT_CATALOG: Dict[str, Dict[str, Any]] = {
    "ballista": {"name": "Balista", "ac": 15, "hp": 50, "attack_bonus": 6, "damage": "3d10", "damage_type": "Perforante", "range_ft": "120/480", "actions_needed": 3},
    "mangonel": {"name": "Mangano / Catapulta", "ac": 15, "hp": 100, "attack_bonus": 5, "damage": "5d10", "damage_type": "Contundente", "range_ft": "200/800", "actions_needed": 5},
    "trebuchet": {"name": "Trabucco", "ac": 15, "hp": 150, "attack_bonus": 5, "damage": "8d10", "damage_type": "Contundente", "range_ft": "300/1200", "actions_needed": 5},
    "cannon": {"name": "Cannone", "ac": 19, "hp": 75, "attack_bonus": 6, "damage": "8d10", "damage_type": "Contundente", "range_ft": "600/2400", "actions_needed": 3},
    "ram": {"name": "Ariete (Battering Ram)", "ac": 15, "hp": 100, "attack_bonus": 8, "damage": "3d10", "damage_type": "Contundente", "range_ft": "5", "actions_needed": 1, "siege_double": True},
}


def handle_siege_action(engine_key: str, target_name: str, game_state: Any) -> Tuple[bool, str]:
    info = SIEGE_EQUIPMENT_CATALOG.get(str(engine_key or "ballista").lower())
    if not info:
        return False, f"Arma d'assedio '{engine_key}' non riconosciuta."
    target = game_state.find_player(target_name) if target_name else None
    atk_r = roll_dice(f"1d20+{info['attack_bonus']}")["total"]
    dmg_r = roll_dice(info["damage"])["total"]
    if target:
        hit = atk_r >= int(getattr(target, "ac", 10))
        if hit:
            from server.rules.combat import apply_damage
            if info.get("siege_double") and getattr(target, "is_object", False):
                dmg_r *= 2
            fin, _, _, _ = apply_damage(target, dmg_r, damage_type=info["damage_type"], game_state=game_state)
            msg = f"🏰 [ASSEDIO - {info['name']}] TxC {atk_r} COLPISCE {target.name} (CA {getattr(target, 'ac', 10)}): infligge {fin} danni ({info['damage_type']})!"
        else:
            msg = f"🏰 [ASSEDIO - {info['name']}] TxC {atk_r} MANCA {target.name} (CA {getattr(target, 'ac', 10)})."
    else:
        msg = f"🏰 [ASSEDIO - {info['name']}] Tiro {atk_r}, danno potenziale {dmg_r} {info['damage_type']} (Gittata {info['range_ft']} ft)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    return True, msg


def calculate_sentient_ego(int_score: int, wis_score: int, cha_score: int, special_bonuses: int = 0) -> int:
    """DMG p. 214: Punteggio Ego di un oggetto magico senziente."""
    ego = max(0, (int_score - 10) // 2) + max(0, (wis_score - 10) // 2) + max(0, (cha_score - 10) // 2) + int(special_bonuses or 0)
    return max(1, ego)


def resolve_sentient_conflict(wielder: Any, item_name: str, ego_score: int, game_state: Any, forced_roll: Optional[int] = None) -> Tuple[bool, str]:
    cha_save = get_effective_save_bonus_from_dict(wielder, "CAR")
    r = (int(forced_roll) + cha_save) if forced_roll is not None else roll_dice(f"1d20{'+' if cha_save >= 0 else ''}{cha_save}")["total"]
    won = r >= int(ego_score)
    msg = (
        f"🗡️ [CONFLITTO EGO DMG p.216 - {item_name}] {wielder.name} supera TS CAR {r} >= Ego {ego_score} e mantiene il controllo!"
        if won else
        f"😈 [CONFLITTO EGO DMG p.216 - {item_name}] {wielder.name} fallisce TS CAR {r} < Ego {ego_score}: l'oggetto assume il controllo per 1d12 ore!"
    )
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    return won, msg


ARTIFACT_MINOR_BENEFICIAL = [
    "+1 ad una caratteristica (fino a 24)",
    "Resistenza a un tipo di danno scelto",
    "Competenza in un'abilità scelta",
    "Immunità alle malattie mentre sintonizzato",
    "Lanci un trucchetto a volontà",
]
ARTIFACT_MAJOR_BENEFICIAL = [
    "+2 ad una caratteristica (fino a 24)",
    "Rigeneri 1d6 PF all'inizio del turno finché hai almeno 1 PF",
    "Bonus +1 alla CA",
    "Immunità a essere Affascinato e Spaventato",
    "Puoi lanciare un incantesimo di 4°-7° livello 1/giorno",
]
ARTIFACT_MINOR_DETRIMENTAL = [
    "Svantaggio alle prove con un certo tipo di creatura",
    "I tuoi occhi emettono bagliori spettrali nel raggio di 3 m",
    "Il tuo allineamento tende leggermente verso quello dell'artefatto",
    "Devi mangiare e bere il doppio della razione normale",
]
ARTIFACT_MAJOR_DETRIMENTAL = [
    "Subisci 4d10 danni necrotici al primo legame di sintonia",
    "Quando esaurisci l'ultima carica potresti attrarre un'entità ostile",
    "Quando usi una proprietà maggiore, i PF Max scendono di 1d6 fino a riposo lungo",
    "Non puoi recuperare PF tramite cure non magiche",
]


def roll_artifact_properties(minor_ben: int = 2, major_ben: int = 1, minor_det: int = 1, major_det: int = 1) -> Dict[str, Any]:
    return {
        "minor_beneficial": [random.choice(ARTIFACT_MINOR_BENEFICIAL) for _ in range(max(0, minor_ben))],
        "major_beneficial": [random.choice(ARTIFACT_MAJOR_BENEFICIAL) for _ in range(max(0, major_ben))],
        "minor_detrimental": [random.choice(ARTIFACT_MINOR_DETRIMENTAL) for _ in range(max(0, minor_det))],
        "major_detrimental": [random.choice(ARTIFACT_MAJOR_DETRIMENTAL) for _ in range(max(0, major_det))],
        "destruction": "Può essere distrutto solo gettandolo nella fornace del Piano Originario o tramite Desiderio guidato.",
    }


def level_up_sidekick(entity: Any, role: str = "warrior", target_level: Optional[int] = None) -> Dict[str, Any]:
    """TCE Sidekicks: Avanza Esperto / Combattente / Incantatore."""
    fs = getattr(entity, "full_sheet", None)
    if not isinstance(fs, dict):
        fs = {}
        entity.full_sheet = fs
    cur_l = max(1, int(fs.get("level", getattr(entity, "level", 1)) or 1))
    new_l = max(cur_l + 1, int(target_level)) if target_level else min(20, cur_l + 1)
    r_low = str(role or "warrior").lower()
    con_mod = entity_get_attr_mod(entity, "COS")
    hp_gain = max(1, (5 + con_mod)) * max(1, new_l - cur_l)
    entity.max_hp = int(getattr(entity, "max_hp", 10)) + hp_gain
    entity.hp = int(getattr(entity, "hp", 10)) + hp_gain
    fs["level"] = new_l
    fs["sidekick_role"] = r_low
    fs["hp_max"] = entity.max_hp
    fs["hp_current"] = entity.hp
    return {"name": getattr(entity, "name", "Sidekick"), "role": r_low, "level": new_l, "max_hp": entity.max_hp}


def adjust_renown_or_piety(entity: Any, track: str, delta: int, label: str = "") -> int:
    """DMG p. 22 / Theros Piety: Traccia Fama (Renown) o Pietà (Piety) sulla scheda."""
    fs = getattr(entity, "full_sheet", None)
    if not isinstance(fs, dict):
        fs = {}
        entity.full_sheet = fs
    key = "piety" if "piet" in str(track).lower() else "renown"
    cur = int(fs.get(key, 0) or 0)
    new_v = max(0, cur + int(delta or 0))
    fs[key] = new_v
    if label:
        fs[f"{key}_org"] = label
    return new_v


BASTION_FACILITIES_CATALOG: Dict[str, Dict[str, Any]] = {
    "barracks": {"name": "Caserma (Barracks)", "order": "Recruit Bastion Defenders", "cost_gp": 500},
    "arcane_study": {"name": "Studio Arcano", "order": "Craft Magic Item / Spell Focus", "cost_gp": 1000},
    "sanctuary": {"name": "Santuario", "order": "Sacred Charm & Healing", "cost_gp": 800},
    "workshop": {"name": "Officina (Workshop)", "order": "Craft Mundane/Siege Gear", "cost_gp": 600},
    "treasury": {"name": "Tesoreria", "order": "Trade & Collect Dividends (+2d6x10 MO)", "cost_gp": 1200},
}


def resolve_bastion_turn(facility_key: str) -> Dict[str, Any]:
    fac = BASTION_FACILITIES_CATALOG.get(str(facility_key or "treasury").lower(), BASTION_FACILITIES_CATALOG["treasury"])
    gold_r = sum(random.randint(1, 6) for _ in range(2)) * 10 if "treasury" in str(facility_key).lower() else 0
    return {"facility": fac["name"], "order": fac["order"], "gold_dividend": gold_r}


def handle_optional_rule_action_request(data: dict, player: Any, game_state: Any) -> None:
    """Dispatcher unificato OPTIONAL_RULE_ACTION_REQUEST dal client/DM per DMG, XGtE & TCE."""
    action = str(data.get("action", "")).strip().lower()
    actor = game_state.find_player(data.get("actor_name")) if data.get("actor_name") else player
    target = game_state.find_player(data.get("target_name")) if data.get("target_name") else actor

    if action == "morale_check":
        evaluate_morale_checks(game_state, trigger_reason=data.get("reason", "manual"), forced_save_roll=data.get("forced_roll"))
        return
    if action == "hero_point":
        ok, msg = handle_spend_hero_point(actor, data.get("mode", "roll_bonus"), game_state)
        if not ok and getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply(msg))
        return
    if action in ("fear_save", "horror_save"):
        kind = "fear" if "fear" in action else "horror"
        ok, msg = handle_fear_or_horror_save(target, kind, int(data.get("dc", 13) or 13), game_state, forced_roll=data.get("forced_roll"))
        if not ok and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(msg))
        return
    if action == "healing_surge":
        ok, msg = handle_healing_surge(actor, int(data.get("count", 1) or 1), game_state)
        if not ok and getattr(actor, "conn", None):
            send_message(actor.conn, make_error_reply(msg))
        return
    if action == "harvest_poison":
        handle_harvest_poison(actor, data.get("target_name", ""), data.get("poison_name", ""), game_state, forced_roll=data.get("forced_roll"))
        return
    if action == "siege_action":
        handle_siege_action(data.get("engine", "ballista"), data.get("target_name", ""), game_state)
        return
    if action == "complex_trap_add":
        t = register_complex_trap(game_state, data.get("trap", data))
        broadcast(game_state, make_chat_broadcast("Sistema", f"⚙️ [TRAPPOLA COMPLESSA REGISTRATA] {t['name']} (Init {t['initiative']}, CD {t['dc']} {t['save_stat']}, {t['damage_formula']})."))
        return
    if action == "sentient_conflict":
        resolve_sentient_conflict(target, data.get("item_name", "Spada Senziente"), int(data.get("ego", 12) or 12), game_state, forced_roll=data.get("forced_roll"))
        return
    if action == "cure_injury":
        ok, msg = cure_lingering_injury(target, method=data.get("method", "regenerate"), injury_name=data.get("injury_name"))
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, getattr(target, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
    if action == "roll_artifact":
        props = roll_artifact_properties()
        msg = f"👑 [ARTEFATTO DMG p.219] Benefiche: {', '.join(props['major_beneficial'][:1])} | Deteriori: {', '.join(props['major_detrimental'][:1])}"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return
    if action == "sidekick_level_up" and target:
        res = level_up_sidekick(target, role=data.get("role", "warrior"), target_level=data.get("level"))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🤝 [SEGUACE TCE] {res['name']} ({res['role'].capitalize()}) sale al Livello {res['level']} (PF Max: {res['max_hp']})!"))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
    if action == "renown_piety" and target:
        val = adjust_renown_or_piety(target, data.get("track", "renown"), int(data.get("delta", 1) or 1), data.get("label", ""))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🏛️ [{str(data.get('track', 'Fama')).upper()}] {target.name}: {val}"))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
    if action == "declare_speed_factor":
        if not actor:
            return
        sp_action = str(data.get("speed_action", "melee") or "melee").strip().lower()
        sp_lvl = int(data.get("spell_level", 1) or 1)
        if sp_action == "spell":
            actor.speed_factor_declared_action = f"spell_{max(1, min(9, sp_lvl))}"
        elif sp_action == "cantrip":
            actor.speed_factor_declared_action = "cantrip"
        else:
            actor.speed_factor_declared_action = sp_action
        mod_v = compute_speed_factor_modifier(actor, actor.speed_factor_declared_action)
        broadcast(
            game_state,
            make_chat_broadcast(
                "Sistema",
                f"⚡ [FATTORE VELOCITÀ DMG p.270] {actor.name} dichiara azione '{actor.speed_factor_declared_action}' (Modificatore Iniziativa {mod_v:+d}).",
            ),
        )
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "toggle_squeeze":
        if not actor:
            return
        conds = getattr(actor, "conditions", None)
        if not isinstance(conds, list):
            conds = []
            actor.conditions = conds
        active = bool(getattr(actor, "is_squeezing", False)) or any("spremere" in str(c).lower() or "squeez" in str(c).lower() for c in conds)
        if active:
            actor.is_squeezing = False
            actor.conditions = [c for c in conds if "spremere" not in str(c).lower() and "squeez" not in str(c).lower()]
            msg = f"📦 [MOVIMENTO] {actor.name} esce dallo spazio stretto (Squeezing disattivato)."
        else:
            actor.is_squeezing = True
            if not any("spremere" in str(c).lower() or "squeez" in str(c).lower() for c in conds):
                conds.append("Spremere (Squeezing)")
            msg = f"📦 [SPREMERE - PHB p.192] {actor.name} attraversa uno spazio stretto (movimento dimezzato / doppio costo, svantaggio TpC e TS DES, vantaggio ai TpC contro di lui)."
        _sync_conds(actor)
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(actor.name, getattr(actor, "hp", 0), getattr(actor, "max_hp", 0), getattr(actor, "initiative", 0), actor.conditions, getattr(actor, "temp_hp", 0)))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "jump_check":
        if not actor:
            return
        from common.dnd5e_tables import calculate_jump_distances
        running = bool(data.get("running_start", True))
        str_sc = entity_get_effective_attr(actor, "FOR")
        j = calculate_jump_distances(str_sc, running_start=running)
        mode_lbl = "con rincorsa (10 ft / 3m)" if running else "da fermo (senza rincorsa)"
        msg = (
            f"🦘 [SALTO PHB p.182] {actor.name} (FOR {j['str_score']}, {mode_lbl}): "
            f"Salto in Lungo fino a {j['long_jump_ft']} ft ({j['long_jump_m']} m) | "
            f"Salto in Alto fino a {j['high_jump_ft']} ft ({j['high_jump_m']} m)."
        )
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    if action == "racial_trait":
        if not actor:
            return
        trait = str(data.get("trait", "") or "").strip().lower()
        lvl = max(1, entity_get_total_level(actor))
        fs = getattr(actor, "full_sheet", None)
        if not isinstance(fs, dict):
            fs = {}
            actor.full_sheet = fs
        if trait == "breath_weapon":
            from common.dnd5e_tables import entity_find_resource, entity_spend_resource
            if entity_find_resource(actor, "soffio draconico", "breath weapon") is None:
                fs.setdefault("custom_resources", []).append({"name": "Soffio Draconico", "current": 1, "max": 1, "reset_on": "short"})
            ok, nc, mx = entity_spend_resource(actor, ("soffio draconico", "breath weapon"), 1)
            if not ok:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Soffio Draconico già utilizzato fino al prossimo Riposo Breve o Lungo."))
                return
            dice_n = 2 if lvl < 6 else (3 if lvl < 11 else (4 if lvl < 16 else 5))
            dc = 8 + entity_get_attr_mod(actor, "COS") + ((lvl - 1) // 4 + 2)
            dmg_r = roll_dice(f"{dice_n}d6")
            actor.has_acted_this_turn = True
            msg = f"🐉 [SOFFIO DRACONICO - CD {dc} DES] {actor.name} esala energia draconica per {dmg_r['total']} ({dice_n}d6) danni! ({nc}/{mx} usi)"
            if target and target is not actor:
                con_or_dex = get_effective_save_bonus_from_dict(target, "DES")
                sr = roll_dice(f"1d20{'+' if con_or_dex >= 0 else ''}{con_or_dex}")["total"]
                raw = (dmg_r["total"] // 2) if sr >= dc else dmg_r["total"]
                from server.rules.combat import apply_damage
                fd, _, _, _ = apply_damage(target, raw, damage_type=str(data.get("damage_type", "Fuoco")), game_state=game_state)
                msg += f" -> {target.name} TS DES {sr}: {fd} danni!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return
        if trait == "healing_hands":
            from common.dnd5e_tables import entity_find_resource, entity_spend_resource
            if entity_find_resource(actor, "mani guaritrici", "healing hands") is None:
                fs.setdefault("custom_resources", []).append({"name": "Mani Guaritrici", "current": 1, "max": 1, "reset_on": "long"})
            ok, nc, mx = entity_spend_resource(actor, ("mani guaritrici", "healing hands"), 1)
            if not ok:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Mani Guaritrici già utilizzate fino al Riposo Lungo."))
                return
            t_ent = target or actor
            old_hp = getattr(t_ent, "hp", 0)
            t_ent.hp = min(getattr(t_ent, "max_hp", old_hp + lvl), old_hp + lvl)
            actor.has_acted_this_turn = True
            msg = f"✨ [MANI GUARITRICI] {actor.name} cura {t_ent.name} di +{t_ent.hp - old_hp} PF ({t_ent.hp}/{getattr(t_ent, 'max_hp', t_ent.hp)})!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_player_stats_update(t_ent.name, t_ent.hp, getattr(t_ent, "max_hp", t_ent.hp), getattr(t_ent, "initiative", 0), getattr(t_ent, "conditions", []), getattr(t_ent, "temp_hp", 0)))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return
        if trait == "stones_endurance":
            from common.dnd5e_tables import entity_find_resource, entity_spend_resource
            if entity_find_resource(actor, "tenacia della pietra", "stone's endurance") is None:
                fs.setdefault("custom_resources", []).append({"name": "Tenacia della Pietra", "current": 1, "max": 1, "reset_on": "short"})
            ok, nc, mx = entity_spend_resource(actor, ("tenacia della pietra", "stone's endurance"), 1)
            if not ok:
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Tenacia della Pietra già usata fino al Riposo Breve/Lungo."))
                return
            con_m = entity_get_attr_mod(actor, "COS")
            red = max(0, roll_dice("1d12")["total"] + con_m)
            actor.reaction_used_this_turn = True
            actor.stones_endurance_shield = red
            msg = f"🪨 [TENACIA DELLA PIETRA] {actor.name} prepara uno scudo di pietra riducendo i prossimi danni subiti fino a {red} PF (1d12 + {con_m})!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return
        if trait == "feline_agility":
            if getattr(actor, "feline_agility_spent", False):
                if getattr(actor, "conn", None):
                    send_message(actor.conn, make_error_reply("Agilità Felina richiede di rimanere fermo 1 turno per ricaricarsi."))
                return
            actor.feline_agility_spent = True
            actor.feline_agility_active = True
            msg = f"🐆 [AGILITÀ FELINA] {actor.name} raddoppia la velocità di movimento fino alla fine del turno!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return

    if action == "bastion_order":
        res = resolve_bastion_turn(data.get("facility", "treasury"))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🏰 [BASTIONE] {res['facility']} -> {res['order']}" + (f" (+{res['gold_dividend']} MO)" if res["gold_dividend"] else "")))
        return

    from server.dm_dmg_systems import (
        calculate_monster_cr_dmg,
        resolve_mob_attack,
        roll_potion_miscibility,
        resolve_spell_scroll_use,
        resolve_social_check,
        adjust_npc_loyalty,
        create_vehicle_state,
        apply_vehicle_damage,
        resolve_wilderness_travel_checks,
        resolve_wilderness_hazard,
    )

    if action == "calc_cr":
        res = calculate_monster_cr_dmg(
            hp=int(data.get("hp", 50) or 50),
            ac=int(data.get("ac", 14) or 14),
            dpr=float(data.get("dpr", 12) or 12),
            attack_bonus=int(data.get("attack_bonus", 4) or 4),
            save_dc=int(data.get("save_dc", 13) or 13),
            use_save_dc=bool(data.get("use_save_dc", False)),
            has_resistances=bool(data.get("has_resistances", False)),
            has_immunities=bool(data.get("has_immunities", False)),
            magic_resistance=bool(data.get("magic_resistance", False)),
        )
        msg = (
            f"🧮 [CALCOLATORE CR DMG p.274] HP Effettivi: {res['effective_hp']} | CA Effettiva: {res['effective_ac']} | "
            f"CR Difensivo: {res['defensive_cr']} | CR Offensivo: {res['offensive_cr']} -> "
            f"**CR Finale: {res['final_cr']}** (Bonus Comp. +{res['proficiency_bonus']}, {res['xp']} PE)"
        )
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    if action == "mob_attack":
        if data.get("respect_opt") and not _opt_enabled(game_state, "opt_mob_attacks", False):
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Attacchi di Folla (Mob Attacks) disabilitati nel Pannello Automazioni."))
            return
        t_ac = int(data.get("target_ac") or (getattr(target, "ac", 15) if target else 15))
        res = resolve_mob_attack(
            num_attackers=int(data.get("num_attackers", 8) or 8),
            attack_bonus=int(data.get("attack_bonus", 4) or 4),
            target_ac=t_ac,
            damage_per_hit=int(data.get("damage_per_hit", 5) or 5),
            advantage=bool(data.get("advantage", False)),
            disadvantage=bool(data.get("disadvantage", False)),
        )
        t_name = target.name if target else f"CA {t_ac}"
        msg = (
            f"👥 [ATTACCO DI FOLLA DMG p.250] {res['num_attackers']} attaccanti vs {t_name} (CA {t_ac}, d20={res['d20_needed']}+): "
            f"{res['attackers_per_hit']} per colpo -> **{res['hits']} colpi automatici** ({res['total_damage']} danni)!"
        )
        if target and res["total_damage"] > 0 and bool(data.get("apply_damage", False)):
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(target, res["total_damage"], damage_type=str(data.get("damage_type", "Tagliente")), game_state=game_state)
            msg += f" -> Danni applicati a {target.name}: {fd} PF."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "potion_miscibility":
        res = roll_potion_miscibility(d100_roll=data.get("forced_roll"))
        msg = f"🧪 [MISCIBILITÀ POZIONI DMG p.140] {actor.name if actor else 'PG'}: {res['summary']}"
        if actor and res["self_damage"] > 0 and bool(data.get("apply_damage", True)):
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(actor, res["self_damage"], damage_type="Forza", game_state=game_state)
            msg += f" (Subiti {fd} PF)"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "spell_scroll":
        mishap_on = _opt_enabled(game_state, "opt_scroll_mishap", True)
        res = resolve_spell_scroll_use(
            spell_level=int(data.get("spell_level", 3) or 3),
            on_class_list=bool(data.get("on_class_list", True)),
            max_castable_level=int(data.get("max_castable_level", 1) or 1),
            caster_ability_mod=int(data.get("caster_ability_mod", 3) or 3),
            check_roll=data.get("forced_check_roll"),
            mishap_save_mod=int(data.get("mishap_save_mod", 0) or 0),
            mishap_save_roll=data.get("forced_save_roll"),
            mishap_table_roll=data.get("forced_mishap_roll"),
            trigger_mishap_on_fail=mishap_on,
        )
        msg = f"📜 [PERGAMENA MAGICA DMG p.140/200] {actor.name if actor else 'Incantatore'}: {res['summary']}"
        if actor and res.get("mishap") and res["mishap"].get("damage", 0) > 0 and bool(data.get("apply_damage", True)):
            from server.rules.combat import apply_damage
            fd, _, _, _ = apply_damage(actor, res["mishap"]["damage"], damage_type="Forza", game_state=game_state)
            msg += f" (Subiti {fd} PF)"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "social_loyalty":
        parts: List[str] = []
        if data.get("check_total") is not None or data.get("attitude"):
            soc = resolve_social_check(data.get("attitude", "indifferent"), int(data.get("check_total", 12) or 12))
            parts.append(f"🗣️ [INTERAZIONE DMG p.245 | {soc['attitude'].upper()} | Prova {soc['check_total']}] {soc['description']}")
        if data.get("loyalty_delta") is not None and target:
            cur_l = int(getattr(target, "npc_loyalty", getattr(target, "full_sheet", {}).get("npc_loyalty", 10) if isinstance(getattr(target, "full_sheet", None), dict) else 10))
            loy = adjust_npc_loyalty(cur_l, int(data.get("loyalty_delta", 0) or 0))
            target.npc_loyalty = loy["loyalty"]
            if isinstance(getattr(target, "full_sheet", None), dict):
                target.full_sheet["npc_loyalty"] = loy["loyalty"]
            parts.append(f"🤝 [LEALTÀ PNG DMG p.93] {target.name}: {loy['description']}")
        if parts:
            broadcast(game_state, make_chat_broadcast("Sistema", " | ".join(parts)))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "vehicle_damage":
        if not isinstance(getattr(game_state, "vehicles", None), dict):
            game_state.vehicles = {}
        v_name = str(data.get("vehicle_name") or "Veliero del Party").strip()
        v_tpl = str(data.get("template") or "sailing_ship").strip().lower()
        if v_name not in game_state.vehicles or data.get("reset"):
            game_state.vehicles[v_name] = create_vehicle_state(v_tpl, custom_name=v_name)
        veh = game_state.vehicles[v_name]
        res = apply_vehicle_damage(veh, int(data.get("damage", 0) or 0), component=str(data.get("component", "hull")))
        msg = (
            f"⛵ [VEICOLI DMG p.119] {veh['name']} ({res['component'].upper()}): {res['status_note']} "
            f"[Scafo {veh['hull']['hp']}/{veh['hull']['max_hp']} | Vele {veh['sails']['hp']}/{veh['sails']['max_hp']} | Timone {veh['helm']['hp']}/{veh['helm']['max_hp']}]"
        )
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "wilderness_check":
        if data.get("hazard_type"):
            hz = resolve_wilderness_hazard(data.get("hazard_type"), save_total=data.get("save_total"), d20_roll=data.get("forced_roll"))
            msg = f"🌲 [PERICOLO SELVAGGIO DMG p.105] {hz['hazard']} (CD {hz['save_dc']}): {'Superato!' if hz['saved'] else 'Fallito!'}"
            if hz.get("damage", 0) > 0:
                msg += f" -> {hz['damage']} danni ({hz['damage_type']})."
                if target and bool(data.get("apply_damage", False)):
                    from server.rules.combat import apply_damage
                    apply_damage(target, hz["damage"], damage_type=hz["damage_type"], game_state=game_state)
            if hz.get("exhaustion_gained", 0) > 0 and target:
                target.exhaustion_level = min(6, int(getattr(target, "exhaustion_level", 0) or 0) + hz["exhaustion_gained"])
                msg += f" -> {target.name} +1 Indebolimento!"
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            return
        nav_r = int(data["nav_roll"]) if data.get("nav_roll") is not None else random.randint(1, 20)
        for_r = int(data["forage_roll"]) if data.get("forage_roll") is not None else random.randint(1, 20)
        wt = resolve_wilderness_travel_checks(
            terrain=str(data.get("terrain", "forest")),
            nav_roll_total=nav_r,
            forage_roll_total=for_r,
            wis_mod=int(data.get("wis_mod", 0) or 0),
            pace=str(data.get("pace", "normal")),
            has_ranger_natural_explorer=bool(data.get("ranger_explorer", False)),
        )
        lost_lbl = "PERSI!" if wt["got_lost"] else "Sulla rotta"
        forage_lbl = (
            "Impossibile ad andatura veloce"
            if not wt["can_forage"]
            else (f"+{wt['food_pounds']} libbre cibo / +{wt['water_gallons']} galloni acqua" if wt["forage_success"] else f"Fallito (CD {wt['forage_dc']})")
        )
        msg = f"🧭 [SOPRAVVIVENZA DMG p.111 - {wt['terrain']}] Orientamento {wt['effective_nav_roll']}/{wt['nav_dc']}: {lost_lbl} | Foraggiamento: {forage_lbl}."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    if action == "beholder_eye_rays":
        if not actor:
            return
        from server.dm_monster_engine import roll_beholder_eye_rays
        tgts = [target] if (target and target is not actor) else None
        roll_beholder_eye_rays(actor, targets=tgts, game_state=game_state, count=int(data.get("count", 3) or 3), forced_indices=data.get("forced_indices"))
        return

    if action == "antimagic_cone":
        if not actor:
            return
        from server.dm_monster_engine import toggle_antimagic_cone
        now_on = toggle_antimagic_cone(
            actor,
            game_state,
            active=bool(data.get("active", True)),
            direction_deg=float(data.get("direction_deg", getattr(actor, "facing_angle", 0.0)) or 0.0),
            range_hexes=int(data.get("range_hexes", 30) or 30),
        )
        broadcast(game_state, make_chat_broadcast("Sistema", f"👁️ [CONO ANTIMAGIA] {actor.name}: {'ATTIVO (150 ft)' if now_on else 'DISATTIVATO'}."))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return

    if action == "toggle_avert_eyes":
        if not actor:
            return
        cur = bool(getattr(actor, "averting_eyes", False))
        new_val = bool(data["avert"]) if "avert" in data else (not cur)
        actor.averting_eyes = new_val
        broadcast(game_state, make_chat_broadcast("Sistema", f"🙈 [SGUARDO PIETRIFICANTE] {actor.name}: {'Distoglie lo sguardo (evita TS inizio turno, svantaggio agli attacchi)' if new_val else 'Riprende a guardare normalmente'}."))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return


def open_optional_rules_tools_dialog(dm_gui, initial_tab: int = 0):
    """Re-export of the 4-tab DM Workbench UI from server.dm_optional_tools_ui."""
    from server.dm_optional_tools_ui import open_optional_rules_tools_dialog as _open_ui

    return _open_ui(dm_gui, initial_tab=initial_tab)

