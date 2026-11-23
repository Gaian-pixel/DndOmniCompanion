import os
import json
import random
from common.hex_utils import Hex, hex_linedraw, get_visible_hexes, grid_distance_3d
from common.network_utils import send_message, broadcast
from common.i18n import is_condition_active
from common.item_modifiers import get_effective_attribute_from_dict, get_effective_save_bonus_from_dict

def get_effective_map_walls(current_map):
    """Restituisce l'insieme dei muri comprensivo di porte chiuse, serrate o segrete che bloccano LoS e passaggio."""
    if not current_map: return []
    walls = [list(w) for w in current_map.get("walls", [])]
    for d in current_map.get("doors", []):
        if d.get("state", "closed") in ("closed", "locked", "secret"):
            walls.append([d.get("q", 0), d.get("r", 0)])
    return walls

def auto_explore_fow(player, game_state):
    """Calcola la visibilità (LoS + Luce dinamica) del giocatore e aggiorna la FoW della mappa."""
    cur_map = getattr(game_state, "current_map", None)
    if not isinstance(cur_map, dict) or not cur_map.get("fow_enabled", False):
        return False
    pos = getattr(player, "position", None)
    if not isinstance(pos, (list, tuple)) or len(pos) < 2:
        return False
    try:
        h = Hex(int(pos[0]), int(pos[1]))
    except (TypeError, ValueError):
        return False
    raw_conds = getattr(player, "conditions", [])
    conds = raw_conds if isinstance(raw_conds, list) else []
    from server.rules.reaction_magic import _parse_sense_range_hexes
    if is_condition_active(conds, "Accecato") or is_condition_active(conds, "Blinded"):
        blind_r = _parse_sense_range_hexes(player, "vista cieca", "blindsight", "visione del vero", "truesight")
        if blind_r <= 0:
            return False
        effective_rad = blind_r
    else:
        try:
            raw_vis = getattr(player, 'vision_radius', 6)
            vision_rad = int(raw_vis) if isinstance(raw_vis, (int, float)) else 6
        except (TypeError, ValueError):
            vision_rad = 6
        try:
            raw_light = getattr(player, 'light_radius', 0)
            light_rad = int(raw_light) if isinstance(raw_light, (int, float)) else 0
        except (TypeError, ValueError):
            light_rad = 0
        effective_rad = max(vision_rad, light_rad)

    grid_type = cur_map.get("grid_type", "hex")
    walls = get_effective_map_walls(cur_map)
    visible_hexes = get_visible_hexes(h, effective_rad, walls, grid_type=grid_type)
    
    for other_p in (getattr(game_state, "players", None) or []):
        if other_p.name != player.name and getattr(other_p, 'is_party_member', False) is True:
            raw_olight = getattr(other_p, 'light_radius', 0)
            o_light = int(raw_olight) if isinstance(raw_olight, (int, float)) else 0
            o_pos = getattr(other_p, 'position', None)
            if o_light > 0 and isinstance(o_pos, (list, tuple)) and len(o_pos) >= 2:
                try:
                    o_hex = Hex(int(o_pos[0]), int(o_pos[1]))
                    o_light_hexes = get_visible_hexes(o_hex, o_light, walls, grid_type=grid_type)
                    visible_hexes.extend(o_light_hexes)
                except (TypeError, ValueError):
                    pass

    changed = False
    fow_rev = cur_map.setdefault("fow_revealed", [])
    fow_draft = cur_map.setdefault("fow_draft", [])
    rev_set = {
        (int(item[0]), int(item[1]))
        for item in fow_rev
        if isinstance(item, (list, tuple)) and len(item) >= 2
    }
    draft_set = {
        (int(item[0]), int(item[1]))
        for item in fow_draft
        if isinstance(item, (list, tuple)) and len(item) >= 2
    }

    for rh in visible_hexes:
        key = (int(rh.q), int(rh.r))
        pos_entry = [key[0], key[1]]
        if key not in rev_set:
            rev_set.add(key)
            fow_rev.append(pos_entry)
            changed = True
        if key not in draft_set:
            draft_set.add(key)
            fow_draft.append(pos_entry)
            changed = True

    return changed


def _extract_oa_weapon_details(reactor) -> dict:
    """Estrae i parametri dell'arma da mischia principale per un Attacco d'Opportunità 5e."""
    sheet = getattr(reactor, "full_sheet", None)
    s_dict = sheet if isinstance(sheet, dict) else {}
    str_val = get_effective_attribute_from_dict(s_dict or reactor, "FOR")
    dex_val = get_effective_attribute_from_dict(s_dict or reactor, "DES")
    str_mod = (int(str_val) - 10) // 2
    dex_mod = (int(dex_val) - 10) // 2
    from common.dnd5e_tables import entity_get_total_level
    tot_lvl = max(1, int(entity_get_total_level(reactor) or 1))
    pb = int(s_dict.get("proficiency_bonus") or (((tot_lvl - 1) // 4) + 2))

    for w in (s_dict.get("weapons") or []):
        if not isinstance(w, dict):
            continue
        props = f"{w.get('properties', '')} {w.get('type', '')} {w.get('desc', '')}".lower()
        name_l = str(w.get("name", "")).lower()
        is_ranged_only = (
            any(k in props for k in ("distanza", "ranged", "munizioni", "ammunition"))
            or any(rn in name_l for rn in ("arco", "bow", "balestra", "crossbow", "fionda", "sling", "cerbottana", "blowgun"))
        ) and not ("lancio" in props or "thrown" in props)
        if is_ranged_only:
            continue
        is_finesse = "accurat" in props or "finesse" in props or any(
            fn in name_l for fn in ("stocco", "rapier", "pugnale", "dagger", "scimitarra", "scimitar", "spada corta", "shortsword")
        )
        stat_mod = max(str_mod, dex_mod) if is_finesse else str_mod
        w_bonus = int(w.get("bonus", w.get("magic_bonus", 0)) or 0)
        hit_b = stat_mod + pb + w_bonus
        dmg_dice = str(w.get("damage_dice", w.get("damage", "1d8")) or "1d8").strip()
        dmg_mod = stat_mod + w_bonus
        if "+" not in dmg_dice and "-" not in dmg_dice and dmg_mod != 0:
            dmg_formula = f"{dmg_dice}+{dmg_mod}" if dmg_mod > 0 else f"{dmg_dice}{dmg_mod}"
        else:
            dmg_formula = dmg_dice
        return {
            "weapon_name": w.get("name", "Attacco d'Opportunità"),
            "hit_bonus": hit_b,
            "damage_formula": dmg_formula,
            "damage_type": w.get("damage_type", "Tagliente"),
        }

    for act in (s_dict.get("actions") or s_dict.get("attacks") or []):
        if not isinstance(act, dict):
            continue
        act_t = str(act.get("type", act.get("attack_type", ""))).lower()
        if "ranged" in act_t or "distanza" in act_t:
            continue
        if act.get("damage") or act.get("damage_formula"):
            return {
                "weapon_name": act.get("name", "Attacco d'Opportunità"),
                "hit_bonus": int(act.get("atk_bonus", act.get("hit_bonus", str_mod + pb)) or 0),
                "damage_formula": str(act.get("damage_formula", act.get("damage", "1d6"))),
                "damage_type": act.get("damage_type", "Tagliente"),
            }

    best_mod = str_mod
    dmg_sfx = f"+{best_mod}" if best_mod > 0 else (str(best_mod) if best_mod < 0 else "")
    return {
        "weapon_name": "Attacco d'Opportunità",
        "hit_bonus": best_mod + pb,
        "damage_formula": f"1d6{dmg_sfx}",
        "damage_type": "Contundente",
    }

def _evaluate_creature_space_traversal(player, step_hex, is_final_step: bool, game_state, is_incorporeal: bool = False):
    """
    PHB p. 191: Movimento attraverso gli spazi occupati da altre creature:
    - Spazio di una creatura alleata = Terreno Difficile (costo 2x).
    - Spazio di una creatura ostile = bloccato, salvo >=2 taglie di differenza,
      Agilità Halfling (+1 taglia), Incorporeità, o manovra DMG Overrun/Tumble.
    - Non è consentito terminare volontariamente il movimento nello spazio di un'altra creatura.
    Ritorna: (blocked: bool, step_extra_cost: int, reason: str)
    """
    if not player or not game_state:
        return False, 0, ""
    _size_map = {"minuscola": 0, "tiny": 0, "piccola": 1, "small": 1, "media": 2, "medium": 2, "grande": 3, "large": 3, "enorme": 4, "huge": 4, "mastodontica": 5, "gargantuan": 5}
    p_rank = _size_map.get(str(getattr(player, "size", "Media")).strip().lower(), 2)
    p_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
    p_elev = getattr(player, "elevation", 0) or 0
    from common.subclass_and_race_rules import has_halfling_nimbleness
    halfling_nimb = has_halfling_nimbleness(player)
    overrun_tgt = str(getattr(player, "overrun_tumble_through_target", "") or "")
    incaps = ("incosciente", "unconscious", "paralizzato", "paralyzed", "pietrificato", "petrified", "stordito", "stunned", "morto", "dead", "incapacitato", "incapacitated")

    extra_cost = 0
    for other in getattr(game_state, "players", []):
        if other is player or getattr(other, "name", "") == getattr(player, "name", ""):
            continue
        if getattr(other, "hp", 1) <= 0 or is_condition_active(getattr(other, "conditions", []), "Morto"):
            continue
        if getattr(other, "is_object", False) or getattr(other, "layer", "token") == "gm":
            continue
        o_pos = getattr(other, "position", None)
        if not o_pos or len(o_pos) < 2 or int(o_pos[0]) != int(step_hex.q) or int(o_pos[1]) != int(step_hex.r):
            continue
        if abs(p_elev - (getattr(other, "elevation", 0) or 0)) > 1:
            continue
        # Ignora cavalcatura / cavaliere / creatura afferrata / scalata
        if getattr(player, "mount_name", None) == other.name or getattr(other, "mount_name", None) == player.name:
            continue
        if getattr(player, "climbing_on_target", None) == other.name or getattr(other, "grappled_by", None) == player.name:
            continue

        o_conds = getattr(other, "conditions", []) or []
        o_incap = any(is_condition_active(o_conds, c) for c in incaps)
        if is_final_step and not o_incap and not is_incorporeal:
            return True, 1, f"Non puoi terminare volontariamente il movimento nello spazio occupato da {other.name} (PHB p. 191)."

        o_party = bool(getattr(other, "is_party_member", False) or getattr(other, "conn", None))
        is_hostile = (p_party != o_party)
        extra_cost = max(extra_cost, 1)  # Attraversare spazio di un'altra creatura costa +1 (terreno difficile)
        if is_hostile and not is_incorporeal and not o_incap:
            o_rank = _size_map.get(str(getattr(other, "size", "Media")).strip().lower(), 2)
            size_ok = abs(p_rank - o_rank) >= 2
            nimb_ok = halfling_nimb and (o_rank == p_rank + 1)
            tumble_ok = bool(overrun_tgt and overrun_tgt == other.name)
            if not (size_ok or nimb_ok or tumble_ok):
                return True, 1, f"Lo spazio ostile di {other.name} a [{step_hex.q}, {step_hex.r}] blocca il passaggio (PHB p. 191: servono ≥2 taglie di differenza, Agilità Halfling o Overrun/Tumble)."
    return False, extra_cost, ""


def handle_move_request(data, player, game_state):
    orig_player = player
    reply_conn = getattr(orig_player, "conn", None)
    caller_name = getattr(orig_player, "name", None)
    from common.network_utils import is_dm_actor
    is_dm_caller = is_dm_actor(orig_player) or getattr(orig_player, "is_dm", False)
    if isinstance(data, dict) and data.get("entity_name") and data.get("entity_name") != caller_name:
        target_mover = game_state.find_player(data.get("entity_name"))
        is_owner = target_mover and (
            is_dm_caller
            or getattr(target_mover, "owner", None) == caller_name
            or getattr(target_mover, "master_name", None) == caller_name
        )
        if not is_owner:
            from common.protocol import make_error_reply
            if reply_conn:
                send_message(reply_conn, make_error_reply(f"Non sei autorizzato a muovere il token '{data.get('entity_name')}'."))
            return
        player = target_mover

    err_conn = reply_conn or getattr(player, "conn", None)

    from server.rules.class_abilities import _check_surprised_block
    if _check_surprised_block(player, game_state, "muoverti"):
        return

    conds = getattr(player, "conditions", [])
    blocking = ["Afferrato", "Grappled", "Trattenuto", "Restrained", "Privo di Sensi", "Incapacitato", "Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(conds, c) for c in blocking) or getattr(player, "exhaustion_level", 0) >= 5 or getattr(player, "hp", 1) <= 0:
        from common.protocol import make_error_reply
        if err_conn:
            send_message(err_conn, make_error_reply("La tua velocità è 0 o sei incapacitato/morto. Non puoi muoverti."))
        return

    to_pos = data.get("to")
    move_path = None
    # L'elevazione DM deriva esclusivamente dal mittente originale (`orig_player`), mai da `conn is None` del compagno
    if is_dm_caller or orig_player is None:
        is_dm = True
    elif getattr(orig_player, "conn", None) is None and data.get("is_dm_force", False):
        is_dm = True
    else:
        is_dm = False
    
    if to_pos:
        if not isinstance(to_pos, (list, tuple)) or len(to_pos) < 2 or not all(isinstance(v, int) for v in to_pos[:2]):
            from common.protocol import make_error_reply
            if err_conn:
                send_message(err_conn, make_error_reply("Coordinate di destinazione non valide."))
            return
        is_teleport = bool(data.get("is_teleport", False))
        is_forced = bool(data.get("is_forced", False))
        if not is_dm and not is_teleport and not is_forced and getattr(game_state, "current_map", None):
            from common.i18n import get_map_scale_info
            if get_map_scale_info(game_state.current_map).get("scale_type") in ("exploration", "world"):
                from common.protocol import make_error_reply
                if err_conn:
                    send_message(err_conn, make_error_reply("Mappa di esplorazione: movimento libero disabilitato. Usa il Viaggio o aspetta il DM."))
                return

        if not is_dm and not is_forced:
            from server.rules.reaction_magic import check_fear_source_movement_block
            fear_blocked, fear_msg = check_fear_source_movement_block(player, to_pos, game_state)
            if fear_blocked:
                from common.protocol import make_error_reply
                if err_conn:
                    send_message(err_conn, make_error_reply(fear_msg))
                return
                
        cur_m_mv = getattr(game_state, "current_map", None)
        grid_type_mv = cur_m_mv.get("grid_type", "hex") if isinstance(cur_m_mv, dict) else "hex"
        walls_list_pos = get_effective_map_walls(cur_m_mv) if cur_m_mv else []
        from server.dm_monster_engine import is_incorporeal_entity, has_spider_climb
        is_incorporeal = is_incorporeal_entity(player)
        from_pos = getattr(player, "position", None)
        move_path = (
            hex_linedraw(Hex(from_pos[0], from_pos[1]), Hex(to_pos[0], to_pos[1]), grid_type=grid_type_mv)
            if from_pos and len(from_pos) >= 2 else None
        )
        if not is_dm and walls_list_pos and not is_incorporeal:
            walls_cell_set = {
                (w[0], w[1]) for w in walls_list_pos
                if isinstance(w, (list, tuple)) and len(w) >= 2
            }
            if is_teleport:
                steps_to_check = [Hex(to_pos[0], to_pos[1])]
            else:
                steps_to_check = move_path[1:] if move_path else [Hex(to_pos[0], to_pos[1])]

            def _reject_wall_at(bq, br):
                from common.protocol import make_error_reply
                door_blocked = None
                if getattr(game_state, "current_map", None):
                    for d in game_state.current_map.get("doors", []):
                        if d.get("q") == bq and d.get("r") == br and d.get("state", "closed") in ("closed", "locked", "secret"):
                            door_blocked = d
                            break
                if err_conn:
                    if door_blocked:
                        d_name = door_blocked.get("name", "Porta")
                        d_st = "serrata a chiave" if door_blocked.get("state") == "locked" else "chiusa"
                        send_message(err_conn, make_error_reply(f"Il percorso è bloccato: la {d_name} a [{bq}, {br}] è {d_st}! Cliccaci sopra per aprirla."))
                    else:
                        send_message(err_conn, make_error_reply(f"Movimento non consentito: c'è un muro sul percorso a [{bq}, {br}]!"))

            prev_step = Hex(from_pos[0], from_pos[1]) if (from_pos and len(from_pos) >= 2) else None
            for step in steps_to_check:
                if [step.q, step.r] in walls_list_pos:
                    _reject_wall_at(step.q, step.r)
                    return
                if not is_teleport and grid_type_mv == "square" and prev_step is not None:
                    if abs(step.q - prev_step.q) == 1 and abs(step.r - prev_step.r) == 1:
                        c1 = (step.q, prev_step.r)
                        c2 = (prev_step.q, step.r)
                        if c1 in walls_cell_set and c2 in walls_cell_set:
                            _reject_wall_at(c1[0], c1[1])
                            return
                prev_step = step
            
        in_combat = getattr(player, "in_combat", False) or getattr(game_state, "combat_active", False)
        strict_lock = False
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
        else:
            strict_lock = getattr(game_state, "strict_turn_lock", False)

        if in_combat and not is_dm and strict_lock and not bool(data.get("is_forced", False)):
            curr_turn = game_state.get_current_turn_player()
            allowed_turn_names = {player.name}
            if getattr(player, "name", None) != caller_name and (
                getattr(player, "owner", None) == caller_name or getattr(player, "master_name", None) == caller_name
            ):
                allowed_turn_names.add(caller_name)
            if curr_turn and curr_turn.name not in allowed_turn_names:
                from common.protocol import make_error_reply
                if err_conn:
                    send_message(err_conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
                return

        if in_combat and not is_forced and not is_teleport and hasattr(player, "position") and player.position and len(player.position) >= 2:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = to_pos[0], to_pos[1]
            speed = getattr(player, "speed", 30)
            speed_unit = getattr(player, "speed_unit", None)
            sheet = getattr(player, "full_sheet", None)
            if not (isinstance(sheet, dict) and sheet.get("_speed_bonuses_applied")):
                from common.feats_and_classes import get_entity_speed_bonus_ft, get_armor_nonproficiency_penalties
                _spd_bonus = get_entity_speed_bonus_ft(player)
                _str_pen = get_armor_nonproficiency_penalties(player).get("str_speed_penalty", 0)
                if str(speed_unit or "").lower() == "m":
                    speed = max(0, float(speed or 9) + round((_spd_bonus - _str_pen) * 0.3, 1))
                else:
                    speed = max(0, int(speed or 30) + _spd_bonus - _str_pen)
            if sheet and not speed_unit:
                speed_unit = sheet.get("speed_unit")
            from common.i18n import speed_to_hexes, format_distance_hexes
            base_hexes = speed_to_hexes(speed, speed_unit)

            # Regola D&D 5e Ingombro (Variant Encumbrance PHB p. 176)
            if sheet and isinstance(sheet.get("attributes"), dict):
                try:
                    str_val = get_effective_attribute_from_dict(player, "FOR")
                    from common.character_schema import compute_carried_weight_from_sheet
                    tot_w = compute_carried_weight_from_sheet(sheet, backpack_dropped=getattr(player, "backpack_dropped", False))
                    from common.subclass_and_race_rules import get_powerful_build_multiplier
                    pb_mult = get_powerful_build_multiplier(player)
                    if tot_w > (str_val * 15 * pb_mult):
                        base_hexes = 0  # Sovraccarico: movimento bloccato
                    elif tot_w > (str_val * 10 * pb_mult):
                        base_hexes = max(1, base_hexes - 4)  # Gravemente ingombrato (-20 ft)
                    elif tot_w > (str_val * 5 * pb_mult):
                        base_hexes = max(1, base_hexes - 2)  # Ingombrato (-10 ft)
                except (ValueError, TypeError):
                    pass

            exh = getattr(player, "exhaustion_level", 0)
            if exh >= 2:
                base_hexes = max(1, base_hexes // 2)
            from server.dm_optional_tools import get_lingering_injury_penalties
            _inj_pen = get_lingering_injury_penalties(player)
            if _inj_pen.get("speed_halved"):
                base_hexes = max(1, base_hexes // 2)
            elif _inj_pen.get("speed_penalty_ft", 0) > 0:
                base_hexes = max(1, base_hexes - max(1, _inj_pen["speed_penalty_ft"] // 5))
            is_dashed = is_condition_active(conds, "Scatto")
            max_hexes = base_hexes * 2 if is_dashed else base_hexes
            eff_names = [str(e.get("name", "")).lower() for e in getattr(player, "active_effects", []) if isinstance(e, dict)]
            conds_lower = [str(c).lower() for c in conds]
            if any(k in conds_lower for k in ["velocità", "haste"]) or any(k in eff_names for k in ["velocità", "haste"]):
                max_hexes *= 2
            if any(k in conds_lower for k in ["lentezza", "slow"]) or any(k in eff_names for k in ["lentezza", "slow"]):
                max_hexes = max(1, max_hexes // 2)
            # Calcolo percorso con hex_linedraw e applicazione Terreno Difficile (D&D 5e: costo doppio per ogni casella)
            cur_map = getattr(game_state, "current_map", None)
            diff_terrain = cur_map.get("difficult_terrain", {}) if cur_map else {}
            diff_map = {}
            if isinstance(diff_terrain, dict):
                for k, v in diff_terrain.items():
                    if isinstance(k, str) and "," in k:
                        parts = k.split(",")
                        diff_map[(int(parts[0]), int(parts[1]))] = str(v).lower()
                    elif isinstance(k, (tuple, list)) and len(k) >= 2:
                        diff_map[(int(k[0]), int(k[1]))] = str(v).lower()
            elif isinstance(diff_terrain, list):
                for item in diff_terrain:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        diff_map[(int(item[0]), int(item[1]))] = "fango"

            p_start = Hex(q1, r1)
            p_end = Hex(q2, r2)
            move_path = hex_linedraw(p_start, p_end, grid_type=grid_type_mv)
            
            cost_prone = 2 if is_condition_active(conds, "Prono") else 1
            is_squeezing_mv = bool(getattr(player, "is_squeezing", False)) or is_condition_active(conds, "Spremere") or is_condition_active(conds, "Squeezing")
            req_hexes = 0
            has_diff_terrain_in_path = False
            _n_steps = len(move_path[1:])
            for _s_idx, step in enumerate(move_path[1:]):
                step_tup = (step.q, step.r)
                is_step_diff = (step_tup in diff_map)
                if is_step_diff:
                    has_diff_terrain_in_path = True
                step_cost = 2 if is_step_diff else 1
                # PHB p. 191 Attraversamento spazi di altre creature (alleato = terreno difficile, ostile = bloccato se taglia simile)
                if not is_dm and not bool(data.get("is_teleport", False)) and not bool(data.get("is_forced", False)) and not data.get("is_jump"):
                    _blk, _cr_ext, _blk_reason = _evaluate_creature_space_traversal(
                        player, step, (_s_idx == _n_steps - 1), game_state, is_incorporeal=is_incorporeal
                    )
                    if _blk:
                        from common.protocol import make_error_reply
                        if err_conn:
                            send_message(err_conn, make_error_reply(_blk_reason))
                        return
                    if _cr_ext > 0 and step_cost == 1:
                        step_cost += _cr_ext
                        has_diff_terrain_in_path = True
                # Movimento Incorporeo (MM): attraversare oggetti/muri conta come terreno difficile
                if is_incorporeal and [step.q, step.r] in walls_list_pos:
                    step_cost = max(step_cost, 2)
                # Ranger Lv 8 Passo Naturale (Land's Stride, PHB p. 92) o Spider Climb (MM): terreno difficile non magico non costa movimento extra
                if step_cost > 1:
                    from common.dnd5e_tables import entity_get_class_level as _m_cls, entity_has_keyword as _m_kw
                    if _m_cls(player, "ranger") >= 8 or _m_kw(player, "passo naturale", "land's stride", "andatura del terreno") or has_spider_climb(player):
                        _dt_val = diff_map.get(step_tup)
                        _dt_str = str(_dt_val or "").lower() if isinstance(_dt_val, (str, dict)) else ""
                        if "magic" not in _dt_str and not (is_incorporeal and [step.q, step.r] in walls_list_pos):
                            step_cost = 1
                if is_condition_active(conds, "Prono"):
                    step_cost += 1
                if is_squeezing_mv:
                    step_cost += 1
                req_hexes += step_cost

            # Salto in Lungo PHB p. 182: se dichiarato is_jump, verifica limite Forza (con o senza rincorsa)
            if data.get("is_jump") and not is_dm:
                from common.dnd5e_tables import calculate_jump_distances
                _j_str = get_effective_attribute_from_dict(player, "FOR")
                _j_info = calculate_jump_distances(_j_str, running_start=bool(data.get("running_start", True)))
                _j_ft_req = max(0, len(move_path[1:]) * 5)
                _j_max_ft = float(_j_info["long_jump_ft"]) + float(data.get("athletics_extra_ft", 0) or 0)
                if _j_ft_req > _j_max_ft and game_state.automation_settings.get("strict_movement_limits", True):
                    from common.protocol import make_error_reply
                    if err_conn:
                        send_message(err_conn, make_error_reply(f"Salto non consentito: richiesti {_j_ft_req} ft contro max {_j_max_ft:.0f} ft (FOR {_j_str})."))
                    return

            # PHB p. 195 Trascinare creatura afferrata: movimento dimezzato (costo x2) a meno che >= 2 taglie più piccola
            _size_map = {"minuscola": 0, "tiny": 0, "piccola": 1, "small": 1, "media": 2, "medium": 2, "grande": 3, "large": 3, "enorme": 4, "huge": 4, "mastodontica": 5, "gargantuan": 5}
            p_srank = _size_map.get(str(getattr(player, "size", "Media")).strip().lower(), 2)
            grappled_victims = [
                g for g in getattr(game_state, "players", [])
                if g.name != player.name and getattr(g, "grappled_by", None) == player.name and is_condition_active(getattr(g, "conditions", []), "Afferrato")
            ]
            if any(_size_map.get(str(getattr(g, "size", "Media")).strip().lower(), 2) > (p_srank - 2) for g in grappled_victims):
                req_hexes *= 2

            # Combattimento Subacqueo (PHB p. 198): muoversi immersi senza velocità di nuoto costa movimento doppio
            from common.dnd5e_tables import entity_has_keyword as _ehk_mv, entity_get_class_level as _ecls_mv
            p_fs = getattr(player, "full_sheet", None) or {}
            _monk_l_mv = _ecls_mv(player, "monaco", "monk")
            _rogue_l_mv = _ecls_mv(player, "ladro", "rogue")
            _sub_mv = str(p_fs.get("subclass", "") or "").lower()
            has_monk_water_wall = _monk_l_mv >= 9
            has_second_story_climb = (_rogue_l_mv >= 3 and ("furfante" in _sub_mv or "thief" in _sub_mv)) or _ehk_mv(player, "secondo piano", "second-story work")
            has_swim_spd = bool(p_fs.get("speed_swim", 0) or (getattr(player, "speed_swim", 0) or 0)) or _ehk_mv(player, "nuotare", "nuoto", "swim", "tritone", "triton") or has_monk_water_wall
            if (getattr(player, "is_submerged", False) or is_condition_active(conds, "Immerso")) and not has_swim_spd:
                req_hexes *= 2
            elif getattr(player, "is_climbing", False) and not (has_monk_water_wall or has_second_story_climb or _ehk_mv(player, "scalare", "climb")):
                req_hexes *= 2

            spent = getattr(player, "movement_spent_this_turn", 0)
            strict_move = True
            if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                strict_move = game_state.automation_settings.get("strict_movement_limits", True)

            if (spent + req_hexes) > max_hexes:
                if strict_move:
                    from common.protocol import make_error_reply
                    if err_conn:
                        rem = max(0, max_hexes - spent)
                        rem_str = format_distance_hexes(rem, speed_unit)
                        tot_str = format_distance_hexes(max_hexes, speed_unit)
                        diff_hint = " (Attraversare terreno difficile raddoppia il costo!)" if has_diff_terrain_in_path else ""
                        if cost_prone == 2 and not has_diff_terrain_in_path:
                            send_message(err_conn, make_error_reply(f"Movimento non consentito: sei Prono. Ti restano {rem // 2} esagoni ({rem_str})."))
                        else:
                            hint = " (Puoi usare l'Azione di Scatto /dash per raddoppiare la velocità!)" if not is_dashed else ""
                            send_message(err_conn, make_error_reply(f"Movimento non consentito: la distanza supera la velocità rimasta per questo turno ({rem_str} rimasti su {tot_str}).{diff_hint}{hint}"))
                    return
                else:
                    game_state.log_dm_message(f"[MOVIMENTO] {player.name} supera la velocità normale del turno ({spent + req_hexes}/{max_hexes} esagoni) - Consentito in modalità tavolo.")
            player.movement_spent_this_turn = spent + req_hexes

        # Rilevamento Attacco d'Opportunità (Opportunity Attack - D&D 5e RAW PHB p. 195, Volo Radente MM, Sentinella & Maestro d'Armi Astate PHB)
        from_pos = list(player.position) if hasattr(player, "position") and player.position else None
        is_teleport = bool(data.get("is_teleport", False))
        is_forced = bool(data.get("is_forced", False))
        if in_combat and from_pos and from_pos != to_pos and not is_teleport and not is_forced:
            disengaged = is_condition_active(conds, "Disimpegno")
            from common.dnd5e_tables import entity_has_keyword as _ehk_oa
            has_flyby = _ehk_oa(player, "volo radente", "flyby")
            for other in getattr(game_state, "players", []):
                if other.name != player.name and getattr(other, "hp", 0) > 0 and hasattr(other, "position") and other.position:
                    is_enemy = (getattr(player, "is_party_member", False) != getattr(other, "is_party_member", False))
                    has_reacted = getattr(other, "has_reacted_this_turn", False)
                    if is_enemy and not has_reacted:
                        has_sentinel = _ehk_oa(other, "sentinella", "sentinel")
                        has_pam = _ehk_oa(other, "maestro d'armi astate", "polearm master", "armi astate")
                        qo, ro = other.position[0], other.position[1]
                        reach = getattr(other, "reach", 1) or 1
                        cur_m = getattr(game_state, "current_map", None)
                        g_type = cur_m.get("grid_type", "hex") if cur_m else "hex"
                        d_rule = "standard"
                        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                            d_rule = game_state.automation_settings.get("square_diagonal_rule", "standard")
                        z_oth = getattr(other, "elevation", 0) or 0
                        z_ply = getattr(player, "elevation", 0) or 0

                        exited_reach = False
                        entered_reach = False
                        if move_path and len(move_path) > 1:
                            for p_i in range(len(move_path) - 1):
                                s_cur, s_nxt = move_path[p_i], move_path[p_i + 1]
                                cq1 = getattr(s_cur, "q", s_cur[0] if isinstance(s_cur, (list, tuple)) else 0)
                                cr1 = getattr(s_cur, "r", s_cur[1] if isinstance(s_cur, (list, tuple)) else 0)
                                cq2 = getattr(s_nxt, "q", s_nxt[0] if isinstance(s_nxt, (list, tuple)) else 0)
                                cr2 = getattr(s_nxt, "r", s_nxt[1] if isinstance(s_nxt, (list, tuple)) else 0)
                                d_c = grid_distance_3d(Hex(cq1, cr1), Hex(qo, ro), z_ply, z_oth, grid_type=g_type, diagonal_rule=d_rule)
                                d_n = grid_distance_3d(Hex(cq2, cr2), Hex(qo, ro), z_ply, z_oth, grid_type=g_type, diagonal_rule=d_rule)
                                if d_c <= reach and d_n > reach:
                                    exited_reach = True
                                if d_c > reach and d_n <= reach:
                                    entered_reach = True
                        else:
                            d_f = grid_distance_3d(Hex(from_pos[0], from_pos[1]), Hex(qo, ro), z_ply, z_oth, grid_type=g_type, diagonal_rule=d_rule)
                            d_t = grid_distance_3d(Hex(to_pos[0], to_pos[1]), Hex(qo, ro), z_ply, z_oth, grid_type=g_type, diagonal_rule=d_rule)
                            exited_reach = (d_f <= reach and d_t > reach)
                            entered_reach = (d_f > reach and d_t <= reach)

                        from common.subclass_and_race_rules import has_no_oa_against
                        if has_no_oa_against(player, other):
                            continue
                        provoke_exit = exited_reach and (not has_flyby) and (not disengaged or has_sentinel)
                        provoke_enter = entered_reach and has_pam
                        if provoke_exit or provoke_enter:
                            incaps = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
                            o_conds = getattr(other, "conditions", [])
                            is_blind = any(is_condition_active(o_conds, c) for c in ["Cieco", "Accecato", "Blinded"])
                            is_mover_invis = is_condition_active(conds, "Invisibile")
                            from server.rules.reaction_magic import check_special_senses_see_target
                            can_perceive_special, _ = check_special_senses_see_target(other, player, reach)
                            if (not is_blind or can_perceive_special) and (not is_mover_invis or can_perceive_special) and not any(is_condition_active(o_conds, c) for c in incaps):
                                reason_oa = "entra nella portata (Maestro d'Armi Astate)" if provoke_enter and not provoke_exit else f"esce dalla portata di mischia ({reach * 1.5}m)"
                                opp_alert = f"⚠️ [OPPORTUNITÀ] {player.name} {reason_oa} di {other.name}! {other.name} può usare la Reazione per un Attacco d'Opportunità!"
                                game_state.log_dm_message(f"[COMBAT] {opp_alert}")
                                from common.protocol import make_chat_broadcast, make_opportunity_alert, make_prompt_reaction
                                from server.rules.reaction_magic import _has_no_reactions_effect
                                broadcast(game_state, make_chat_broadcast("Sistema", opp_alert))
                                if getattr(other, "conn", None):
                                    send_message(other.conn, make_opportunity_alert(player.name, f"{player.name} {reason_oa}!"))
                                    auto_react = (getattr(game_state, "automation_settings", {}) or {}).get("auto_prompt_reactions", True)
                                    if auto_react and not getattr(other, "has_reacted_this_turn", False) and not getattr(other, "surprised", False) and not _has_no_reactions_effect(other):
                                        send_message(other.conn, make_prompt_reaction(
                                            "OPPORTUNITY_ATTACK",
                                            player.name,
                                            other.name,
                                            _extract_oa_weapon_details(other),
                                        ))

        prev_pos = list(player.position) if hasattr(player, "position") and player.position else None
        game_state.move_player(player.name, to_pos)
        if getattr(player, "overrun_tumble_through_target", None):
            player.overrun_tumble_through_target = None
        if prev_pos and to_pos and prev_pos != to_pos and not is_teleport:
            _dm_s_mv = getattr(game_state, "automation_settings", {}) or {}
            if _dm_s_mv.get("opt_facing", False):
                from server.dm_optional_tools import update_facing_from_move
                _gt_mv = (getattr(game_state, "current_map", {}) or {}).get("grid_type", "hex")
                update_facing_from_move(player, prev_pos, to_pos, grid_type=_gt_mv)
        if is_teleport or data.get("is_forced", False):
            from server.rules.reaction_magic import break_grapple_if_out_of_reach
            break_grapple_if_out_of_reach(player, game_state)

        # Tracciamento movimento rettilineo per Charge/Pounce (MM)
        if prev_pos and prev_pos != to_pos and not is_teleport:
            cur_m_dir = getattr(game_state, "current_map", None)
            g_t_dir = cur_m_dir.get("grid_type", "hex") if cur_m_dir else "hex"
            dq = (1 if to_pos[0] > prev_pos[0] else (-1 if to_pos[0] < prev_pos[0] else 0))
            dr = (1 if to_pos[1] > prev_pos[1] else (-1 if to_pos[1] < prev_pos[1] else 0))
            step_hexes = int(grid_distance_3d(Hex(prev_pos[0], prev_pos[1]), Hex(to_pos[0], to_pos[1]), 0, 0, grid_type=g_t_dir))
            if getattr(player, "last_move_dir", None) == (dq, dr) or not getattr(player, "last_move_dir", None):
                player.moved_straight_hexes = getattr(player, "moved_straight_hexes", 0) + step_hexes
            else:
                player.moved_straight_hexes = step_hexes
            player.last_move_dir = (dq, dr)

        # Trascinamento creature Afferrate (Grappled) + Cavalcatura sincronizzata (Mount)
        from common.protocol import make_player_move as _mk_pmv
        for other_m in getattr(game_state, "players", []):
            if other_m.name == player.name:
                continue
            if getattr(other_m, "grappled_by", None) == player.name and is_condition_active(getattr(other_m, "conditions", []), "Afferrato") and prev_pos:
                g_dest = [move_path[-2].q, move_path[-2].r] if (move_path and len(move_path) >= 2) else prev_pos
                game_state.move_player(other_m.name, g_dest)
                broadcast(game_state, _mk_pmv(other_m.name, g_dest))
            elif getattr(other_m, "mount_name", None) == player.name:
                game_state.move_player(other_m.name, list(to_pos))
                broadcast(game_state, _mk_pmv(other_m.name, list(to_pos)))

        # Effetti Pericolosi Terreno Difficile (Ghiaccio, Rovi, Palude)
        cur_map = getattr(game_state, "current_map", None)
        diff_terrain = cur_map.get("difficult_terrain", {}) if cur_map else {}
        diff_map = {}
        if isinstance(diff_terrain, dict):
            for k, v in diff_terrain.items():
                if isinstance(k, str) and "," in k:
                    parts = k.split(",")
                    diff_map[(int(parts[0]), int(parts[1]))] = str(v).lower()
                elif isinstance(k, (tuple, list)) and len(k) >= 2:
                    diff_map[(int(k[0]), int(k[1]))] = str(v).lower()
        elif isinstance(diff_terrain, list):
            for item in diff_terrain:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    diff_map[(int(item[0]), int(item[1]))] = "fango"

        to_tup = (to_pos[0], to_pos[1])
        if to_tup in diff_map:
            t_type = diff_map[to_tup]
            if t_type in ("ghiaccio", "ice"):
                # D&D 5e: Ghiaccio Scivoloso -> TS Destrezza CD 10 o cade prono
                dex_mod = get_effective_save_bonus_from_dict(player, "DES")
                dex_roll = random.randint(1, 20) + dex_mod
                if dex_roll < 10:
                    if "Prono" not in player.conditions:
                        player.conditions.append("Prono")
                    alert = f"🧊 {player.name} scivola sul Ghiaccio (TS Des {dex_roll} vs CD 10) e cade Prono!"
                    game_state.log_dm_message(f"[TERRENO] {alert}")
                    from common.protocol import make_chat_broadcast, make_player_stats_update
                    broadcast(game_state, make_chat_broadcast("Sistema", alert))
                    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, getattr(player, 'initiative', 0), player.conditions, getattr(player, 'temp_hp', 0)))
                else:
                    from common.protocol import make_chat_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", f"🧊 {player.name} attraversa il ghiaccio mantenendo l'equilibrio (TS Des {dex_roll} vs CD 10)."))
            elif t_type in ("rovi", "briars", "spine"):
                # D&D 5e: Rovi acuminati -> 1d4 danni da spine via apply_damage (Temp HP, resistenze, death saves)
                thorn_dmg = random.randint(1, 4)
                from server.rules.combat import apply_damage
                final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(player, thorn_dmg, "Perforante", game_state)
                alert = f"🌿 {player.name} attraversa i Rovi acuminati e subisce {final_dmg} danni perforanti{note}!"
                game_state.log_dm_message(f"[TERRENO] {alert}")
                from common.protocol import make_chat_broadcast, make_player_stats_update
                broadcast(game_state, make_chat_broadcast("Sistema", alert))
                broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, getattr(player, 'initiative', 0), player.conditions, getattr(player, 'temp_hp', 0)))
        
        # Gestione Trappole D&D 5e sulla mappa
        if getattr(game_state, "current_map", None):
            traps = game_state.current_map.get("traps", [])
            if is_teleport:
                path_coords = {(to_pos[0], to_pos[1])}
            else:
                path_coords = {(getattr(step, "q", step[0] if isinstance(step, (list, tuple)) else 0), getattr(step, "r", step[1] if isinstance(step, (list, tuple)) else 0)) for step in move_path} if move_path else {(to_pos[0], to_pos[1])}
            for trap in traps:
                t_coord = (trap.get("q"), trap.get("r"))
                if t_coord in path_coords and not trap.get("triggered", False):
                    trap["triggered"] = True
                    trap["hidden"] = False
                    trap["secret"] = False
                    trap_name = trap.get("name", "Trappola a Trabocchetto")
                    trap_dc = trap.get("dc", 13)
                    trap_dmg = trap.get("damage", "2d10")
                    trap_dtype = trap.get("damage_type", "Perforante")
                    
                    alert = f"💥 [TRAPPOLA 5e] {player.name} attiva una trappola ({trap_name})!"
                    game_state.log_dm_message(f"[TRAPPOLA] {alert}")
                    from common.protocol import make_chat_broadcast, make_map_data_update_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", alert))
                    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
                    
                    if getattr(player, "conn", None):
                        from common.protocol import make_prompt_save
                        send_message(player.conn, make_prompt_save("DES", trap_dc, trap_dmg, True, trap_name, trap_dtype))
                    else:
                        from server.rules.combat import _process_save_result
                        from common.dice import roll_dice
                        mod = get_effective_save_bonus_from_dict(player, "DES")
                        mod_str = f"+{mod}" if mod >= 0 else str(mod)
                        res = roll_dice(f"1d20{mod_str}")
                        is_crit = res["rolls"][0] == 20
                        is_fail = res["rolls"][0] == 1
                        _process_save_result(player.name, "DES", res["total"], is_crit, is_fail, trap_dc, trap_dmg, True, trap_name, game_state, trap_dtype)
        
        if getattr(game_state, "current_map", None):
            teleports = game_state.current_map.get("teleports", {})
            pos_key = f"{to_pos[0]},{to_pos[1]}"
            if pos_key in teleports:
                raw_map_file = str(teleports[pos_key])
                map_file = os.path.basename(raw_map_file)
                maps_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "maps"))
                map_path = os.path.abspath(os.path.join(maps_dir, map_file))
                
                camp_folder = getattr(game_state.active_campaign, "folder_path", None) if getattr(game_state, "active_campaign", None) else None
                camp_folder_abs = os.path.abspath(camp_folder) if camp_folder else None
                
                is_safe = map_path.startswith(maps_dir + os.sep) or (camp_folder_abs and map_path.startswith(camp_folder_abs + os.sep))
                if is_safe and os.path.exists(map_path):
                    try:
                        with open(map_path, "r", encoding="utf-8") as f:
                            new_map_data = json.load(f)
                        from common.network_utils import resolve_map_image_data
                        resolve_map_image_data(new_map_data, extra_dirs=[os.path.dirname(map_path), camp_folder_abs])
                        
                        game_state.load_map(new_map_data)
                        
                        from common.protocol import make_chat_broadcast, make_game_state, make_map_data_update_broadcast
                        broadcast(game_state, make_map_data_update_broadcast(new_map_data))
                        broadcast(game_state, make_game_state(game_state.get_state_dict()))
                        broadcast(game_state, make_chat_broadcast("Sistema", "Il gruppo è stato teletrasportato."))
                        game_state._trigger_gui_update()
                        return
                    except Exception as e:
                        print(f"Errore caricamento mappa teleport {map_file}: {e}")

        # Pericoli movimento da Incantesimi ad Area (es. Crescita di Spine / Spike Growth) - non si applica al teletrasporto
        if not is_teleport and getattr(game_state, "active_aoes", None):
            from common.spell_effects_engine import apply_spell_movement_hazards
            from common.protocol import make_chat_broadcast, make_player_stats_update
            haz_msgs = apply_spell_movement_hazards(player, locals().get("from_pos"), to_pos, game_state)
            for hm in haz_msgs:
                broadcast(game_state, make_chat_broadcast("Sistema", hm))
                broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, getattr(player, "conditions", []), getattr(player, "temp_hp", 0)))

        # Sincronizzazione visibilità FoW per token non del party che entrano/escono dalla zona rivelata
        is_party_ent = bool(
            getattr(player, "is_party_member", False)
            or getattr(player, "is_companion", False)
            or getattr(player, "conn", None) is not None
        )
        cur_map_vis = getattr(game_state, "current_map", None)
        if isinstance(cur_map_vis, dict) and cur_map_vis.get("fow_enabled", False):
            if not is_party_ent and getattr(player, "layer", "token") != "gm" and not getattr(player, "is_hidden", False) and not getattr(player, "in_pocket_dimension", False):
                from common.network_utils import _extract_rev_set
                rev_set_vis = _extract_rev_set(cur_map_vis)
                was_vis = bool(prev_pos and len(prev_pos) >= 2 and (prev_pos[0], prev_pos[1]) in rev_set_vis)
                now_vis = (to_pos[0], to_pos[1]) in rev_set_vis
                if was_vis and not now_vis:
                    from common.protocol import make_player_left
                    broadcast(game_state, make_player_left(player.name))
                elif not was_vis and now_vis and hasattr(game_state, "sanitize_player_for_players"):
                    from common.protocol import make_player_joined
                    broadcast(game_state, make_player_joined(game_state.sanitize_player_for_players(player)))

        # Auto-explore FoW around the player's new position with true Line of Sight (LoS) and Dynamic Light
        # Only party members / companions / connected players reveal FoW (monsters/NPCs must not reveal fog!)
        auto_fow = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_fow = game_state.automation_settings.get("auto_explore_fow", True)

        if auto_fow and is_party_ent and getattr(game_state, "current_map", None) and game_state.current_map.get("fow_enabled", False):
            changed = auto_explore_fow(player, game_state)
            if changed:
                game_state._trigger_gui_update()
                from common.protocol import make_fow_update_broadcast, make_player_move
                broadcast(game_state, make_player_move(player.name, to_pos, movement_spent_this_turn=getattr(player, "movement_spent_this_turn", 0)))
                broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"], fow_enabled=True))
                return
                
        from common.protocol import make_player_move
        broadcast(game_state, make_player_move(player.name, to_pos, movement_spent_this_turn=getattr(player, "movement_spent_this_turn", 0)))


def handle_stand_up_request(data, player, game_state):
    """
    Rialzarsi da terra (Prono) secondo D&D 5e RAW (PHB p. 190):
    Costa una quantità di movimento pari alla metà della velocità massima (max_hexes // 2).
    Non è possibile rialzarsi se la velocità è 0 o il movimento rimasto non basta.
    """
    if not player:
        return
    from common.i18n import is_condition_active, speed_to_hexes
    from common.network_utils import send_message, broadcast
    from common.protocol import make_error_reply, make_chat_broadcast, make_player_stats_update

    err_msg = None
    stats_pkt = None
    with game_state.lock:
        conds = getattr(player, "conditions", [])
        if not is_condition_active(conds, "Prono"):
            err_msg = f"{player.name} non è Prono a terra!"
        else:
            in_combat = getattr(game_state, "combat_active", False)
            speed = getattr(player, "speed", 30)
            if speed <= 0 or getattr(player, "exhaustion_level", 0) >= 5 or any(
                is_condition_active(conds, c) for c in ("Afferrato", "Grappled", "Trattenuto", "Restrained", "Paralizzato", "Incosciente", "Stordito", "Pietrificato", "Incapacitato")
            ):
                err_msg = "Impossibile rialzarsi: velocità pari a 0 o condizione che impedisce il movimento (PHB p. 190)!"
            else:
                if in_combat:
                    speed_unit = getattr(player, "speed_unit", None)
                    base_hexes = speed_to_hexes(speed, speed_unit)
                    is_dashed = is_condition_active(conds, "Scatto")
                    max_hexes = base_hexes * 2 if is_dashed else base_hexes
                    cost = max(1, max_hexes // 2)
                    spent = getattr(player, "movement_spent_this_turn", 0)
                    strict_move = True
                    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                        strict_move = game_state.automation_settings.get("strict_movement_limits", True)
                    if strict_move and (spent + cost) > max_hexes:
                        err_msg = (
                            f"Non hai abbastanza movimento per rialzarti! Rialzarsi costa {cost} esagoni "
                            f"(metà del tuo movimento). Ti restano solo {max(0, max_hexes - spent)} esagoni."
                        )
                    else:
                        player.movement_spent_this_turn = spent + cost

                if not err_msg:
                    player.conditions = [c for c in conds if str(c).strip().lower() not in ("prono", "prone")]
                    if getattr(player, "full_sheet", None) and isinstance(player.full_sheet.get("conditions"), list):
                        player.full_sheet["conditions"] = list(player.conditions)
                    stats_pkt = make_player_stats_update(
                        player.name,
                        player.hp,
                        player.max_hp,
                        player.initiative,
                        list(player.conditions),
                        getattr(player, "temp_hp", 0),
                    )

    if err_msg:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(err_msg))
        return

    broadcast(game_state, stats_pkt)
    msg = f"🛡️ {player.name} si rialza da terra (Prono rimosso, costo: metà del movimento)."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(msg)
    game_state._trigger_gui_update()
