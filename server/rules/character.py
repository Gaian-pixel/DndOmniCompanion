from common.protocol import (
    make_campaign_starter_granted,
    make_chat_broadcast,
    make_error_reply,
    make_game_state,
    make_map_data_update_broadcast,
    make_player_stats_update,
)
from common.network_utils import send_message, broadcast
import copy
import math
import time
from common.character_schema import restore_entity_rest_resources
from server.rules.combat import _apply_hp_change, apply_damage, clear_unconscious_and_reset_death_saves
from common.dice import roll_dice
from common.i18n import is_condition_active

def handle_update_stats_request(data, player, game_state):
    try:
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            data = data["data"]
        is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
        req_name = data.get("name") or data.get("target_name") or data.get("token_name")
        target = player
        if is_dm and req_name:
            target = game_state.find_player(req_name)
        elif req_name:
            found_t = game_state.find_player(req_name)
            if found_t:
                target = found_t
        if not target:
            return
        if not is_dm and player:
            is_owner = (target.name == player.name or getattr(target, "owner", None) == player.name or getattr(target, "master_name", None) == player.name)
            if not is_owner:
                return
            
        hp = int(data.get("hp", target.hp))
        max_hp = int(data.get("max_hp", target.max_hp)) if data.get("max_hp") is not None else target.max_hp
        if not is_dm and getattr(target, "max_hp", 0) and max_hp != target.max_hp:
            # Connected non-DM clients cannot mutate max_hp via raw UPDATE_STATS
            # (prevents max_hp spoofing and pre-UPDATE_FULL_SHEET level-up HP race).
            max_hp = target.max_hp
        initiative = int(data.get("initiative", target.initiative)) if data.get("initiative") is not None else target.initiative
        conditions = data.get("conditions", getattr(target, "conditions", []))
        if isinstance(conditions, list):
            from server.dm_monster_engine import filter_swarm_condition
            conditions = [c for c in conditions if filter_swarm_condition(target, c)]
        if "temp_hp" in data and data.get("temp_hp") is not None:
            temp_hp = int(data.get("temp_hp"))
        else:
            temp_hp = getattr(target, "temp_hp", 0)
        pending_fow_map = False
        stats_payload = None
        preserved_on_reconnect = False
        with game_state.lock:
            preserve_stats = bool(getattr(target, "_preserve_stats_on_join", False)) and not is_dm
            preserve_until = getattr(target, "_preserve_join_until", None)
            if preserve_stats and isinstance(preserve_until, (int, float)) and time.monotonic() > preserve_until:
                target._preserve_stats_on_join = False
                target._preserve_server_state_on_join = False
                target._preserve_join_until = None
                preserve_stats = False
            if preserve_stats:
                target._preserve_stats_on_join = False
                preserved_on_reconnect = True
                if data.get("initiative") is not None:
                    target.initiative_bonus = initiative
                    if not (getattr(game_state, "combat_active", False) and getattr(target, "in_combat", False)):
                        target.initiative = initiative
                stats_payload = make_player_stats_update(
                    target.name, target.hp, target.max_hp, target.initiative,
                    list(getattr(target, "conditions", []) or []), getattr(target, "temp_hp", 0),
                    light_radius=getattr(target, "light_radius", 0),
                    light_color=getattr(target, "light_color", "#FFA500"),
                    elevation=getattr(target, "elevation", 0),
                )
            else:
                target.max_hp = max_hp
                target.temp_hp = max(0, temp_hp)
                if data.get("initiative") is not None:
                    target.initiative_bonus = initiative
                    if not (getattr(game_state, "combat_active", False) and getattr(target, "in_combat", False)):
                        target.initiative = initiative
                target.conditions = conditions
                if "light_radius" in data:
                    target.light_radius = max(0, int(data["light_radius"]))
                if "light_color" in data:
                    target.light_color = str(data["light_color"])
                if "elevation" in data:
                    old_elev = getattr(target, "elevation", 0)
                    new_elev = int(data["elevation"])
                    target.elevation = new_elev
                    if old_elev > new_elev and data.get("is_fall", False):
                        from server.rules.combat import resolve_falling
                        resolve_falling(target, old_elev - new_elev, game_state)
                incap = ("incapacitato", "incapacitated", "incosciente", "unconscious", "paralizzato", "paralyzed", "stordito", "stunned", "pietrificato", "petrified", "morto", "dead")
                if any(str(c).strip().lower() in incap for c in conditions) or hp <= 0:
                    from server.rules.combat import drop_concentration
                    drop_concentration(target, game_state, notify=True)
                    target.readied_action_data = None
                    if isinstance(conditions, list):
                        conditions[:] = [c for c in conditions if str(c).strip().lower() != "azione preparata"]
                    if isinstance(getattr(target, "conditions", None), list):
                        target.conditions = [c for c in target.conditions if str(c).strip().lower() != "azione preparata"]
                    if isinstance(getattr(target, "full_sheet", None), dict) and isinstance(target.full_sheet.get("conditions"), list):
                        target.full_sheet["conditions"] = [
                            c for c in target.full_sheet["conditions"] if str(c).strip().lower() != "azione preparata"
                        ]
                _apply_hp_change(target, hp, game_state)
                if isinstance(getattr(target, "full_sheet", None), dict):
                    target.full_sheet["hp_current"] = target.hp
                    target.full_sheet["hp"] = target.hp
                    target.full_sheet["current_hp"] = target.hp
                    target.full_sheet["hp_max"] = target.max_hp
                    target.full_sheet["max_hp"] = target.max_hp
                    target.full_sheet["temp_hp"] = target.temp_hp
                    target.full_sheet["conditions"] = list(target.conditions)
                from server.rules.movement import auto_explore_fow
                _is_party_tgt = (not getattr(target, "is_npc", False)) and (
                    bool(
                        getattr(target, "is_party_member", False)
                        or getattr(target, "is_companion", False)
                        or getattr(target, "conn", None) is not None
                    )
                    or (target is player)
                )
                pending_fow_map = bool(auto_explore_fow(target, game_state)) if _is_party_tgt else False
                stats_payload = make_player_stats_update(
                    target.name, target.hp, target.max_hp, target.initiative,
                    list(target.conditions), target.temp_hp,
                    light_radius=getattr(target, "light_radius", 0),
                    light_color=getattr(target, "light_color", "#FFA500"),
                    elevation=getattr(target, "elevation", 0),
                )
        if pending_fow_map:
            broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
        game_state._trigger_gui_update()
        broadcast(game_state, stats_payload)
        if preserved_on_reconnect:
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
    except Exception as e:
        print("Errore handle_update_stats_request:", e)


def handle_set_elevation_request(data, player, game_state):
    """Imposta la quota 3D / altitudine in piedi di un personaggio o mostro."""
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    target_name = data.get("target_name") or data.get("name") or (player.name if player else None)
    target = game_state.find_player(target_name) if target_name else None
    if not target:
        return

    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and player:
        is_owner = (target.name == player.name or getattr(target, "owner", None) == player.name or getattr(target, "master_name", None) == player.name)
        if not is_owner:
            return

    old_elev = getattr(target, "elevation", 0)
    new_elev = int(data.get("elevation", 0))
    is_fall = data.get("is_fall", False)
    
    if is_fall and old_elev > new_elev:
        fall_dist = old_elev - new_elev
        from server.rules.combat import resolve_falling
        resolve_falling(target, fall_dist, game_state)
    else:
        target.elevation = new_elev
        broadcast(game_state, make_player_stats_update(
            target.name, target.hp, target.max_hp, target.initiative,
            getattr(target, "conditions", []), getattr(target, "temp_hp", 0),
            elevation=target.elevation,
            active_effects=getattr(target, "active_effects", [])
        ))
        msg = f"📐 **Quota 3D**: {target.name} imposta la quota ad altitudine **{new_elev} ft**."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[QUOTA] {msg}")
        game_state._trigger_gui_update()


def handle_update_full_sheet_request(data, player, game_state):
    char_data = data.get("character") or data.get("sheet")
    if char_data:
        from common.character_schema import normalize_character_dict
        from common.network_utils import is_dm_actor
        norm = normalize_character_dict(char_data)
        if isinstance(char_data, dict):
            char_data.update(norm)
        else:
            char_data = norm

        with game_state.lock:
            existing_sheet = getattr(player, "full_sheet", None)
            had_existing_sheet = isinstance(existing_sheet, dict) and bool(existing_sheet)
            is_dm = is_dm_actor(player)
            preserve_until = getattr(player, "_preserve_join_until", None)
            preserve_reconnect = bool(getattr(player, "_preserve_server_state_on_join", False))
            if preserve_reconnect and isinstance(preserve_until, (int, float)) and time.monotonic() > preserve_until:
                preserve_reconnect = False
                player._preserve_stats_on_join = False
                player._preserve_join_until = None
            elif preserve_reconnect and preserve_until is None:
                player._preserve_join_until = time.monotonic() + 1.0
            elif not preserve_reconnect and not getattr(player, "_preserve_stats_on_join", False):
                player._preserve_join_until = None
            player._preserve_server_state_on_join = False

            # Preserva i flag di starter kit lato server per impedire ri-assegnazioni ripetute
            if had_existing_sheet:
                if existing_sheet.get("starting_kit_applied"):
                    char_data["starting_kit_applied"] = True
                if existing_sheet.get("campaign_starter_received"):
                    char_data["campaign_starter_received"] = True

            from common.starter_equipment import apply_class_and_race_starter_kit, apply_campaign_starter_kit
            # Se il personaggio non ha ancora ricevuto il kit iniziale di classe/razza, assegnalo
            if not char_data.get("starting_kit_applied"):
                apply_class_and_race_starter_kit(char_data)

            granted_campaign_starter = False
            # Se non ha ancora ricevuto lo starter kit della campagna, assegnalo
            if not char_data.get("campaign_starter_received"):
                campaign_kit = getattr(game_state, "campaign_starter_kit", None)
                apply_campaign_starter_kit(char_data, campaign_kit)
                granted_campaign_starter = True

            # Protezione e vincoli di gioco: se il PG ha già un full_sheet registrato sul server,
            # impedisci aumenti unilaterali di valuta, livello/attributi o spawn abusivo di oggetti senza approvazione del DM
            prev_server_ac = int(existing_sheet.get("ac", getattr(player, "ac", 10)) or 10) if had_existing_sheet else None
            stripped_unapproved_item = False
            if had_existing_sheet and not is_dm:
                srv_hp_cur = player.hp if hasattr(player, "hp") and isinstance(player.hp, (int, float)) else existing_sheet.get("hp_current", 10)
                srv_hp_max = player.max_hp if hasattr(player, "max_hp") and isinstance(player.max_hp, (int, float)) else existing_sheet.get("hp_max", 10)
                try:
                    srv_hp_cur = int(srv_hp_cur)
                except (ValueError, TypeError):
                    srv_hp_cur = 10
                try:
                    srv_hp_max = max(1, int(srv_hp_max))
                except (ValueError, TypeError):
                    srv_hp_max = 10

                try:
                    server_lvl = max(1, int(existing_sheet.get("level", 1) or 1))
                except (ValueError, TypeError):
                    server_lvl = 1
                try:
                    client_lvl = max(1, min(20, int(char_data.get("level", server_lvl) or server_lvl)))
                except (ValueError, TypeError):
                    client_lvl = server_lvl
                if client_lvl > server_lvl + 1:
                    client_lvl = server_lvl + 1
                    char_data["level"] = client_lvl
                char_data["proficiency_bonus"] = 2 + (client_lvl - 1) // 4

                def _canon_cls_key(name):
                    low = str(name or "").strip().lower()
                    aliases = {
                        "guerriero": "fighter", "fighter": "fighter",
                        "ladro": "rogue", "rogue": "rogue",
                        "mago": "wizard", "wizard": "wizard",
                        "chierico": "cleric", "cleric": "cleric",
                        "druido": "druid", "druid": "druid",
                        "barbaro": "barbarian", "barbarian": "barbarian",
                        "bardo": "bard", "bard": "bard",
                        "paladino": "paladin", "paladin": "paladin",
                        "ranger": "ranger",
                        "stregone": "sorcerer", "sorcerer": "sorcerer",
                        "warlock": "warlock",
                        "monaco": "monk", "monk": "monk",
                        "artefice": "artificer", "artificer": "artificer",
                    }
                    return aliases.get(low, low)

                def _asi_set_for_cls(name):
                    ck = _canon_cls_key(name)
                    if ck == "fighter":
                        return (4, 6, 8, 12, 14, 16, 19)
                    if ck == "rogue":
                        return (4, 8, 10, 12, 16, 19)
                    return (4, 8, 12, 16, 19)

                # Valida eventuale progressione multiclasse e verifica se una classe ha raggiunto un livello ASI
                srv_cls_raw = existing_sheet.get("classes")
                cli_cls_raw = char_data.get("classes")
                srv_cls_map = {}
                if isinstance(srv_cls_raw, dict) and srv_cls_raw:
                    for ck, cv in srv_cls_raw.items():
                        try:
                            srv_cls_map[_canon_cls_key(ck)] = int(cv or 0)
                        except (ValueError, TypeError):
                            pass
                elif existing_sheet.get("char_class"):
                    srv_cls_map[_canon_cls_key(existing_sheet.get("char_class"))] = server_lvl

                asi_earned = False
                new_barb_lvl = srv_cls_map.get("barbarian", 0)
                if isinstance(cli_cls_raw, dict) and cli_cls_raw and client_lvl > server_lvl:
                    sanitized_cls = {}
                    total_cli_cls = 0
                    new_barb_lvl = 0
                    for ck, cv in cli_cls_raw.items():
                        try:
                            new_cv = max(0, int(cv or 0))
                        except (ValueError, TypeError):
                            new_cv = 0
                        canon_k = _canon_cls_key(ck)
                        old_cv = srv_cls_map.get(canon_k, 0)
                        if new_cv < old_cv:
                            new_cv = old_cv
                        if new_cv > old_cv + 1:
                            new_cv = old_cv + 1
                        sanitized_cls[ck] = new_cv
                        total_cli_cls += new_cv
                        if canon_k == "barbarian":
                            new_barb_lvl += new_cv
                        if new_cv > old_cv and new_cv in _asi_set_for_cls(canon_k):
                            asi_earned = True
                    if total_cli_cls > client_lvl and isinstance(srv_cls_raw, dict) and srv_cls_raw:
                        char_data["classes"] = copy.deepcopy(srv_cls_raw)
                        asi_earned = False
                        new_barb_lvl = srv_cls_map.get("barbarian", 0)
                    else:
                        char_data["classes"] = sanitized_cls
                elif client_lvl > server_lvl:
                    single_cls = char_data.get("char_class") or existing_sheet.get("char_class") or ""
                    asi_earned = client_lvl in _asi_set_for_cls(single_cls)
                    if _canon_cls_key(single_cls) == "barbarian":
                        new_barb_lvl = client_lvl
                elif isinstance(srv_cls_raw, dict) and srv_cls_raw:
                    char_data["classes"] = copy.deepcopy(srv_cls_raw)

                srv_barb_lvl = srv_cls_map.get("barbarian", 0)
                is_barb_20 = (new_barb_lvl >= 20)
                primal_champion_gained = (client_lvl > server_lvl and srv_barb_lvl < 20 and new_barb_lvl >= 20)

                server_attrs = existing_sheet.get("attributes", {})
                client_attrs = char_data.get("attributes", {})
                if isinstance(server_attrs, dict) and isinstance(client_attrs, dict):
                    if client_lvl <= server_lvl or (not asi_earned and not primal_champion_gained):
                        for a_k, a_val in server_attrs.items():
                            if a_k in client_attrs:
                                try:
                                    if int(client_attrs[a_k]) > int(a_val):
                                        client_attrs[a_k] = a_val
                                except (ValueError, TypeError):
                                    client_attrs[a_k] = a_val
                    else:
                        # Campione Primordiale (Barbaro Lv 20, PHB p. 49): +4 FOR e +4 COS fino a 24;
                        # ASI di classe: fino a +2 punti totali (max 20, o 24 FOR/COS per Barbaro Lv 20)
                        remaining_asi = 2 if asi_earned else 0
                        for a_k, a_val in server_attrs.items():
                            if a_k in client_attrs:
                                try:
                                    s_v = int(a_val)
                                    c_v = int(client_attrs[a_k])
                                except (ValueError, TypeError):
                                    client_attrs[a_k] = a_val
                                    continue
                                if c_v > s_v:
                                    key_up = str(a_k).upper()
                                    attr_cap = 24 if (is_barb_20 and key_up in ("FOR", "COS", "STR", "CON")) else 20
                                    primal_budget = 4 if (primal_champion_gained and key_up in ("FOR", "COS", "STR", "CON")) else 0
                                    want_gain = max(0, min(attr_cap, c_v) - s_v)
                                    primal_used = min(primal_budget, want_gain)
                                    asi_used = min(remaining_asi, max(0, want_gain - primal_used))
                                    client_attrs[a_k] = s_v + primal_used + asi_used
                                    remaining_asi -= asi_used
                    char_data["attributes"] = client_attrs

                # Gestione HP: immutabile a parità di livello, aumento validato D&D 5e al level-up
                if client_lvl <= server_lvl:
                    char_data["hp_current"] = srv_hp_cur
                    char_data["hp_max"] = srv_hp_max
                else:
                    try:
                        old_cos = int(server_attrs.get("COS", 10) or 10)
                    except (ValueError, TypeError):
                        old_cos = 10
                    try:
                        new_cos = int(char_data.get("attributes", {}).get("COS", old_cos) or old_cos)
                    except (ValueError, TypeError):
                        new_cos = old_cos
                    old_cos_mod = (old_cos - 10) // 2
                    new_cos_mod = (new_cos - 10) // 2
                    retro_con = max(0, new_cos_mod - old_cos_mod) * server_lvl

                    def _has_tough(sheet_d):
                        ft_blob = str(sheet_d.get("features", "") or "").lower()
                        if "robusto" in ft_blob or "tough" in ft_blob:
                            return True
                        for lst_k in ("feats", "features_list"):
                            for ent in (sheet_d.get(lst_k) or []):
                                nm = str(ent.get("name", "") if isinstance(ent, dict) else ent).lower()
                                if "robusto" in nm or "tough" in nm:
                                    return True
                        return False

                    retro_tough = (2 * client_lvl) if (_has_tough(char_data) and not _has_tough(existing_sheet)) else 0
                    max_level_gain = max(1, 12 + new_cos_mod + 4) + retro_con + retro_tough
                    try:
                        req_hp_max = int(char_data.get("hp_max", srv_hp_max) or srv_hp_max)
                    except (ValueError, TypeError):
                        req_hp_max = srv_hp_max
                    approved_hp_max = max(srv_hp_max + 1, min(req_hp_max, srv_hp_max + max_level_gain))
                    hp_delta = max(0, approved_hp_max - srv_hp_max)
                    char_data["hp_max"] = approved_hp_max
                    char_data["hp_current"] = min(approved_hp_max, max(0, srv_hp_cur) + hp_delta)

                char_data["hp"] = char_data["hp_current"]
                char_data["current_hp"] = char_data["hp_current"]
                char_data["max_hp"] = char_data["hp_max"]

                if preserve_reconnect:
                    for dict_k in ("spell_slots", "pact_slots", "class_resources", "hit_dice_pools"):
                        if isinstance(existing_sheet.get(dict_k), dict):
                            char_data[dict_k] = copy.deepcopy(existing_sheet[dict_k])
                    if isinstance(existing_sheet.get("custom_resources"), list):
                        char_data["custom_resources"] = copy.deepcopy(existing_sheet["custom_resources"])
                    for sc_k in ("spell_points_current", "spell_points_max", "hit_dice_current", "exhaustion_level", "inspiration", "has_inspiration"):
                        if sc_k in existing_sheet and existing_sheet[sc_k] is not None:
                            char_data[sc_k] = existing_sheet[sc_k]
                    srv_temp = getattr(player, "temp_hp", existing_sheet.get("temp_hp", 0))
                    char_data["temp_hp"] = max(0, int(srv_temp or 0))
                    srv_conds = getattr(player, "conditions", None)
                    if isinstance(srv_conds, list):
                        char_data["conditions"] = list(srv_conds)
                    elif isinstance(existing_sheet.get("conditions"), list):
                        char_data["conditions"] = list(existing_sheet["conditions"])
                    if isinstance(existing_sheet.get("pact_slots"), dict):
                        pact_s = existing_sheet["pact_slots"]
                        player.pact_slots_max = int(pact_s.get("max", 0) or 0)
                        player.pact_slots_current = int(pact_s.get("current", 0) or 0)
                        player.pact_slot_level = int(pact_s.get("level", 0) or 0)
                elif client_lvl <= server_lvl:
                    # Proteggi le risorse autorevoli lato server da ripristini/sovrascritture fuori finestra di riconnessione
                    srv_slots = existing_sheet.get("spell_slots")
                    cli_slots = char_data.get("spell_slots")
                    if isinstance(srv_slots, dict) and isinstance(cli_slots, dict):
                        merged_slots = copy.deepcopy(srv_slots)
                        for lv_k, s_ent in srv_slots.items():
                            c_ent = cli_slots.get(lv_k)
                            if isinstance(s_ent, dict) and isinstance(c_ent, dict):
                                try:
                                    s_cur = int(s_ent.get("current", s_ent.get("max", 0)) or 0)
                                    c_cur = int(c_ent.get("current", s_cur) or 0)
                                    merged_slots[lv_k]["current"] = max(0, min(s_cur, c_cur))
                                except (ValueError, TypeError):
                                    pass
                        char_data["spell_slots"] = merged_slots
                    srv_pact = existing_sheet.get("pact_slots")
                    cli_pact = char_data.get("pact_slots")
                    if isinstance(srv_pact, dict):
                        merged_pact = copy.deepcopy(srv_pact)
                        if isinstance(cli_pact, dict):
                            try:
                                s_p_cur = int(srv_pact.get("current", 0) or 0)
                                c_p_cur = int(cli_pact.get("current", s_p_cur) or 0)
                                merged_pact["current"] = max(0, min(s_p_cur, c_p_cur))
                            except (ValueError, TypeError):
                                pass
                        char_data["pact_slots"] = merged_pact
                    for sc_k in ("spell_points_current", "hit_dice_current", "temp_hp"):
                        if sc_k in existing_sheet and existing_sheet[sc_k] is not None:
                            try:
                                s_v = int(existing_sheet[sc_k] or 0)
                                c_v = int(char_data.get(sc_k, s_v) if char_data.get(sc_k) is not None else s_v)
                                char_data[sc_k] = max(0, min(s_v, c_v))
                            except (ValueError, TypeError):
                                char_data[sc_k] = existing_sheet[sc_k]
                    if isinstance(existing_sheet.get("hit_dice_pools"), dict):
                        from common.character_schema import sync_hit_dice_pools
                        srv_pools = existing_sheet["hit_dice_pools"]
                        cli_pools = char_data.get("hit_dice_pools")
                        if isinstance(cli_pools, dict):
                            merged_pools = {}
                            for dk, sv_p in srv_pools.items():
                                if isinstance(sv_p, dict):
                                    s_tot = int(sv_p.get("total", 0) or 0)
                                    s_cur = int(sv_p.get("current", s_tot) or 0)
                                    c_p = cli_pools.get(dk, {})
                                    c_cur = int(c_p.get("current", s_cur) or 0) if isinstance(c_p, dict) else s_cur
                                    merged_pools[dk] = {"total": s_tot, "current": max(0, min(s_cur, c_cur))}
                            char_data["hit_dice_pools"] = merged_pools
                        sync_hit_dice_pools(char_data, allow_scalar_override=True)
                    if "spell_points_max" in existing_sheet and existing_sheet["spell_points_max"] is not None:
                        char_data["spell_points_max"] = existing_sheet["spell_points_max"]
                    if "exhaustion_level" in existing_sheet and existing_sheet["exhaustion_level"] is not None:
                        try:
                            s_ex = int(existing_sheet["exhaustion_level"] or 0)
                            c_ex = int(char_data.get("exhaustion_level", s_ex) or 0)
                            char_data["exhaustion_level"] = max(s_ex, c_ex)
                        except (ValueError, TypeError):
                            char_data["exhaustion_level"] = existing_sheet["exhaustion_level"]
                    if "inspiration" in existing_sheet or "has_inspiration" in existing_sheet:
                        srv_insp = bool(existing_sheet.get("has_inspiration", existing_sheet.get("inspiration", False)))
                        cli_insp = bool(char_data.get("has_inspiration", char_data.get("inspiration", False)))
                        eff_insp = srv_insp and cli_insp
                        char_data["inspiration"] = eff_insp
                        char_data["has_inspiration"] = eff_insp
                    srv_cr = existing_sheet.get("class_resources")
                    cli_cr = char_data.get("class_resources")
                    if isinstance(srv_cr, dict) and isinstance(cli_cr, dict):
                        merged_cr = copy.deepcopy(srv_cr)
                        for rk, sv in srv_cr.items():
                            if rk in cli_cr:
                                cv = cli_cr[rk]
                                if isinstance(sv, bool):
                                    merged_cr[rk] = bool(sv) and bool(cv)
                                elif isinstance(sv, int) and str(rk).endswith("_current"):
                                    try:
                                        merged_cr[rk] = max(0, min(int(sv), int(cv)))
                                    except (ValueError, TypeError):
                                        pass
                        char_data["class_resources"] = merged_cr
                    srv_cust = existing_sheet.get("custom_resources")
                    cli_cust = char_data.get("custom_resources")
                    if isinstance(srv_cust, list) and isinstance(cli_cust, list):
                        cli_by_name = {
                            str(r.get("name", "")).strip().lower(): r
                            for r in cli_cust if isinstance(r, dict) and r.get("name")
                        }
                        merged_cust = copy.deepcopy(srv_cust)
                        for sr in merged_cust:
                            if not isinstance(sr, dict):
                                continue
                            cr = cli_by_name.get(str(sr.get("name", "")).strip().lower())
                            if isinstance(cr, dict):
                                try:
                                    sr["current"] = max(0, min(int(sr.get("current", 0) or 0), int(cr.get("current", sr.get("current", 0)) or 0)))
                                except (ValueError, TypeError):
                                    pass
                        char_data["custom_resources"] = merged_cust
                    srv_conds = getattr(player, "conditions", None)
                    if isinstance(srv_conds, list):
                        char_data["conditions"] = list(srv_conds)
                    elif isinstance(existing_sheet.get("conditions"), list):
                        char_data["conditions"] = list(existing_sheet["conditions"])

                server_currency = existing_sheet.get("currency", {})
                client_currency = char_data.get("currency", {})
                if isinstance(server_currency, dict) and isinstance(client_currency, dict):
                    all_coin_keys = set(list(client_currency.keys()) + list(server_currency.keys()) + ["MR", "MA", "ME", "MO", "MP", "cp", "sp", "ep", "gp", "pp"])
                    for c_k in all_coin_keys:
                        if c_k in client_currency:
                            s_val = server_currency.get(c_k, 0)
                            try:
                                if int(client_currency[c_k]) > int(s_val):
                                    client_currency[c_k] = int(s_val)
                            except (ValueError, TypeError):
                                client_currency[c_k] = s_val
                    char_data["currency"] = client_currency
                    char_data["wallet"] = dict(client_currency)
                    char_data["gp"] = str(client_currency.get("MO", 0))

                server_inv = existing_sheet.get("inventory_grid", [])
                client_inv = char_data.get("inventory_grid", [])
                if isinstance(server_inv, list) and isinstance(client_inv, list):
                    allowed_counts = {}
                    from common.starter_equipment import get_pack_contents
                    client_pack_counts = {}
                    for c_it in client_inv:
                        if isinstance(c_it, dict) and c_it.get("name"):
                            ck = str(c_it.get("name", "")).strip().lower()
                            if get_pack_contents(ck):
                                raw_cq = c_it.get("qty", 1)
                                try:
                                    cq = max(0, int(1 if raw_cq is None else raw_cq))
                                except (ValueError, TypeError):
                                    cq = 1
                                if cq > 0:
                                    client_pack_counts[ck] = client_pack_counts.get(ck, 0) + cq

                    for s_it in server_inv:
                        if isinstance(s_it, dict) and s_it.get("name"):
                            k = str(s_it.get("name", "")).strip().lower()
                            raw_sq = s_it.get("qty", 1)
                            try:
                                q = max(0, int(1 if raw_sq is None else raw_sq))
                            except (ValueError, TypeError):
                                q = 1
                            if q <= 0:
                                continue
                            pack_subs = get_pack_contents(k)
                            if pack_subs:
                                still_closed = min(q, client_pack_counts.get(k, 0))
                                unpacked_q = max(0, q - still_closed)
                                client_pack_counts[k] = max(0, client_pack_counts.get(k, 0) - still_closed)
                                allowed_counts[k] = allowed_counts.get(k, 0) + still_closed
                                if unpacked_q > 0:
                                    for p_sub in pack_subs:
                                        sub_k = str(p_sub.get("name", "")).strip().lower()
                                        sub_q = int(p_sub.get("qty", 1) or 1) * unpacked_q
                                        allowed_counts[sub_k] = allowed_counts.get(sub_k, 0) + sub_q
                            else:
                                allowed_counts[k] = allowed_counts.get(k, 0) + q

                    for s_i in range(len(client_inv)):
                        c_it = client_inv[s_i]
                        if isinstance(c_it, dict) and c_it.get("name"):
                            k = str(c_it.get("name", "")).strip().lower()
                            rem_allowed = allowed_counts.get(k, 0)
                            raw_qty = c_it.get("qty", 1)
                            try:
                                c_q = max(0, int(1 if raw_qty is None else raw_qty))
                            except (ValueError, TypeError):
                                c_q = 1
                            if c_q == 0:
                                if rem_allowed > 0:
                                    c_it["qty"] = 0
                                else:
                                    client_inv[s_i] = None
                            elif rem_allowed <= 0:
                                client_inv[s_i] = None
                                stripped_unapproved_item = True
                            else:
                                actual_q = min(c_q, rem_allowed)
                                c_it["qty"] = actual_q
                                allowed_counts[k] = rem_allowed - actual_q
                    char_data["inventory_grid"] = client_inv

                # Valida weapons e spellbook contro aggiunte non autorizzate a parità di livello
                if "weapons" in existing_sheet and isinstance(existing_sheet["weapons"], list) and isinstance(char_data.get("weapons"), list):
                    if client_lvl <= server_lvl:
                        allowed_weapons = {str(w.get("name", "")).strip().lower() for w in existing_sheet["weapons"] if isinstance(w, dict)}
                        if isinstance(char_data.get("inventory_grid"), list):
                            for inv_it in char_data["inventory_grid"]:
                                if isinstance(inv_it, dict) and inv_it.get("name") and int(inv_it.get("qty", 1) or 0) > 0:
                                    allowed_weapons.add(str(inv_it.get("name", "")).strip().lower())
                        char_data["weapons"] = [
                            w for w in char_data["weapons"]
                            if isinstance(w, dict) and str(w.get("name", "")).strip().lower() in allowed_weapons
                        ]

                if "spellbook" in existing_sheet and isinstance(existing_sheet["spellbook"], list) and isinstance(char_data.get("spellbook"), list):
                    if client_lvl <= server_lvl:
                        allowed_spells = {str(sp.get("name", "")).strip().lower() for sp in existing_sheet["spellbook"] if isinstance(sp, dict)}
                        char_data["spellbook"] = [
                            sp for sp in char_data["spellbook"]
                            if isinstance(sp, dict) and str(sp.get("name", "")).strip().lower() in allowed_spells
                        ]

                # Proteggi diario, note e privilegi registrati sul server da modifiche non approvate
                if "journal_notes" in existing_sheet and existing_sheet["journal_notes"] is not None:
                    char_data["journal_notes"] = existing_sheet["journal_notes"]
                if "notes" in existing_sheet and existing_sheet["notes"] is not None:
                    char_data["notes"] = existing_sheet["notes"]
                if "features" in existing_sheet and existing_sheet["features"] is not None:
                    if client_lvl <= server_lvl:
                        char_data["features"] = existing_sheet["features"]

            try:
                from common.item_modifiers import calculate_character_item_modifiers, compute_effective_ac
                item_mods = calculate_character_item_modifiers(char_data)
                has_def_items = (
                    item_mods.get("equipped_armor") is not None or
                    item_mods.get("has_shield", False) or
                    item_mods.get("bonus_ac", 0) != 0 or
                    item_mods.get("special_ac_base") is not None
                )
                prev_had_def_items = False
                if isinstance(existing_sheet, dict):
                    prev_mods = calculate_character_item_modifiers(existing_sheet)
                    prev_had_def_items = (
                        prev_mods.get("equipped_armor") is not None or
                        prev_mods.get("has_shield", False) or
                        prev_mods.get("bonus_ac", 0) != 0 or
                        prev_mods.get("special_ac_base") is not None
                    )
                calc_ac = compute_effective_ac(char_data, item_mods)
                if has_def_items or stripped_unapproved_item or (prev_had_def_items and not has_def_items):
                    char_data["ac"] = calc_ac
                elif had_existing_sheet and not is_dm and prev_server_ac is not None:
                    client_ac = int(char_data.get("ac", prev_server_ac) or prev_server_ac)
                    if client_ac > max(prev_server_ac, calc_ac):
                        char_data["ac"] = max(prev_server_ac, calc_ac)
                elif not is_dm and int(char_data.get("level", 1) or 1) > int((existing_sheet or {}).get("level", 1) or 1):
                    char_data["ac"] = max(int(char_data.get("ac", calc_ac) or calc_ac), calc_ac)
            except Exception:
                pass

            player.full_sheet = char_data
            player.avatar_b64 = char_data.get("avatar_b64") or getattr(player, "avatar_b64", None)
            try:
                player.proficiency_bonus = int(char_data.get("proficiency_bonus", 2) or 2)
            except (ValueError, TypeError):
                pass
            if isinstance(char_data.get("pact_slots"), dict):
                pact_s = char_data["pact_slots"]
                player.pact_slots_max = int(pact_s.get("max", 0) or 0)
                player.pact_slots_current = int(pact_s.get("current", 0) or 0)
                player.pact_slot_level = int(pact_s.get("level", 0) or 0)
            try:
                player.hp = int(char_data.get("hp_current", player.hp))
            except (ValueError, TypeError):
                pass
            if player.hp <= 0:
                from server.rules.combat import drop_concentration
                drop_concentration(player, game_state, reason="HP a 0")
                conds = getattr(player, "conditions", [])
                for c in ["Incosciente", "Prono"]:
                    if c not in conds:
                        conds.append(c)
                player.conditions = conds
            player.max_hp = char_data.get("hp_max", player.max_hp)
            if "ac" in char_data:
                try:
                    player.ac = int(char_data["ac"])
                except (ValueError, TypeError):
                    pass
            if "temp_hp" in char_data and char_data.get("temp_hp") is not None:
                player.temp_hp = char_data.get("temp_hp")
            if char_data.get("initiative") is not None:
                try:
                    player.initiative_bonus = int(char_data.get("initiative"))
                    if not (getattr(game_state, "combat_active", False) and getattr(player, "in_combat", False)):
                        player.initiative = player.initiative_bonus
                except (ValueError, TypeError):
                    pass
            player.exhaustion_level = char_data.get("exhaustion_level", getattr(player, "exhaustion_level", 0))
            player.speed = char_data.get("speed", getattr(player, "speed", 30))
            player.speed_unit = char_data.get("speed_unit", getattr(player, "speed_unit", None))
            player.damage_resistances = char_data.get("damage_resistances", getattr(player, "damage_resistances", []))
            player.damage_immunities = char_data.get("damage_immunities", getattr(player, "damage_immunities", []))
            player.damage_vulnerabilities = char_data.get("damage_vulnerabilities", getattr(player, "damage_vulnerabilities", []))
            if char_data.get("light_radius") is not None:
                try:
                    player.light_radius = max(0, int(char_data["light_radius"]))
                except (TypeError, ValueError):
                    pass
            if char_data.get("light_color"):
                player.light_color = str(char_data["light_color"])
            if callable(getattr(player, "check_has_darkvision", None)) and player.check_has_darkvision() is True:
                player.has_darkvision = True
                try:
                    raw_v = getattr(player, "vision_radius", 6)
                    cur_v = int(raw_v) if isinstance(raw_v, (int, float)) else 6
                except (TypeError, ValueError):
                    cur_v = 6
                player.vision_radius = max(12, cur_v)
            from server.rules.movement import auto_explore_fow
            auto_explore_fow(player, game_state)

        if granted_campaign_starter and getattr(player, "conn", None):
            send_message(player.conn, make_campaign_starter_granted(char_data.get("inventory_grid", []), full_sheet=char_data))
            broadcast(game_state, make_chat_broadcast("Sistema", f"[CAMPAGNA] {player.name} ha ricevuto l'equipaggiamento iniziale della campagna dal Master!"))
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_targeted_action(data, player, game_state):
    conds = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
    if any(is_condition_active(conds, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi eseguire azioni mirate mentre sei Incosciente, Paralizzato o a 0 HP!"))
        return

    target_name = data.get("target_name")
    action_type = data.get("action_type")
    formula = data.get("formula")
    reason = data.get("reason", "")
    damage_type = data.get("damage_type", "Tagliente")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return
    
    try:
        if formula:
            result = roll_dice(formula)
            val = result["total"]
        else:
            val = 0
            
        note_str = ""
        if action_type in ["danno", "damage"]:
            final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, val, damage_type, game_state)
            note_str = f" ({damage_type}){note}"
            if temp_absorbed > 0:
                note_str += f" [{temp_absorbed} assorbiti da Temp HP]"
            val = final_dmg
        elif action_type in ["cura", "heal"]:
            t_fs_h = getattr(target_player, "full_sheet", None) or {}
            t_type_h = (str(t_fs_h.get("type", "")) + " " + str(target_player.name)).lower()
            is_spell_heal = bool(data.get("is_spell") or data.get("spell_name"))
            if getattr(target_player, "is_object", False) or (
                is_spell_heal and any(k in t_type_h for k in ("costrutto", "construct", "non morto", "non-morto", "undead", "golem"))
            ):
                msg_err = f"❌ Le cure magiche non hanno effetto su {target_player.name} (Oggetto/Costrutto/Non Morto)."
                broadcast(game_state, make_chat_broadcast("Sistema", msg_err))
                return
            _apply_hp_change(target_player, target_player.hp + val, game_state)
        elif action_type in ["temp_hp", "temp"]:
            from server.rules.reaction_magic import apply_temp_hp
            apply_temp_hp(target_player, val, game_state, choice=data.get("temp_hp_choice"))
            
        temp_disp = f" (+{target_player.temp_hp} Temp)" if getattr(target_player, "temp_hp", 0) > 0 else ""
        p_name = player.name if player else "DM"
        log_msg = f"{p_name} usa {reason or action_type} su {target_name}: {action_type} di {val}{note_str}. HP attuali: {target_player.hp}/{target_player.max_hp}{temp_disp}"
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
        broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
        game_state._trigger_gui_update()
        
    except ValueError as e:
        send_message(player.conn, make_error_reply(f"Errore nella formula: {str(e)}"))

def handle_set_travel_role_request(data, player, game_state):
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    role = data.get("role", "Nessuna")
    marching_order = data.get("marching_order", getattr(player, "marching_order", "Centro"))
    player.travel_role = role
    player.marching_order = marching_order
    from common.protocol import make_game_state, make_chat_broadcast
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    broadcast(game_state, make_chat_broadcast("Viaggio", f"🏕️ {player.name} si posiziona in [{marching_order}] con ruolo: {role}"))

def _require_dm_or_error(player) -> bool:
    """Consente l'esecuzione solo al Dungeon Master, notificando eventuali client non autorizzati."""
    from common.network_utils import is_dm_actor, send_message
    from common.protocol import make_error_reply
    if is_dm_actor(player):
        return True
    if getattr(player, "conn", None):
        send_message(player.conn, make_error_reply("Azione riservata al Dungeon Master."))
    return False


def handle_set_travel_params_request(data, player, game_state):
    if not _require_dm_or_error(player):
        return
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    with game_state.lock:
        biome = data.get("biome", getattr(game_state, "travel_biome", "foresta"))
        danger = data.get("danger", getattr(game_state, "travel_danger", "moderate"))
        pace = data.get("pace", getattr(game_state, "travel_pace", "Normale"))
        terrain = data.get("terrain", getattr(game_state, "travel_terrain", "Foresta"))

        game_state.travel_biome = biome
        game_state.travel_danger = danger
        game_state.travel_pace = pace
        game_state.travel_terrain = terrain
        state_snap = game_state.get_state_dict()

    from common.protocol import make_game_state, make_chat_broadcast
    from common.network_utils import broadcast
    broadcast(game_state, make_game_state(state_snap))
    msg = f"🧭 [VIAGGIO] Parametri aggiornati: Bioma={biome}, Pericolo={danger}, Andatura={pace}, Terreno={terrain}"
    broadcast(game_state, make_chat_broadcast("Viaggio", msg))
    game_state.log_dm_message(f"[TRAVEL] {msg}")

def handle_set_watch_shifts_request(data, player, game_state):
    if not _require_dm_or_error(player):
        return
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    shifts = data.get("shifts", {})
    has_campfire = bool(data.get("has_campfire", True))

    with game_state.lock:
        game_state.camp_watch_shifts = shifts
        game_state.camp_has_campfire = has_campfire
        state_snap = game_state.get_state_dict()

    from common.protocol import make_game_state, make_chat_broadcast
    from common.network_utils import broadcast
    broadcast(game_state, make_game_state(state_snap))
    
    summary = []
    for s_idx in range(1, 5):
        val = shifts.get(s_idx) or shifts.get(str(s_idx)) or "Nessuno"
        summary.append(f"T{s_idx}: {val}")
    fire_str = "🔥 Falò acceso" if has_campfire else "🌑 Falò spento"
    msg = f"🏕️ [ACCAMPAMENTO] Turni di guardia configurati ({', '.join(summary)} | {fire_str})"
    broadcast(game_state, make_chat_broadcast("Viaggio", msg))
    game_state.log_dm_message(f"[CAMP] {msg}")

def handle_resolve_night_camp_request(data, player, game_state):
    if not _require_dm_or_error(player):
        return
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]

    from common.travel_data import resolve_night_camp_simulation
    from common.protocol import make_chat_broadcast, make_game_state
    from common.network_utils import broadcast, send_message

    pending_broadcasts = []
    pending_direct = []

    with game_state.lock:
        res = resolve_night_camp_simulation(
            watch_shifts=getattr(game_state, "camp_watch_shifts", {}),
            players=getattr(game_state, "players", []),
            biome_key=getattr(game_state, "travel_biome", "foresta"),
            danger_key=getattr(game_state, "travel_danger", "moderate"),
            has_campfire=getattr(game_state, "camp_has_campfire", True)
        )

        # Avanza l'ora sul server di 8 ore
        game_state.time_hour = getattr(game_state, "time_hour", 8) + 8
        while game_state.time_hour >= 24:
            game_state.time_hour -= 24
            game_state.time_day = getattr(game_state, "time_day", 1) + 1
            game_state.travel_hours_today = 0
            game_state.travel_miles_today = 0
            while game_state.time_day > 30:
                game_state.time_day -= 30
                game_state.time_month = getattr(game_state, "time_month", 1) + 1
                while game_state.time_month > 12:
                    game_state.time_month -= 12
                    game_state.time_year = getattr(game_state, "time_year", 1492) + 1

        header = "========================================\n🏕️ RISOLUZIONE NOTTE & RIPOSO LUNGO (8 ORE)\n========================================"
        log_text = "\n".join(res["logs"])
        full_msg = f"{header}\n{log_text}"

        if res["ambush"]:
            full_msg += "\n\n🚨 IMBOSCATA NOTTURNA! Il gruppo viene assalito durante il riposo! Iniziativa richiesta!"
            # D&D 5e RAW: Solo i membri del party che stavano dormendo (esclusa la sentinella) iniziano Incoscienti e Proni
            for p in getattr(game_state, "players", []):
                if getattr(p, "is_party_member", False) and p.name != res.get("sentinel_name"):
                    if "Morto" in getattr(p, "conditions", []) or "Dead" in getattr(p, "conditions", []):
                        continue
                    if not hasattr(p, "conditions"): p.conditions = []
                    if "Incosciente" not in p.conditions: p.conditions.append("Incosciente")
                    if "Prono" not in p.conditions: p.conditions.append("Prono")
                    if getattr(p, "full_sheet", None):
                        p.full_sheet["conditions"] = list(p.conditions)
            pending_broadcasts.append(make_chat_broadcast("Sistema", full_msg))
        else:
            full_msg += "\n\n✨ Notte serena! Tutti recuperano HP e Slot Incantesimo (Riposo Lungo completato)."
            for p in getattr(game_state, "players", []):
                if not getattr(p, "is_party_member", False) and not getattr(p, "is_companion", False):
                    continue
                if "Morto" in getattr(p, "conditions", []) or "Dead" in getattr(p, "conditions", []):
                    continue
                for note in _apply_player_long_rest(p, game_state):
                    pending_broadcasts.append(make_chat_broadcast("Sistema", note))
                if getattr(p, "conn", None):
                    pending_direct.append((p.conn, {"type": "DO_LONG_REST", "data": {}}))
            pending_broadcasts.append(make_chat_broadcast("Sistema", full_msg))

        state_snap = game_state.get_state_dict()

    for b_msg in pending_broadcasts:
        broadcast(game_state, b_msg)
    for c_conn, c_msg in pending_direct:
        send_message(c_conn, c_msg)

    game_state.log_dm_message(f"[NIGHT-CAMP] {full_msg}")
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(state_snap))

def handle_generate_encounter_request(data, player, game_state):
    if not _require_dm_or_error(player):
        return
    if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
        data = data["data"]
    with game_state.lock:
        biome = data.get("biome", getattr(game_state, "travel_biome", "foresta"))
        danger = data.get("danger", getattr(game_state, "travel_danger", "moderate"))
    is_night = bool(data.get("is_night", False))
    force_category = data.get("force_category")

    from common.travel_data import generate_biome_encounter
    res = generate_biome_encounter(biome, danger, is_night, force_category)

    from common.protocol import make_chat_broadcast
    from common.network_utils import broadcast, send_message

    if res.get("occurred", False):
        m_names = ", ".join([f"{m['count']}x {m['name']}" for m in res.get("monsters", [])]) if res.get("monsters") else ""
        msg = f"🎲 [INCONTRO 5e - {res.get('category', '').upper()}] {res.get('title')}\n{res.get('description')}"
        if m_names:
            msg += f"\n⚔️ Nemici avvistati: {m_names} (a {res.get('dist_hexes', 6)} esagoni, Furtività CD {res.get('stealth_dc', 12)})"
        if res.get("reward"):
            msg += f"\n✨ Scoperta/Ricompensa: {res.get('reward')}"
        if res.get("save_stat"):
            msg += f"\n⚠️ Pericolo: Richiesto TS {res.get('save_stat')} CD {res.get('save_dc')} ({res.get('fail_effect')})"
        broadcast(game_state, make_chat_broadcast("Viaggio", msg))
        game_state.log_dm_message(f"[ENCOUNTER] {msg}")
    else:
        msg = f"🎲 [INCONTRO 5e] {res.get('message', 'Nessun incontro.')}"
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_chat_broadcast("Viaggio", msg))
        game_state.log_dm_message(f"[ENCOUNTER] {msg}")

def _apply_player_long_rest(p, game_state):
    """Apply canonical D&D 5e Long Rest recovery to a Player entity and return alert notes."""
    from common.feats_and_classes import evaluate_armor_sleep
    from common.dnd5e_tables import entity_get_class_level as _cls_lvl, entity_get_attr_mod as _attr_m
    from server.dm_monster_engine import restore_drain_penalties

    alerts = []
    dm_settings = getattr(game_state, "automation_settings", {}) or {}
    if not dm_settings.get("opt_slow_natural_healing", False):
        p.hp = p.max_hp
    p.temp_hp = 0
    _sleep_res = evaluate_armor_sleep(p, game_state)
    if not _sleep_res["blocks_exhaustion_recovery"]:
        p.exhaustion_level = max(0, getattr(p, "exhaustion_level", 0) - 1)
    elif getattr(p, "exhaustion_level", 0) > 0:
        alerts.append(_sleep_res["note"])
    elif _sleep_res["penalized"]:
        alerts.append(_sleep_res["note"])

    conds = [
        c for c in getattr(p, "conditions", [])
        if not str(c).startswith("Sfinimento")
        and not str(c).lower().startswith("exhaustion")
        and str(c).strip().lower() not in (
            "incosciente", "unconscious", "privo di sensi",
            "stabilizzato", "stable", "morente", "dying",
            "prono", "prone", "avvelenato", "poisoned", "azione preparata",
        )
    ]
    if p.exhaustion_level > 0:
        conds.append(f"Sfinimento (Liv. {p.exhaustion_level})")
    p.conditions = conds
    p.readied_action_data = None
    p.relentless_rage_uses = 0
    p.frightful_immune_list = []
    clear_unconscious_and_reset_death_saves(p)
    if getattr(p, "full_sheet", None):
        p.full_sheet["hp_current"] = p.hp
        p.full_sheet["exhaustion_level"] = p.exhaustion_level
        p.full_sheet["temp_hp"] = 0
        p.full_sheet["conditions"] = list(getattr(p, "conditions", []))
        # D&D 5e RAW: Ripristina metà dei Dadi Vita (minimo 1), inclusi pool multiclasse
        from common.character_schema import recover_hit_dice_pools
        _hd_frac = _sleep_res["hd_fraction"] if "_sleep_res" in locals() else 0.5
        recover_hit_dice_pools(p.full_sheet, fraction=_hd_frac)
        # Talento Fortunato (Lucky, PHB p. 167): ricarica 3 Punti Fortuna
        p.full_sheet["lucky_points"] = 3
        # Mago Abiuratore: ripristina Interdizione Arcana al massimo
        _wiz_l = _cls_lvl(p, "mago", "wizard")
        _sub_w = str(p.full_sheet.get("subclass", "") or "").lower()
        if _wiz_l >= 2 and ("abiuraz" in _sub_w or "abjur" in _sub_w):
            _ward_max = max(1, 2 * _wiz_l + max(0, _attr_m(p, "INT")))
            p.arcane_ward_hp = _ward_max
            p.full_sheet["arcane_ward_hp"] = _ward_max
    restore_entity_rest_resources(p, rest_type="long")
    restore_drain_penalties(p, rest_type="long")
    return alerts


def trigger_group_long_rest(game_state, reason="Il gruppo si è accampato per un Riposo Lungo."):
    game_state.travel_hours_today = 0
    from common.protocol import make_chat_broadcast
    from common.network_utils import send_message, broadcast
    
    auto_rest = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_rest = game_state.automation_settings.get("auto_apply_rest_recovery", True)
        
    if not auto_rest:
        msg = f"⛺ {reason} Richiesta di Riposo registrata (in attesa di conferma DM / verifica incontri casuali)."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[RIPOSO] {msg}")
        game_state.ongoing_rest_vote = None
        game_state._trigger_gui_update()
        return

    _pending_notes = []
    with game_state.lock:
        for p in getattr(game_state, "players", []):
            if not getattr(p, "is_party_member", False) and not getattr(p, "is_companion", False):
                continue
            if "Morto" in getattr(p, "conditions", []) or "Dead" in getattr(p, "conditions", []):
                continue
            _pending_notes.extend(_apply_player_long_rest(p, game_state))
        state_snap = game_state.get_state_dict()
    for note in _pending_notes:
        broadcast(game_state, make_chat_broadcast("Sistema", note))
    dm_settings = getattr(game_state, "automation_settings", {}) or {}
    rest_key = dm_settings.get("opt_rest_variant", "standard")
    from common.dnd5e_tables import REST_VARIANTS
    r_info = REST_VARIANTS.get(rest_key, REST_VARIANTS["standard"])
    rest_note = f" [Variante DMG {r_info.get('label', rest_key)}: {r_info.get('long_hours', 8)}h]" if rest_key != "standard" else ""
    if dm_settings.get("auto_advance_time", True) and hasattr(game_state, "advance_game_time"):
        long_hours = int(r_info.get("long_hours", 8))
        if long_hours > 0:
            game_state.advance_game_time(hours=long_hours)
    broadcast(game_state, make_chat_broadcast("Sistema", f"{reason} Tutti recuperano HP e Slot.{rest_note}"))
    for p in getattr(game_state, "players", []):
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "DO_LONG_REST", "data": {}})
    game_state.ongoing_rest_vote = None
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(state_snap))

def handle_long_rest_request(data, player, game_state):
    if getattr(game_state, "combat_active", False):
        from common.network_utils import send_message
        if getattr(player, "conn", None): send_message(player.conn, {"type": "ERROR_REPLY", "data": {"text": "Non puoi riposare durante il combattimento!"}})
        return
        
    players = getattr(game_state, "players", [])
    active_conns = len([p for p in players if getattr(p, "conn", None)])
    if active_conns <= 1:
        # Nessun altro client connesso (test, modalità offline o singolo giocatore): applica direttamente il riposo lungo
        trigger_group_long_rest(game_state)
        return
        
    needed = max(1, math.ceil(active_conns / 2))
    game_state.ongoing_rest_vote = {"initiator": player.name, "votes_needed": needed, "total_conns": active_conns, "votes_received": 0, "votes_rejected": 0, "voters": set()}
    game_state.log_dm_message(f"[Sistema] {player.name} ha proposto un Riposo Lungo. Voti favorevoli necessari: {needed}/{active_conns}.")
    from common.network_utils import send_message
    for p in players:
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "PROMPT_LONG_REST_VOTE", "data": {"initiator": player.name}})

def handle_long_rest_vote(data, player, game_state):
    vote = data.get("vote", False)
    rejected_msg = None
    approved_trigger = False
    with game_state.lock:
        vote_data = getattr(game_state, "ongoing_rest_vote", None)
        if not vote_data:
            return
        voters = vote_data.setdefault("voters", set())
        if player.name in voters:
            return
        voters.add(player.name)

        if not vote:
            vote_data["votes_rejected"] = vote_data.get("votes_rejected", 0) + 1
            game_state.log_dm_message(f"[Sistema] {player.name} ha votato NO al riposo lungo.")
            if vote_data["votes_rejected"] > (vote_data["total_conns"] - vote_data["votes_needed"]):
                rejected_msg = f"Il Riposo Lungo proposto da {vote_data['initiator']} e' stato respinto dalla maggioranza."
                game_state.ongoing_rest_vote = None
        else:
            vote_data["votes_received"] += 1
            if vote_data["votes_received"] >= vote_data["votes_needed"]:
                game_state.log_dm_message("[Sistema] La maggioranza dei giocatori ha approvato il Riposo Lungo!")
                approved_trigger = True

    if rejected_msg:
        from common.protocol import make_chat_broadcast
        broadcast(game_state, make_chat_broadcast("Sistema", rejected_msg))
    elif approved_trigger:
        trigger_group_long_rest(game_state, reason="Il gruppo ha approvato il Riposo Lungo!")

def handle_custom_spell_request(data, player, game_state):
    spell = data.get("spell", {})
    if not spell: return
    game_state.gui_queue.put({
        "type": "CUSTOM_SPELL_REQUEST",
        "player": player,
        "spell": spell
    })
    game_state.log_dm_message(f"[MAGIA] {player.name} richiede l'approvazione per l'incantesimo custom '{spell.get('name', 'Sconosciuto')}'.")

def handle_currency_request(data, player, game_state):
    coin = data.get("coin", "MO")
    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    reason = data.get("reason", "")
    if amount <= 0:
        return
    game_state.gui_queue.put({
        "type": "CURRENCY_REQUEST",
        "player": player,
        "coin": coin,
        "amount": amount,
        "reason": reason
    })
    game_state.log_dm_message(f"[VALUTA] {player.name} richiede {amount} {coin}. Motivazione: {reason or 'Nessuna'}")

def handle_item_approval_request(data, player, game_state):
    item = data.get("item", {})
    slot_idx = data.get("slot_idx")
    if not item or not isinstance(item, dict):
        return
    game_state.gui_queue.put({
        "type": "ITEM_APPROVAL_REQUEST",
        "player": player,
        "item": item,
        "slot_idx": slot_idx
    })
    game_state.log_dm_message(f"[OGGETTO] {player.name} richiede approvazione per '{item.get('name', 'Oggetto')}'.")


def handle_journal_approval_request(data, player, game_state):
    content = data.get("content", "")
    field_name = data.get("field_name", "journal_notes")
    title = data.get("title", "")
    game_state.gui_queue.put({
        "type": "JOURNAL_APPROVAL_REQUEST",
        "player": player,
        "field_name": field_name,
        "content": content,
        "title": title
    })
    field_disp = "Biografia & Diario" if "journal" in field_name else ("Privilegi & Tratti" if "features" in field_name else "Appunti / Note")
    game_state.log_dm_message(f"[DIARIO] {player.name} richiede l'approvazione per modificare {field_disp}.")
