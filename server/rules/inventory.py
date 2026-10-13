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

def handle_buy_item_request(data, player, game_state):
    shop_name = data.get("shop_name")
    item_name = data.get("item_name")
    
    if not shop_name or not item_name: return
    
    shop = getattr(game_state, "shops", {}).get(shop_name)
    if not shop: return
    
    item_to_buy = None
    for item in shop.get("items", []):
        if item.get("name") == item_name:
            item_to_buy = item
            break
            
    if not item_to_buy: return
    
    price = int(item_to_buy.get("price", 0))
    player_gp = int(player.full_sheet.get("gp", 0)) if getattr(player, "full_sheet", None) else 0
    
    if player_gp < price:
        send_message(player.conn, {"type": "ERROR", "message": "Non hai abbastanza monete d'oro."})
        return
        
    # Deduct gold and add item
    player.full_sheet["gp"] = str(player_gp - price)
    inv = player.full_sheet.setdefault("inventory", [])
    
    # Try to stack
    stacked = False
    for i in inv:
        if i.get("name") == item_name:
            i["quantity"] = str(int(i.get("quantity", 1)) + 1)
            stacked = True
            break
            
    if not stacked:
        inv.append({"name": item_name, "quantity": "1", "description": "Acquistato al negozio", "equipped": False})
        
    player.full_sheet["inventory"] = inv
    game_state._trigger_gui_update()
    
    from common.protocol import make_game_state, make_chat_broadcast
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    broadcast(game_state, make_chat_broadcast("Sistema", f"{player.name} ha acquistato {item_name} da {shop_name} per {price} mo."))

def handle_give_gold_request(data, player, game_state):
    target_name = data.get("target_name")
    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    if not target_name or amount <= 0:
        return
        
    target_player = game_state.find_player(target_name)
    if target_player and target_player.conn:
        send_message(target_player.conn, {"type": "RECEIVE_GOLD", "data": {"amount": amount, "sender": player.name}})
        log_msg = f"{player.name} ha donato {amount} Monete d'Oro (MO) a {target_name}."
        game_state.log_dm_message(f"[SISTEMA] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
    else:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{target_name} non è online e non può ricevere oro."))
