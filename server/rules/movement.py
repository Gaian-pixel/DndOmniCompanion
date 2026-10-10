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
    if to_pos:
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
            max_hexes = speed // 5
            cost = 2 if "Prono" in getattr(player, "conditions", []) else 1
            if dist * cost > max_hexes:
                from common.network_utils import send_message
                from common.protocol import make_error_reply
                if getattr(player, "conn", None):
                    if cost == 2:
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: sei Prono, la distanza massima è {max_hexes // 2} esagoni."))
                    else:
                        send_message(player.conn, make_error_reply(f"Movimento non consentito: la distanza supera la tua velocità di {speed}ft."))
                return

        game_state.move_player(player.name, to_pos)
        
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

