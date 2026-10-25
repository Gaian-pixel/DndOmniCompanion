from common.protocol import *
from common.network_utils import send_message, broadcast
import math
from server.rules.combat import _apply_hp_change, apply_damage
from common.dice import roll_dice
from common.i18n import is_condition_active

def handle_update_stats_request(data, player, game_state):
    try:
        target = player
        if not target and data.get("name"):
            target = game_state.find_player(data.get("name"))
        if not target:
            return
            
        hp = int(data.get("hp", target.hp))
        max_hp = int(data.get("max_hp", target.max_hp)) if data.get("max_hp") is not None else target.max_hp
        initiative = int(data.get("initiative", target.initiative)) if data.get("initiative") is not None else target.initiative
        conditions = data.get("conditions", getattr(target, "conditions", []))
        temp_hp = int(data.get("temp_hp", getattr(target, "temp_hp", 0)))
        target.max_hp = max_hp
        target.temp_hp = max(0, temp_hp)
        target.initiative = initiative
        target.conditions = conditions
        if "light_radius" in data:
            target.light_radius = max(0, int(data["light_radius"]))
        if "light_color" in data:
            target.light_color = str(data["light_color"])
        _apply_hp_change(target, hp, game_state)
        from server.rules.movement import auto_explore_fow
        if auto_explore_fow(target, game_state):
            broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
        game_state._trigger_gui_update()
        broadcast(game_state, make_player_stats_update(target.name, target.hp, target.max_hp, target.initiative, target.conditions, target.temp_hp))
    except Exception as e:
        print("Errore handle_update_stats_request:", e)


def handle_update_full_sheet_request(data, player, game_state):
    char_data = data.get("character") or data.get("sheet")
    if char_data:
        from common.starter_equipment import apply_class_and_race_starter_kit, apply_campaign_starter_kit
        # Se il personaggio non ha ancora ricevuto il kit iniziale di classe/razza, assegnalo
        if not char_data.get("starting_kit_applied"):
            apply_class_and_race_starter_kit(char_data)
        
        # Se non ha ancora ricevuto lo starter kit della campagna, assegnalo
        if not char_data.get("campaign_starter_received"):
            campaign_kit = getattr(game_state, "campaign_starter_kit", None)
            apply_campaign_starter_kit(char_data, campaign_kit)
            if getattr(player, "conn", None):
                from common.protocol import make_campaign_starter_granted, make_chat_broadcast
                from common.network_utils import send_message
                send_message(player.conn, make_campaign_starter_granted(char_data.get("inventory_grid", []), full_sheet=char_data))
                broadcast(game_state, make_chat_broadcast("Sistema", f"[CAMPAGNA] {player.name} ha ricevuto l'equipaggiamento iniziale della campagna dal Master!"))

        # Protezione e vincoli di gioco: se il PG ha già un full_sheet registrato sul server,
        # impedisci aumenti unilaterali di valuta, attributi o spawn abusivo di oggetti senza approvazione del DM
        if isinstance(getattr(player, "full_sheet", None), dict) and player.full_sheet:
            if hasattr(player, "hp") and isinstance(player.hp, (int, float)):
                char_data["hp_current"] = player.hp
            elif "hp_current" in player.full_sheet:
                char_data["hp_current"] = player.full_sheet["hp_current"]
            if hasattr(player, "max_hp") and isinstance(player.max_hp, (int, float)):
                char_data["hp_max"] = player.max_hp
            elif "hp_max" in player.full_sheet:
                char_data["hp_max"] = player.full_sheet["hp_max"]

            server_currency = player.full_sheet.get("currency", {})
            client_currency = char_data.get("currency", {})
            if isinstance(server_currency, dict) and isinstance(client_currency, dict):
                all_coin_keys = set(list(client_currency.keys()) + list(server_currency.keys()) + ["MR", "MA", "ME", "MO", "MP", "cp", "sp", "ep", "gp", "pp"])
                for c_k in all_coin_keys:
                    if c_k in client_currency:
                        s_val = server_currency.get(c_k, 0)
                        try:
                            if int(client_currency[c_k]) > int(s_val):
                                client_currency[c_k] = int(s_val)
                        except (ValueError, TypeError):
                            client_currency[c_k] = s_val
                char_data["currency"] = client_currency

            server_attrs = player.full_sheet.get("attributes", {})
            client_attrs = char_data.get("attributes", {})
            if isinstance(server_attrs, dict) and isinstance(client_attrs, dict):
                if char_data.get("level", 1) <= player.full_sheet.get("level", 1):
                    for a_k, a_val in server_attrs.items():
                        if a_k in client_attrs and client_attrs[a_k] > a_val:
                            client_attrs[a_k] = a_val
                char_data["attributes"] = client_attrs

            server_inv = player.full_sheet.get("inventory_grid", [])
            client_inv = char_data.get("inventory_grid", [])
            if isinstance(server_inv, list) and isinstance(client_inv, list):
                allowed_counts = {}
                from common.starter_equipment import get_pack_contents
                client_pack_counts = {}
                for c_it in client_inv:
                    if isinstance(c_it, dict) and c_it.get("name"):
                        ck = str(c_it.get("name", "")).strip().lower()
                        if get_pack_contents(ck):
                            try:
                                cq = max(1, int(c_it.get("qty", 1) or 1))
                            except (ValueError, TypeError):
                                cq = 1
                            client_pack_counts[ck] = client_pack_counts.get(ck, 0) + cq

                for s_it in server_inv:
                    if isinstance(s_it, dict) and s_it.get("name"):
                        k = str(s_it.get("name", "")).strip().lower()
                        try:
                            q = max(1, int(s_it.get("qty", 1) or 1))
                        except (ValueError, TypeError):
                            q = 1
                        pack_subs = get_pack_contents(k)
                        if pack_subs:
                            still_closed = min(q, client_pack_counts.get(k, 0))
                            unpacked_q = max(0, q - still_closed)
                            client_pack_counts[k] = max(0, client_pack_counts.get(k, 0) - still_closed)
                            allowed_counts[k] = allowed_counts.get(k, 0) + still_closed
                            if unpacked_q > 0:
                                for p_sub in pack_subs:
                                    sub_k = str(p_sub.get("name", "")).strip().lower()
                                    sub_q = int(p_sub.get("qty", 1) or 1) * unpacked_q
                                    allowed_counts[sub_k] = allowed_counts.get(sub_k, 0) + sub_q
                        else:
                            allowed_counts[k] = allowed_counts.get(k, 0) + q

                for s_i in range(len(client_inv)):
                    c_it = client_inv[s_i]
                    if isinstance(c_it, dict) and c_it.get("name"):
                        k = str(c_it.get("name", "")).strip().lower()
                        rem_allowed = allowed_counts.get(k, 0)
                        if rem_allowed <= 0:
                            client_inv[s_i] = None
                        else:
                            try:
                                c_q = max(1, int(c_it.get("qty", 1) or 1))
                            except (ValueError, TypeError):
                                c_q = 1
                            actual_q = min(c_q, rem_allowed)
                            c_it["qty"] = actual_q
                            allowed_counts[k] = rem_allowed - actual_q
                char_data["inventory_grid"] = client_inv

            # Valida weapons e spellbook contro aggiunte non autorizzate a parità di livello
            if "weapons" in player.full_sheet and isinstance(player.full_sheet["weapons"], list) and isinstance(char_data.get("weapons"), list):
                if char_data.get("level", 1) <= player.full_sheet.get("level", 1):
                    allowed_weapons = {str(w.get("name", "")).strip().lower() for w in player.full_sheet["weapons"] if isinstance(w, dict)}
                    char_data["weapons"] = [
                        w for w in char_data["weapons"]
                        if isinstance(w, dict) and str(w.get("name", "")).strip().lower() in allowed_weapons
                    ]

            if "spellbook" in player.full_sheet and isinstance(player.full_sheet["spellbook"], list) and isinstance(char_data.get("spellbook"), list):
                if char_data.get("level", 1) <= player.full_sheet.get("level", 1):
                    allowed_spells = {str(sp.get("name", "")).strip().lower() for sp in player.full_sheet["spellbook"] if isinstance(sp, dict)}
                    char_data["spellbook"] = [
                        sp for sp in char_data["spellbook"]
                        if isinstance(sp, dict) and str(sp.get("name", "")).strip().lower() in allowed_spells
                    ]

            # Proteggi diario, note e privilegi registrati sul server da modifiche non approvate
            if "journal_notes" in player.full_sheet and player.full_sheet["journal_notes"] is not None:
                char_data["journal_notes"] = player.full_sheet["journal_notes"]
            if "notes" in player.full_sheet and player.full_sheet["notes"] is not None:
                char_data["notes"] = player.full_sheet["notes"]
            if "features" in player.full_sheet and player.full_sheet["features"] is not None:
                if char_data.get("level", 1) <= player.full_sheet.get("level", 1):
                    char_data["features"] = player.full_sheet["features"]

        player.full_sheet = char_data
        player.avatar_b64 = char_data.get("avatar_b64") or getattr(player, "avatar_b64", None)
        player.hp = char_data.get("hp_current", player.hp)
        player.max_hp = char_data.get("hp_max", player.max_hp)
        player.temp_hp = char_data.get("temp_hp", getattr(player, "temp_hp", 0))
        player.initiative = char_data.get("initiative", player.initiative)
        player.exhaustion_level = char_data.get("exhaustion_level", getattr(player, "exhaustion_level", 0))
        player.speed = char_data.get("speed", getattr(player, "speed", 30))
        player.speed_unit = char_data.get("speed_unit", getattr(player, "speed_unit", None))
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))

def handle_targeted_action(data, player, game_state):
    conds = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(conds, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi eseguire azioni mirate mentre sei Incosciente, Paralizzato o a 0 HP!"))
        return

    target_name = data.get("target_name")
    action_type = data.get("action_type")
    formula = data.get("formula")
    reason = data.get("reason", "")
    damage_type = data.get("damage_type", "Tagliente")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return
    
    try:
        if formula:
            result = roll_dice(formula)
            val = result["total"]
        else:
            val = 0
            
        note_str = ""
        if action_type in ["danno", "damage"]:
            final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, val, damage_type, game_state)
            note_str = f" ({damage_type}){note}"
            if temp_absorbed > 0:
                note_str += f" [{temp_absorbed} assorbiti da Temp HP]"
            val = final_dmg
        elif action_type in ["cura", "heal"]:
            _apply_hp_change(target_player, target_player.hp + val, game_state)
        elif action_type in ["temp_hp", "temp"]:
            target_player.temp_hp = max(getattr(target_player, "temp_hp", 0), val)
            
        temp_disp = f" (+{target_player.temp_hp} Temp)" if getattr(target_player, "temp_hp", 0) > 0 else ""
        log_msg = f"{player.name} usa {reason or action_type} su {target_name}: {action_type} di {val}{note_str}. HP attuali: {target_player.hp}/{target_player.max_hp}{temp_disp}"
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
        broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
        game_state._trigger_gui_update()
        
    except ValueError as e:
        send_message(player.conn, make_error_reply(f"Errore nella formula: {str(e)}"))

def handle_set_travel_role_request(data, player, game_state):
    role = data.get("role", "Nessuna")
    marching_order = data.get("marching_order", getattr(player, "marching_order", "Centro"))
    player.travel_role = role
    player.marching_order = marching_order
    from common.protocol import make_game_state, make_chat_broadcast
    game_state._trigger_gui_update()
    broadcast(game_state, make_game_state(game_state.get_state_dict()))
    broadcast(game_state, make_chat_broadcast("Viaggio", f"🏕️ {player.name} si posiziona in [{marching_order}] con ruolo: {role}"))

def trigger_group_long_rest(game_state, reason="Il gruppo si è accampato per un Riposo Lungo."):
    game_state.travel_hours_today = 0
    from common.protocol import make_chat_broadcast
    from common.network_utils import send_message, broadcast
    
    auto_rest = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_rest = game_state.automation_settings.get("auto_apply_rest_recovery", True)
        
    if not auto_rest:
        msg = f"⛺ {reason} Richiesta di Riposo registrata (in attesa di conferma DM / verifica incontri casuali)."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[RIPOSO] {msg}")
        game_state.ongoing_rest_vote = None
        game_state._trigger_gui_update()
        return

    broadcast(game_state, make_chat_broadcast("Sistema", f"{reason} Tutti recuperano HP e Slot."))
    for p in getattr(game_state, "players", []):
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "DO_LONG_REST", "data": {}})
    game_state.ongoing_rest_vote = None
    game_state._trigger_gui_update()

def handle_long_rest_request(data, player, game_state):
    if getattr(game_state, "combat_active", False):
        from common.network_utils import send_message
        if getattr(player, "conn", None): send_message(player.conn, {"type": "ERROR_REPLY", "data": {"text": "Non puoi riposare durante il combattimento!"}})
        return
        
    players = getattr(game_state, "players", [])
    active_conns = len([p for p in players if getattr(p, "conn", None)])
    if active_conns == 0: return
        
    needed = max(1, math.ceil(active_conns / 2))
    game_state.ongoing_rest_vote = {"initiator": player.name, "votes_needed": needed, "total_conns": active_conns, "votes_received": 0, "votes_rejected": 0, "voters": set()}
    game_state.log_dm_message(f"[Sistema] {player.name} ha proposto un Riposo Lungo. Voti favorevoli necessari: {needed}/{active_conns}.")
    from common.network_utils import send_message
    for p in players:
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "PROMPT_LONG_REST_VOTE", "data": {"initiator": player.name}})

def handle_long_rest_vote(data, player, game_state):
    vote = data.get("vote", False)
    vote_data = getattr(game_state, "ongoing_rest_vote", None)
    if not vote_data: return
    voters = vote_data.setdefault("voters", set())
    if player.name in voters:
        return
    voters.add(player.name)
    
    if not vote:
        vote_data["votes_rejected"] = vote_data.get("votes_rejected", 0) + 1
        game_state.log_dm_message(f"[Sistema] {player.name} ha votato NO al riposo lungo.")
        if vote_data["votes_rejected"] > (vote_data["total_conns"] - vote_data["votes_needed"]):
            from common.protocol import make_chat_broadcast
            broadcast(game_state, make_chat_broadcast("Sistema", f"Il Riposo Lungo proposto da {vote_data['initiator']} e' stato respinto dalla maggioranza."))
            game_state.ongoing_rest_vote = None
        return
        
    vote_data["votes_received"] += 1
    if vote_data["votes_received"] >= vote_data["votes_needed"]:
        game_state.log_dm_message("[Sistema] La maggioranza dei giocatori ha approvato il Riposo Lungo!")
        trigger_group_long_rest(game_state, reason="Il gruppo ha approvato il Riposo Lungo!")

def handle_custom_spell_request(data, player, game_state):
    spell = data.get("spell", {})
    if not spell: return
    game_state.gui_queue.put({
        "type": "CUSTOM_SPELL_REQUEST",
        "player": player,
        "spell": spell
    })
    game_state.log_dm_message(f"[MAGIA] {player.name} richiede l'approvazione per l'incantesimo custom '{spell.get('name', 'Sconosciuto')}'.")

def handle_currency_request(data, player, game_state):
    coin = data.get("coin", "MO")
    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    reason = data.get("reason", "")
    if amount <= 0:
        return
    game_state.gui_queue.put({
        "type": "CURRENCY_REQUEST",
        "player": player,
        "coin": coin,
        "amount": amount,
        "reason": reason
    })
    game_state.log_dm_message(f"[VALUTA] {player.name} richiede {amount} {coin}. Motivazione: {reason or 'Nessuna'}")

def handle_item_approval_request(data, player, game_state):
    item = data.get("item", {})
    slot_idx = data.get("slot_idx")
    if not item or not isinstance(item, dict):
        return
    game_state.gui_queue.put({
        "type": "ITEM_APPROVAL_REQUEST",
        "player": player,
        "item": item,
        "slot_idx": slot_idx
    })
    game_state.log_dm_message(f"[OGGETTO] {player.name} richiede approvazione per '{item.get('name', 'Oggetto')}'.")


def handle_journal_approval_request(data, player, game_state):
    content = data.get("content", "")
    field_name = data.get("field_name", "journal_notes")
    title = data.get("title", "")
    game_state.gui_queue.put({
        "type": "JOURNAL_APPROVAL_REQUEST",
        "player": player,
        "field_name": field_name,
        "content": content,
        "title": title
    })
    field_disp = "Biografia & Diario" if "journal" in field_name else ("Privilegi & Tratti" if "features" in field_name else "Appunti / Note")
    game_state.log_dm_message(f"[DIARIO] {player.name} richiede l'approvazione per modificare {field_disp}.")
