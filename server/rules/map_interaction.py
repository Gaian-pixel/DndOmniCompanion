import re
import random
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw
from common.network_utils import send_message, broadcast
from common.protocol import *
import math
def handle_create_aoe_request(data, player, game_state):
    aoe_data = data.get("aoe_data")
    if not aoe_data:
        return
        
    game_state.add_aoe(aoe_data)
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    
    if not aoe_data.get("req_save"):
        return
        
    from common.hex_utils import Hex, get_sphere_hexes, get_cone_hexes, get_line_hexes
    
    origin = Hex(*aoe_data["origin"])
    aoe_type = aoe_data.get("type", "sfera")
    size = aoe_data.get("size", 3)
    
    if aoe_type in ["sfera", "cubo"]:
        hexes = get_sphere_hexes(origin, size)
    elif aoe_type == "cono":
        target = Hex(*aoe_data.get("target", aoe_data["origin"]))
        hexes = get_cone_hexes(origin, target, size)
    elif aoe_type == "linea":
        target = Hex(*aoe_data.get("target", aoe_data["origin"]))
        hexes = get_line_hexes(origin, target)
    else:
        hexes = []
        
    affected_players = []
    for p in getattr(game_state, "players", []):
        if getattr(p, "hp", 0) > 0 and getattr(p, "position", None):
            pos_hex = Hex(p.position[0], p.position[1])
            if pos_hex in hexes:
                affected_players.append(p)
                
    if not affected_players:
        return
        
    from common.protocol import make_prompt_save
    game_state.log_dm_message(f"[AoE] {player.name} ha lanciato un'AoE. {len(affected_players)} bersagli colpiti.")
    
    for p in affected_players:
        if hasattr(p, "conn") and p.conn:
            send_message(p.conn, make_prompt_save(
                stat=aoe_data.get("stat", "DES"),
                dc=aoe_data.get("dc", 10),
                damage_formula=aoe_data.get("dmg", "8d6"),
                half_on_success=aoe_data.get("half", True),
                source_name=player.name
            ))
            game_state.log_dm_message(f"[AoE] Richiesto Tiro Salvezza a {p.name}.")
        else:
            # Mostro gestito dal server/DM
            game_state.log_dm_message(f"[AoE] {p.name} (NPC) è nell'area. Il DM deve tirare il TS manualmente o possiamo automatizzarlo.")

def handle_clear_aoes_request(data, player, game_state):
    game_state.clear_aoes()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_ping_request(data, player, game_state):
    q = data.get("q")
    r = data.get("r")
    color = data.get("color", "yellow")
    if q is not None and r is not None:
        broadcast(game_state, make_ping_broadcast(q, r, color))
        game_state.gui_queue.put({"type": "PING_BROADCAST", "payload": {"q": q, "r": r, "color": color}})


def handle_toggle_wall_request(data, player, game_state):
    q, r = data.get("q"), data.get("r")
    if q is None or r is None: return
    
    if not hasattr(game_state, "current_map") or game_state.current_map is None:
        return
        
    walls = game_state.current_map.setdefault("walls", [])
    w = [q, r]
    if w in walls:
        walls.remove(w)
    else:
        walls.append(w)
        
    game_state._trigger_gui_update()
    from common.protocol import make_map_data_update_broadcast
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))

def handle_toggle_cover_request(data, player, game_state):
    q, r = data.get("q"), data.get("r")
    cover_type = data.get("cover_type")
    if q is None or r is None or not cover_type: return
    
    if not hasattr(game_state, "current_map") or game_state.current_map is None:
        return
        
    cover_list = game_state.current_map.setdefault(cover_type, [])
    w = [q, r]
    if w in cover_list:
        cover_list.remove(w)
    else:
        cover_list.append(w)
        
    game_state._trigger_gui_update()
    from common.protocol import make_map_data_update_broadcast
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))

def handle_draw_request(data, player, game_state):
    points = data.get("points", [])
    color = data.get("color", "red")
    from common.network_utils import broadcast
    broadcast(game_state, {"type": "DRAW_BROADCAST", "data": {"points": points, "color": color}})


