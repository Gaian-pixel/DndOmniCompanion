import re
import random
from common.protocol import *
from common.network_utils import send_message, broadcast
import math

def handle_give_item_request(data, player, game_state):
    target_name = data.get("target_name")
    item = data.get("item")
    if not isinstance(item, dict):
        return
    if not target_name or not item: return

    give_qty = int(item.get("qty", 1) or 1)
    if give_qty <= 0:
        return
    
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

    give_qty = int(item.get("qty", 1) or 1)
    sender_sheet = getattr(player, "full_sheet", None)
    with game_state.lock:
        if sender_sheet and isinstance(sender_sheet.get("inventory_grid"), list):
            found_in_sender = False
            for s_idx, slot in enumerate(sender_sheet["inventory_grid"]):
                if slot and isinstance(slot, dict) and slot.get("name") == item.get("name"):
                    curr_q = int(slot.get("qty", 1) or 1)
                    if curr_q > give_qty:
                        slot["qty"] = curr_q - give_qty
                    else:
                        sender_sheet["inventory_grid"][s_idx] = None
                    found_in_sender = True
                    break
            if not found_in_sender:
                if player and getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply("Non possiedi questo oggetto nello zaino."))
                return

        # Inserisci nel primo slot libero o impila nel destinatario
        donated_item = dict(item)
        donated_item["qty"] = give_qty
        donated_item["attuned"] = False
        donated_item["container"] = "backpack"
        if recip_sheet:
            placed = False
            for s_idx, slot in enumerate(recip_sheet["inventory_grid"]):
                if slot and isinstance(slot, dict) and slot.get("name") == donated_item.get("name"):
                    slot["qty"] = int(slot.get("qty", 1) or 1) + give_qty
                    placed = True
                    break
            if not placed:
                for s_idx in range(len(recip_sheet["inventory_grid"])):
                    if recip_sheet["inventory_grid"][s_idx] is None:
                        recip_sheet["inventory_grid"][s_idx] = dict(donated_item)
                        break
            try:
                from common.item_modifiers import compute_effective_ac, calculate_character_item_modifiers
                r_mods = calculate_character_item_modifiers(recip_sheet)
                if r_mods.get("equipped_armor") is not None or r_mods.get("has_shield", False) or r_mods.get("bonus_ac", 0) != 0 or r_mods.get("special_ac_base") is not None:
                    recip_sheet["ac"] = compute_effective_ac(recip_sheet, r_mods)
                    target_player.ac = recip_sheet["ac"]
            except Exception:
                pass
        if sender_sheet:
            try:
                from common.item_modifiers import compute_effective_ac
                sender_sheet["ac"] = compute_effective_ac(sender_sheet)
                player.ac = sender_sheet["ac"]
            except Exception:
                pass

    donated_item["_sender"] = player.name
    send_message(target_player.conn, make_receive_item(donated_item))
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
        
    found = None
    loot_entry = None
    with game_state.lock:
        loots = game_state.current_map.get('loots', [])
        for l in loots:
            if l['q'] == q and l['r'] == r:
                found = l
                break
                
        if found:
            sheet = getattr(player, "full_sheet", None)
            contents = found.get("contents") if isinstance(found.get("contents"), dict) else None
            is_container_loot = contents is not None
            loot_entry = None
            coin_sync_msgs = []
            item_sync_msgs = []

            if sheet:
                if not isinstance(sheet.get("inventory_grid"), list) or len(sheet["inventory_grid"]) == 0:
                    sheet["inventory_grid"] = [None] * 25

                if is_container_loot:
                    wallet = contents.get("wallet", {})
                    items = list(contents.get("items", []))
                    # Se non ci sono monete e ci sono oggetti, verifica che almeno un oggetto entri nello zaino
                    if not any(v > 0 for v in wallet.values()) and items:
                        has_space = any(s is None for s in sheet["inventory_grid"])
                        if not has_space:
                            if getattr(player, "conn", None):
                                send_message(player.conn, make_error_reply("Zaino pieno! Non puoi raccogliere questi oggetti."))
                            return

                    # 1. Trasferisci monete sincronizzando sia currency che wallet/gp
                    if wallet:
                        p_curr = sheet.get("currency")
                        p_wallet = sheet.get("wallet")
                        if not isinstance(p_curr, dict):
                            base_coins = dict(p_wallet) if isinstance(p_wallet, dict) else {}
                            try:
                                base_mo = int(base_coins.get("MO", sheet.get("gp", 0)) or 0)
                            except (ValueError, TypeError):
                                base_mo = 0
                            p_curr = {
                                "MR": int(base_coins.get("MR", 0) or 0),
                                "MA": int(base_coins.get("MA", 0) or 0),
                                "ME": int(base_coins.get("ME", 0) or 0),
                                "MO": base_mo,
                                "MP": int(base_coins.get("MP", 0) or 0),
                            }
                            sheet["currency"] = p_curr
                        if not isinstance(p_wallet, dict):
                            p_wallet = dict(p_curr)
                            sheet["wallet"] = p_wallet

                        coin_notes = []
                        for c_type, c_qty in list(wallet.items()):
                            try:
                                c_qty_int = int(c_qty or 0)
                            except (ValueError, TypeError):
                                c_qty_int = 0
                            if c_qty_int > 0:
                                prev_val = max(int(p_curr.get(c_type, 0) or 0), int(p_wallet.get(c_type, 0) or 0))
                                new_val = prev_val + c_qty_int
                                p_curr[c_type] = new_val
                                p_wallet[c_type] = new_val
                                if c_type == "MO":
                                    sheet["gp"] = str(new_val)
                                coin_notes.append(f"{c_qty_int} {c_type}")
                                coin_sync_msgs.append(make_currency_response(player.name, c_type, c_qty_int, approved=True, reason="Spoglie"))
                        contents["wallet"] = {}
                        if coin_notes:
                            c_str = ", ".join(coin_notes)
                            broadcast(game_state, make_chat_broadcast("Sistema", f"💰 {player.name} ha raccolto {c_str} dalle spoglie!"))

                    # 2. Trasferisci oggetti reali senza sprecare slot per il contenitore fittizio e senza distruggere l'eccedenza
                    unplaced_items = []
                    for extra_item in items:
                        placed_extra = False
                        item_copy = dict(extra_item) if isinstance(extra_item, dict) else {"name": str(extra_item), "qty": 1, "type": "Equipaggiamento", "weight": 1.0}
                        item_copy["attuned"] = False
                        item_copy["container"] = "backpack"
                        item_copy.setdefault("_sender", "Forziere")
                        for s_i in range(len(sheet["inventory_grid"])):
                            if sheet["inventory_grid"][s_i] is None:
                                sheet["inventory_grid"][s_i] = dict(item_copy)
                                item_sync_msgs.append(make_receive_item(dict(item_copy)))
                                placed_extra = True
                                break
                        if not placed_extra:
                            unplaced_items.append(extra_item)

                    if unplaced_items:
                        contents["items"] = unplaced_items
                        if getattr(player, "conn", None):
                            send_message(player.conn, make_error_reply(f"Zaino pieno: {len(unplaced_items)} oggetti sono rimasti a terra."))
                    else:
                        loots.remove(found)
                else:
                    has_space = any(s is None for s in sheet["inventory_grid"])
                    if not has_space:
                        if getattr(player, "conn", None):
                            send_message(player.conn, make_error_reply("Zaino pieno! Non puoi raccogliere questo oggetto."))
                        return
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
                    for s_i in range(len(sheet["inventory_grid"])):
                        if sheet["inventory_grid"][s_i] is None:
                            sheet["inventory_grid"][s_i] = dict(loot_entry)
                            break
                    item_sync_msgs.append(make_receive_item(dict(loot_entry)))
            else:
                loots.remove(found)
                if not is_container_loot:
                    loot_entry = {
                        "name": found["item"],
                        "type": "Misto",
                        "qty": found["qty"],
                        "weight": 1.0,
                        "attuned": False,
                        "desc": "Raccolto da forziere/spoglie",
                        "_sender": "Forziere"
                    }
                    item_sync_msgs.append(make_receive_item(dict(loot_entry)))

    if found:
        if getattr(player, 'conn', None):
            for c_msg in coin_sync_msgs:
                send_message(player.conn, c_msg)
            for i_msg in item_sync_msgs:
                send_message(player.conn, i_msg)
            
        game_state.log_dm_message(f'[Loot] {player.name} ha raccolto {found["qty"]}x {found["item"]}.')
        if hasattr(game_state, "record_journal_event"):
            try:
                game_state.record_journal_event("loot", "Raccolta Bottino", f"{player.name} ha raccolto {found['qty']}x {found['item']}.", actor=player.name)
            except Exception:
                pass
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_buy_item_request(data, player, game_state):
    shop_name = data.get("shop_name")
    item_name = data.get("item_name")
    
    if not shop_name or not item_name: return
    
    with game_state.lock:
        shop = getattr(game_state, "shops", {}).get(shop_name)
        if not shop: return
        
        item_to_buy = None
        shop_items = shop.get("items")
        if not shop_items:
            raw_inv = shop.get("resolved_inventory") or shop.get("inventory") or []
            shop_items = []
            for raw_it in raw_inv:
                if isinstance(raw_it, dict):
                    raw_p = raw_it.get("price", raw_it.get("cost_gp", raw_it.get("cost", 10)))
                    try:
                        import re as _re
                        p_val = int(_re.search(r"(\d+)", str(raw_p)).group(1)) if isinstance(raw_p, str) and _re.search(r"(\d+)", str(raw_p)) else int(raw_p)
                    except (ValueError, TypeError):
                        p_val = 10
                    shop_items.append({
                        "name": raw_it.get("name", "Oggetto"),
                        "price": max(0, p_val),
                        "qty": int(raw_it.get("qty", 1) or 1),
                        "weight": float(raw_it.get("weight", 1.0) or 1.0),
                        "type": raw_it.get("type", "Equipaggiamento"),
                        "description": raw_it.get("description", raw_it.get("desc", "")),
                    })
                else:
                    shop_items.append({"name": str(raw_it), "price": 10, "qty": 1, "weight": 1.0})
            shop["items"] = shop_items
        for item in shop_items:
            if item.get("name") == item_name:
                item_to_buy = item
                break
                
        if not item_to_buy: return
        
        price = int(item_to_buy.get("price", 0))
        if price < 0:
            return
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
        if isinstance(sheet.get("wallet"), dict):
            sheet["wallet"]["MO"] = new_mo
        sheet["gp"] = str(new_mo)
        
        # Inserisci nella griglia inventario (preservando griglie > 25 slot)
        if not isinstance(sheet.get("inventory_grid"), list) or len(sheet["inventory_grid"]) == 0:
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
            for idx in range(len(sheet["inventory_grid"])):
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

    with game_state.lock:
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
            if isinstance(sender_sheet.get("wallet"), dict):
                sender_sheet["wallet"]["MO"] = new_sg
            sender_sheet["gp"] = str(new_sg)

        recip_sheet = getattr(target_player, "full_sheet", None)
        if recip_sheet:
            r_curr = recip_sheet.setdefault("currency", {"MR": 0, "MA": 0, "ME": 0, "MO": 0, "MP": 0})
            r_gold = int(r_curr.get("MO", 0)) if isinstance(r_curr, dict) else int(recip_sheet.get("gp", 0))
            new_rg = r_gold + amount
            if isinstance(r_curr, dict):
                r_curr["MO"] = new_rg
            if isinstance(recip_sheet.get("wallet"), dict):
                recip_sheet["wallet"]["MO"] = new_rg
            recip_sheet["gp"] = str(new_rg)

    send_message(target_player.conn, {"type": "RECEIVE_GOLD", "data": {"amount": amount, "sender": player.name}})
    log_msg = f"{player.name} ha donato {amount} Monete d'Oro (MO) a {target_name}."
    game_state.log_dm_message(f"[SISTEMA] {log_msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
