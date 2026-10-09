# commands.py
from common.protocol import *
from common.dice import roll_dice
from common.network_utils import send_message, broadcast

def _apply_hp_change(target_player, new_hp_unbounded, game_state):
    old_hp = target_player.hp
    excess_damage = 0
    if new_hp_unbounded < 0:
        excess_damage = abs(new_hp_unbounded)
    
    target_player.hp = max(0, min(target_player.max_hp, new_hp_unbounded))
    
    is_npc = not hasattr(target_player, "conn") or target_player.conn is None
    
    if target_player.hp == 0:
        if is_npc:
            if "Morto" not in getattr(target_player, "conditions", []):
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                target_player.conditions.append("Morto")
        else:
            if excess_damage >= target_player.max_hp:
                if "Morto" not in getattr(target_player, "conditions", []):
                    if not hasattr(target_player, "conditions"): target_player.conditions = []
                    target_player.conditions.append("Morto")
                    msg = f"!!! {target_player.name} E' MORTO SUL COLPO A CAUSA DI DANNO MASSICCIO !!!"
                    from common.protocol import make_chat_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", msg))
                    game_state.log_dm_message(msg)
            else:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Concentrazione" in target_player.conditions:
                    target_player.conditions.remove("Concentrazione")
                if "Incosciente" not in target_player.conditions:
                    target_player.conditions.append("Incosciente")
                if "Prono" not in target_player.conditions:
                    target_player.conditions.append("Prono")
                if old_hp == 0 and new_hp_unbounded < 0:
                    msg = f"{target_player.name} subisce danni mentre è a 0 HP! Segna un fallimento nel Tiro Salvezza contro la morte!"
                    from common.protocol import make_chat_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", msg))
                    game_state.log_dm_message(msg)
    elif target_player.hp > 0:
        if old_hp == 0 and "Incosciente" in getattr(target_player, "conditions", []):
            target_player.conditions.remove("Incosciente")

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
                    from common.protocol import make_game_state
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
                from common.protocol import make_game_state
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
                from common.protocol import make_game_state
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
                from common.protocol import make_game_state
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
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
        import random
        # 1. Roll to Hit
        has_adv = False
        has_dis = False
        flanking = False
        
        p_cond = getattr(player, "conditions", [])
        t_cond = getattr(target_player, "conditions", [])
        
        if "Invisibile" in p_cond: has_adv = True
        if "Invisibile" in t_cond: has_dis = True
        if any(c in p_cond for c in ["Avvelenato", "Trattenuto", "Prono"]): has_dis = True
        if "Trattenuto" in t_cond: has_adv = True
        
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = target_player.position[0], target_player.position[1]
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            if "Prono" in t_cond:
                if dist == 1: has_adv = True
                elif dist > 1: has_dis = True
            if dist == 1:
                opp_q = q2 + (q2 - q1)
                opp_r = r2 + (r2 - r1)
                for p in getattr(game_state, "players", []):
                    if p.name != player.name and getattr(p, "hp", 0) > 0:
                        if hasattr(p, "position") and p.position and p.position[0] == opp_q and p.position[1] == opp_r:
                            p_c = getattr(p, "conditions", [])
                            if "Invisibile" not in p_c and "Nascosto" not in p_c:
                                has_adv = True
                                flanking = True
                                break

        if has_adv and has_dis:
            has_adv = False
            has_dis = False
            
        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        if has_adv:
            base_roll = max(roll1, roll2)
        elif has_dis:
            base_roll = min(roll1, roll2)
        else:
            base_roll = roll1
            
        try:
            hit_roll = base_roll + int(hit_bonus)
        except ValueError:
            hit_roll = base_roll
            
        is_crit = (base_roll == 20)
        is_fail = (base_roll == 1)
        
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
                
        # Check cover and line of sight
        blocked_by_wall = False
        cover_bonus = 0
        cover_name = None
        
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            from common.hex_utils import hex_linedraw, Hex
            p_hex = Hex(player.position[0], player.position[1])
            t_hex = Hex(target_player.position[0], target_player.position[1])
            line = hex_linedraw(p_hex, t_hex)
            
            if getattr(game_state, "current_map", None):
                walls = game_state.current_map.get("walls", [])
                half_cover = game_state.current_map.get("half_cover", [])
                three_quarters = game_state.current_map.get("three_quarters_cover", [])
                
                for step in line[1:]:
                    pos = [step.q, step.r]
                    if pos in walls:
                        blocked_by_wall = True
                        break
                    elif pos in three_quarters:
                        if cover_bonus < 5:
                            cover_bonus = 5
                            cover_name = "Tre Quarti di Copertura"
                    elif pos in half_cover:
                        if cover_bonus < 2:
                            cover_bonus = 2
                            cover_name = "Mezza Copertura"

        if cover_bonus > 0 and not blocked_by_wall:
            target_ac += cover_bonus
                
        hits = (is_crit or (not is_fail and hit_roll >= target_ac)) and not blocked_by_wall
        
        log_msg = f"{player.name} attacca {target_name} con {weapon_name}."
        if flanking:
            log_msg += " (Fiancheggiamento)"
        if has_adv:
            log_msg += " (Vantaggio)"
        elif has_dis:
            log_msg += " (Svantaggio)"
        log_msg += f" Tiro per colpire: {hit_roll}"
        if benedizione_bonus > 0:
            log_msg += f" (+{benedizione_bonus} Benedizione)"
        log_msg += f" vs CA {target_ac}."
        if scudo_applicato:
            log_msg += " (Scudo +5 CA applicato)"
        if cover_name:
            log_msg += f" (+{cover_bonus} {cover_name})"
        
        if blocked_by_wall:
            log_msg += " Bloccato dal Muro."
        elif hits:
            log_msg += " COLPITO!"
            if is_crit: log_msg += " (CRITICO!)"
            if damage_formula:
                dmg_result = roll_dice(damage_formula)
                dmg_val = dmg_result["total"]
                if is_crit:
                    # Raddoppia i dadi del danno
                    crit_dmg_result = roll_dice(damage_formula)
                    dmg_val += crit_dmg_result["total"]
                    
                _apply_hp_change(target_player, target_player.hp - dmg_val, game_state)
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
                _apply_hp_change(target_player, target_player.hp - dmg_val, game_state)
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
    "TOGGLE_COVER_REQUEST": handle_toggle_cover_request,
}

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
        broadcast(game_state, make_chat_broadcast("Sistema", f"Il gruppo si e' accampato per un Riposo Lungo. Tutti recuperano HP e Slot."))
        from common.network_utils import send_message
        for p in getattr(game_state, "players", []):
            if getattr(p, "conn", None):
                send_message(p.conn, {"type": "DO_LONG_REST", "data": {}})
        game_state.ongoing_rest_vote = None

command_handlers['TAKE_LOOT_REQUEST'] = handle_take_loot_request
command_handlers['LONG_REST_REQUEST'] = handle_long_rest_request
command_handlers['LONG_REST_VOTE'] = handle_long_rest_vote
