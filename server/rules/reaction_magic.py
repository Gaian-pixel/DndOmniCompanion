"""
reaction_magic.py - Gestione centralizzata di D&D 5e RAW:
- Bypass armi magiche, argentate e in adamantio + Tratto Magic Weapons
- Tutti i sensi (Vista Cieca / Blindsight, Visione del Vero / Truesight, Percezione Tellurica / Tremorsense,
  Luce Solare / Sunlight Sensitivity, Luce Fioca / Dim Light -5 PP, Keen Senses)
- Enforcement completo delle 15 condizioni (Affascinato, Spaventato con sorgente & blocco movimento,
  Pietrificato, Trattenuto, Avvelenato, Sfinimento 1-6, Invisibile, Accecato, Assordato, Prono,
  Incapacitato/Paralizzato/Stordito/Incosciente auto-release lotta e blocco reazioni)
- Reazioni live (Incantesimo Scudo, Controincantesimo, Deflettere Missili, Schivata Prodigiosa pre-0HP,
  Identificazione Incantesimo XGtE) + Dissolvi Magie (Dispel Magic) + Fuga da Lotta + Temp HP Choice
"""

import re
import random
from typing import Dict, Any, Optional, Tuple, List

from common.dice import roll_dice
from common.i18n import is_condition_active
from common.hex_utils import Hex, hex_linedraw, grid_distance_3d
from common.network_utils import send_message, broadcast
from common.protocol import (
    make_chat_broadcast,
    make_error_reply,
    make_player_stats_update,
    make_prompt_reaction,
    make_map_data_update_broadcast,
    make_game_state,
)
from common.dnd5e_tables import (
    INCAPACITATING_CONDITIONS,
    entity_has_keyword,
    entity_get_class_level,
    entity_get_total_level,
    is_incapacitated_entity as _common_is_incapacitated,
)
from common.item_modifiers import get_effective_attribute_from_dict
from common.character_schema import consume_spell_or_pact_slot


def _has_no_reactions_effect(entity) -> bool:
    for fx in (getattr(entity, "active_effects", None) or []):
        if isinstance(fx, dict) and fx.get("no_reactions"):
            return True
    return False


def is_incapacitated(entity) -> bool:
    return _common_is_incapacitated(entity)


is_incapacitated_entity = is_incapacitated


def get_entity_attack_flags(attacker, weapon_name: str = "", data: Optional[dict] = None) -> Tuple[bool, bool, bool]:
    """
    Ritorna (is_magical, is_silvered, is_adamantine) per un attacco considerando:
    - flag espliciti nel payload (`is_magical`, `is_silvered`, `is_adamantine`, `is_spell`, `weapon_props`)
    - tratto 'Magic Weapons' / 'Armi Magiche' o 'Ki-Empowered Strikes' (Monaco 6+) / 'Primal Strike' (Druido Luna 6+)
    - nome o proprietà dell'arma (+1/+2/+3, magico, argento, adamantio)
    """
    d = data or {}
    w_low = str(weapon_name or "").lower()
    props = [str(p).lower() for p in (d.get("weapon_props") or [])]

    is_mag = bool(d.get("is_magical") or d.get("is_spell"))
    is_silv = bool(d.get("is_silvered"))
    is_adam = bool(d.get("is_adamantine"))

    if any(k in w_low for k in ("+1", "+2", "+3", "magic", "magica", "magico", "incantat", "sacr", "maledett")):
        is_mag = True
    if any(k in props for k in ("magic", "magical", "magica", "magico")):
        is_mag = True

    if any(k in w_low for k in ("argent", "silver")) or any("argent" in p or "silver" in p for p in props):
        is_silv = True
    if any(k in w_low for k in ("adamant",)) or any("adamant" in p for p in props):
        is_adam = True

    if attacker:
        if entity_has_keyword(attacker, "armi magiche", "magic weapons"):
            is_mag = True
        is_unarmed = any(k in w_low for k in ("senz'armi", "unarmed", "pugno", "calci", "artiglio", "morso"))
        if is_unarmed:
            if entity_get_class_level(attacker, "monaco", "monk") >= 6 or entity_has_keyword(attacker, "colpi potenziati dal ki", "ki-empowered strikes"):
                is_mag = True
            ws = getattr(attacker, "wild_shape", None)
            if isinstance(ws, dict) and ws.get("active") and entity_get_class_level(attacker, "druido", "druid") >= 6:
                is_mag = True
        # Controlla inventario equipaggiato su full_sheet
        sheet = getattr(attacker, "full_sheet", None) or {}
        for wep in (sheet.get("weapons", []) or []):
            if isinstance(wep, dict) and w_low and str(wep.get("name", "")).lower() == w_low:
                if int(wep.get("magic_bonus", wep.get("bonus", 0)) or 0) > 0 or wep.get("is_magical"):
                    is_mag = True
                if wep.get("is_silvered"):
                    is_silv = True
                if wep.get("is_adamantine"):
                    is_adam = True

    return is_mag, is_silv, is_adam


def match_conditional_damage_modifier(entry_list: list, dt: str, damage_map: dict,
                                      is_magical: bool = False, is_silvered: bool = False,
                                      is_adamantine: bool = False) -> Tuple[bool, str]:
    """
    Valuta liste di resistenze/immunità 5e gestendo clausole condizionali MM:
    - 'da attacchi non magici' / 'from nonmagical attacks'
    - 'non argentati' / 'not silvered'
    - 'non in adamantio' / 'not adamantine'
    Ritorna (applica_modificatore, nota_bypass).
    """
    aliases = set(damage_map.get(dt, [dt]))
    aliases.add(dt)
    for mk, mvals in (damage_map or {}).items():
        if dt == mk or dt in mvals:
            aliases.add(mk)
            aliases.update(mvals)
    bypass_note = ""

    for raw_entry in entry_list or []:
        e = str(raw_entry or "").strip().lower()
        if not e:
            continue

        # Verifica se questo elemento riguarda il tipo di danno dt
        if not any(re.search(rf"\b{re.escape(al)}\b", e) or al == e for al in aliases):
            # Supporto per voci generiche "all" o "tutti" (es. Pietrificato o Sciame)
            if e not in ("all", "tutti", "all damage"):
                continue

        requires_nonmagical = any(k in e for k in ("non mag", "non-mag", "nonmag"))
        allows_silver = any(k in e for k in ("argent", "silver"))
        allows_adam = any(k in e for k in ("adamant",))

        if requires_nonmagical:
            if is_magical:
                bypass_note = " (Difesa superata da arma magica)"
                continue
            if allows_silver and is_silvered:
                bypass_note = " (Difesa superata da arma argentata)"
                continue
            if allows_adam and is_adamantine:
                bypass_note = " (Difesa superata da arma in adamantio)"
                continue
        elif allows_silver and not allows_adam and is_silvered:
            bypass_note = " (Difesa superata da arma argentata)"
            continue
        elif allows_adam and is_adamantine:
            bypass_note = " (Difesa superata da arma in adamantio)"
            continue

        return True, ""

    return False, bypass_note


def release_grapples_held_by(grappler, game_state, reason: str = "") -> List[str]:
    """PHB p. 195: se chi afferra diventa incapacitato o scende a 0 HP, rilascia automaticamente le prese."""
    if not grappler or not game_state:
        return []
    released = []
    for p in getattr(game_state, "players", []):
        if getattr(p, "grappled_by", None) == grappler.name:
            p.grappled_by = None
            if hasattr(p, "conditions") and isinstance(p.conditions, list):
                p.conditions = [c for c in p.conditions if str(c).strip().lower() not in ("afferrato", "grappled")]
            if isinstance(getattr(p, "full_sheet", None), dict) and isinstance(p.full_sheet.get("conditions"), list):
                p.full_sheet["conditions"] = list(p.conditions)
            released.append(p.name)
            broadcast(game_state, make_player_stats_update(
                p.name, p.hp, p.max_hp, p.initiative, getattr(p, "conditions", []), getattr(p, "temp_hp", 0)
            ))
    if released and game_state:
        msg = f"🔓 Lotta interrotta: {grappler.name} {reason or 'non può più mantenere la presa'}; {', '.join(released)} è/sono libero/i!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[LOTTA] {msg}")
    return released


def break_grapple_if_out_of_reach(target, game_state) -> bool:
    """Se una creatura afferrata (o chi la trattiene) si sposta/viene spinta fuori portata (5 ft), termina la presa (PHB p. 195)."""
    if not target or not game_state:
        return False
    grappler_name = getattr(target, "grappled_by", None)
    if not grappler_name:
        return False
    grappler = game_state.find_player(grappler_name)
    if not grappler or not getattr(grappler, "position", None) or not getattr(target, "position", None):
        target.grappled_by = None
        return True
    if is_incapacitated(grappler):
        release_grapples_held_by(grappler, game_state, "è incapacitato")
        return True
    cur_map = getattr(game_state, "current_map", {}) or {}
    g_type = cur_map.get("grid_type", "hex")
    reach = getattr(grappler, "reach", 1) or 1
    dist = grid_distance_3d(
        Hex(target.position[0], target.position[1]),
        Hex(grappler.position[0], grappler.position[1]),
        getattr(target, "elevation", 0),
        getattr(grappler, "elevation", 0),
        grid_type=g_type,
    )
    if dist > reach:
        target.grappled_by = None
        if hasattr(target, "conditions") and isinstance(target.conditions, list):
            target.conditions = [c for c in target.conditions if str(c).strip().lower() not in ("afferrato", "grappled")]
        if isinstance(getattr(target, "full_sheet", None), dict) and isinstance(target.full_sheet.get("conditions"), list):
            target.full_sheet["conditions"] = list(target.conditions)
        msg = f"🔓 {target.name} è uscito dalla portata di {grappler.name}: la condizione Afferrato termina (PHB p. 195)!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_player_stats_update(
            target.name, target.hp, target.max_hp, target.initiative, getattr(target, "conditions", []), getattr(target, "temp_hp", 0)
        ))
        return True
    return False


def _parse_sense_range_hexes(entity, *keywords, default_ft: int = 60) -> int:
    """Restituisce la portata in esagoni (5 ft/cella) se l'entità possiede uno specifico senso speciale."""
    if not entity:
        return 0
    sheet = getattr(entity, "full_sheet", None) or {}
    chunks = [
        str(getattr(entity, "senses", "") or ""),
        str(sheet.get("senses", "") or ""),
        str(getattr(entity, "features", "") or ""),
        str(sheet.get("features", "") or ""),
        " ".join(str(c) for c in (getattr(entity, "conditions", []) or [])),
        " ".join(str(t) for t in (sheet.get("traits", []) or []) if isinstance(sheet.get("traits"), list)),
    ]
    raw_txt = " ".join(chunks).lower()
    if not any(k in raw_txt for k in keywords):
        return 0
    for kw in keywords:
        m = re.search(rf"{re.escape(kw)}[^\d]{{0,18}}(\d+)\s*(?:ft|p|piedi|m\b)?", raw_txt)
        if m:
            val = int(m.group(1))
            if "m" in m.group(0) and "ft" not in m.group(0):
                return max(1, int(round(val / 1.5)))
            return max(1, val // 5)
    return max(1, default_ft // 5)


def check_special_senses_see_target(observer, target, dist_hex: float) -> Tuple[bool, str]:
    """
    Verifica Vista Cieca (Blindsight), Visione del Vero (Truesight), Percezione Tellurica (Tremorsense).
    Ritorna (può_percepire_bersaglio, motivo_senso).
    """
    true_r = _parse_sense_range_hexes(observer, "visione del vero", "truesight", default_ft=120)
    if true_r > 0 and dist_hex <= true_r:
        return True, "Visione del Vero (Truesight)"

    blind_r = _parse_sense_range_hexes(observer, "vista cieca", "blindsight", default_ft=60)
    if blind_r > 0 and dist_hex <= blind_r:
        return True, "Vista Cieca (Blindsight)"

    tremor_r = _parse_sense_range_hexes(observer, "percezione tellurica", "tremorsense", default_ft=60)
    if tremor_r > 0 and dist_hex <= tremor_r and getattr(target, "elevation", 0) <= 0:
        return True, "Percezione Tellurica (Tremorsense)"

    return False, ""


def is_in_sunlight(entity, game_state) -> bool:
    """Determina se la creatura si trova alla luce solare diretta (MM Sensibilità alla Luce Solare)."""
    if not game_state:
        return False
    cur_map = getattr(game_state, "current_map", {}) or {}
    if cur_map.get("is_indoor", False) or cur_map.get("is_underground", False):
        return False
    weather = str(getattr(game_state, "weather", "Sereno")).lower()
    if any(k in weather for k in ("oscur", "darkness", "buio", "notte", "night", "tempesta", "storm")):
        return False
    hr = int(getattr(game_state, "time_hour", 12) or 12)
    return 6 <= hr < 20


def has_entity_sunlight_sensitivity(entity) -> bool:
    return entity_has_keyword(entity, "sensibilità alla luce solare", "sunlight sensitivity", "ipersensibilità alla luce")


def get_environmental_light_level(pos_hex, game_state) -> str:
    """Restituisce 'bright', 'dim', o 'darkness' per una posizione sulla mappa."""
    if not game_state:
        return "bright"
    weather = str(getattr(game_state, "weather", "Sereno")).lower()
    cur_map = getattr(game_state, "current_map", {}) or {}
    amb = str(cur_map.get("ambient_light", "") or "").lower()
    if any(k in weather for k in ("oscurit", "darkness", "buio")) or amb == "darkness":
        base = "darkness"
    elif any(k in weather for k in ("luce fioca", "dim", "crepuscolo", "nebbia", "fog", "pioggia")) or amb == "dim":
        base = "dim"
    else:
        hr = int(getattr(game_state, "time_hour", 12) or 12)
        base = "darkness" if (hr < 5 or hr >= 21) else ("dim" if (hr < 6 or hr >= 20) else "bright")

    if pos_hex and base != "bright":
        for p in getattr(game_state, "players", []):
            lr = getattr(p, "light_radius", 0) or 0
            if lr > 0 and getattr(p, "position", None):
                d = max(abs(pos_hex[0] - p.position[0]), abs(pos_hex[0] + pos_hex[1] - p.position[0] - p.position[1]), abs(pos_hex[1] - p.position[1]))
                if d <= lr:
                    return "bright"
                elif d <= lr * 2 and base == "darkness":
                    base = "dim"
    return base


def check_passive_perception(entity, game_state, sight_based: bool = True) -> int:
    """Calcola Percezione Passiva 5e includendo Vantaggio (+5) / Svantaggio (-5) da Luce Fioca, Scurovisione, Keen Senses."""
    from server.rules.combat import _get_entity_skill_bonus
    base = 10 + _get_entity_skill_bonus(entity, "Percezione", "Perception", "SAG")
    conds = getattr(entity, "conditions", []) or []
    if is_condition_active(conds, "Accecato") and sight_based:
        return 0
    if is_condition_active(conds, "Assordato") and not sight_based:
        return 0
    if getattr(entity, "exhaustion_level", 0) >= 1 or is_condition_active(conds, "Avvelenato"):
        base -= 5
    if sight_based and game_state:
        light = get_environmental_light_level(getattr(entity, "position", None), game_state)
        has_dv = getattr(entity, "check_has_darkvision", lambda: False)()
        if light == "darkness":
            if has_dv or _parse_sense_range_hexes(entity, "vista cieca", "blindsight", "visione del vero", "truesight") > 0:
                if has_dv:
                    base -= 5  # Darkness counts as Dim Light -> -5 Passive Perception (PHB p. 183)
            else:
                return 0
        elif light == "dim" and not has_dv:
            base -= 5
        if has_entity_sunlight_sensitivity(entity) and is_in_sunlight(entity, game_state):
            base -= 5
    if entity_has_keyword(entity, "sensi acuti", "keen senses", "olfatto acuto", "vista acuta", "udito acuto"):
        base += 5
    from common.subclass_and_race_rules import get_passive_observant_bonus
    base += get_passive_observant_bonus(entity, "Percezione")
    return max(0, base)


def check_fear_source_movement_block(player, to_pos, game_state) -> Tuple[bool, str]:
    """PHB p. 290: Una creatura Spaventata non può volontariamente avvicinarsi alla fonte della sua paura."""
    conds = getattr(player, "conditions", []) or []
    if not is_condition_active(conds, "Spaventato"):
        return False, ""
    sources = getattr(player, "frightened_sources", None)
    if not isinstance(sources, dict) or not sources:
        return False, ""
    cur_pos = getattr(player, "position", None)
    if not cur_pos or not to_pos:
        return False, ""
    cur_map = getattr(game_state, "current_map", {}) or {}
    g_type = cur_map.get("grid_type", "hex")
    walls = []
    if cur_map:
        from server.rules.movement import get_effective_map_walls
        walls = get_effective_map_walls(cur_map)

    for src_name in list(sources.keys()):
        src = game_state.find_player(src_name) if game_state else None
        if not src or not getattr(src, "position", None) or getattr(src, "hp", 1) <= 0:
            continue
        # Verifica Linea di Vista se sorgente attiva
        los_clear = True
        if walls:
            for st in hex_linedraw(Hex(cur_pos[0], cur_pos[1]), Hex(src.position[0], src.position[1]))[1:-1]:
                if [st.q, st.r] in walls:
                    los_clear = False
                    break
        if not los_clear:
            continue
        d_before = grid_distance_3d(Hex(cur_pos[0], cur_pos[1]), Hex(src.position[0], src.position[1]), getattr(player, "elevation", 0), getattr(src, "elevation", 0), grid_type=g_type)
        d_after = grid_distance_3d(Hex(to_pos[0], to_pos[1]), Hex(src.position[0], src.position[1]), getattr(player, "elevation", 0), getattr(src, "elevation", 0), grid_type=g_type)
        if d_after < d_before:
            return True, f"😱 Sei Spaventato da {src.name} (in linea di vista): non puoi volontariamente avvicinarti ad essa (PHB p. 290)!"
    return False, ""


def apply_temp_hp(target, new_amount: int, game_state=None, choice: Optional[str] = None) -> Tuple[int, str]:
    """PHB p. 198: I Punti Ferita Temporanei non si sommano mai. Se ne hai già, scegli se tenere o sostituire."""
    amt = max(0, int(new_amount or 0))
    if amt <= 0:
        return getattr(target, "temp_hp", 0), ""
    cur = max(0, int(getattr(target, "temp_hp", 0) or 0))
    if cur == 0:
        target.temp_hp = amt
        note = ""
    elif choice == "keep":
        note = f" (Mantieni {cur} Temp HP invece di {amt} - PHB p. 198)"
    elif choice == "replace":
        target.temp_hp = amt
        note = f" (Sostituiti {cur} con {amt} Temp HP - PHB p. 198)"
    else:
        if amt > cur:
            target.temp_hp = amt
            note = f" (Temp HP non cumulabili: sostituiti {cur} -> {amt}, PHB p. 198)"
        else:
            note = f" (Temp HP non cumulabili: mantenuti i {cur} attuali > {amt}, PHB p. 198)"
    if isinstance(getattr(target, "full_sheet", None), dict):
        target.full_sheet["temp_hp"] = target.temp_hp
    return target.temp_hp, note


def entity_has_prepared_spell(entity, *keywords) -> bool:
    sheet = getattr(entity, "full_sheet", None) or {}
    sb = sheet.get("spellbook", []) or sheet.get("spells", []) or []
    txt = " ".join(str(s.get("name", s) if isinstance(s, dict) else s).lower() for s in sb)
    txt += " " + str(sheet.get("features", "") or "").lower()
    return any(k in txt for k in keywords)


def entity_has_available_slot(entity, min_level: int = 1) -> bool:
    sheet = getattr(entity, "full_sheet", None)
    if not isinstance(sheet, dict):
        return False
    pact = sheet.get("pact_slots")
    if isinstance(pact, dict) and pact.get("current", 0) > 0 and pact.get("level", 0) >= min_level:
        return True
    slots = sheet.get("spell_slots", {}) or {}
    for lvl in range(min_level, 10):
        sl = slots.get(str(lvl))
        if isinstance(sl, dict) and sl.get("current", 0) > 0:
            return True
        if isinstance(sl, list) and len(sl) >= 2 and sl[0] > 0:
            return True
    return False


def maybe_prompt_defense_reactions(target_player, attacker, attack_details: dict, game_state):
    """
    Emette prompt live per reazioni difensive appropriate al momento dell'attacco:
    - SHIELD_SPELL (se il colpo è andato a segno ma target_ac + 5 lo farebbe mancare, non è critico, ha Scudo e uno slot)
    - DEFLECT_MISSILES (Monaco Lv 3+ colpito da attacco a distanza con arma)
    """
    if not target_player or not game_state:
        return
    if getattr(target_player, "has_reacted_this_turn", False) or getattr(target_player, "surprised", False) or is_incapacitated(target_player) or _has_no_reactions_effect(target_player):
        return
    auto_react = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_react = game_state.automation_settings.get("auto_prompt_reactions", True)
    if not auto_react or not getattr(target_player, "conn", None):
        return

    is_ranged = bool(attack_details.get("is_ranged", False))
    is_spell = bool(attack_details.get("is_spell", False))
    hits = bool(attack_details.get("hits", False))
    is_crit = bool(attack_details.get("is_crit", False))
    hit_roll = int(attack_details.get("hit_roll", 0) or 0)
    target_ac = int(attack_details.get("target_ac", 10) or 10)
    w_name = attack_details.get("weapon_name", "Attacco")

    # 1. SHIELD_SPELL
    if hits and not is_crit and hit_roll < (target_ac + 5):
        if entity_has_prepared_spell(target_player, "scudo", "shield") and entity_has_available_slot(target_player, 1):
            send_message(target_player.conn, make_prompt_reaction(
                "SHIELD_SPELL",
                attacker.name if attacker else "Attaccante",
                {
                    "weapon_name": w_name,
                    "hit_roll": hit_roll,
                    "current_ac": target_ac,
                    "dmg_dealt": attack_details.get("dmg_to_hp", 0),
                }
            ))
            return

    # 2. DEFENSIVE_DUELIST (Talento Duellante Difensivo PHB p. 165)
    if hits and not is_crit and not is_spell:
        from common.feats_and_classes import check_defensive_duelist_bonus
        dd_pb = check_defensive_duelist_bonus(target_player)
        if dd_pb > 0 and hit_roll < (target_ac + dd_pb):
            send_message(target_player.conn, make_prompt_reaction(
                "DEFENSIVE_DUELIST",
                attacker.name if attacker else "Attaccante",
                {
                    "weapon_name": w_name,
                    "hit_roll": hit_roll,
                    "current_ac": target_ac,
                    "bonus_ac": dd_pb,
                    "dmg_dealt": attack_details.get("dmg_to_hp", 0),
                    "dmg_to_hp": attack_details.get("dmg_to_hp", 0),
                }
            ))
            return

    # 3. ILLUSORY_SELF (Mago Illusione Lv 10+ - 1/riposo breve forza il mancato)
    if hits and not getattr(target_player, "illusory_self_used", False):
        sub_t = str((getattr(target_player, "full_sheet", {}) or {}).get("subclass", getattr(target_player, "subclass", ""))).lower()
        if entity_get_class_level(target_player, "mago", "wizard") >= 10 and "illusion" in sub_t:
            send_message(target_player.conn, make_prompt_reaction(
                "ILLUSORY_SELF",
                attacker.name if attacker else "Attaccante",
                {"weapon_name": w_name, "dmg_to_hp": attack_details.get("dmg_to_hp", 0)}
            ))
            return

    # 4. DAMPEN_ELEMENTS (Chierico Natura Lv 6+: Resistenza immediata a acido/freddo/fuoco/fulmine/tuono)
    dmg_t_l = str(attack_details.get("damage_type", "") or "").lower()
    if hits and any(k in dmg_t_l for k in ("acido", "acid", "freddo", "cold", "fuoco", "fire", "fulmine", "lightning", "tuono", "thunder")):
        sub_t = str((getattr(target_player, "full_sheet", {}) or {}).get("subclass", getattr(target_player, "subclass", ""))).lower()
        if entity_get_class_level(target_player, "chierico", "cleric") >= 6 and ("natur" in sub_t):
            send_message(target_player.conn, make_prompt_reaction(
                "DAMPEN_ELEMENTS",
                attacker.name if attacker else "Attaccante",
                {"damage_type": attack_details.get("damage_type", "Fuoco"), "dmg_to_hp": attack_details.get("dmg_to_hp", 0)}
            ))
            return

    # 5. DEFLECT_MISSILES (Monaco 3+ su attacco arma a distanza)
    if hits and is_ranged and not is_spell:
        monk_lvl = entity_get_class_level(target_player, "monaco", "monk")
        if monk_lvl >= 3 or entity_has_keyword(target_player, "deflettere missili", "devia proiettili", "deflect missiles"):
            send_message(target_player.conn, make_prompt_reaction(
                "DEFLECT_MISSILES",
                attacker.name if attacker else "Attaccante",
                {
                    "weapon_name": w_name,
                    "incoming_damage": attack_details.get("dmg_to_hp", attack_details.get("final_dmg", 0)),
                }
            ))


def maybe_prompt_counterspell_reactions(caster, spell_name: str, spell_level: int, game_state, cast_id: Optional[str] = None) -> List[str]:
    """
    Invia prompt live COUNTERSPELL alle creature avversarie entro 60 ft (12 celle) in LoS
    che hanno Controincantesimo/Counterspell e uno slot di livello >= 3.
    """
    if not caster or not game_state or spell_level <= 0:
        return []
    auto_react = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_react = game_state.automation_settings.get("auto_prompt_reactions", True)
    if not auto_react:
        return []

    caster_party = bool(getattr(caster, "is_party_member", False) or getattr(caster, "conn", None))
    c_pos = getattr(caster, "position", None)
    cur_map = getattr(game_state, "current_map", {}) or {}
    g_type = cur_map.get("grid_type", "hex")
    prompted = []

    for other in getattr(game_state, "players", []):
        if other.name == caster.name or is_incapacitated(other) or _has_no_reactions_effect(other):
            continue
        if getattr(other, "has_reacted_this_turn", False) or getattr(other, "surprised", False):
            continue
        other_party = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
        if other_party == caster_party:
            continue
        if not entity_has_prepared_spell(other, "controincantesimo", "counterspell"):
            continue
        if not entity_has_available_slot(other, 3):
            continue
        o_pos = getattr(other, "position", None)
        if c_pos and o_pos:
            dist = grid_distance_3d(Hex(c_pos[0], c_pos[1]), Hex(o_pos[0], o_pos[1]), getattr(caster, "elevation", 0), getattr(other, "elevation", 0), grid_type=g_type)
            if dist > 12.0:
                continue
        if getattr(other, "conn", None):
            send_message(other.conn, make_prompt_reaction(
                "COUNTERSPELL",
                caster.name,
                {"spell_name": spell_name, "spell_level": spell_level, "slot_level": 3, "cast_id": cast_id}
            ))
            prompted.append(other.name)
    return prompted


def handle_escape_grapple_request(data, player, game_state):
    """Azione 'Sfuggire a una Lotta' (PHB p. 195): Atletica o Acrobazia vs Atletica dell'afferratore."""
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player:
        return
    conds = getattr(player, "conditions", []) or []
    if not is_condition_active(conds, "Afferrato") and not getattr(player, "grappled_by", None):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non sei attualmente Afferrato!"))
        return
    if is_incapacitated(player):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Sei incapacitato e non puoi liberarti dalla presa!"))
        return

    from server.rules.combat import _get_entity_skill_bonus
    grappler_name = data.get("grappler_name") or getattr(player, "grappled_by", None)
    grappler = game_state.find_player(grappler_name) if (grappler_name and game_state) else None

    ath = _get_entity_skill_bonus(player, "Atletica", "Athletics", "FOR")
    acr = _get_entity_skill_bonus(player, "Acrobazia", "Acrobatics", "DES")
    use_acr = acr >= ath
    v_bonus = acr if use_acr else ath
    v_skill = "Acrobazia" if use_acr else "Atletica"

    v_dis = getattr(player, "exhaustion_level", 0) >= 1 or is_condition_active(conds, "Avvelenato") or is_condition_active(conds, "Spaventato")
    r1, r2 = random.randint(1, 20), random.randint(1, 20)
    v_d20 = min(r1, r2) if v_dis else r1
    v_tot = v_d20 + v_bonus

    if grappler and getattr(grappler, "hp", 1) > 0 and not is_incapacitated(grappler):
        g_bonus = _get_entity_skill_bonus(grappler, "Atletica", "Athletics", "FOR")
        g_conds = getattr(grappler, "conditions", []) or []
        g_adv = is_condition_active(g_conds, "Ira")
        g_dis = getattr(grappler, "exhaustion_level", 0) >= 1 or is_condition_active(g_conds, "Avvelenato") or is_condition_active(g_conds, "Spaventato")
        g1, g2 = random.randint(1, 20), random.randint(1, 20)
        g_d20 = max(g1, g2) if (g_adv and not g_dis) else (min(g1, g2) if (g_dis and not g_adv) else g1)
        g_tot = g_d20 + g_bonus
        escaped = v_tot >= g_tot
        vs_txt = f"vs {grappler.name} [Atletica {g_tot}]"
    else:
        escaped = True
        vs_txt = "(l'avversario non può più trattenere la presa)"

    from contextlib import nullcontext
    lock_ctx = game_state.lock if (game_state and hasattr(game_state, "lock")) else nullcontext()
    with lock_ctx:
        player.has_acted_this_turn = True
        if escaped:
            player.grappled_by = None
            player.conditions = [c for c in conds if str(c).strip().lower() not in ("afferrato", "grappled")]
            if isinstance(getattr(player, "full_sheet", None), dict):
                player.full_sheet["conditions"] = list(player.conditions)
            msg = f"🤸 **Fuga dalla Lotta (PHB p. 195)**: {player.name} [{v_skill} {v_tot}] {vs_txt} -> **SI LIBERA!**"
        else:
            msg = f"🤼 **Fuga dalla Lotta (PHB p. 195)**: {player.name} [{v_skill} {v_tot}] {vs_txt} -> **FALLITA**, resta Afferrato!"

    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
    game_state.log_dm_message(f"[LOTTA] {msg}")
    game_state._trigger_gui_update()


def handle_dispel_magic_request(data, player, game_state):
    """
    Dissolvi Magie (Dispel Magic - D&D 5e RAW PHB p. 234):
    - Effetti/AoE creati con incantesimo di livello <= slot_level sono dissolti automaticamente.
    - Incantesimi di livello superiore richiedono Prova d'Incantatore (d20 + mod caratteristica) vs CD 10 + liv. incantesimo.
    """
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player or not game_state:
        return
    from common.network_utils import is_dm_actor
    try:
        slot_level = max(3, min(9, int(data.get("slot_level", 3) or 3)))
    except (ValueError, TypeError):
        slot_level = 3

    target_update_payload = None
    with game_state.lock:
        # Consuma slot obbligatorio per PG (3° liv.+); il DM locale può testare liberamente
        sheet = getattr(player, "full_sheet", None)
        if not is_dm_actor(player):
            if not isinstance(sheet, dict) or not entity_has_available_slot(player, slot_level):
                err_conn = getattr(player, "conn", None)
                ok_slot = False
            else:
                ok_slot, _ = consume_spell_or_pact_slot(sheet, slot_level)
                err_conn = getattr(player, "conn", None)
            if not ok_slot:
                target_name = None
                target = None
                slot_failed = True
            else:
                slot_failed = False
                target_name = data.get("target_name")
                target = game_state.find_player(target_name) if target_name else player
        else:
            slot_failed = False
            err_conn = None
            if isinstance(sheet, dict) and entity_has_available_slot(player, slot_level):
                consume_spell_or_pact_slot(sheet, slot_level)
            target_name = data.get("target_name")
            target = game_state.find_player(target_name) if target_name else player

        if slot_failed:
            pass
        else:
            best_mod = max(
                (get_effective_attribute_from_dict(sheet if isinstance(sheet, dict) else player, s) - 10) // 2
                for s in ("INT", "SAG", "CAR")
            )
            if entity_get_class_level(player, "bardo", "bard") >= 2:
                tot_lvl = entity_get_total_level(player)
                pb = 2 + (tot_lvl - 1) // 4
                best_mod += pb // 2  # Jack of All Trades applies to Dispel Magic ability check!
            if entity_get_class_level(player, "mago", "wizard") >= 10 and "abiur" in str((sheet or {}).get("subclass", "")).lower():
                tot_lvl = entity_get_total_level(player)
                best_mod += 2 + (tot_lvl - 1) // 4  # Improved Abjuration!

            dispelled = []
            resisted = []

            if target and getattr(target, "active_effects", None):
                remaining = []
                for fx in list(target.active_effects):
                    s_lvl = int(fx.get("spell_level", 1) or 1)
                    is_magic = fx.get("is_magical", True)
                    if not is_magic:
                        remaining.append(fx)
                        continue
                    if s_lvl <= slot_level:
                        dispelled.append(f"{fx.get('name', 'Effetto')} (Lv.{s_lvl}, automatico)")
                    else:
                        r = random.randint(1, 20)
                        tot = r + best_mod
                        dc = 10 + s_lvl
                        if tot >= dc:
                            dispelled.append(f"{fx.get('name', 'Effetto')} (Lv.{s_lvl}, {tot}>={dc})")
                        else:
                            resisted.append(f"{fx.get('name', 'Effetto')} (Lv.{s_lvl}, {tot}<{dc})")
                            remaining.append(fx)
                target.active_effects = remaining
                # Pulisci condizioni orfane dagli effetti dissolti
                active_fx_conds = {fx.get("condition") for fx in remaining if fx.get("condition")}
                for magic_c in ("Benedizione", "Anatema", "Velocità", "Lentezza", "Scudo", "Oscurità"):
                    if magic_c not in active_fx_conds and magic_c in getattr(target, "conditions", []):
                        target.conditions.remove(magic_c)
                if isinstance(getattr(target, "full_sheet", None), dict):
                    target.full_sheet["conditions"] = list(getattr(target, "conditions", []))
                target_update_payload = make_player_stats_update(
                    target.name, target.hp, target.max_hp, target.initiative,
                    list(getattr(target, "conditions", [])), getattr(target, "temp_hp", 0),
                    active_effects=list(target.active_effects),
                )

            if data.get("dispel_aoe") and getattr(game_state, "active_aoes", None):
                aoe_idx = int(data.get("aoe_index", 0) or 0)
                if 0 <= aoe_idx < len(game_state.active_aoes):
                    aoe = game_state.active_aoes[aoe_idx]
                    s_lvl = int(aoe.get("spell_level", 3) or 3)
                    if s_lvl <= slot_level or (random.randint(1, 20) + best_mod) >= (10 + s_lvl):
                        removed_aoe = game_state.active_aoes.pop(aoe_idx)
                        dispelled.append(f"AoE '{removed_aoe.get('name', 'Incantesimo')}'")

            player.has_acted_this_turn = True
            msg = f"✨ **Dissolvi Magie (Lv.{slot_level})** di {player.name} su {target.name if target else 'Area'}:"
            if dispelled:
                msg += f" Dissolti: {', '.join(dispelled)}."
            if resisted:
                msg += f" Hanno resistito: {', '.join(resisted)}."
            if not dispelled and not resisted:
                msg += " Nessun effetto magico attivo da dissolvere."

    if slot_failed:
        if err_conn:
            send_message(err_conn, make_error_reply(f"Nessuno slot incantesimo di {slot_level}° livello+ disponibile per Dissolvi Magie."))
        return

    if target_update_payload:
        broadcast(game_state, target_update_payload)
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(f"[MAGIA] {msg}")


def handle_identify_spell_reaction_request(data, player, game_state):
    """XGtE p. 85: Reazione per identificare un incantesimo mentre viene lanciato (Arcano CD 15 + livello)."""
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    if not player or not game_state:
        return
    with game_state.lock:
        if getattr(player, "has_reacted_this_turn", False) or is_incapacitated(player):
            return
        from server.rules.combat import _get_entity_skill_bonus
        spell_name = str(data.get("spell_name", "Incantesimo Sconosciuto"))
        spell_level = max(0, min(9, int(data.get("spell_level", 1) or 1)))
        dc = 15 + spell_level
        arc_bonus = _get_entity_skill_bonus(player, "Arcano", "Arcana", "INT")
        on_list = bool(data.get("on_class_spell_list", False))
        r1, r2 = random.randint(1, 20), random.randint(1, 20)
        d20 = max(r1, r2) if on_list else r1
        tot = d20 + arc_bonus
        player.has_reacted_this_turn = True
    if tot >= dc:
        msg = f"🔎 [Identificare Incantesimo XGtE p.85] {player.name} (Reazione, Arcano {tot} >= CD {dc}) riconosce subito l'incantesimo: **{spell_name}** (Liv. {spell_level})!"
    else:
        msg = f"🔎 [Identificare Incantesimo XGtE p.85] {player.name} (Reazione, Arcano {tot} < CD {dc}) non riesce a identificare l'incantesimo in tempo."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[MAGIA] {msg}")
