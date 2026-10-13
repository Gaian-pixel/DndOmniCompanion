import re
import random
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw
from common.network_utils import send_message, broadcast
import math
def handle_move_request(data, player, game_state):
    if "Afferrato" in getattr(player, "conditions", []) or "Privo di Sensi" in getattr(player, "conditions", []):
        from common.network_utils import send_message
        from common.protocol import make_error_reply
        if player.conn:
            send_message(player.conn, make_error_reply("La tua velocità è 0. Non puoi muoverti."))
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
        if in_combat and hasattr(player, "position") and player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = to_pos[0], to_pos[1]
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            speed = getattr(player, "speed", 30)
            is_dashed = "Scatto" in getattr(player, "conditions", [])
            eff_speed = speed * 2 if is_dashed else speed
            max_hexes = eff_speed // 5
            cost = 2 if "Prono" in getattr(player, "conditions", []) else 1
            if dist * cost > max_hexes:
                from common.network_utils import send_message
                from common.protocol import make_error_reply
                if getattr(player, "conn", None):
                    if cost == 2:
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: sei Prono, la distanza massima è {max_hexes // 2} esagoni."))
                    else:
                        hint = " (Puoi usare l'Azione di Scatto /dash per raddoppiare la velocità!)" if not is_dashed else ""
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: la distanza ({dist * 5}ft) supera la tua velocità di {eff_speed}ft.{hint}"))
                return

        # Rilevamento Attacco d'Opportunità (Opportunity Attack)
        from_pos = list(player.position) if hasattr(player, "position") and player.position else None
        if in_combat and from_pos and from_pos != to_pos:
            disengaged = "Disimpegno" in getattr(player, "conditions", [])
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
                                if not any(c in getattr(other, "conditions", []) for c in incaps):
                                    opp_alert = f"⚠️ [OPPORTUNITÀ] {player.name} esce dalla portata di mischia di {other.name}! {other.name} può usare la Reazione per un Attacco d'Opportunità!"
                                    game_state.log_dm_message(f"[COMBAT] {opp_alert}")
                                    from common.protocol import make_chat_broadcast, make_opportunity_alert
                                    broadcast(game_state, make_chat_broadcast("Sistema", opp_alert))
                                    if getattr(other, "conn", None):
                                        send_message(other.conn, make_opportunity_alert(player.name, f"{player.name} si sta allontanando da te!"))

        game_state.move_player(player.name, to_pos)
        
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
                        
                        from common.protocol import make_chat_broadcast, make_game_state, make_map_data_update
                        broadcast(game_state, make_map_data_update(new_map_data))
                        broadcast(game_state, make_game_state(game_state.get_state_dict()))
                        broadcast(game_state, make_chat_broadcast("Sistema", f"Il gruppo è stato teletrasportato."))
                        game_state._trigger_gui_update()
                        return
                    except Exception as e:
                        print(f"Errore caricamento mappa teleport {map_file}: {e}")

        
        # Auto-explore FoW around the player's new position
        if getattr(game_state, "current_map", None) and game_state.current_map.get("fow_enabled", False):
            from common.hex_utils import Hex, get_sphere_hexes, hex_linedraw
            h = Hex(to_pos[0], to_pos[1])
            vision_rad = getattr(player, 'vision_radius', 6)
            revealed = get_sphere_hexes(h, vision_rad)
            changed = False
            
            fow_rev = game_state.current_map.get("fow_revealed", [])
            fow_draft = game_state.current_map.get("fow_draft", [])
            walls_list = [Hex(w[0], w[1]) for w in walls_list_pos]
            
            for rh in revealed:
                line = hex_linedraw(h, rh)
                blocked = False
                for step in line[:-1]:
                    if step != h and step in walls_list:
                        blocked = True
                        break
                if blocked:
                    continue
                    
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

