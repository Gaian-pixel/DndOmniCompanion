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
        
    aoe_data["caster"] = player.name
    # Regola D&D 5e: Gestione Concentrazione per AoE
    if aoe_data.get("concentration", False):
        conds = getattr(player, "conditions", [])
        if "Concentrazione" not in conds:
            conds.append("Concentrazione")
            broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        
        # Un incantatore può mantenere una sola concentrazione alla volta: rimuovi AoE precedenti
        if hasattr(game_state, "active_aoes"):
            for old in list(game_state.active_aoes):
                if old.get("caster") == player.name and old.get("concentration"):
                    game_state.active_aoes.remove(old)
                    game_state.log_dm_message(f"[CONCENTRAZIONE] La concentrazione di {player.name} sulla precedente AoE si spezza a favore della nuova.")

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
        hexes = get_line_hexes(origin, target, size)
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
            # Mostro/NPC gestito dal server/DM: tiro salvezza ed applicazione automatica dei danni!
            try:
                from server.rules.combat import _process_save_result
                from common.dice import roll_dice
                stat = aoe_data.get("stat", "DES")
                dc = aoe_data.get("dc", 10)
                damage_formula = aoe_data.get("dmg", "8d6")
                half_on_success = aoe_data.get("half", True)
                mod = 0
                if getattr(p, "full_sheet", None):
                    attr = p.full_sheet.get("attributes", {})
                    if stat in attr:
                        mod = (int(attr[stat]) - 10) // 2
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                save_result = roll_dice(f"1d20{mod_str}")
                roll_tot = save_result["total"]
                is_crit = save_result["rolls"][0] == 20
                is_fail = save_result["rolls"][0] == 1
                _process_save_result(p.name, stat, roll_tot, is_crit, is_fail, dc, damage_formula, half_on_success, player.name, game_state)
            except Exception as e:
                game_state.log_dm_message(f"[AoE] Errore tiro automatico TS per {p.name}: {e}")

def handle_clear_aoes_request(data, player, game_state):
    is_dm = (getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if is_dm:
        game_state.clear_aoes()
    else:
        if hasattr(game_state, "active_aoes"):
            game_state.active_aoes = [a for a in game_state.active_aoes if a.get("caster") != player.name]
            game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_ping_request(data, player, game_state):
    q = data.get("q")
    r = data.get("r")
    color = data.get("color", "yellow")
    if q is not None and r is not None:
        broadcast(game_state, make_ping_broadcast(q, r, color))
        game_state.gui_queue.put({"type": "PING_BROADCAST", "payload": {"q": q, "r": r, "color": color}})


def handle_toggle_wall_request(data, player, game_state):
    is_dm = (getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Solo il Dungeon Master può modificare i muri sulla mappa."))
        return
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
    is_dm = (getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Solo il Dungeon Master può modificare le coperture sulla mappa."))
        return
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
    if not hasattr(game_state, "drawn_lines") or not isinstance(game_state.drawn_lines, list):
        game_state.drawn_lines = []
    game_state.drawn_lines.append({"points": points, "color": color})
    from common.network_utils import broadcast
    broadcast(game_state, {"type": "DRAW_BROADCAST", "data": {"points": points, "color": color}})

def handle_clear_drawings_request(data, player, game_state):
    game_state.drawn_lines = []
    from common.network_utils import broadcast
    from common.protocol import make_clear_drawings_broadcast
    broadcast(game_state, make_clear_drawings_broadcast())
    game_state._trigger_gui_update()

def handle_toggle_door_request(data, player, game_state):
    """Gestisce l'apertura, chiusura o scasso di una porta (D&D 5e)."""
    if not getattr(game_state, "current_map", None):
        return
    q = data.get("q")
    r = data.get("r")
    req_state = data.get("state")
    is_dm = (player is None or getattr(player, "role", "") == "DM")
    
    doors = game_state.current_map.setdefault("doors", [])
    target_door = None
    for d in doors:
        if d.get("q") == q and d.get("r") == r:
            target_door = d
            break
            
    if not target_door:
        if is_dm:
            new_door = {"q": q, "r": r, "state": "closed", "name": "Porta in Legno", "dc": 15, "break_dc": 17, "key_name": ""}
            doors.append(new_door)
            broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
            broadcast(game_state, make_chat_broadcast("Sistema", f"🚪 Il DM ha posizionato una nuova Porta a ({q}, {r})."))
            game_state._trigger_gui_update()
        return

    # Se non è DM, controlla distanza (deve essere adiacente: <= 1)
    if not is_dm and hasattr(player, "position") and player.position:
        pq, pr = player.position[0], player.position[1]
        dist = max(abs(pq - q), abs(pq + pr - q - r), abs(pr - r))
        if dist > 1:
            if player.conn:
                send_message(player.conn, make_error_reply("Sei troppo lontano per interagire con questa porta (devi essere adiacente)!"))
            return

    cur_state = target_door.get("state", "closed")
    door_name = target_door.get("name", "Porta")
    dc = target_door.get("dc", 15)
    method = data.get("method") or "lockpick"
    key_item = data.get("key_item")

    from server.rules.movement import auto_explore_fow

    if is_dm:
        if req_state:
            target_door["state"] = req_state
        else:
            cycle = {"closed": "open", "open": "locked", "locked": "secret", "secret": "closed"}
            target_door["state"] = cycle.get(cur_state, "open")
        new_state = target_door["state"]
        broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🚪 {door_name} a ({q}, {r}) impostata su '{new_state.upper()}' dal DM."))
        for p in game_state.players:
            if auto_explore_fow(p, game_state):
                broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
        game_state._trigger_gui_update()
        return

    p_name = player.name if player else "Un giocatore"
    if cur_state == "open":
        target_door["state"] = "closed"
        broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🚪 {p_name} chiude la {door_name}."))
        for p in game_state.players:
            auto_explore_fow(p, game_state)
        game_state._trigger_gui_update()
    elif cur_state == "closed":
        target_door["state"] = "open"
        broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🚪 {p_name} apre la {door_name}."))
        for p in game_state.players:
            if auto_explore_fow(p, game_state):
                broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
        game_state._trigger_gui_update()
    elif cur_state == "locked":
        if method == "key":
            door_key = target_door.get("key_name", "").strip()
            key_matched = False
            used_key_name = key_item or "Chiave"
            if door_key:
                if key_item and door_key.lower() in key_item.lower():
                    key_matched = True
                    used_key_name = key_item
                elif getattr(player, "full_sheet", None):
                    inv_items = player.full_sheet.get("inventory_grid", []) + player.full_sheet.get("inventory", [])
                    for it in inv_items:
                        if it and isinstance(it, dict) and door_key.lower() in it.get("name", "").lower():
                            key_matched = True
                            used_key_name = it.get("name")
                            break
            else:
                key_matched = True

            if key_matched:
                target_door["state"] = "open"
                broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
                broadcast(game_state, make_chat_broadcast("Sistema", f"🔑 {p_name} inserisce '{used_key_name}' nella toppa e apre senza sforzo la {door_name}!"))
                for p in game_state.players:
                    if auto_explore_fow(p, game_state):
                        broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
                game_state._trigger_gui_update()
            else:
                if player.conn:
                    send_message(player.conn, make_error_reply(f"La chiave che possiedi non è adatta per questa porta (richiede: '{door_key}')."))
            return

        elif method == "knock":
            if getattr(player, "full_sheet", None):
                slots = player.full_sheet.get("spell_slots", {})
                if "2" in slots and isinstance(slots["2"], dict):
                    if slots["2"].get("current", 0) > 0:
                        slots["2"]["current"] -= 1
                        if player.conn:
                            send_message(player.conn, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, getattr(player, "conditions", []), getattr(player, "temp_hp", 0)))
            target_door["state"] = "open"
            broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
            broadcast(game_state, make_chat_broadcast("Sistema", f"🪄 {p_name} lancia l'incantesimo Scassinare (Knock)! La serratura scatta rumorosamente e la {door_name} si spalanca! 🔔 Un rimbombo udibile fino a 90 metri (300 ft) echeggia nelle vicinanze!"))
            for p in game_state.players:
                if auto_explore_fow(p, game_state):
                    broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
            game_state._trigger_gui_update()
            return

        elif method == "break":
            str_mod = 0
            pb = 2
            has_prof = False
            has_expertise = False
            if getattr(player, "full_sheet", None):
                attrs = player.full_sheet.get("attributes", {})
                str_val = attrs.get("FOR", attrs.get("STR", 10))
                try: str_mod = (int(str_val) - 10) // 2
                except Exception: str_mod = 0
                lvl = player.full_sheet.get("level", 1)
                pb = 2 + max(0, (int(lvl) - 1) // 4)
                skills = player.full_sheet.get("skills", {})
                ath = skills.get("Atletica", skills.get("Athletics", 0))
                if ath == 2:
                    has_expertise = True
                elif ath == 1:
                    has_prof = True
            break_bonus = str_mod + (2 * pb if has_expertise else (pb if has_prof else 0))
            break_dc = target_door.get("break_dc") or (dc + 2)
            d20 = random.randint(1, 20)
            total = d20 + break_bonus
            detail = f"{d20} + {break_bonus} ({str_mod} FOR" + (f", +{2*pb} Maestria Atletica" if has_expertise else (f", +{pb} Atletica" if has_prof else "")) + ")"
            if d20 == 20 or total >= break_dc:
                target_door["state"] = "open"
                broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
                broadcast(game_state, make_chat_broadcast("Sistema", f"💥 {p_name} sfonda la {door_name} con un colpo devastante! [Tiro Forza: {total} ({detail}) vs CD {break_dc}] 📢 Il violento boato dello schianto rimbomba nel dungeon!"))
                for p in game_state.players:
                    if auto_explore_fow(p, game_state):
                        broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
                game_state._trigger_gui_update()
            else:
                broadcast(game_state, make_chat_broadcast("Sistema", f"🛡️ {p_name} si scaglia contro la {door_name} [Tiro Forza: {total} ({detail}) vs CD {break_dc}], ma la porta resiste saldamente all'impatto!"))
            return

        else: # "lockpick"
            dex_mod = 0
            pb = 2
            has_prof = False
            has_expertise = False
            if getattr(player, "full_sheet", None):
                sheet = player.full_sheet
                attrs = sheet.get("attributes", {})
                dex_val = attrs.get("DES", attrs.get("DEX", 10))
                try: dex_mod = (int(dex_val) - 10) // 2
                except Exception: dex_mod = 0
                lvl = sheet.get("level", 1)
                pb = 2 + max(0, (int(lvl) - 1) // 4)
                
                c_cls = str(sheet.get("char_class", "")).lower()
                if any(k in c_cls for k in ["ladro", "rogue"]):
                    has_prof = True
                    if int(lvl) >= 1:
                        feats = str(sheet.get("features", "")).lower()
                        if "maestria" in feats or "expertise" in feats or "scasso" in feats:
                            has_expertise = True
                
                skills = sheet.get("skills", {})
                if skills.get("Arnesi da Scasso") == 2 or skills.get("Thieves' Tools") == 2:
                    has_expertise = True
                    has_prof = True
                elif skills.get("Arnesi da Scasso") == 1 or skills.get("Thieves' Tools") == 1:
                    has_prof = True
                    
                feats = str(sheet.get("features", "")).lower()
                if "arnesi da scasso" in feats or "thieves' tools" in feats:
                    has_prof = True

            lock_bonus = dex_mod + (2 * pb if has_expertise else (pb if has_prof else 0))
            d20 = random.randint(1, 20)
            total = d20 + lock_bonus
            detail = f"{d20} + {lock_bonus} ({dex_mod} DES" + (f", +{2*pb} Maestria Arnesi" if has_expertise else (f", +{pb} Competenza Arnesi" if has_prof else "")) + ")"
            if d20 == 20 or total >= dc:
                target_door["state"] = "open"
                broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
                broadcast(game_state, make_chat_broadcast("Sistema", f"🔓 {p_name} scassina la serratura della {door_name} con gli Arnesi da Scasso! [Tiro: {total} ({detail}) vs CD {dc}] e la spalanca!"))
                for p in game_state.players:
                    if auto_explore_fow(p, game_state):
                        broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"]))
                game_state._trigger_gui_update()
            else:
                fumble_msg = " ⚠️ Un arnese si è quasi incastrato nella toppa!" if d20 == 1 else ""
                broadcast(game_state, make_chat_broadcast("Sistema", f"🔒 {p_name} tenta di scassinare la {door_name} con gli Arnesi da Scasso [Tiro: {total} ({detail}) vs CD {dc}], ma i perni non scattano!{fumble_msg}"))
    elif cur_state == "secret":
        if player.conn:
            send_message(player.conn, make_error_reply("Non noti nulla di insolito qui."))

def handle_room_pin_request(data, player, game_state):
    """Gestisce le spille di mappa e note stanza (Room Pins) riservate al DM."""
    if not getattr(game_state, "current_map", None):
        return
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm:
        return
    action = data.get("action", "add")
    pin = data.get("pin", {})
    pins = game_state.current_map.setdefault("room_pins", [])
    
    if action == "add":
        pins.append(pin)
    elif action == "delete":
        pin_id = pin.get("id")
        game_state.current_map["room_pins"] = [p for p in pins if p.get("id") != pin_id]
    elif action == "update":
        pin_id = pin.get("id")
        for i, p in enumerate(pins):
            if p.get("id") == pin_id:
                pins[i] = pin
                break
    elif action == "read_aloud":
        text = pin.get("read_aloud", "")
        title = pin.get("title", "Descrizione Stanza")
        if text:
            msg = f"📜 [{title}]\n\"{text}\""
            broadcast(game_state, make_chat_broadcast("Narratore (DM)", msg))
            game_state.log_dm_message(f"[NARRATORE] {title}: {text}")
            return
            
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
    game_state._trigger_gui_update()

def handle_resolve_aoe_request(data, player, game_state):
    """Risolve Tiri Salvezza e applica danni per tutti i token all'interno di un'AoE già presente sulla mappa."""
    if not getattr(game_state, "active_aoes", None):
        return
    aoe_index = data.get("aoe_index", 0)
    if aoe_index < 0 or aoe_index >= len(game_state.active_aoes):
        aoe_index = 0
    aoe_data = game_state.active_aoes[aoe_index]
    
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
        hexes = get_line_hexes(origin, target, size)
    else:
        hexes = []

    stat = data.get("stat") or aoe_data.get("stat", "DES")
    dc = int(data.get("dc") or aoe_data.get("dc", 13))
    damage_formula = data.get("damage_formula") or aoe_data.get("dmg", "8d6")
    half_on_success = bool(data.get("half_on_success", True))
    damage_type = data.get("damage_type") or aoe_data.get("damage_type", "Fuoco")
    caster_name = aoe_data.get("caster", player.name if player else "Incantatore")

    affected_players = []
    for p in getattr(game_state, "players", []):
        if getattr(p, "hp", 0) > 0 and getattr(p, "position", None):
            pos_hex = Hex(p.position[0], p.position[1])
            if pos_hex in hexes:
                affected_players.append(p)

    if not affected_players:
        msg = f"⚡ Nessuna creatura si trova nell'area dell'incantesimo ({aoe_type.capitalize()} a {origin.q},{origin.r})."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    msg = f"💥 Risoluzione AoE di {caster_name} ({aoe_type.capitalize()} R={size}): {len(affected_players)} creature coinvolte! Richiesto TS su {stat} CD {dc} ({damage_formula} {damage_type})."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[AoE] {msg}")

    from common.protocol import make_prompt_save
    for p in affected_players:
        if getattr(p, "conn", None):
            send_message(p.conn, make_prompt_save(
                stat=stat, dc=dc, damage_formula=damage_formula,
                half_on_success=half_on_success, source_name=caster_name,
                damage_type=damage_type
            ))
        else:
            try:
                from server.rules.combat import _process_save_result
                from common.dice import roll_dice
                mod = 0
                if getattr(p, "full_sheet", None):
                    attr = p.full_sheet.get("attributes", {})
                    if stat in attr:
                        mod = (int(attr[stat]) - 10) // 2
                mod_str = f"+{mod}" if mod >= 0 else str(mod)
                save_result = roll_dice(f"1d20{mod_str}")
                roll_tot = save_result["total"]
                is_crit = save_result["rolls"][0] == 20
                is_fail = save_result["rolls"][0] == 1
                _process_save_result(p.name, stat, roll_tot, is_crit, is_fail, dc, damage_formula, half_on_success, caster_name, game_state, damage_type)
            except Exception as e:
                game_state.log_dm_message(f"[AoE] Errore tiro TS automatico per {p.name}: {e}")



