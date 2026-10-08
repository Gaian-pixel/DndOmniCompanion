# commands.py
from common.protocol import *
from common.dice import roll_dice
from common.network_utils import send_message, broadcast

def handle_chat(data, player, game_state):
    text = data.get("text", "").strip()
    if not text: return
    game_state.log_dm_message(f"[{player.name}]: {text}")
    broadcast(game_state, make_chat_broadcast(player.name, text))

def handle_whisper(data, player, game_state):
    to_name = data.get("to"); text = data.get("text")
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

def handle_move_request(data, player, game_state):
    to_pos = data.get("to")
    if to_pos:
        game_state.move_player(player.name, to_pos)
        broadcast(game_state, make_player_move(player.name, to_pos))

def handle_update_stats_request(data, player, game_state):
    try:
        hp = int(data.get("hp"))
        max_hp = int(data.get("max_hp"))
        initiative = int(data.get("initiative"))
        conditions = data.get("conditions", [])
        player.hp = hp
        player.max_hp = max_hp
        player.initiative = initiative
        player.conditions = conditions
        game_state._trigger_gui_update()
        broadcast(game_state, make_player_stats_update(player.name, hp, max_hp, initiative, conditions))
    except:
        pass

def handle_update_full_sheet_request(data, player, game_state):
    char_data = data.get("character")
    if char_data:
        player.full_sheet = char_data
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_targeted_action(data, player, game_state):
    target_name = data.get("target_name")
    action_type = data.get("action_type")
    formula = data.get("formula")
    reason = data.get("reason", "")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return
    
    try:
        if formula:
            result = roll_dice(formula)
            val = result["total"]
        else:
            val = 0
            
        if action_type == "danno":
            target_player.hp = max(0, target_player.hp - val)
        elif action_type == "cura":
            target_player.hp = min(target_player.max_hp, target_player.hp + val)
            
        log_msg = f"{player.name} usa {reason} su {target_name}: {action_type} di {val}. HP attuali: {target_player.hp}/{target_player.max_hp}"
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
        broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
        game_state._trigger_gui_update()
        
    except ValueError as e:
        send_message(player.conn, make_error_reply(f"Errore nella formula: {str(e)}"))

def handle_give_item_request(data, player, game_state):
    target_name = data.get("target_name")
    item = data.get("item")
    if not target_name or not item: return
    
    target_player = game_state.find_player(target_name)
    if target_player and target_player.conn:
        item["_sender"] = player.name
        send_message(target_player.conn, make_receive_item(item))
        log_msg = f"{player.name} ha donato '{item.get('name')}' a {target_name}."
        game_state.log_dm_message(f"[SISTEMA] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
    else:
        send_message(player.conn, make_error_reply(f"{target_name} non è online e non può ricevere oggetti."))

def handle_create_aoe_request(data, player, game_state):
    aoe_data = data.get("aoe_data")
    if aoe_data:
        game_state.add_aoe(aoe_data)
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_clear_aoes_request(data, player, game_state):
    game_state.clear_aoes()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_set_travel_role_request(data, player, game_state):
    role = data.get("role", "Nessuna")
    player.travel_role = role
    from common.protocol import make_game_state
    # from server.server import broadcast  # Not needed, broadcast is already imported at the top of the file
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_start_combat_request(data, player, game_state):
    initiator_name = data.get("initiator")
    game_state.gui_queue.put({"type": "SHOW_COMBAT_CONFIG", "payload": {"initiator": initiator_name}})

def handle_end_turn_request(data, player, game_state):
    # Solo chi è di turno può passarlo
    current = game_state.get_current_turn_player()
    if current and current.name == player.name:
        game_state.next_turn()
        # Announce turn
        next_p = game_state.get_current_turn_player()
        if next_p:
            msg = f"Round {game_state.round_number} - Turno di {next_p.name}!"
            game_state.log_dm_message(f"[COMBAT] {msg}")
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_submit_initiative(data, player, game_state):
    init = data.get("initiative", 0)
    player.initiative = init
    
    with game_state.lock:
        if game_state.combat_active and len(game_state.players) > 0:
            current_active = game_state.players[game_state.turn_index] if game_state.turn_index < len(game_state.players) else None
            game_state.players.sort(key=lambda p: (getattr(p, 'in_combat', True), p.initiative), reverse=True)
            if current_active:
                try:
                    game_state.turn_index = game_state.players.index(current_active)
                except ValueError:
                    game_state.turn_index = 0
            
    game_state._trigger_gui_update()
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions))
    from common.protocol import make_game_state
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    game_state.log_dm_message(f"[COMBAT] {player.name} tira iniziativa: {init}")


def handle_ping_request(data, player, game_state):
    q = data.get("q")
    r = data.get("r")
    color = data.get("color", "yellow")
    if q is not None and r is not None:
        broadcast(game_state, make_ping_broadcast(q, r, color))
        game_state.gui_queue.put({"type": "PING_BROADCAST", "payload": {"q": q, "r": r, "color": color}})

command_handlers = {
    "CHAT": handle_chat,
    "WHISPER": handle_whisper,
    "ROLL_REQUEST": handle_roll_request,
    "MOVE_REQUEST": handle_move_request,
    "UPDATE_STATS_REQUEST": handle_update_stats_request,
    "UPDATE_FULL_SHEET_REQUEST": handle_update_full_sheet_request,
    "TARGETED_ACTION_REQUEST": handle_targeted_action,
    "GIVE_ITEM_REQUEST": handle_give_item_request,
    "CREATE_AOE_REQUEST": handle_create_aoe_request,
    "CLEAR_AOES_REQUEST": handle_clear_aoes_request,
    "SET_TRAVEL_ROLE_REQUEST": handle_set_travel_role_request,
    "START_COMBAT_REQUEST": handle_start_combat_request,
    "END_TURN_REQUEST": handle_end_turn_request,
    "SUBMIT_INITIATIVE": handle_submit_initiative,
    "PING_REQUEST": handle_ping_request,
}
