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
    if not target_player or not target_player.conn:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{target_name} non è online e non può ricevere oggetti."))
        return

    # Verifica spazio nel destinatario se ha un full_sheet
    recip_sheet = getattr(target_player, "full_sheet", None)
    if recip_sheet:
        if not isinstance(recip_sheet.get("inventory_grid"), list):
            recip_sheet["inventory_grid"] = [None] * 25
        if not any(slot is None for slot in recip_sheet["inventory_grid"]):
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Lo zaino di {target_name} è pieno!"))
            return

    # Verifica possesso e svuota lo slot del mittente sul server nel full_sheet
    sender_sheet = getattr(player, "full_sheet", None)
    if sender_sheet and isinstance(sender_sheet.get("inventory_grid"), list):
        found_in_sender = False
        for s_idx, slot in enumerate(sender_sheet["inventory_grid"]):
            if slot and isinstance(slot, dict) and slot.get("name") == item.get("name"):
                sender_sheet["inventory_grid"][s_idx] = None
                found_in_sender = True
                break
        if not found_in_sender:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Non possiedi questo oggetto nello zaino."))
            return

    # Inserisci nel primo slot libero del destinatario sul server
    if recip_sheet:
        for s_idx in range(len(recip_sheet["inventory_grid"])):
            if recip_sheet["inventory_grid"][s_idx] is None:
                recip_sheet["inventory_grid"][s_idx] = dict(item)
                break

    item["_sender"] = player.name
    send_message(target_player.conn, make_receive_item(item))
    log_msg = f"{player.name} ha donato '{item.get('name')}' a {target_name}."
    game_state.log_dm_message(f"[SISTEMA] {log_msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

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
        
        loot_entry = {
            "name": found["item"],
            "type": "Misto",
            "qty": found["qty"],
            "weight": 1.0,
            "attuned": False,
            "desc": "Raccolto da forziere/spoglie",
            "_sender": "Forziere"
        }
        # Aggiungi allo zaino del giocatore sul server
        sheet = getattr(player, "full_sheet", None)
        if sheet:
            if not isinstance(sheet.get("inventory_grid"), list):
                sheet["inventory_grid"] = [None] * 25
            for s_i in range(len(sheet["inventory_grid"])):
                if sheet["inventory_grid"][s_i] is None:
                    sheet["inventory_grid"][s_i] = dict(loot_entry)
                    break

        if getattr(player, 'conn', None):
            send_message(player.conn, make_receive_item(loot_entry))
            
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
    sheet = getattr(player, "full_sheet", None)
    if not sheet: return
    
    curr = sheet.setdefault("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
    player_mo = int(curr.get("MO", 0)) if isinstance(curr, dict) else int(sheet.get("gp", 0))
    if player_mo < price:
        legacy_gp = int(sheet.get("gp", 0))
        if legacy_gp < price:
            if player.conn:
                send_message(player.conn, make_error_reply("Non hai abbastanza monete d'oro per questo acquisto."))
            return
        player_mo = legacy_gp
        
    # Detrai oro sia dalla borsa moderna che dal campo legacy
    new_mo = player_mo - price
    if isinstance(curr, dict):
        curr["MO"] = new_mo
    sheet["gp"] = str(new_mo)
    
    # Inserisci nella griglia 25 slot
    if not isinstance(sheet.get("inventory_grid"), list) or len(sheet["inventory_grid"]) != 25:
        sheet["inventory_grid"] = [None] * 25
        
    new_entry = {
        "name": item_name,
        "type": item_to_buy.get("type", "Equipaggiamento"),
        "qty": int(item_to_buy.get("qty", 1) or 1),
        "weight": float(item_to_buy.get("weight", 1.0) or 1.0),
        "attuned": False,
        "desc": item_to_buy.get("description", f"Acquistato da {shop_name}")
    }
    
    placed = False
    placed_slot = None
    for idx, slot in enumerate(sheet["inventory_grid"]):
        if slot and isinstance(slot, dict) and slot.get("name") == item_name:
            slot["qty"] = int(slot.get("qty", 1)) + new_entry["qty"]
            placed = True
            placed_slot = idx
            break
            
    if not placed:
        for idx in range(25):
            if sheet["inventory_grid"][idx] is None:
                sheet["inventory_grid"][idx] = new_entry
                placed = True
                placed_slot = idx
                break
                
    if not placed:
        # Ripristina oro
        if isinstance(curr, dict):
            curr["MO"] = player_mo
        sheet["gp"] = str(player_mo)
        if player.conn:
            send_message(player.conn, make_error_reply("Zaino pieno! Non hai slot liberi."))
        return

    # Mantieni sincronizzato anche l'array legacy per compatibilità
    inv = sheet.setdefault("inventory", [])
    stacked = False
    for i in inv:
        if i.get("name") == item_name:
            i["quantity"] = str(int(i.get("quantity", 1)) + 1)
            stacked = True
            break
    if not stacked:
        inv.append({"name": item_name, "quantity": "1", "description": f"Acquistato da {shop_name}", "equipped": False})
        
    # Invia notifiche di sincronizzazione al client
    if player.conn:
        send_message(player.conn, make_currency_response(player.name, "MO", -price, approved=True, reason=f"Acquisto {item_name}"))
        send_message(player.conn, make_item_approval_response(player.name, new_entry, placed_slot, approved=True, reason="Acquisto Shop"))

    game_state._trigger_gui_update()
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
    if not target_player or not target_player.conn:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"{target_name} non è online e non può ricevere oro."))
        return

    # Convalida e scala oro dal mittente sul server
    sender_sheet = getattr(player, "full_sheet", None)
    if sender_sheet:
        curr = sender_sheet.setdefault("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
        s_gold = int(curr.get("MO", 0)) if isinstance(curr, dict) else int(sender_sheet.get("gp", 0))
        if s_gold < amount:
            if player.conn:
                send_message(player.conn, make_error_reply(f"Non hai abbastanza monete d'oro. Ne possiedi {s_gold} MO."))
            return
        new_sg = s_gold - amount
        if isinstance(curr, dict):
            curr["MO"] = new_sg
        sender_sheet["gp"] = str(new_sg)
        if player.conn:
            send_message(player.conn, make_currency_response(player.name, "MO", -amount, approved=True, reason=f"Donato a {target_name}"))

    # Accredita sul destinatario sul server
    recip_sheet = getattr(target_player, "full_sheet", None)
    if recip_sheet:
        r_curr = recip_sheet.setdefault("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
        r_gold = int(r_curr.get("MO", 0)) if isinstance(r_curr, dict) else int(recip_sheet.get("gp", 0))
        new_rg = r_gold + amount
        if isinstance(r_curr, dict):
            r_curr["MO"] = new_rg
        recip_sheet["gp"] = str(new_rg)
        send_message(target_player.conn, make_currency_response(target_name, "MO", amount, approved=True, reason=f"Ricevuto da {player.name}"))

    send_message(target_player.conn, {"type": "RECEIVE_GOLD", "data": {"amount": amount, "sender": player.name}})
    log_msg = f"{player.name} ha donato {amount} Monete d'Oro (MO) a {target_name}."
    game_state.log_dm_message(f"[SISTEMA] {log_msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
