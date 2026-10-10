import re
import random
from common.protocol import *
from common.network_utils import send_message, broadcast
import math
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

def handle_take_loot_request(data, player, game_state):
    q = data.get('q')
    r = data.get('r')
    if q is None or r is None or not getattr(game_state, 'current_map', None):
        return
        
    loots = game_state.current_map.get('loots', [])
    found = None
    for l in loots:
        if l['q'] == q and l['r'] == r:
            found = l
            break
            
    if found:
        loots.remove(found)
        from common.protocol import make_give_item_broadcast, make_game_state
        from common.network_utils import send_message
        
        if getattr(player, 'conn', None):
            send_message(player.conn, {'type': 'GIVE_ITEM', 'data': {'sender': 'Sistema', 'target': player.name, 'item_name': found['item'], 'qty': found['qty']}})
            
        game_state.log_dm_message(f'[Loot] {player.name} ha raccolto {found["qty"]}x {found["item"]}.')
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

