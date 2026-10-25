import re
import random
import math
import threading
from common.protocol import *
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw, get_cover_between
from common.network_utils import send_message, broadcast
from common.dice import roll_dice
from common.i18n import is_condition_active

def _spawn_corpse_loot(target_player, game_state):
    """Spawna automaticamente un forziere con le spoglie sulla mappa quando un mostro o PNG muore a 0 HP."""
    if not game_state or not getattr(game_state, "current_map", None):
        return
    pos = getattr(target_player, "position", None)
    if not pos:
        return
    loots = game_state.current_map.setdefault("loots", [])
    loot_name = f"Spoglie di {target_player.name}"
    already_looted = any(l.get("q") == pos[0] and l.get("r") == pos[1] and l.get("item") == loot_name for l in loots)
    if not already_looted:
        loots.append({
            "q": pos[0],
            "r": pos[1],
            "item": loot_name,
            "qty": 1
        })
        msg = f"☠️ {target_player.name} è caduto! Un forziere con le sue spoglie è apparso sulla mappa."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[LOOT] {msg}")
        broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))

def drop_concentration(player, game_state, notify=True):
    """Interrompe la concentrazione di un personaggio (5e RAW) e rimuove le sue AoE attive collegate."""
    had_conc = False
    if hasattr(player, "conditions") and "Concentrazione" in player.conditions:
        player.conditions.remove("Concentrazione")
        had_conc = True
    if getattr(player, "full_sheet", None) and isinstance(player.full_sheet.get("conditions"), list):
        if "Concentrazione" in player.full_sheet["conditions"]:
            player.full_sheet["conditions"].remove("Concentrazione")
            had_conc = True

    removed_aoes = False
    if game_state and hasattr(game_state, "active_aoes"):
        for aoe in list(game_state.active_aoes):
            if aoe.get("caster") == player.name and aoe.get("concentration"):
                game_state.active_aoes.remove(aoe)
                removed_aoes = True
        if removed_aoes:
            broadcast(game_state, make_combat_state_update_broadcast(
                game_state.combat_active, game_state.turn_index, game_state.round_number, game_state.active_aoes
            ))

    if (had_conc or removed_aoes) and notify and game_state:
        break_msg = f"La concentrazione di {player.name} si spezza! Gli effetti ad essa legati svaniscono."
        broadcast(game_state, make_chat_broadcast("Sistema", break_msg))
        game_state.log_dm_message(f"[CONCENTRAZIONE] {break_msg}")


def apply_damage(target_player, raw_damage, damage_type="Tagliente", game_state=None):
    """
    Applica il danno secondo le regole D&D 5e:
    1. Resistenze, Immunità e Vulnerabilità (inclusa Ira Barbarica)
    2. Assorbimento Punti Ferita Temporanei (Temp HP) prima degli HP effettivi
    3. Morte istantanea (danno residuo >= HP max)
    4. Condizioni Incosciente/Prono o Morto per i mostri + drop spoglie
    5. Tiro Salvezza Concentrazione
    Ritorna: (danno_finale, note_moltiplicatore, temp_assorbiti, danno_a_hp)
    """
    if raw_damage <= 0:
        return 0, "", 0, 0
        
    dt = str(damage_type).strip().lower() if damage_type else "tagliente"
    
    # Mappatura bilingue per tipi di danno 5e
    damage_map = {
        "tagliente": ["tagliente", "slashing"], "slashing": ["tagliente", "slashing"],
        "perforante": ["perforante", "piercing"], "piercing": ["perforante", "piercing"],
        "contundente": ["contundente", "bludgeoning"], "bludgeoning": ["contundente", "bludgeoning"],
        "fuoco": ["fuoco", "fire"], "fire": ["fuoco", "fire"],
        "freddo": ["freddo", "cold"], "cold": ["freddo", "cold"],
        "fulmine": ["fulmine", "lightning"], "lightning": ["fulmine", "lightning"],
        "veleno": ["veleno", "poison"], "poison": ["veleno", "poison"],
        "acido": ["acido", "acid"], "acid": ["acido", "acid"],
        "psichico": ["psichico", "psychic"], "psychic": ["psichico", "psychic"],
        "necrotico": ["necrotico", "necrotic"], "necrotic": ["necrotico", "necrotic"],
        "radioso": ["radioso", "radiant"], "radiant": ["radioso", "radiant"],
        "forza": ["forza", "force"], "force": ["forza", "force"],
        "tuono": ["tuono", "thunder"], "thunder": ["tuono", "thunder"]
    }
    
    all_target_imm = [str(x).strip().lower() for x in getattr(target_player, "damage_immunities", [])]
    all_target_res = [str(x).strip().lower() for x in getattr(target_player, "damage_resistances", [])]
    all_target_vul = [str(x).strip().lower() for x in getattr(target_player, "damage_vulnerabilities", [])]
    
    # Ira Barbarica: resistenza ai danni fisici (tagliente, perforante, contundente)
    if "Ira" in getattr(target_player, "conditions", []):
        all_target_res.extend(["tagliente", "perforante", "contundente", "slashing", "piercing", "bludgeoning"])
        
    is_immune = any(dt in damage_map.get(k, [k]) for k in all_target_imm) or (dt in all_target_imm)
    is_resistant = any(dt in damage_map.get(k, [k]) for k in all_target_res) or (dt in all_target_res)
    is_vulnerable = any(dt in damage_map.get(k, [k]) for k in all_target_vul) or (dt in all_target_vul)
    
    note = ""
    if is_immune:
        multiplier = 0.0
        note = f" (Immune a {damage_type}: 0 danni!)"
    elif is_resistant and not is_vulnerable:
        multiplier = 0.5
        note = f" (Resistenza a {damage_type}: dimezzato)"
    elif is_vulnerable and not is_resistant:
        multiplier = 2.0
        note = f" (Vulnerabilità a {damage_type}: raddoppiato!)"
    else:
        multiplier = 1.0
        
    final_dmg = int(raw_damage * multiplier)
    
    # Assorbimento Punti Ferita Temporanei (Temp HP)
    cur_temp = getattr(target_player, "temp_hp", 0)
    temp_absorbed = 0
    if cur_temp > 0:
        temp_absorbed = min(cur_temp, final_dmg)
        target_player.temp_hp = cur_temp - temp_absorbed
        dmg_to_hp = final_dmg - temp_absorbed
    else:
        dmg_to_hp = final_dmg
        
    old_hp = target_player.hp
    new_hp_unbounded = old_hp - dmg_to_hp
    excess_damage = abs(new_hp_unbounded) if new_hp_unbounded < 0 else 0
    target_player.hp = max(0, new_hp_unbounded)
    
    is_npc = not hasattr(target_player, "conn") or target_player.conn is None
    auto_death = True
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        auto_death = game_state.automation_settings.get("auto_death_saves", True)
    
    if target_player.hp == 0:
        drop_concentration(target_player, game_state, notify=(not is_npc))
        if is_npc:
            if auto_death:
                if "Morto" not in getattr(target_player, "conditions", []):
                    if not hasattr(target_player, "conditions"): target_player.conditions = []
                    target_player.conditions.append("Morto")
                    _spawn_corpse_loot(target_player, game_state)
            else:
                msg = f"💀 {target_player.name} scende a 0 HP! (In attesa di verdetto DM: sconfitto/ucciso/arreso)"
                if game_state:
                    broadcast(game_state, make_chat_broadcast("Sistema", msg))
                    game_state.log_dm_message(f"[COMBAT] {msg}")
        else:
            if excess_damage >= target_player.max_hp and auto_death:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Morto" not in target_player.conditions:
                    target_player.conditions.append("Morto")
                    msg = f"!!! {target_player.name} E' MORTO SUL COLPO A CAUSA DI DANNO MASSICCIO ({excess_damage} in eccesso) !!!"
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
            else:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Incosciente" not in target_player.conditions:
                    target_player.conditions.append("Incosciente")
                if "Prono" not in target_player.conditions:
                    target_player.conditions.append("Prono")
                if old_hp == 0 and dmg_to_hp > 0:
                    if not hasattr(target_player, "death_saves") or not isinstance(target_player.death_saves, dict):
                        target_player.death_saves = {"successes": 0, "failures": 0}
                    fail_add = 1
                    target_player.death_saves["failures"] += fail_add
                    msg = f"💀 {target_player.name} subisce danni mentre è a 0 HP! Segna {fail_add} fallimento/i nel TS contro la morte (Totale: {target_player.death_saves['failures']}/3)!"
                    if target_player.death_saves["failures"] >= 3:
                        if not hasattr(target_player, "conditions"): target_player.conditions = []
                        if "Morto" not in target_player.conditions:
                            target_player.conditions.append("Morto")
                        msg += f" ⚰️ {target_player.name} ha accumulato 3 fallimenti ed è MORTO!"
                        _spawn_corpse_loot(target_player, game_state)
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
    elif target_player.hp > 0:
        if old_hp == 0:
            if "Incosciente" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Incosciente")
            if "Stabilizzato" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Stabilizzato")
            if hasattr(target_player, "death_saves") and isinstance(target_player.death_saves, dict):
                target_player.death_saves = {"successes": 0, "failures": 0}
            
    # Concentrazione 5e (si attiva quando si subiscono danni)
    if final_dmg > 0 and game_state:
        _trigger_concentration_check(target_player, final_dmg, game_state)
        
    return final_dmg, note, temp_absorbed, dmg_to_hp

def _apply_hp_change(target_player, new_hp_unbounded, game_state):
    """Gestisce variazioni dirette di HP (cure, comandi DM o statistiche)."""
    old_hp = target_player.hp
    excess_damage = 0
    if new_hp_unbounded < 0:
        excess_damage = abs(new_hp_unbounded)
    
    target_player.hp = max(0, min(target_player.max_hp, new_hp_unbounded))
    is_npc = not hasattr(target_player, "conn") or target_player.conn is None
    
    if target_player.hp == 0:
        drop_concentration(target_player, game_state, notify=(not is_npc))
        if is_npc:
            if "Morto" not in getattr(target_player, "conditions", []):
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                target_player.conditions.append("Morto")
                _spawn_corpse_loot(target_player, game_state)
        else:
            if excess_damage >= target_player.max_hp:
                if "Morto" not in getattr(target_player, "conditions", []):
                    if not hasattr(target_player, "conditions"): target_player.conditions = []
                    target_player.conditions.append("Morto")
                    msg = f"!!! {target_player.name} E' MORTO SUL COLPO A CAUSA DI DANNO MASSICCIO !!!"
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
            else:
                if not hasattr(target_player, "conditions"): target_player.conditions = []
                if "Incosciente" not in target_player.conditions:
                    target_player.conditions.append("Incosciente")
                if "Prono" not in target_player.conditions:
                    target_player.conditions.append("Prono")
                if old_hp == 0 and new_hp_unbounded < 0:
                    if not hasattr(target_player, "death_saves") or not isinstance(target_player.death_saves, dict):
                        target_player.death_saves = {"successes": 0, "failures": 0}
                    target_player.death_saves["failures"] += 1
                    msg = f"💀 {target_player.name} subisce danni mentre è a 0 HP! Segna 1 fallimento nel TS contro la morte (Totale: {target_player.death_saves['failures']}/3)!"
                    if target_player.death_saves["failures"] >= 3:
                        if not hasattr(target_player, "conditions"): target_player.conditions = []
                        if "Morto" not in target_player.conditions:
                            target_player.conditions.append("Morto")
                        msg += f" ⚰️ {target_player.name} ha accumulato 3 fallimenti ed è MORTO!"
                        _spawn_corpse_loot(target_player, game_state)
                    if game_state:
                        broadcast(game_state, make_chat_broadcast("Sistema", msg))
                        game_state.log_dm_message(msg)
    elif target_player.hp > 0:
        if old_hp == 0:
            if "Incosciente" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Incosciente")
            if "Stabilizzato" in getattr(target_player, "conditions", []):
                target_player.conditions.remove("Stabilizzato")
            if hasattr(target_player, "death_saves") and isinstance(target_player.death_saves, dict):
                target_player.death_saves = {"successes": 0, "failures": 0}
        
        dmg_val = old_hp - new_hp_unbounded
        if dmg_val > 0 and game_state:
            _trigger_concentration_check(target_player, dmg_val, game_state)

def handle_start_combat_request(data, player, game_state):
    initiator_name = data.get("initiator")
    game_state.gui_queue.put({"type": "SHOW_COMBAT_CONFIG", "payload": {"initiator": initiator_name}})

def _trigger_concentration_check(target_player, dmg_val, game_state):
    if dmg_val > 0 and is_condition_active(getattr(target_player, "conditions", []), "Concentrazione"):
        dc = max(10, dmg_val // 2)
        auto_conc = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_conc = game_state.automation_settings.get("auto_concentration_check", True)
        if not auto_conc:
            msg = f"⚠️ {target_player.name} subisce danni mentre è concentrato! Richiesto TS Costituzione CD {dc} (Gestione DM)."
            broadcast(game_state, make_chat_broadcast("Sistema", msg))
            game_state.log_dm_message(f"[CONCENTRAZIONE] {msg}")
            return
            
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save("COS", dc, "", False, "Sistema (Concentrazione)", "Contundente"))
        else:
            mod = 0
            if target_player.full_sheet:
                attr = target_player.full_sheet.get("attributes", {})
                if "COS" in attr:
                    try:
                        mod = (int(attr["COS"]) - 10) // 2
                    except (ValueError, TypeError):
                        pass
            mod_str = f"+{mod}" if mod >= 0 else str(mod)
            save_result = roll_dice(f"1d20{mod_str}")
            roll_tot = save_result["total"]
            is_crit = save_result["rolls"][0] == 20
            is_fail = save_result["rolls"][0] == 1
            threading.Timer(0.1, _process_save_result, args=(target_player.name, "COS", roll_tot, is_crit, is_fail, dc, "", False, "Sistema (Concentrazione)", game_state, "Contundente")).start()

def handle_end_turn_request(data, player, game_state):
    current = game_state.get_current_turn_player()
    if current and current.name == player.name:
        # Durations tracker
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
                msg = f"L'effetto di '{cond}' su {current.name} è terminato."
                game_state.log_dm_message(f"[SISTEMA] {msg}")
                broadcast(game_state, make_chat_broadcast("Sistema", msg))
                
            if expired:
                broadcast(game_state, make_player_stats_update(current.name, current.hp, current.max_hp, current.initiative, current.conditions, getattr(current, "temp_hp", 0)))
                game_state._trigger_gui_update()

        # Rimuovi condizioni temporanee di fine turno (Scatto, Disimpegno). Schivata resta fino all'inizio del prossimo turno!
        changed_temp = False
        for temp_c in ["Scatto", "Disimpegno", "Dash", "Disengage"]:
            if temp_c in getattr(current, "conditions", []):
                current.conditions.remove(temp_c)
                changed_temp = True
                
        if changed_temp:
            broadcast(game_state, make_player_stats_update(current.name, current.hp, current.max_hp, current.initiative, current.conditions, getattr(current, "temp_hp", 0)))
            game_state._trigger_gui_update()

        game_state.next_turn()
        next_p = game_state.get_current_turn_player()
        if next_p:
            # Broadcast delle condizioni aggiornate di next_p (es. rimozione automatica di Schivata a inizio turno)
            broadcast(game_state, make_player_stats_update(next_p.name, next_p.hp, next_p.max_hp, next_p.initiative, getattr(next_p, "conditions", []), getattr(next_p, "temp_hp", 0)))
            # D&D 5e: Le creature leggendarie recuperano le loro azioni leggendarie all'inizio del proprio turno
            if getattr(next_p, "legendary_actions_max", 0) > 0:
                next_p.legendary_actions_current = next_p.legendary_actions_max
                game_state._trigger_gui_update()
            msg = f"Round {game_state.round_number} - Turno di {next_p.name}!"
            game_state.log_dm_message(f"[COMBAT] {msg}")
            broadcast(game_state, make_chat_broadcast("Sistema", msg))

            # D&D 5e Lair Actions: Se c'è una creatura con Azione di Tana a inizio round (Iniziativa 20)
            has_lair_boss = any(getattr(p, "has_lair_actions", False) for p in game_state.players)
            if has_lair_boss and game_state.turn_index == 0:
                lair_msg = "🏰 [AZIONE DI TANA - Iniziativa 20] La tana del Boss risponde alla volontà del suo padrone! Il DM può attivare un'Azione di Tana."
                broadcast(game_state, make_chat_broadcast("Sistema", lair_msg))
                game_state.log_dm_message(f"[BOSS] {lair_msg}")

            # Notifica al DM per Azioni Leggendarie disponibili a fine turno altrui
            for p in game_state.players:
                if getattr(p, "legendary_actions_max", 0) > 0 and getattr(p, "legendary_actions_current", 0) > 0 and p.name != (next_p.name if next_p else ""):
                    game_state.log_dm_message(f"[BOSS] 👑 {p.name} può usare un'Azione Leggendaria ({p.legendary_actions_current}/{p.legendary_actions_max} disponibili)!")

        next_name = next_p.name if next_p else ""
        broadcast(game_state, make_combat_state_update_broadcast(game_state.combat_active, game_state.turn_index, game_state.round_number, game_state.active_aoes, next_name))


def handle_spend_legendary_action_request(data, player, game_state):
    """
    Gestisce la spesa di Azioni Leggendarie (D&D 5e).
    Un boss leggendario spende azioni tra un turno e l'altro (costo solitamente 1, 2 o 3).
    """
    target_name = data.get("boss_name") or data.get("target_name") or (player.name if player else "")
    action_name = data.get("action_name", "Azione Leggendaria")
    cost = int(data.get("cost", 1))
    
    boss = game_state.find_player(target_name)
    if not boss:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Creatura '{target_name}' non trovata."))
        return
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    if not is_dm and boss.name != player.name and getattr(boss, "owner", None) != player.name:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Solo il DM può attivare le Azioni Leggendarie di un Boss."))
        return
        
    cur_actions = getattr(boss, "legendary_actions_current", 0)
    max_actions = getattr(boss, "legendary_actions_max", 0)
    
    if cur_actions < cost:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Azioni leggendarie insufficienti: {cur_actions}/{max_actions} (richieste: {cost})."))
        return
        
    boss.legendary_actions_current = cur_actions - cost
    msg = f"👑 {boss.name} usa l'Azione Leggendaria '{action_name}' (Costo: {cost})! Azioni rimaste: {boss.legendary_actions_current}/{max_actions}."
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[BOSS] {msg}")
    game_state._trigger_gui_update()

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
    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
    game_state.log_dm_message(f"[COMBAT] {player.name} tira iniziativa: {init}")

def handle_attack_request(data, player, game_state):
    target_name = data.get("target_name")
    weapon_name = data.get("weapon_name", "Attacco")
    hit_bonus = data.get("hit_bonus", 0)
    damage_formula = data.get("damage_formula")
    damage_type = data.get("damage_type", "Tagliente")
    
    target_player = game_state.find_player(target_name)
    if not target_player: return

    p_cond = getattr(player, "conditions", [])
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi attaccare mentre sei Incosciente, Paralizzato o a 0 HP!"))
        return

    strict_lock = False
    if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
        strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
    else:
        strict_lock = getattr(game_state, "strict_turn_lock", False)

    is_reaction = data.get("is_reaction", False)
    if getattr(game_state, "combat_active", False) and strict_lock and not is_reaction:
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and curr_turn.name != player.name:
            if player and getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return
    
    try:
        # 1. Roll to Hit
        adv_reasons = []
        dis_reasons = []
        
        t_cond = getattr(target_player, "conditions", [])
        
        # Vantaggio per l'attaccante
        if is_condition_active(p_cond, "Invisibile"): adv_reasons.append("Invisibile")
        for c in ["Trattenuto", "Paralizzato", "Incosciente", "Accecato", "Pietrificato", "Stordito"]:
            if is_condition_active(t_cond, c): adv_reasons.append(f"Bersaglio {c}")
            
        # Azione di Aiuto: il bersaglio ha 'Aiutato', che conferisce vantaggio al primo attacco alleato
        if is_condition_active(t_cond, "Aiutato"):
            adv_reasons.append("Aiuto Alleato")
            if "Aiutato" in t_cond: t_cond.remove("Aiutato")
            elif "Helped" in t_cond: t_cond.remove("Helped")
            
        # Svantaggio per l'attaccante
        for c in ["Accecato", "Avvelenato", "Trattenuto", "Prono", "Spaventato"]:
            if is_condition_active(p_cond, c): dis_reasons.append(c)
        if is_condition_active(t_cond, "Invisibile"): dis_reasons.append("Bersaglio Invisibile")
        if is_condition_active(t_cond, "Schivata"): dis_reasons.append("Bersaglio in Schivata")
        
        # Indebolimento (Exhaustion) Lv 3+ impone svantaggio a tiri per colpire
        if getattr(player, "exhaustion_level", 0) >= 3:
            dis_reasons.append("Indebolimento Lv3+")
        
        # Gestione distanza e Prono / Fiancheggiamento
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = target_player.position[0], target_player.position[1]
            dist = max(abs(q1 - q2), abs(q1 + r1 - q2 - r2), abs(r1 - r2))
            if is_condition_active(t_cond, "Prono"):
                if dist <= 1: adv_reasons.append("Bersaglio Prono (Mischia)")
                elif dist > 1: dis_reasons.append("Bersaglio Prono (Distanza)")
            if dist <= 1:
                opp_q = q2 + (q2 - q1)
                opp_r = r2 + (r2 - r1)
                attacker_party = bool(getattr(player, "is_party_member", False) or getattr(player, "conn", None))
                target_party = bool(getattr(target_player, "is_party_member", False) or getattr(target_player, "conn", None))
                for p in getattr(game_state, "players", []):
                    if p.name != player.name and getattr(p, "hp", 0) > 0:
                        if hasattr(p, "position") and p.position and p.position[0] == opp_q and p.position[1] == opp_r:
                            p_c = getattr(p, "conditions", [])
                            p_party = bool(getattr(p, "is_party_member", False) or getattr(p, "conn", None))
                            is_ally = (p_party == attacker_party) if attacker_party != target_party else True
                            incapacitated = any(is_condition_active(p_c, c) for c in ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"])
                            if is_ally and not incapacitated and "Invisibile" not in p_c and "Nascosto" not in p_c:
                                adv_reasons.append("Fiancheggiamento")
                                break

            # Effetti Atmosferici D&D 5e (DMG p. 109-110)
            weather_val = str(getattr(game_state, "weather", "Sereno")).strip().lower()
            if weather_val in ("tempesta", "storm"):
                if dist > 1:
                    dis_reasons.append("Tempesta (Vento forte e pioggia battente)")
            elif weather_val in ("nebbia", "fog"):
                if dist > 1:
                    dis_reasons.append("Nebbia fitta (Visibilità pesantemente oscurata)")
            elif weather_val in ("pioggia", "rain"):
                if dist >= 4:
                    dis_reasons.append("Pioggia intensa (Scarsa visibilità)")
            elif weather_val in ("neve", "snow"):
                if dist >= 3:
                    dis_reasons.append("Neve e bufera (Scarsa visibilità)")

            # Oscurità Ambientale o Magica (D&D 5e PHB p. 183 & p. 194-195)
            is_global_darkness = weather_val in ("oscurita", "oscurità", "darkness", "buio")
            in_magical_darkness_aoe = False
            for aoe in getattr(game_state, "active_aoes", []):
                aoe_name = str(aoe.get("name", "")).lower()
                aoe_type = str(aoe.get("type", "")).lower()
                if "oscurit" in aoe_name or "darkness" in aoe_name or aoe_type == "darkness":
                    aoe_orig = aoe.get("origin", [0, 0])
                    aoe_r = aoe.get("size", 3)
                    d_att = max(abs(q1 - aoe_orig[0]), abs(q1 + r1 - aoe_orig[0] - aoe_orig[1]), abs(r1 - aoe_orig[1]))
                    d_def = max(abs(q2 - aoe_orig[0]), abs(q2 + r2 - aoe_orig[0] - aoe_orig[1]), abs(r2 - aoe_orig[1]))
                    if d_att <= aoe_r or d_def <= aoe_r:
                        in_magical_darkness_aoe = True
                        break

            if is_global_darkness or in_magical_darkness_aoe:
                def is_illuminated(pos_q, pos_r, entity_obj):
                    if getattr(entity_obj, "light_radius", 0) > 0:
                        return True
                    for other in getattr(game_state, "players", []):
                        if getattr(other, "light_radius", 0) > 0 and getattr(other, "position", None):
                            d_l = max(abs(pos_q - other.position[0]), abs(pos_q + pos_r - other.position[0] - other.position[1]), abs(pos_r - other.position[1]))
                            if d_l <= other.light_radius:
                                return True
                    return False

                att_in_light = is_illuminated(q1, r1, player)
                def_in_light = is_illuminated(q2, r2, target_player)

                def entity_has_darkvision(entity_obj):
                    if in_magical_darkness_aoe:
                        conds = [str(c).lower() for c in getattr(entity_obj, "conditions", [])]
                        sheet = getattr(entity_obj, "full_sheet", None) or {}
                        feats = [str(f).lower() for f in sheet.get("features", [])]
                        traits = [str(t).lower() for t in sheet.get("traits", [])]
                        all_text = " ".join(conds + feats + traits)
                        return "vista del diavolo" in all_text or "devil's sight" in all_text or "truesight" in all_text or "visione del vero" in all_text
                    
                    if getattr(entity_obj, "has_darkvision", None) is not None:
                        return bool(entity_obj.has_darkvision)
                    conds = [str(c).lower() for c in getattr(entity_obj, "conditions", [])]
                    if any("scurovisione" in c or "darkvision" in c for c in conds):
                        return True
                    sheet = getattr(entity_obj, "full_sheet", None)
                    if isinstance(sheet, dict):
                        race = str(sheet.get("race", "")).lower()
                        dv_races = ("elfo", "elf", "nano", "dwarf", "mezzelfo", "half-elf", "mezzorco", "half-orc", "gnomo", "gnome", "tiefling", "drow", "duergar", "dragonide")
                        if any(r in race for r in dv_races):
                            return True
                        senses = str(sheet.get("senses", "")).lower()
                        if "scurovisione" in senses or "darkvision" in senses:
                            return True
                        traits = [str(t).lower() for t in sheet.get("traits", [])]
                        if any("scurovisione" in t or "darkvision" in t for t in traits):
                            return True
                        feats = [str(f).lower() for f in sheet.get("features", [])]
                        if any("scurovisione" in f or "darkvision" in f for f in feats):
                            return True
                    return getattr(entity_obj, "vision_radius", 6) > 6

                att_has_dv = entity_has_darkvision(player)
                def_has_dv = entity_has_darkvision(target_player)

                att_dv_range = getattr(player, "vision_radius", 12)
                def_dv_range = getattr(target_player, "vision_radius", 12)

                att_sees_def = def_in_light or (att_has_dv and dist <= att_dv_range)
                def_sees_att = att_in_light or (def_has_dv and dist <= def_dv_range)

                if not att_sees_def and not def_sees_att:
                    # Entrambi nel buio: vantaggio e svantaggio si annullano
                    dis_reasons.append("Bersaglio non visibile al buio")
                    adv_reasons.append("Attaccante celato nel buio")
                elif att_sees_def and not def_sees_att:
                    # Attaccante vede ma bersaglio non lo vede -> Vantaggio
                    adv_reasons.append("Attaccante Invisibile nell'Oscurità (Scurovisione/Luce)")
                elif not att_sees_def and def_sees_att:
                    # Bersaglio vede l'attaccante ma l'attaccante non vede il bersaglio -> Svantaggio
                    dis_reasons.append("Bersaglio Non Visibile nell'Oscurità (Attaccante Cieco)")

            # Terreni Difficili & Pericolosi D&D 5e sulla mappa
            cur_map = getattr(game_state, "current_map", None)
            diff_terrain = cur_map.get("difficult_terrain", {}) if cur_map else {}
            diff_dict = {}
            if isinstance(diff_terrain, dict):
                for k, v in diff_terrain.items():
                    if isinstance(k, str) and "," in k:
                        parts = k.split(",")
                        diff_dict[(int(parts[0]), int(parts[1]))] = str(v).lower()
                    elif isinstance(k, (tuple, list)) and len(k) >= 2:
                        diff_dict[(int(k[0]), int(k[1]))] = str(v).lower()
            elif isinstance(diff_terrain, list):
                for item in diff_terrain:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        diff_dict[(int(item[0]), int(item[1]))] = "fango"

            # Attaccante su terreno difficile instabile / intralciante
            p_pos_tup = (q1, r1)
            if p_pos_tup in diff_dict:
                t_type = diff_dict[p_pos_tup]
                if t_type in ("ghiaccio", "ice"):
                    dis_reasons.append("Terreno Scivoloso (Ghiaccio)")
                elif t_type in ("rovi", "briars", "spine"):
                    dis_reasons.append("Intralcio nei Rovi")
                elif t_type in ("palude", "swamp"):
                    dis_reasons.append("Immerso nella Palude")
                elif t_type in ("macerie", "rubble", "rocce"):
                    dis_reasons.append("Equilibrio Instabile (Macerie)")
                elif t_type in ("fango", "mud"):
                    dis_reasons.append("Fango Profondo")

            # Bersaglio intralciato su terreno difficile
            t_pos_tup = (q2, r2)
            if t_pos_tup in diff_dict:
                t_target_type = diff_dict[t_pos_tup]
                if t_target_type in ("rovi", "briars", "spine"):
                    adv_reasons.append("Bersaglio Intralciato nei Rovi")
                elif t_target_type in ("fango", "mud"):
                    adv_reasons.append("Bersaglio Bloccato nel Fango")

        has_adv = len(adv_reasons) > 0
        has_dis = len(dis_reasons) > 0
        had_both_cancel = False
        if has_adv and has_dis:
            has_adv = False
            has_dis = False
            had_both_cancel = True
            
        auto_calc_adv = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_calc_adv = game_state.automation_settings.get("auto_calc_advantage", True)

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)
        if auto_calc_adv and has_adv:
            base_roll = max(roll1, roll2)
            d20_detail = f"max({roll1}, {roll2})={base_roll}"
        elif auto_calc_adv and has_dis:
            base_roll = min(roll1, roll2)
            d20_detail = f"min({roll1}, {roll2})={base_roll}"
        else:
            base_roll = roll1
            d20_detail = str(base_roll)
            
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
        
        # 2. CA Bersaglio
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
                
        # Line of Sight e Copertura D&D 5e (Ostacoli e Creature Interposte)
        blocked_by_wall = False
        cover_bonus = 0
        cover_name = None
        
        if hasattr(player, "position") and player.position and hasattr(target_player, "position") and target_player.position:
            p_hex = Hex(player.position[0], player.position[1])
            t_hex = Hex(target_player.position[0], target_player.position[1])
            line = hex_linedraw(p_hex, t_hex)
            
            if getattr(game_state, "current_map", None):
                from server.rules.movement import get_effective_map_walls
                walls = get_effective_map_walls(game_state.current_map)
                for step in line[1:]:
                    if [step.q, step.r] in walls:
                        blocked_by_wall = True
                        break
                
                if not blocked_by_wall:
                    half_cover = game_state.current_map.get("half_cover", [])
                    three_quarters = game_state.current_map.get("three_quarters_cover", [])
                    other_creatures = [
                        p for p in game_state.players 
                        if p.name != player.name and p.name != target_player.name and getattr(p, "position", None)
                        and getattr(p, "hp", 1) > 0 and "Morto" not in getattr(p, "conditions", [])
                        and getattr(p, "layer", "token") != "gm"
                    ]
                    cover_bonus, cover_name = get_cover_between(p_hex, t_hex, half_cover, three_quarters, other_creatures)

        # Copertura Tattica D&D 5e RAW esplicita inviata dal client o dal DM
        explicit_cover = str(data.get("cover", "auto")).lower()
        if explicit_cover in ("total", "totale"):
            blocked_by_wall = True
            cover_name = "Copertura Totale"
        elif explicit_cover in ("half", "mezza"):
            cover_bonus = 2
            cover_name = "Mezza Copertura (+2 CA)"
        elif explicit_cover in ("three_quarters", "3/4", "tre_quarti"):
            cover_bonus = 5
            cover_name = "Tre Quarti di Copertura (+5 CA)"
        elif explicit_cover in ("none", "nessuna"):
            cover_bonus = 0
            cover_name = None

        if cover_bonus > 0 and not blocked_by_wall:
            target_ac += cover_bonus
                
        hits = (is_crit or (not is_fail and hit_roll >= target_ac)) and not blocked_by_wall
        
        log_msg = f"{player.name} attacca {target_name} con {weapon_name}."
        if has_adv:
            log_msg += f" Tiro con Vantaggio (causa: {', '.join(adv_reasons)})."
        elif has_dis:
            log_msg += f" Tiro con Svantaggio (causa: {', '.join(dis_reasons)})."
        elif had_both_cancel:
            log_msg += f" Tiro Normale (Vantaggio e Svantaggio si annullano: {', '.join(adv_reasons)} vs {', '.join(dis_reasons)})."
        log_msg += f" Tiro per colpire: {hit_roll} [d20: {d20_detail}]"
        if benedizione_bonus > 0:
            log_msg += f" (+{benedizione_bonus} Benedizione)"
        log_msg += f" vs CA {target_ac}."
        if scudo_applicato:
            log_msg += " (Scudo +5 CA applicato)"
        if cover_name and cover_bonus > 0:
            log_msg += f" ({cover_name})"
        
        if blocked_by_wall:
            if cover_name == "Copertura Totale":
                log_msg += " ATTACCO BLOCCATO: Bersaglio protetto da Copertura Totale!"
            else:
                log_msg += " Bloccato dal Muro."
        elif hits:

            log_msg += " COLPITO!"
            # Regola D&D 5e RAW: Qualsiasi attacco a segno entro 1.5m su bersaglio Incosciente o Paralizzato e' un critico automatico!
            if not is_crit and dist <= 1 and any(is_condition_active(t_cond, c) for c in ["Incosciente", "Paralizzato", "Unconscious", "Paralyzed"]):
                is_crit = True
                log_msg += " 🌟 (CRITICO AUTOMATICO: Bersaglio Incosciente/Paralizzato entro 1.5m!)"
            elif is_crit:
                log_msg += " 🌟 (CRITICO! 20 Naturale - Dadi danno raddoppiati!)"
            if damage_formula:
                dmg_result = roll_dice(damage_formula, is_crit=is_crit)
                dmg_val = max(0, dmg_result["total"])
                
                # Bonus danno Ira Barbarica (+2 per attacchi in mischia)
                if "Ira" in getattr(player, "conditions", []):
                    dmg_val += 2
                    log_msg += " (+2 Ira Barbarica)"

                # Regola D&D 5e: Attacco Furtivo del Ladro (Sneak Attack)
                # Requisiti: classe Ladro, arma accurata/distanza, vantaggio OPPURE alleato entro 1 esagono senza svantaggio, max 1 volta per turno
                is_rogue = False
                rogue_lvl = 1
                if getattr(player, "full_sheet", None) or hasattr(player, "char_class"):
                    sheet = getattr(player, "full_sheet", {}) or {}
                    cls_name = str(sheet.get("class", sheet.get("char_class", getattr(player, "char_class", "")))).lower()
                    feat_obj = sheet.get("features", getattr(player, "features", []))
                    features_str = " ".join(str(f).lower() for f in feat_obj) if isinstance(feat_obj, list) else str(feat_obj).lower()
                    if "ladro" in cls_name or "rogue" in cls_name or "furtivo" in features_str or "sneak" in features_str:
                        is_rogue = True
                        try:
                            rogue_lvl = int(sheet.get("level", getattr(player, "level", 1)))
                        except (ValueError, TypeError):
                            rogue_lvl = 1

                if is_rogue and not getattr(player, "sneak_attack_used_this_turn", False):
                    has_adjacent_ally = False
                    if hasattr(target_player, "position") and target_player.position:
                        tq, tr = target_player.position[0], target_player.position[1]
                        for other in getattr(game_state, "players", []):
                            if other.name != player.name and other.name != target_player.name and getattr(other, "hp", 0) > 0:
                                if hasattr(other, "position") and other.position:
                                    oq, or_ = other.position[0], other.position[1]
                                    d_o = max(abs(tq - oq), abs(tq + tr - oq - or_), abs(tr - or_))
                                    if d_o <= 1 and "Incosciente" not in getattr(other, "conditions", []) and "Morto" not in getattr(other, "conditions", []):
                                        has_adjacent_ally = True
                                        break
                    
                    if has_adv or (has_adjacent_ally and not has_dis):
                        sneak_dice_count = max(1, math.ceil(rogue_lvl / 2))
                        sneak_formula = f"{sneak_dice_count}d6"
                        s_res = roll_dice(sneak_formula, is_crit=is_crit)
                        sneak_dmg = s_res["total"]
                        dmg_val += sneak_dmg
                        player.sneak_attack_used_this_turn = True
                        log_msg += f" 🗡️ (+{sneak_dmg} Attacco Furtivo [{sneak_formula}])"
                    
                auto_apply = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    auto_apply = game_state.automation_settings.get("auto_apply_damage", True)

                if auto_apply:
                    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, dmg_val, damage_type, game_state)
                    log_msg += f" Danno: {final_dmg} ({damage_type}){note}."
                    if temp_absorbed > 0:
                        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
                    log_msg += f" HP {target_name}: {target_player.hp}/{target_player.max_hp}"
                    if getattr(target_player, "temp_hp", 0) > 0:
                        log_msg += f" (+{target_player.temp_hp} Temp)"
                    
                    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
                    game_state._trigger_gui_update()
                else:
                    import uuid
                    pending_id = f"dmg_{uuid.uuid4().hex[:8]}"
                    pending_info = {
                        "id": pending_id,
                        "attacker": player.name,
                        "target": target_name,
                        "raw_damage": dmg_val,
                        "damage_type": damage_type,
                        "is_crit": is_crit,
                        "weapon_name": weapon_name
                    }
                    if not hasattr(game_state, "pending_damages"):
                        game_state.pending_damages = {}
                    game_state.pending_damages[pending_id] = pending_info
                    
                    log_msg += f" 🎯 Danno Calcolato: {dmg_val} ({damage_type}). [In attesa di conferma DM]"
                    if hasattr(game_state, "gui_queue") and game_state.gui_queue:
                        game_state.gui_queue.put({"type": "PENDING_DAMAGE_PROMPT", "payload": pending_info})
                    game_state._trigger_gui_update()
        else:
            if is_fail:
                log_msg += " 💀 MANCATO! (FALLIMENTO CRITICO - 1 Naturale!)"
            else:
                log_msg += " MANCATO!"
            
        game_state.log_dm_message(f"[COMBAT] {log_msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", log_msg))
        
    except Exception as e:
        send_message(player.conn, make_error_reply(f"Errore nell'attacco: {str(e)}"))

def _process_save_result(target_name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state, damage_type="Fuoco", cover="none"):
    if hasattr(target_name, "name"):
        target_player = target_name
        target_name = target_player.name
    else:
        target_player = game_state.find_player(target_name)
    if not target_player: return
    
    benedizione_bonus = 0
    if "Benedizione" in getattr(target_player, "conditions", []):
        benedizione_bonus = random.randint(1, 4)
        roll_total += benedizione_bonus
        
    extra_adv_note = ""
    if stat in ("DES", "DEX"):
        if "Schivata" in getattr(target_player, "conditions", []):
            extra_adv_note += " (Vantaggio da Schivata)"
        cover_val = str(cover).lower()
        if cover_val in ("half", "mezza"):
            roll_total += 2
            extra_adv_note += " (+2 TS Mezza Copertura)"
        elif cover_val in ("three_quarters", "3/4", "tre_quarti"):
            roll_total += 5
            extra_adv_note += " (+5 TS Tre Quarti di Copertura)"


    # Regola 5e: Creature Incoscienti, Paralizzate o Stordite falliscono automaticamente i TS su Forza e Destrezza
    auto_fail_cond = None
    if stat in ("FOR", "DES", "STR", "DEX"):
        for c in ["Incosciente", "Paralizzato", "Stordito", "Pietrificato"]:
            if is_condition_active(getattr(target_player, "conditions", []), c):
                auto_fail_cond = c
                break

    if auto_fail_cond:
        success = False
        extra_adv_note += f" (Fallimento automatico per condizione: {auto_fail_cond})"
    else:
        success = is_crit or (not is_fail and roll_total >= dc)
    
    # D&D 5e: Resistenze Leggendarie (es. 3/giorno)
    # Se la creatura fallisce un TS, può scegliere di considerarlo automaticamente un successo.
    used_legendary_resistance = False
    if not success and getattr(target_player, "legendary_resistances_current", 0) > 0:
        target_player.legendary_resistances_current -= 1
        success = True
        used_legendary_resistance = True
        if game_state:
            game_state._trigger_gui_update()
    
    log_msg = f"{target_name} effettua un TS su {stat} contro CD {dc} di {source_name}. Risultato: {roll_total}{extra_adv_note}"
    if benedizione_bonus > 0:
        log_msg += f" (+{benedizione_bonus} Benedizione)"
    log_msg += "."
    if used_legendary_resistance:
        if is_fail:
            log_msg += " (1 Naturale annullato!)"
        log_msg += f" 👑 RESISTENZA LEGGENDARIA USATA! Il fallimento si trasforma in SUCCESSO! (Rimaste: {target_player.legendary_resistances_current}/{target_player.legendary_resistances_max})"
    elif success:
        if is_crit:
            log_msg += " 🌟 SUCCESSO CRITICO (20 Naturale)! SUPERATO!"
        else:
            log_msg += " SUPERATO!"
    else:
        if is_fail:
            log_msg += " 💀 FALLIMENTO CRITICO (1 Naturale)! FALLITO!"
        else:
            log_msg += " FALLITO!"
        if source_name == "Sistema (Concentrazione)":
            drop_concentration(target_player, game_state, notify=True)
            broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
            game_state._trigger_gui_update()
        
    if damage_formula:
        try:
            clean_dmg = str(damage_formula).strip()
            if clean_dmg.isdigit():
                dmg_val = int(clean_dmg)
            else:
                dmg_res = roll_dice(clean_dmg)
                dmg_val = dmg_res["total"]
            
            # Elusione (Evasion) D&D 5e: Ladro/Monaco su TS Destrezza
            has_evasion = False
            if stat in ("DES", "DEX") and target_player:
                tokens = [str(c) for c in getattr(target_player, "conditions", [])]
                feat_obj = getattr(target_player, "features", [])
                if isinstance(feat_obj, list):
                    tokens.extend([str(f) for f in feat_obj])
                elif isinstance(feat_obj, str) and feat_obj:
                    tokens.append(feat_obj)
                sheet = getattr(target_player, "full_sheet", None)
                if isinstance(sheet, dict):
                    sf = sheet.get("features", [])
                    if isinstance(sf, list):
                        tokens.extend([str(f) for f in sf])
                    elif isinstance(sf, str) and sf:
                        tokens.append(sf)
                p_text = " ".join(tokens).lower()
                if "elusione" in p_text or "evasion" in p_text:
                    has_evasion = True

            if success:
                if has_evasion:
                    dmg_val = 0
                    log_msg += " (Elusione 5e: 0 danni con TS superato!)"
                elif half_on_success:
                    dmg_val = dmg_val // 2
                else:
                    dmg_val = 0
            else:
                if has_evasion and half_on_success:
                    dmg_val = dmg_val // 2
                    log_msg += " (Elusione 5e: subisce solo metà danni nonostante il TS fallito!)"
                    
            if dmg_val > 0:
                auto_apply_aoe = True
                if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                    auto_apply_aoe = game_state.automation_settings.get("auto_apply_aoe_damage", game_state.automation_settings.get("auto_apply_damage", True))
                
                if auto_apply_aoe:
                    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, dmg_val, damage_type, game_state)
                    log_msg += f" Subisce {final_dmg} danni ({damage_type}){note}!"
                    if temp_absorbed > 0:
                        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
                    log_msg += f" HP: {target_player.hp}/{target_player.max_hp}"
                    if getattr(target_player, "temp_hp", 0) > 0:
                        log_msg += f" (+{target_player.temp_hp} Temp)"
                    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
                    game_state._trigger_gui_update()
                else:
                    import uuid
                    pending_id = f"dmg_{uuid.uuid4().hex[:8]}"
                    pending_info = {
                        "id": pending_id,
                        "attacker": source_name,
                        "target": target_name,
                        "raw_damage": dmg_val,
                        "damage_type": damage_type,
                        "is_crit": False,
                        "weapon_name": f"TS {stat} ({source_name})"
                    }
                    if not hasattr(game_state, "pending_damages"):
                        game_state.pending_damages = {}
                    game_state.pending_damages[pending_id] = pending_info
                    log_msg += f" 🎯 Danno Calcolato (TS): {dmg_val} ({damage_type}). [In attesa di conferma DM]"
                    if hasattr(game_state, "gui_queue") and game_state.gui_queue:
                        game_state.gui_queue.put({"type": "PENDING_DAMAGE_PROMPT", "payload": pending_info})
                    game_state._trigger_gui_update()
            else:
                log_msg += " Non subisce danni."
        except Exception as e:
            log_msg += f" (Errore formula danni: {e})"
            
    game_state.log_dm_message(f"[TS] {log_msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", log_msg))

def handle_force_save_request(data, player, game_state):
    targets = data.get("targets", [])
    stat = data.get("stat")
    dc = data.get("dc")
    damage_formula = data.get("damage_formula")
    half_on_success = data.get("half_on_success", True)
    damage_type = data.get("damage_type", "Fuoco")
    
    for t_name in targets:
        target_player = game_state.find_player(t_name)
        if not target_player: continue
        
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_prompt_save(stat, dc, damage_formula, half_on_success, player.name, damage_type))
        else:
            try:
                mod = 0
                if target_player.full_sheet:
                    attr = target_player.full_sheet.get("attributes", {})
                    if stat in attr:
                        try:
                            mod = (int(attr[stat]) - 10) // 2
                        except (ValueError, TypeError):
                            pass
                
                # Vantaggio ai TS su DES per Schivata
                if stat == "DES" and "Schivata" in getattr(target_player, "conditions", []):
                    r1 = random.randint(1, 20)
                    r2 = random.randint(1, 20)
                    base_roll = max(r1, r2)
                else:
                    base_roll = random.randint(1, 20)
                    
                roll_tot = base_roll + mod
                is_crit = (base_roll == 20)
                is_fail = (base_roll == 1)
                
                _process_save_result(target_player.name, stat, roll_tot, is_crit, is_fail, dc, damage_formula, half_on_success, player.name, game_state, damage_type)
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
    damage_type = data.get("damage_type", "Fuoco")
    cover = data.get("cover", "none")
    
    _process_save_result(player.name, stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, game_state, damage_type, cover=cover)


def _validate_combat_tactical_action(player, game_state, action_label: str) -> bool:
    """Verifica che il combattimento sia attivo, il personaggio non sia incapacitato e (se strict_turn_lock) sia il suo turno."""
    if not getattr(game_state, "combat_active", False):
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Puoi usare l'azione di {action_label} solo durante il combattimento!"))
        return False

    p_cond = getattr(player, "conditions", []) if player else []
    blocking = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(p_cond, c) for c in blocking) or getattr(player, "hp", 1) <= 0:
        if player and getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Non puoi compiere l'azione di {action_label} mentre sei Incosciente, Paralizzato, Stordito o a 0 HP!"))
        return False

    if getattr(game_state, "strict_turn_lock", False):
        curr_turn = game_state.get_current_turn_player()
        if curr_turn and player and curr_turn.name != player.name:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
            return False

    return True

def handle_dash_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Scatto"):
        return
    if "Scatto" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Scatto")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🏃 {player.name} compie l'Azione di Scatto! Velocità raddoppiata per questo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Scatto.")
        game_state._trigger_gui_update()

def handle_disengage_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Disimpegno"):
        return
    if "Disimpegno" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Disimpegno")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"💨 {player.name} compie l'Azione di Disimpegno! I suoi movimenti non provocheranno attacchi d'opportunità per questo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Disimpegno.")
        game_state._trigger_gui_update()

def handle_dodge_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Schivata"):
        return
    if "Schivata" not in getattr(player, "conditions", []):
        if not hasattr(player, "conditions") or player.conditions is None:
            player.conditions = []
        player.conditions.append("Schivata")
        player.has_acted_this_turn = True
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        broadcast(game_state, make_chat_broadcast("Sistema", f"🛡️ {player.name} compie l'Azione di Schivata! Gli attacchi contro di lui avranno svantaggio e ha vantaggio ai TS su Destrezza fino all'inizio del suo prossimo turno."))
        game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Schivata.")
        game_state._trigger_gui_update()

def handle_help_request(data, player, game_state):
    if not _validate_combat_tactical_action(player, game_state, "Aiuto"):
        return
    target_name = data.get("target_name")
    if not target_name: return
    target_player = game_state.find_player(target_name)
    if not target_player: return
    if not hasattr(target_player, "conditions") or target_player.conditions is None:
        target_player.conditions = []
    if "Aiutato" not in target_player.conditions:
        target_player.conditions.append("Aiutato")
    player.has_acted_this_turn = True
    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
    broadcast(game_state, make_chat_broadcast("Sistema", f"🤝 {player.name} compie l'Azione di Aiuto contro {target_name}! Il prossimo attacco alleato contro {target_name} avrà Vantaggio."))
    game_state.log_dm_message(f"[COMBAT] {player.name} ha usato Aiuto contro {target_name}.")
    game_state._trigger_gui_update()

def handle_short_rest_request(data, player, game_state):
    hd_spent = data.get("hd_spent", 1)
    hp_rec = data.get("hp_recovered", 0)
    msg = f"☕ {player.name} ha completato un Riposo Breve (ha speso {hd_spent} Dado/i Vita e recuperato {hp_rec} HP)!"
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    game_state.log_dm_message(f"[RIPOSO] {msg}")

def handle_reaction_response(data, player, game_state):
    """Gestisce la risposta del client a un prompt di reazione 5e (Attacco d'Opportunità, Scudo, ecc.)."""
    reaction_type = data.get("reaction_type")
    accepted = data.get("accepted", False)
    target_name = data.get("target_name")
    details = data.get("details", {})
    
    if not accepted or not player:
        return
        
    if getattr(player, "has_reacted_this_turn", False):
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Hai già consumato la tua Reazione per questo round!"))
        return
        
    player.has_reacted_this_turn = True
    
    if reaction_type == "OPPORTUNITY_ATTACK":
        msg = f"⚔️ {player.name} usa la propria REAZIONE per effettuare un Attacco d'Opportunità contro {target_name}!"
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        
        w_name = details.get("weapon_name", "Attacco d'Opportunità")
        hit_bonus = details.get("hit_bonus", 0)
        damage_formula = details.get("damage_formula", "1d8")
        damage_type = details.get("damage_type", "Tagliente")
        
        handle_attack_request({
            "target_name": target_name,
            "weapon_name": w_name,
            "hit_bonus": hit_bonus,
            "damage_formula": damage_formula,
            "damage_type": damage_type,
            "is_reaction": True
        }, player, game_state)
        
    elif reaction_type == "SHIELD_SPELL":
        conds = getattr(player, "conditions", [])
        if "Scudo" not in conds:
            conds.append("Scudo")
        msg = f"🛡️ {player.name} usa la propria REAZIONE per lanciare l'incantesimo Scudo! Ottiene +5 CA fino all'inizio del suo prossimo turno."
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        game_state.log_dm_message(f"[REAZIONE] {msg}")
        broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, player.initiative, player.conditions, getattr(player, "temp_hp", 0)))
        game_state._trigger_gui_update()

def handle_set_automation_mode_request(data, player, game_state):
    """Gestisce la modifica della modalità di automazione (manual, hybrid, full) da parte del DM."""
    is_dm = (player is None or getattr(player, "role", "") == "DM")
    if not is_dm:
        return
    mode = data.get("mode", "hybrid")
    settings = data.get("settings", {})
    game_state.set_automation_mode(mode, settings)
    
    mode_names = {
        "manual": "🎲 Tavolo Tradizionale (Controllo DM & Pen & Paper)",
        "hybrid": "⚖️ Ibrido Assistito (Consigliato)",
        "full": "⚡ Full Automation (Tattico Rapido)"
    }
    mode_title = mode_names.get(mode, mode.upper())
    msg = f"🎮 Modalità di Gestione Campagna impostata su: '{mode_title}' dal DM."
    game_state.log_dm_message(f"[SISTEMA] {msg}")
    broadcast(game_state, make_chat_broadcast("Sistema", msg))
    from common.protocol import make_automation_settings_broadcast
    broadcast(game_state, make_automation_settings_broadcast(mode, game_state.automation_settings))
    game_state._trigger_gui_update()

def handle_apply_pending_damage_request(data, player, game_state):
    """Permette al DM di confermare, dimezzare o annullare un danno calcolato prima di applicarlo agli HP."""
    is_dm = (player is None or getattr(player, "role", "") == "DM")
    if not is_dm:
        return
        
    pending_id = data.get("pending_id")
    action = data.get("action", "apply") # "apply", "half", "cancel", "custom"
    custom_amount = data.get("custom_amount")
    
    if not hasattr(game_state, "pending_damages") or pending_id not in game_state.pending_damages:
        return
        
    pending = game_state.pending_damages.pop(pending_id)
    target_name = pending["target"]
    target_player = game_state.find_player(target_name)
    attacker_name = pending.get("attacker", "Attaccante")
    damage_type = pending.get("damage_type", "Tagliente")
    raw_damage = pending.get("raw_damage", 0)
    
    if action == "cancel":
        msg = f"❌ Il DM ha ANNULLATO il danno ({raw_damage} {damage_type}) inflitto da {attacker_name} su {target_name}."
        game_state.log_dm_message(f"[COMBAT] {msg}")
        broadcast(game_state, make_chat_broadcast("DM", msg))
        game_state._trigger_gui_update()
        return
        
    if not target_player:
        return
        
    if action == "half":
        calc_dmg = max(1, raw_damage // 2)
        desc_prefix = f"🛡️ Il DM applica DANNO DIMEZZATO ({raw_damage} -> {calc_dmg} {damage_type})"
    elif action == "custom" and custom_amount is not None:
        try:
            calc_dmg = max(0, int(custom_amount))
            desc_prefix = f"🎯 Il DM applica DANNO PERSONALIZZATO ({calc_dmg} {damage_type})"
        except (ValueError, TypeError):
            calc_dmg = raw_damage
            desc_prefix = f"⚔️ Il DM applica DANNO PIENO ({calc_dmg} {damage_type})"
    else: # "apply"
        calc_dmg = raw_damage
        desc_prefix = f"⚔️ Il DM applica DANNO PIENO ({calc_dmg} {damage_type})"
        
    final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(target_player, calc_dmg, damage_type, game_state)
    log_msg = f"{desc_prefix} a {target_name}{note}."
    if temp_absorbed > 0:
        log_msg += f" [{temp_absorbed} assorbiti da Temp HP]."
    log_msg += f" HP {target_name}: {target_player.hp}/{target_player.max_hp}"
    if getattr(target_player, "temp_hp", 0) > 0:
        log_msg += f" (+{target_player.temp_hp} Temp)"
        
    game_state.log_dm_message(f"[COMBAT] {log_msg}")
    broadcast(game_state, make_chat_broadcast("DM", log_msg))
    broadcast(game_state, make_player_stats_update(target_player.name, target_player.hp, target_player.max_hp, target_player.initiative, target_player.conditions, getattr(target_player, "temp_hp", 0)))
    game_state._trigger_gui_update()

