import re
import random
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw, get_visible_hexes
from common.network_utils import send_message, broadcast
from common.i18n import is_condition_active
import math

def handle_move_request(data, player, game_state):
    from common.network_utils import send_message, broadcast
    conds = getattr(player, "conditions", [])
    blocking = ["Afferrato", "Privo di Sensi", "Incapacitato", "Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(conds, c) for c in blocking) or getattr(player, "exhaustion_level", 0) >= 5 or getattr(player, "hp", 1) <= 0:
        from common.protocol import make_error_reply
        if player.conn:
            send_message(player.conn, make_error_reply("La tua velocità è 0 o sei incapacitato/morto. Non puoi muoverti."))
        return

    to_pos = data.get("to")
    is_dm = data.get("is_dm_force", False)
    
    if to_pos:
        if not is_dm and getattr(game_state, "current_map", None):
            hex_size = game_state.current_map.get("hex_size", 60)
            if hex_size < 40:
                from common.network_utils import send_message
                from common.protocol import make_error_reply
                if player.conn:
                    send_message(player.conn, make_error_reply("Mappa di esplorazione: movimento libero disabilitato. Usa il Viaggio o aspetta il DM."))
                return
                
        walls_list_pos = game_state.current_map.get("walls", []) if getattr(game_state, "current_map", None) else []
        if [to_pos[0], to_pos[1]] in walls_list_pos:
            from common.network_utils import send_message
            from common.protocol import make_error_reply
            if player.conn:
                send_message(player.conn, make_error_reply("Non puoi muoverti lì, c'è un muro!"))
            return
            
        in_combat = getattr(player, "in_combat", False) or getattr(game_state, "combat_active", False)
        if in_combat and not is_dm and getattr(game_state, "strict_turn_lock", False):
            curr_turn = game_state.get_current_turn_player()
            if curr_turn and curr_turn.name != player.name:
                from common.protocol import make_error_reply
                if player.conn:
                    send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
                return

        if in_combat and hasattr(player, "position") and player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = to_pos[0], to_pos[1]
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            speed = getattr(player, "speed", 30)
            speed_unit = getattr(player, "speed_unit", None)
            sheet = getattr(player, "full_sheet", None)
            if sheet and not speed_unit:
                speed_unit = sheet.get("speed_unit")
            from common.i18n import speed_to_hexes, format_distance_hexes
            base_hexes = speed_to_hexes(speed, speed_unit)

            # Regola D&D 5e Ingombro (Encumbrance)
            if sheet and isinstance(sheet.get("attributes"), dict):
                try:
                    str_val = int(sheet["attributes"].get("FOR", 10))
                    inv_grid = sheet.get("inventory_grid", [])
                    tot_w = sum(float(it.get("weight", 0.0) or 0.0) * int(it.get("qty", 1) or 1) for it in inv_grid if it and isinstance(it, dict))
                    if tot_w > (str_val * 15):
                        base_hexes = max(1, base_hexes - 4)
                    elif tot_w > (str_val * 10):
                        base_hexes = max(2, base_hexes - 2)
                except (ValueError, TypeError):
                    pass

            exh = getattr(player, "exhaustion_level", 0)
            if exh >= 2:
                base_hexes = max(1, base_hexes // 2)
            is_dashed = is_condition_active(conds, "Scatto")
            max_hexes = base_hexes * 2 if is_dashed else base_hexes
            cost = 2 if is_condition_active(conds, "Prono") else 1
            
            spent = getattr(player, "movement_spent_this_turn", 0)
            req_hexes = dist * cost
            if (spent + req_hexes) > max_hexes:
                from common.network_utils import send_message
                from common.protocol import make_error_reply
                if getattr(player, "conn", None):
                    rem = max(0, max_hexes - spent)
                    rem_str = format_distance_hexes(rem, speed_unit)
                    tot_str = format_distance_hexes(max_hexes, speed_unit)
                    if cost == 2:
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: sei Prono. Ti restano {rem // 2} esagoni ({rem_str})."))
                    else:
                        hint = " (Puoi usare l'Azione di Scatto /dash per raddoppiare la velocità!)" if not is_dashed else ""
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: la distanza supera la velocità rimasta per questo turno ({rem_str} rimasti su {tot_str}).{hint}"))
                return
            player.movement_spent_this_turn = spent + req_hexes

        # Rilevamento Attacco d'Opportunità (Opportunity Attack)
        from_pos = list(player.position) if hasattr(player, "position") and player.position else None
        if in_combat and from_pos and from_pos != to_pos:
            disengaged = is_condition_active(conds, "Disimpegno")
            if not disengaged:
                for other in getattr(game_state, "players", []):
                    if other.name != player.name and getattr(other, "hp", 0) > 0 and hasattr(other, "position") and other.position:
                        is_enemy = (getattr(player, "is_party_member", False) != getattr(other, "is_party_member", False))
                        if is_enemy:
                            qo, ro = other.position[0], other.position[1]
                            dist_from = max(abs(from_pos[0] - qo), abs(from_pos[0] + from_pos[1] - qo - ro), abs(from_pos[1] - ro))
                            dist_to = max(abs(to_pos[0] - qo), abs(to_pos[0] + to_pos[1] - qo - ro), abs(to_pos[1] - ro))
                            if dist_from <= 1 and dist_to > 1:
                                incaps = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
                                o_conds = getattr(other, "conditions", [])
                                if not any(is_condition_active(o_conds, c) for c in incaps):
                                    opp_alert = f"⚠️ [OPPORTUNITÀ] {player.name} esce dalla portata di mischia di {other.name}! {other.name} può usare la Reazione per un Attacco d'Opportunità!"
                                    game_state.log_dm_message(f"[COMBAT] {opp_alert}")
                                    from common.protocol import make_chat_broadcast, make_opportunity_alert
                                    broadcast(game_state, make_chat_broadcast("Sistema", opp_alert))
                                    if getattr(other, "conn", None):
                                        send_message(other.conn, make_opportunity_alert(player.name, f"{player.name} si sta allontanando da te!"))

        game_state.move_player(player.name, to_pos)
        
        # Gestione Trappole D&D 5e sulla mappa
        if getattr(game_state, "current_map", None):
            traps = game_state.current_map.get("traps", [])
            for trap in traps:
                if trap.get("q") == to_pos[0] and trap.get("r") == to_pos[1] and not trap.get("triggered", False):
                    trap["triggered"] = True
                    trap["hidden"] = False
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
                        mod = 0
                        if getattr(player, "full_sheet", None):
                            attr = player.full_sheet.get("attributes", {})
                            if "DES" in attr:
                                try: mod = (int(attr["DES"]) - 10) // 2
                                except: pass
                        mod_str = f"+{mod}" if mod >= 0 else str(mod)
                        res = roll_dice(f"1d20{mod_str}")
                        is_crit = res["rolls"][0] == 20
                        is_fail = res["rolls"][0] == 1
                        _process_save_result(player.name, "DES", res["total"], is_crit, is_fail, trap_dc, trap_dmg, True, trap_name, game_state, trap_dtype)
        
        if getattr(game_state, "current_map", None):
            teleports = game_state.current_map.get("teleports", {})
            pos_key = f"{to_pos[0]},{to_pos[1]}"
            if pos_key in teleports:
                map_file = teleports[pos_key]
                import os, json, base64
                maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "maps")
                map_path = os.path.join(maps_dir, map_file)
                if os.path.exists(map_path):
                    try:
                        with open(map_path, "r", encoding="utf-8") as f:
                            new_map_data = json.load(f)
                        if 'base_image_path' in new_map_data and new_map_data['base_image_path']:
                            with open(new_map_data['base_image_path'], "rb") as img_f:
                                new_map_data['bg_image_data'] = base64.b64encode(img_f.read()).decode('utf-8')
                        
                        game_state.load_map(new_map_data)
                        
                        from common.protocol import make_chat_broadcast, make_game_state, make_map_data_update_broadcast
                        broadcast(game_state, make_map_data_update_broadcast(new_map_data))
                        broadcast(game_state, make_game_state(game_state.get_state_dict()))
                        broadcast(game_state, make_chat_broadcast("Sistema", f"Il gruppo è stato teletrasportato."))
                        game_state._trigger_gui_update()
                        return
                    except Exception as e:
                        print(f"Errore caricamento mappa teleport {map_file}: {e}")

        # Auto-explore FoW around the player's new position with true Line of Sight (LoS) and Dynamic Light
        if getattr(game_state, "current_map", None) and game_state.current_map.get("fow_enabled", False):
            h = Hex(to_pos[0], to_pos[1])
            vision_rad = getattr(player, 'vision_radius', 6)
            light_rad = getattr(player, 'light_radius', 0)
            effective_rad = max(vision_rad, light_rad)
            walls = game_state.current_map.get("walls", [])
            visible_hexes = get_visible_hexes(h, effective_rad, walls)
            
            # Luce condivisa dai membri del party con sorgenti luminose attive (Torcia, Lanterna)
            for other_p in game_state.players:
                if other_p.name != player.name and getattr(other_p, 'is_party_member', False) and getattr(other_p, 'light_radius', 0) > 0:
                    o_pos = getattr(other_p, 'position', None)
                    if o_pos:
                        o_hex = Hex(o_pos[0], o_pos[1])
                        o_light_hexes = get_visible_hexes(o_hex, other_p.light_radius, walls)
                        visible_hexes.extend(o_light_hexes)

            changed = False
            fow_rev = game_state.current_map.get("fow_revealed", [])
            fow_draft = game_state.current_map.get("fow_draft", [])
            
            for rh in visible_hexes:
                pos = [rh.q, rh.r]
                if pos not in fow_rev:
                    fow_rev.append(pos)
                    changed = True
                if pos not in fow_draft:
                    fow_draft.append(pos)
                    changed = True
            
            if changed:
                game_state.current_map["fow_revealed"] = fow_rev
                game_state.current_map["fow_draft"] = fow_draft
                game_state._trigger_gui_update()
                from common.protocol import make_fow_update_broadcast, make_player_move
                broadcast(game_state, make_player_move(player.name, to_pos))
                broadcast(game_state, make_fow_update_broadcast(fow_rev, fow_draft))
                return
                
        from common.protocol import make_player_move
        broadcast(game_state, make_player_move(player.name, to_pos))
