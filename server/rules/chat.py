import re
import random
from common.protocol import *
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw
from common.network_utils import send_message, broadcast
import math
def handle_chat(data, player, game_state):
    text = data.get("text", "").strip()
    if not text: return
    
    if text.startswith("/setsize "):
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            try:
                size_val = int(parts[2])
                target = game_state.find_player(p_name)
                if target:
                    target.size = size_val
                    game_state._trigger_gui_update()
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata size {size_val} per {p_name}")
            except ValueError:
                pass
        return
        
    if text.startswith("/setaura "):
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            try:
                aura_rad = int(parts[2])
                color = parts[3] if len(parts) >= 4 else "yellow"
                target = game_state.find_player(p_name)
                if target:
                    target.aura_radius = aura_rad
                    target.aura_color = color
                    game_state._trigger_gui_update()
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata aura {aura_rad} ({color}) per {p_name}")
            except ValueError:
                pass
        return

    if text.startswith("/vision "):
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            try:
                vis_rad = int(parts[2])
                target = game_state.find_player(p_name)
                if target:
                    target.vision_radius = vis_rad
                    game_state._trigger_gui_update()
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata vista {vis_rad} esagoni per {p_name}")
            except ValueError:
                pass
        return

    if text.startswith("/torch"):
        if getattr(game_state, "current_map", None):
            pos = getattr(player, "position", None)
            if pos:
                lights = game_state.current_map.setdefault("lights", [])
                lights.append({"q": pos[0], "r": pos[1], "radius": 6, "color": "yellow"})
                game_state.log_dm_message(f"[Sistema] {player.name} ha acceso una torcia.")
                
                # Reveal FoW for torch
                if game_state.current_map.get("fow_enabled", False):
                    from common.hex_utils import Hex, get_sphere_hexes, hex_linedraw
                    h = Hex(pos[0], pos[1])
                    revealed = get_sphere_hexes(h, 6)
                    fow_rev = game_state.current_map.get("fow_revealed", [])
                    walls_list = [Hex(w[0], w[1]) for w in game_state.current_map.get("walls", [])]
                    for rh in revealed:
                        line = hex_linedraw(h, rh)
                        blocked = False
                        for step in line[:-1]:
                            if step != h and step in walls_list:
                                blocked = True
                                break
                        if not blocked and [rh.q, rh.r] not in fow_rev:
                            fow_rev.append([rh.q, rh.r])
                
                game_state._trigger_gui_update()
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
        
    if text.startswith("/light "):
        parts = text.split(" ")
        if len(parts) >= 4 and getattr(game_state, "current_map", None):
            try:
                q = int(parts[1])
                r = int(parts[2])
                radius = int(parts[3])
                lights = game_state.current_map.setdefault("lights", [])
                lights.append({"q": q, "r": r, "radius": radius, "color": "yellow"})
                game_state.log_dm_message(f"[Sistema] Luce piazzata in {q}, {r} raggio {radius}.")
                
                # Reveal FoW for light
                if game_state.current_map.get("fow_enabled", False):
                    from common.hex_utils import Hex, get_sphere_hexes, hex_linedraw
                    h = Hex(q, r)
                    revealed = get_sphere_hexes(h, radius)
                    fow_rev = game_state.current_map.get("fow_revealed", [])
                    walls_list = [Hex(w[0], w[1]) for w in game_state.current_map.get("walls", [])]
                    for rh in revealed:
                        line = hex_linedraw(h, rh)
                        blocked = False
                        for step in line[:-1]:
                            if step != h and step in walls_list:
                                blocked = True
                                break
                        if not blocked and [rh.q, rh.r] not in fow_rev:
                            fow_rev.append([rh.q, rh.r])
                            
                game_state._trigger_gui_update()
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
            except ValueError:
                pass
        return
        
    if text.startswith("/loot "):
        parts = text.split(" ", 4)
        if len(parts) >= 4 and getattr(game_state, "current_map", None):
            try:
                q = int(parts[1])
                r = int(parts[2])
                item_name = parts[3]
                qty = int(parts[4]) if len(parts) > 4 else 1
                loots = game_state.current_map.setdefault("loots", [])
                loots.append({"q": q, "r": r, "item": item_name, "qty": qty})
                game_state.log_dm_message(f"[Sistema] Bottino piazzato in {q}, {r}: {qty}x {item_name}.")
                game_state._trigger_gui_update()
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
            except ValueError:
                pass
        return
        
    if text.startswith("/meteo "):
        parts = text.split(" ", 1)
        if len(parts) >= 2:
            new_weather = parts[1].strip().capitalize()
            game_state.weather = new_weather
            game_state._trigger_gui_update()
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            game_state.log_dm_message(f"[SISTEMA] Meteo cambiato in: {new_weather}")
            broadcast(game_state, make_chat_broadcast("Sistema", f"Il meteo è cambiato in: {new_weather}"))
        return
        
    game_state.log_dm_message(f"[{player.name}]: {text}")
    broadcast(game_state, make_chat_broadcast(player.name, text))

def handle_whisper(data, player, game_state):
    to_name = data.get("to"); text = data.get("text")
    if to_name == player.name:
        from common.protocol import make_error_reply
        from common.network_utils import send_message
        send_message(player.conn, make_error_reply("Non puoi sussurrare a te stesso."))
        return
    if to_name.lower() == "dm":
        game_state.gui_queue.put({"type": "PRIVATE_MESSAGE_RECEIVED", "payload": {"from": player.name, "text": text}})
        send_message(player.conn, make_chat_broadcast(f"Tu -> DM", text, is_whisper=True))
        return
    target_player = game_state.find_player(to_name)
    if target_player:
        send_message(target_player.conn, make_chat_broadcast(player.name, text, is_whisper=True))
        send_message(player.conn, make_chat_broadcast(f"Tu -> {to_name}", text, is_whisper=True))
        game_state.log_dm_message(f"[{player.name} -> {to_name}]: {text}")
    else:
        send_message(player.conn, make_error_reply(f"Giocatore '{to_name}' non trovato."))

def handle_roll_request(data, player, game_state):
    formula = data.get("formula"); reason = data.get("reason", "")
    try:
        result = roll_dice(formula)
        log_msg = f"{player.name} tira {formula} ({reason}) e ottiene {result['total']}"
        game_state.log_dm_message(f"[ROLL] {log_msg}")
        broadcast(game_state, make_dice_roll_result(player.name, formula, reason, result))
    except ValueError as e:
        send_message(player.conn, make_error_reply(str(e)))

