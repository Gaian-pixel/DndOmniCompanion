import re
from common.protocol import *
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw
from common.network_utils import send_message, broadcast
import math
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
        
        dmg_val = old_hp - new_hp_unbounded
        if dmg_val > 0:
            _trigger_concentration_check(target_player, dmg_val, game_state)

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
    # Durations tracker
    current_player = game_state.get_current_turn_player()
    if current_player and hasattr(current_player, "condition_durations"):
        expired = []
        for cond, dur in list(current_player.condition_durations.items()):
            if dur > 0:
                current_player.condition_durations[cond] -= 1
                if current_player.condition_durations[cond] <= 0:
                    expired.append(cond)
        
        for cond in expired:
            if cond in current_player.conditions:
                current_player.conditions.remove(cond)
            del current_player.condition_durations[cond]
            game_state.log_dm_message(f"[EFFETTO TERMINATO] {cond} su {current_player.name}")
            from common.protocol import make_chat_broadcast, make_player_stats_update
            broadcast(game_state, make_chat_broadcast("Sistema", f"L'effetto '{cond}' su {current_player.name} e' svanito!"))
            broadcast(game_state, make_player_stats_update(current_player.name, current_player.hp, current_player.max_hp, current_player.initiative, current_player.conditions))
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
        from common.protocol import make_combat_state_update_broadcast
        next_name = next_p.name if next_p else ""
        broadcast(game_state, make_combat_state_update_broadcast(game_state.combat_active, game_state.turn_index, game_state.round_number, game_state.active_aoes, next_name))

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
    from common.protocol import make_map_data_update_broadcast
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
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
        adv_reasons = []
        dis_reasons = []
        flanking = False
        
        p_cond = getattr(player, "conditions", [])
        t_cond = getattr(target_player, "conditions", [])
        
        if "Invisibile" in p_cond: adv_reasons.append("Invisibile")
        for c in ["Trattenuto", "Paralizzato", "Incosciente", "Accecato", "Pietrificato"]:
            if c in t_cond: adv_reasons.append(f"Bersaglio {c}")
            
        for c in ["Accecato", "Avvelenato", "Trattenuto", "Prono"]:
            if c in p_cond: dis_reasons.append(c)
        if "Invisibile" in t_cond: dis_reasons.append("Bersaglio Invisibile")
        
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = target_player.position[0], target_player.position[1]
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            if "Prono" in t_cond:
                if dist <= 1: adv_reasons.append("Bersaglio Prono")
                elif dist > 1: dis_reasons.append("Bersaglio Prono")
            if dist <= 1:
                opp_q = q2 + (q2 - q1)
                opp_r = r2 + (r2 - r1)
                for p in getattr(game_state, "players", []):
                    if p.name != player.name and getattr(p, "hp", 0) > 0:
                        if hasattr(p, "position") and p.position and p.position[0] == opp_q and p.position[1] == opp_r:
                            p_c = getattr(p, "conditions", [])
                            if "Invisibile" not in p_c and "Nascosto" not in p_c:
                                adv_reasons.append("Fiancheggiamento")
                                flanking = True
                                break

        has_adv = len(adv_reasons) > 0
        has_dis = len(dis_reasons) > 0
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
        if has_adv:
            log_msg += f" Tiro con Vantaggio (causa: {', '.join(adv_reasons)})."
        elif has_dis:
            log_msg += f" Tiro con Svantaggio (causa: {', '.join(dis_reasons)})."
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
        else:
            log_msg += " MANCATO!"
            
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
    except Exception as e:
        send_message(player.conn, make_error_reply(f"Errore nell'attacco: {str(e)}"))

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
                from common.protocol import make_player_stats_update, make_chat_broadcast
                broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions))
                game_state._trigger_gui_update()
                
                break_msg = f"La concentrazione di {target_player.name} si spezza!"
                broadcast(game_state, make_chat_broadcast("Sistema", break_msg))
                game_state.log_dm_message(f"[TS] {break_msg}")
        
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

