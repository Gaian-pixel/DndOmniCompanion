# commands.py
from common.protocol import *
from common.dice import roll_dice
from common.network_utils import send_message, broadcast

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
                    from common.protocol import make_game_state
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
                    from common.protocol import make_game_state
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata aura {aura_rad} ({color}) per {p_name}")
            except ValueError:
                pass
        return

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
    if "Afferrato" in getattr(player, "conditions", []) or "Privo di Sensi" in getattr(player, "conditions", []):
        from common.network_utils import send_message
        from common.protocol import make_error_reply
        if player.conn:
            send_message(player.conn, make_error_reply("La tua velocità è 0. Non puoi muoverti."))
        return

    to_pos = data.get("to")
    if to_pos:
        walls_list_pos = game_state.current_map.get("walls", []) if getattr(game_state, "current_map", None) else []
        if [to_pos["q"], to_pos["r"]] in walls_list_pos:
            from common.network_utils import send_message
            from common.protocol import make_error_reply
            if player.conn:
                send_message(player.conn, make_error_reply("Non puoi muoverti lì, c'è un muro!"))
            return
            
        in_combat = getattr(player, "in_combat", False) or getattr(game_state, "combat_active", False)
        if in_combat and hasattr(player, "position") and player.position:
            q1, r1 = player.position.get("q", 0), player.position.get("r", 0)
            q2, r2 = to_pos.get("q", 0), to_pos.get("r", 0)
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            speed = getattr(player, "speed", 30)
            max_hexes = speed // 5
            if dist > max_hexes:
                from common.network_utils import send_message
                from common.protocol import make_error_reply
                if getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply(f"Movimento non consentito: la distanza supera la tua velocità di {speed}ft."))
                return

        game_state.move_player(player.name, to_pos)
        
        # Auto-explore FoW around the player's new position
        if getattr(game_state, "current_map", None) and game_state.current_map.get("fow_enabled", False):
            from common.hex_utils import Hex, get_sphere_hexes, hex_linedraw
            h = Hex(to_pos["q"], to_pos["r"])
            revealed = get_sphere_hexes(h, 6) # 30 feet radius
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
                from common.protocol import make_game_state
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
                return # Game state broadcast includes player move
                
        from common.protocol import make_player_move
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

def _trigger_concentration_check(target_player, dmg_val, game_state):
    if dmg_val > 0 and "Concentrazione" in getattr(target_player, "conditions", []):
        dc = max(10, dmg_val // 2)
        if getattr(target_player, "conn", None):
            from common.protocol import make_prompt_save
            send_message(target_player.conn, make_prompt_save("COS", dc, "", False, "Sistema (Concentrazione)"))
        else:
            from common.dice import roll_dice
            mod = 0
            if target_player.full_sheet:
                attr = target_player.full_sheet.get("attributes", {})
                if "COS" in attr:
                    mod = (int(attr["COS"]) - 10) // 2
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            save_result = roll_dice(f"1d20{mod_str}")
            roll_tot = save_result["total"]
            is_crit = save_result["rolls"][0][0] == 20
            is_fail = save_result["rolls"][0][0] == 1
            import threading
            threading.Timer(0.1, _process_save_result, args=(target_player.name, "COS", roll_tot, is_crit, is_fail, dc, "", False, "Sistema (Concentrazione)", game_state)).start()

def handle_end_turn_request(data, player, game_state):
    # Solo chi è di turno può passarlo
    current = game_state.get_current_turn_player()
    if current and current.name == player.name:
        if hasattr(current, "condition_durations"):
            expired = []
            for cond, dur in list(current.condition_durations.items()):
                current.condition_durations[cond] = dur - 1
                if current.condition_durations[cond] <= 0:
                    expired.append(cond)
            
            for cond in expired:
                del current.condition_durations[cond]
                if cond in current.conditions:
                    current.conditions.remove(cond)
                msg = f"L'effetto di {cond} su {current.name} è terminato."
                game_state.log_dm_message(f"[SISTEMA] {msg}")
                from common.protocol import make_chat_broadcast, make_player_stats_update
                broadcast(game_state, make_chat_broadcast("Sistema", msg))
                
            if expired:
                from common.protocol import make_player_stats_update
                broadcast(game_state, make_player_stats_update(current.name, current.hp, current.max_hp, current.initiative, current.conditions))
                game_state._trigger_gui_update()

        game_state.next_turn()
        # Announce turn
        next_p = game_state.get_current_turn_player()
        if next_p:
            msg = f"Round {game_state.round_number} - Turno di {next_p.name}!"
            game_state.log_dm_message(f"[COMBAT] {msg}")
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
        from common.protocol import make_game_state
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


def handle_attack_request(data, player, game_state):
    target_name = data.get("target_name")
    weapon_name = data.get("weapon_name", "Attacco")
    hit_bonus = data.get("hit_bonus", 0)
    damage_formula = data.get("damage_formula")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return
    
    try:
        from common.dice import roll_dice
        # 1. Roll to Hit
        formula = f"1d20+{hit_bonus}"
        if "Avvelenato" in getattr(player, "conditions", []):
            if " dis" not in formula:
                formula += " dis"
        hit_result = roll_dice(formula)
        hit_roll = hit_result["total"]
        is_crit = (hit_result["rolls"][0][0] == 20)
        is_fail = (hit_result["rolls"][0][0] == 1)
        
        import random
        benedizione_bonus = 0
        if "Benedizione" in getattr(player, "conditions", []):
            benedizione_bonus = random.randint(1, 4)
            hit_roll += benedizione_bonus
        
        # 2. Get Target AC
        target_ac = 10
        if target_player.full_sheet:
            try:
                target_ac = int(target_player.full_sheet.get("ac", 10))
            except (ValueError, TypeError):
                pass
                
        scudo_applicato = False
        if "Scudo" in getattr(target_player, "conditions", []):
            target_ac += 5
            scudo_applicato = True
                
        hits = is_crit or (not is_fail and hit_roll >= target_ac)
        
        log_msg = f"{player.name} attacca {target_name} con {weapon_name}. Tiro per colpire: {hit_roll}"
        if benedizione_bonus > 0:
            log_msg += f" (+{benedizione_bonus} Benedizione)"
        log_msg += f" vs CA {target_ac}."
        if scudo_applicato:
            log_msg += " (Scudo +5 CA applicato)"
        
        if hits:
            log_msg += " COLPITO!"
            if is_crit: log_msg += " (CRITICO!)"
            if damage_formula:
                dmg_result = roll_dice(damage_formula)
                dmg_val = dmg_result["total"]
                if is_crit:
                    # Raddoppia i dadi del danno
                    crit_dmg_result = roll_dice(damage_formula)
                    dmg_val += crit_dmg_result["total"]
                    
                target_player.hp = max(0, target_player.hp - dmg_val)
                log_msg += f" Danno: {dmg_val}. HP {target_name}: {target_player.hp}/{target_player.max_hp}"
                
                broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
                game_state._trigger_gui_update()
                _trigger_concentration_check(target_player, dmg_val, game_state)
        else:
            log_msg += " MANCATO!"
            
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
    except Exception as e:
        send_message(player.conn, make_error_reply(f"Errore nell'attacco: {str(e)}"))

def handle_ping_request(data, player, game_state):
    q = data.get("q")
    r = data.get("r")
    color = data.get("color", "yellow")
    if q is not None and r is not None:
        broadcast(game_state, make_ping_broadcast(q, r, color))
        game_state.gui_queue.put({"type": "PING_BROADCAST", "payload": {"q": q, "r": r, "color": color}})


def _process_save_result(target_name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state):
    target_player = game_state.find_player(target_name)
    if not target_player: return
    
    benedizione_bonus = 0
    if "Benedizione" in getattr(target_player, "conditions", []):
        import random
        benedizione_bonus = random.randint(1, 4)
        roll_total += benedizione_bonus
        
    success = is_crit or (not is_fail and roll_total >= dc)
    
    log_msg = f"{target_name} effettua un TS su {stat} contro CD {dc} di {source_name}. Risultato: {roll_total}"
    if benedizione_bonus > 0:
        log_msg += f" (+{benedizione_bonus} Benedizione)"
    log_msg += "."
    if success:
        log_msg += " SUPERATO!"
    else:
        log_msg += " FALLITO!"
        if source_name == "Sistema (Concentrazione)":
            if "Concentrazione" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Concentrazione")
                from common.protocol import make_player_stats_update
                broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
                game_state._trigger_gui_update()
            log_msg += " La concentrazione si spezza!"
        
    if damage_formula:
        try:
            from common.dice import roll_dice
            dmg_res = roll_dice(damage_formula)
            dmg_val = dmg_res["total"]
            
            if success:
                if half_on_success:
                    dmg_val = dmg_val // 2
                else:
                    dmg_val = 0
                    
            if dmg_val > 0:
                target_player.hp = max(0, target_player.hp - dmg_val)
                log_msg += f" Subisce {dmg_val} danni! HP: {target_player.hp}/{target_player.max_hp}"
                from common.protocol import make_player_stats_update
                broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
                game_state._trigger_gui_update()
                _trigger_concentration_check(target_player, dmg_val, game_state)
            else:
                log_msg += " Non subisce danni."
        except Exception as e:
            log_msg += f" (Errore formula danni: {e})"
            
    game_state.log_dm_message(f"[TS] {log_msg}")
    from common.protocol import make_chat_broadcast
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))

def handle_force_save_request(data, player, game_state):
    targets = data.get("targets", [])
    stat = data.get("stat")
    dc = data.get("dc")
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success", True)
    
    from common.protocol import make_prompt_save
    
    for t_name in targets:
        target_player = game_state.find_player(t_name)
        if not target_player: continue
        
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save(stat, dc, damage_formula, half_on_success, player.name))
        else:
            try:
                from common.dice import roll_dice
                mod = 0
                if target_player.full_sheet:
                    attr = target_player.full_sheet.get("attributes", {})
                    if stat in attr:
                        mod = (int(attr[stat]) - 10) // 2
                
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                save_result = roll_dice(f"1d20{mod_str}")
                roll_tot = save_result["total"]
                is_crit = save_result["rolls"][0] == 20
                is_fail = save_result["rolls"][0] == 1
                
                _process_save_result(target_player.name, stat, roll_tot, is_crit, is_fail, dc, damage_formula, half_on_success, player.name, game_state)
            except Exception as e:
                print("Errore nel roll NPC per TS:", e)

def handle_save_result_request(data, player, game_state):
    stat = data.get("stat")
    roll_total = data.get("roll_total")
    is_crit = data.get("is_crit")
    is_fail = data.get("is_fail")
    dc = data.get("dc")
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success")
    source_name = data.get("source_name")
    
    _process_save_result(player.name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state)

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
    from common.protocol import make_game_state
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_draw_request(data, player, game_state):
    points = data.get("points", [])
    color = data.get("color", "red")
    from common.network_utils import broadcast
    broadcast(game_state, {"type": "DRAW_BROADCAST", "data": {"points": points, "color": color}})

command_handlers = {
    "DRAW_REQUEST": handle_draw_request,
    "CHAT": handle_chat,
    "WHISPER": handle_whisper,
    "ROLL_REQUEST": handle_roll_request,
    "MOVE_REQUEST": handle_move_request,
    "UPDATE_STATS_REQUEST": handle_update_stats_request,
    "UPDATE_FULL_SHEET_REQUEST": handle_update_full_sheet_request,
    "TARGETED_ACTION_REQUEST": handle_targeted_action,
    "ATTACK_REQUEST": handle_attack_request,
    "GIVE_ITEM_REQUEST": handle_give_item_request,
    "CREATE_AOE_REQUEST": handle_create_aoe_request,
    "CLEAR_AOES_REQUEST": handle_clear_aoes_request,
    "SET_TRAVEL_ROLE_REQUEST": handle_set_travel_role_request,
    "START_COMBAT_REQUEST": handle_start_combat_request,
    "END_TURN_REQUEST": handle_end_turn_request,
    "SUBMIT_INITIATIVE": handle_submit_initiative,
    "PING_REQUEST": handle_ping_request,
    "FORCE_SAVE_REQUEST": handle_force_save_request,
    "SAVE_RESULT": handle_save_result_request,
    "TOGGLE_WALL_REQUEST": handle_toggle_wall_request,
}
