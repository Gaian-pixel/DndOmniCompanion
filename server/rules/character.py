import re
import random
from common.protocol import *
from common.network_utils import send_message, broadcast
import math
def handle_update_stats_request(data, player, game_state):
    try:
        hp = int(data.get("hp"))
        max_hp = int(data.get("max_hp"))
        initiative = int(data.get("initiative"))
        conditions = data.get("conditions", [])
        player.max_hp = max_hp
        player.initiative = initiative
        player.conditions = conditions
        _apply_hp_change(player, hp, game_state)
        game_state._trigger_gui_update()
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions))
    except:
        pass

def handle_update_full_sheet_request(data, player, game_state):
    char_data = data.get("character")
    if char_data:
        from common.starter_equipment import apply_class_and_race_starter_kit, apply_campaign_starter_kit
        # Se il personaggio non ha ancora ricevuto il kit iniziale di classe/razza, assegnalo
        if not char_data.get("starting_kit_applied"):
            apply_class_and_race_starter_kit(char_data)
        
        # Se non ha ancora ricevuto lo starter kit della campagna, assegnalo
        if not char_data.get("campaign_starter_received"):
            campaign_kit = getattr(game_state, "campaign_starter_kit", None)
            apply_campaign_starter_kit(char_data, campaign_kit)
            if player.conn:
                from common.protocol import make_campaign_starter_granted, make_chat_broadcast
                from common.network_utils import send_message
                send_message(player.conn, make_campaign_starter_granted(char_data.get("inventory_grid", []), full_sheet=char_data))
                broadcast(game_state, make_chat_broadcast("Sistema", f"[CAMPAGNA] {player.name} ha ricevuto l'equipaggiamento iniziale della campagna dal Master!"))

        player.full_sheet = char_data
        player.hp = char_data.get("hp_current", player.hp)
        player.max_hp = char_data.get("hp_max", player.max_hp)
        player.initiative = char_data.get("initiative", player.initiative)
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
            _apply_hp_change(target_player, target_player.hp - val, game_state)
        elif action_type == "cura":
            _apply_hp_change(target_player, target_player.hp + val, game_state)
            
        log_msg = f"{player.name} usa {reason} su {target_name}: {action_type} di {val}. HP attuali: {target_player.hp}/{target_player.max_hp}"
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
        broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
        game_state._trigger_gui_update()
        
    except ValueError as e:
        send_message(player.conn, make_error_reply(f"Errore nella formula: {str(e)}"))

def handle_set_travel_role_request(data, player, game_state):
    role = data.get("role", "Nessuna")
    player.travel_role = role
    from common.protocol import make_game_state
    # from server.server import broadcast  # Not needed, broadcast is already imported at the top of the file
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_long_rest_request(data, player, game_state):
    if getattr(game_state, "combat_active", False):
        from common.network_utils import send_message
        if getattr(player, "conn", None): send_message(player.conn, {"type": "ERROR_REPLY", "data": {"text": "Non puoi riposare durante il combattimento!"}})
        return
        
    players = getattr(game_state, "players", [])
    active_conns = len([p for p in players if getattr(p, "conn", None)])
    if active_conns == 0: return
        
    game_state.ongoing_rest_vote = {"initiator": player.name, "votes_needed": active_conns, "votes_received": 0}
    game_state.log_dm_message(f"[Sistema] {player.name} ha proposto un Riposo Lungo. In attesa di approvazione da {active_conns} giocatori.")
    from common.network_utils import send_message
    for p in players:
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "PROMPT_LONG_REST_VOTE", "data": {"initiator": player.name}})

def handle_long_rest_vote(data, player, game_state):
    vote = data.get("vote", False)
    vote_data = getattr(game_state, "ongoing_rest_vote", None)
    if not vote_data: return
    
    if not vote:
        game_state.log_dm_message(f"[Sistema] {player.name} ha RIFIUTATO il riposo lungo. Votazione annullata.")
        from common.protocol import make_chat_broadcast
        broadcast(game_state, make_chat_broadcast("Sistema", f"Il Riposo Lungo proposto da {vote_data['initiator']} e' stato annullato perche' {player.name} non ha approvato."))
        game_state.ongoing_rest_vote = None
        return
        
    vote_data["votes_received"] += 1
    if vote_data["votes_received"] >= vote_data["votes_needed"]:
        game_state.log_dm_message(f"[Sistema] Tutti i giocatori hanno approvato il Riposo Lungo!")
        from common.protocol import make_chat_broadcast
        game_state.travel_hours_today = 0
        broadcast(game_state, make_chat_broadcast("Sistema", f"Il gruppo si e' accampato per un Riposo Lungo. Tutti recuperano HP e Slot."))
        from common.network_utils import send_message
        for p in getattr(game_state, "players", []):
            if getattr(p, "conn", None):
                send_message(p.conn, {"type": "DO_LONG_REST", "data": {}})
        game_state.ongoing_rest_vote = None

def handle_custom_spell_request(data, player, game_state):
    spell = data.get("spell", {})
    if not spell: return
    game_state.gui_queue.put({
        "type": "CUSTOM_SPELL_REQUEST",
        "player": player,
        "spell": spell
    })
    game_state.log_dm_message(f"[MAGIA] {player.name} richiede l'approvazione per l'incantesimo custom '{spell.get('name', 'Sconosciuto')}'.")

