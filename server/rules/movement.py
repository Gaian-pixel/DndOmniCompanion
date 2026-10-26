import os
import json
import base64
import random
from common.hex_utils import Hex, hex_linedraw, get_visible_hexes
from common.network_utils import send_message, broadcast
from common.i18n import is_condition_active

def get_effective_map_walls(current_map):
    """Restituisce l'insieme dei muri comprensivo di porte chiuse, serrate o segrete che bloccano LoS e passaggio."""
    if not current_map: return []
    walls = [list(w) for w in current_map.get("walls", [])]
    for d in current_map.get("doors", []):
        if d.get("state", "closed") in ("closed", "locked", "secret"):
            walls.append([d.get("q", 0), d.get("r", 0)])
    return walls

def auto_explore_fow(player, game_state):
    """Calcola la visibilità (LoS + Luce dinamica) del giocatore e aggiorna la FoW della mappa."""
    if not getattr(game_state, "current_map", None) or not game_state.current_map.get("fow_enabled", False):
        return False
    pos = getattr(player, "position", None)
    if not pos:
        return False
    
    h = Hex(pos[0], pos[1])
    vision_rad = getattr(player, 'vision_radius', 6)
    light_rad = getattr(player, 'light_radius', 0)
    effective_rad = max(vision_rad, light_rad)
    grid_type = game_state.current_map.get("grid_type", "hex")
    walls = get_effective_map_walls(game_state.current_map)
    visible_hexes = get_visible_hexes(h, effective_rad, walls, grid_type=grid_type)
    
    for other_p in getattr(game_state, "players", []):
        if other_p.name != player.name and getattr(other_p, 'is_party_member', False) and getattr(other_p, 'light_radius', 0) > 0:
            o_pos = getattr(other_p, 'position', None)
            if o_pos:
                o_hex = Hex(o_pos[0], o_pos[1])
                o_light_hexes = get_visible_hexes(o_hex, other_p.light_radius, walls, grid_type=grid_type)
                visible_hexes.extend(o_light_hexes)

    changed = False
    fow_rev = game_state.current_map.setdefault("fow_revealed", [])
    fow_draft = game_state.current_map.setdefault("fow_draft", [])
    
    for rh in visible_hexes:
        pos_entry = [rh.q, rh.r]
        if pos_entry not in fow_rev:
            fow_rev.append(pos_entry)
            changed = True
        if pos_entry not in fow_draft:
            fow_draft.append(pos_entry)
            changed = True
            
    return changed

def handle_move_request(data, player, game_state):
    conds = getattr(player, "conditions", [])
    blocking = ["Afferrato", "Grappled", "Trattenuto", "Restrained", "Privo di Sensi", "Incapacitato", "Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto"]
    if any(is_condition_active(conds, c) for c in blocking) or getattr(player, "exhaustion_level", 0) >= 5 or getattr(player, "hp", 1) <= 0:
        from common.protocol import make_error_reply
        if player.conn:
            send_message(player.conn, make_error_reply("La tua velocità è 0 o sei incapacitato/morto. Non puoi muoverti."))
        return

    to_pos = data.get("to")
    move_path = None
    is_dm_caller = getattr(player, "is_dm", False) or getattr(player, "role", "") == "DM"
    if getattr(player, "is_party_member", False) and getattr(player, "conn", None) is not None:
        is_dm = is_dm_caller
    else:
        is_dm = is_dm_caller or data.get("is_dm_force", False)
    
    if to_pos:
        if not isinstance(to_pos, (list, tuple)) or len(to_pos) < 2 or not all(isinstance(v, int) for v in to_pos[:2]):
            from common.protocol import make_error_reply
            if player.conn:
                send_message(player.conn, make_error_reply("Coordinate di destinazione non valide."))
            return
        if not is_dm and getattr(game_state, "current_map", None):
            hex_size = game_state.current_map.get("hex_size", 60)
            if hex_size < 40:
                from common.protocol import make_error_reply
                if player.conn:
                    send_message(player.conn, make_error_reply("Mappa di esplorazione: movimento libero disabilitato. Usa il Viaggio o aspetta il DM."))
                return
                
        walls_list_pos = get_effective_map_walls(game_state.current_map) if getattr(game_state, "current_map", None) else []
        from_pos = getattr(player, "position", None)
        if not is_dm and walls_list_pos:
            if from_pos:
                p_start = Hex(from_pos[0], from_pos[1])
                p_end = Hex(to_pos[0], to_pos[1])
                move_path = hex_linedraw(p_start, p_end)
                steps_to_check = move_path[1:]
            else:
                steps_to_check = [Hex(to_pos[0], to_pos[1])]

            for step in steps_to_check:
                if [step.q, step.r] in walls_list_pos:
                    from common.protocol import make_error_reply
                    door_blocked = None
                    if getattr(game_state, "current_map", None):
                        for d in game_state.current_map.get("doors", []):
                            if d.get("q") == step.q and d.get("r") == step.r and d.get("state", "closed") in ("closed", "locked", "secret"):
                                door_blocked = d
                                break
                    if getattr(player, "conn", None):
                        if door_blocked:
                            d_name = door_blocked.get("name", "Porta")
                            d_st = "serrata a chiave" if door_blocked.get("state") == "locked" else "chiusa"
                            send_message(player.conn, make_error_reply(f"Il percorso è bloccato: la {d_name} a [{step.q}, {step.r}] è {d_st}! Cliccaci sopra per aprirla."))
                        else:
                            send_message(player.conn, make_error_reply(f"Movimento non consentito: c'è un muro sul percorso a [{step.q}, {step.r}]!"))
                    return
            
        in_combat = getattr(player, "in_combat", False) or getattr(game_state, "combat_active", False)
        strict_lock = False
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            strict_lock = game_state.automation_settings.get("strict_turn_lock", False)
        else:
            strict_lock = getattr(game_state, "strict_turn_lock", False)

        if in_combat and not is_dm and strict_lock:
            curr_turn = game_state.get_current_turn_player()
            if curr_turn and curr_turn.name != player.name:
                from common.protocol import make_error_reply
                if player.conn:
                    send_message(player.conn, make_error_reply(f"Non è il tuo turno in combattimento! È il turno di {curr_turn.name}."))
                return

        if in_combat and hasattr(player, "position") and player.position and len(player.position) >= 2:
            q1, r1 = player.position[0], player.position[1]
            q2, r2 = to_pos[0], to_pos[1]
            speed = getattr(player, "speed", 30)
            speed_unit = getattr(player, "speed_unit", None)
            sheet = getattr(player, "full_sheet", None)
            if sheet and not speed_unit:
                speed_unit = sheet.get("speed_unit")
            from common.i18n import speed_to_hexes, format_distance_hexes
            base_hexes = speed_to_hexes(speed, speed_unit)

            # Regola D&D 5e Ingombro (Variant Encumbrance PHB p. 176)
            if sheet and isinstance(sheet.get("attributes"), dict):
                try:
                    str_val = int(sheet["attributes"].get("FOR", sheet["attributes"].get("STR", 10)))
                    inv_grid = sheet.get("inventory_grid", [])
                    tot_w = sum(float(it.get("weight", 0.0) or 0.0) * int(it.get("qty", 1) or 1) for it in inv_grid if it and isinstance(it, dict))
                    curr = sheet.get("currency", {})
                    if isinstance(curr, dict):
                        coin_count = sum(int(v or 0) for v in curr.values() if str(v).isdigit())
                        tot_w += coin_count * 0.02
                    if tot_w > (str_val * 15):
                        base_hexes = 0  # Sovraccarico: movimento bloccato
                    elif tot_w > (str_val * 10):
                        base_hexes = max(1, base_hexes - 4)  # Gravemente ingombrato (-20 ft)
                    elif tot_w > (str_val * 5):
                        base_hexes = max(1, base_hexes - 2)  # Ingombrato (-10 ft)
                except (ValueError, TypeError):
                    pass

            exh = getattr(player, "exhaustion_level", 0)
            if exh >= 2:
                base_hexes = max(1, base_hexes // 2)
            is_dashed = is_condition_active(conds, "Scatto")
            max_hexes = base_hexes * 2 if is_dashed else base_hexes
            # Calcolo percorso con hex_linedraw e applicazione Terreno Difficile (D&D 5e: costo doppio per ogni casella)
            cur_map = getattr(game_state, "current_map", None)
            diff_terrain = cur_map.get("difficult_terrain", {}) if cur_map else {}
            diff_map = {}
            if isinstance(diff_terrain, dict):
                for k, v in diff_terrain.items():
                    if isinstance(k, str) and "," in k:
                        parts = k.split(",")
                        diff_map[(int(parts[0]), int(parts[1]))] = str(v).lower()
                    elif isinstance(k, (tuple, list)) and len(k) >= 2:
                        diff_map[(int(k[0]), int(k[1]))] = str(v).lower()
            elif isinstance(diff_terrain, list):
                for item in diff_terrain:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        diff_map[(int(item[0]), int(item[1]))] = "fango"

            p_start = Hex(q1, r1)
            p_end = Hex(q2, r2)
            move_path = hex_linedraw(p_start, p_end)
            
            cost_prone = 2 if is_condition_active(conds, "Prono") else 1
            req_hexes = 0
            has_diff_terrain_in_path = False
            for step in move_path[1:]:
                step_tup = (step.q, step.r)
                is_step_diff = (step_tup in diff_map)
                if is_step_diff:
                    has_diff_terrain_in_path = True
                step_cost = 2 if is_step_diff else 1
                if is_condition_active(conds, "Prono"):
                    step_cost += 1
                req_hexes += step_cost

            spent = getattr(player, "movement_spent_this_turn", 0)
            strict_move = True
            if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
                strict_move = game_state.automation_settings.get("strict_movement_limits", True)

            if (spent + req_hexes) > max_hexes:
                if strict_move:
                    from common.protocol import make_error_reply
                    if getattr(player, "conn", None):
                        rem = max(0, max_hexes - spent)
                        rem_str = format_distance_hexes(rem, speed_unit)
                        tot_str = format_distance_hexes(max_hexes, speed_unit)
                        diff_hint = " (Attraversare terreno difficile raddoppia il costo!)" if has_diff_terrain_in_path else ""
                        if cost_prone == 2 and not has_diff_terrain_in_path:
                            send_message(player.conn, make_error_reply(f"Movimento non consentito: sei Prono. Ti restano {rem // 2} esagoni ({rem_str})."))
                        else:
                            hint = " (Puoi usare l'Azione di Scatto /dash per raddoppiare la velocità!)" if not is_dashed else ""
                            send_message(player.conn, make_error_reply(f"Movimento non consentito: la distanza supera la velocità rimasta per questo turno ({rem_str} rimasti su {tot_str}).{diff_hint}{hint}"))
                    return
                else:
                    game_state.log_dm_message(f"[MOVIMENTO] {player.name} supera la velocità normale del turno ({spent + req_hexes}/{max_hexes} esagoni) - Consentito in modalità tavolo.")
            player.movement_spent_this_turn = spent + req_hexes

        # Rilevamento Attacco d'Opportunità (Opportunity Attack - D&D 5e RAW PHB p. 195)
        from_pos = list(player.position) if hasattr(player, "position") and player.position else None
        is_teleport = bool(data.get("is_teleport", False))
        if in_combat and from_pos and from_pos != to_pos and not is_teleport:
            disengaged = is_condition_active(conds, "Disimpegno")
            if not disengaged:
                for other in getattr(game_state, "players", []):
                    if other.name != player.name and getattr(other, "hp", 0) > 0 and hasattr(other, "position") and other.position:
                        is_enemy = (getattr(player, "is_party_member", False) != getattr(other, "is_party_member", False))
                        # Non può reagire se ha già speso la reazione questo turno
                        has_reacted = getattr(other, "has_reacted_this_turn", False)
                        if is_enemy and not has_reacted:
                            qo, ro = other.position[0], other.position[1]
                            reach = getattr(other, "reach", 1) or 1
                            exited_reach = False
                            if move_path and len(move_path) > 1:
                                for p_i in range(len(move_path) - 1):
                                    s_cur, s_nxt = move_path[p_i], move_path[p_i + 1]
                                    cq1 = getattr(s_cur, "q", s_cur[0] if isinstance(s_cur, (list, tuple)) else 0)
                                    cr1 = getattr(s_cur, "r", s_cur[1] if isinstance(s_cur, (list, tuple)) else 0)
                                    cq2 = getattr(s_nxt, "q", s_nxt[0] if isinstance(s_nxt, (list, tuple)) else 0)
                                    cr2 = getattr(s_nxt, "r", s_nxt[1] if isinstance(s_nxt, (list, tuple)) else 0)
                                    d_c = max(abs(cq1 - qo), abs(cq1 + cr1 - qo - ro), abs(cr1 - ro))
                                    d_n = max(abs(cq2 - qo), abs(cq2 + cr2 - qo - ro), abs(cr2 - ro))
                                    if d_c <= reach and d_n > reach:
                                        exited_reach = True
                                        break
                            else:
                                d_f = max(abs(from_pos[0] - qo), abs(from_pos[0] + from_pos[1] - qo - ro), abs(from_pos[1] - ro))
                                d_t = max(abs(to_pos[0] - qo), abs(to_pos[0] + to_pos[1] - qo - ro), abs(to_pos[1] - ro))
                                exited_reach = (d_f <= reach and d_t > reach)
                            if exited_reach:
                                incaps = ["Incosciente", "Paralizzato", "Pietrificato", "Stordito", "Morto", "Incapacitato", "Incapacitated"]
                                o_conds = getattr(other, "conditions", [])
                                is_blind = any(is_condition_active(o_conds, c) for c in ["Cieco", "Blinded"])
                                if not is_blind and not any(is_condition_active(o_conds, c) for c in incaps):
                                    opp_alert = f"⚠️ [OPPORTUNITÀ] {player.name} esce dalla portata di mischia ({reach * 1.5}m) di {other.name}! {other.name} può usare la Reazione per un Attacco d'Opportunità!"
                                    game_state.log_dm_message(f"[COMBAT] {opp_alert}")
                                    from common.protocol import make_chat_broadcast, make_opportunity_alert
                                    broadcast(game_state, make_chat_broadcast("Sistema", opp_alert))
                                    if getattr(other, "conn", None):
                                        send_message(other.conn, make_opportunity_alert(player.name, f"{player.name} si sta allontanando da te!"))

        game_state.move_player(player.name, to_pos)

        # Effetti Pericolosi Terreno Difficile (Ghiaccio, Rovi, Palude)
        cur_map = getattr(game_state, "current_map", None)
        diff_terrain = cur_map.get("difficult_terrain", {}) if cur_map else {}
        diff_map = {}
        if isinstance(diff_terrain, dict):
            for k, v in diff_terrain.items():
                if isinstance(k, str) and "," in k:
                    parts = k.split(",")
                    diff_map[(int(parts[0]), int(parts[1]))] = str(v).lower()
                elif isinstance(k, (tuple, list)) and len(k) >= 2:
                    diff_map[(int(k[0]), int(k[1]))] = str(v).lower()
        elif isinstance(diff_terrain, list):
            for item in diff_terrain:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    diff_map[(int(item[0]), int(item[1]))] = "fango"

        to_tup = (to_pos[0], to_pos[1])
        if to_tup in diff_map:
            t_type = diff_map[to_tup]
            if t_type in ("ghiaccio", "ice"):
                # D&D 5e: Ghiaccio Scivoloso -> TS Destrezza CD 10 o cade prono
                dex_mod = 0
                if getattr(player, "full_sheet", None) and isinstance(player.full_sheet.get("attributes"), dict):
                    try:
                        dex_val = int(player.full_sheet["attributes"].get("DES", player.full_sheet["attributes"].get("DEX", 10)))
                        dex_mod = (dex_val - 10) // 2
                    except Exception:
                        pass
                    prof_saves = [str(s).upper() for s in player.full_sheet.get("saving_throw_proficiencies", [])]
                    if "DES" in prof_saves or "DEX" in prof_saves:
                        try:
                            lvl = int(player.full_sheet.get("level", 1))
                            dex_mod += 2 + (lvl - 1) // 4
                        except (ValueError, TypeError):
                            dex_mod += 2
                dex_roll = random.randint(1, 20) + dex_mod
                if dex_roll < 10:
                    if "Prono" not in player.conditions:
                        player.conditions.append("Prono")
                    alert = f"🧊 {player.name} scivola sul Ghiaccio (TS Des {dex_roll} vs CD 10) e cade Prono!"
                    game_state.log_dm_message(f"[TERRENO] {alert}")
                    from common.protocol import make_chat_broadcast, make_player_stats_update
                    broadcast(game_state, make_chat_broadcast("Sistema", alert))
                    broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, getattr(player, 'initiative', 0), player.conditions, getattr(player, 'temp_hp', 0)))
                else:
                    from common.protocol import make_chat_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", f"🧊 {player.name} attraversa il ghiaccio mantenendo l'equilibrio (TS Des {dex_roll} vs CD 10)."))
            elif t_type in ("rovi", "briars", "spine"):
                # D&D 5e: Rovi acuminati -> 1d4 danni da spine via apply_damage (Temp HP, resistenze, death saves)
                thorn_dmg = random.randint(1, 4)
                from server.rules.combat import apply_damage
                final_dmg, note, temp_absorbed, dmg_to_hp = apply_damage(player, thorn_dmg, "Perforante", game_state)
                alert = f"🌿 {player.name} attraversa i Rovi acuminati e subisce {final_dmg} danni perforanti{note}!"
                game_state.log_dm_message(f"[TERRENO] {alert}")
                from common.protocol import make_chat_broadcast, make_player_stats_update
                broadcast(game_state, make_chat_broadcast("Sistema", alert))
                broadcast(game_state, make_player_stats_update(player.name, player.hp, player.max_hp, getattr(player, 'initiative', 0), player.conditions, getattr(player, 'temp_hp', 0)))
        
        # Gestione Trappole D&D 5e sulla mappa
        if getattr(game_state, "current_map", None):
            traps = game_state.current_map.get("traps", [])
            path_coords = {(getattr(step, "q", step[0] if isinstance(step, (list, tuple)) else 0), getattr(step, "r", step[1] if isinstance(step, (list, tuple)) else 0)) for step in move_path} if move_path else {(to_pos[0], to_pos[1])}
            for trap in traps:
                t_coord = (trap.get("q"), trap.get("r"))
                if t_coord in path_coords and not trap.get("triggered", False):
                    trap["triggered"] = True
                    trap["hidden"] = False
                    trap_name = trap.get("name", "Trappola a Trabocchetto")
                    trap_dc = trap.get("dc", 13)
                    trap_dmg = trap.get("damage", "2d10")
                    trap_dtype = trap.get("damage_type", "Perforante")
                    
                    alert = f"💥 [TRAPPOLA 5e] {player.name} attiva una trappola ({trap_name})!"
                    game_state.log_dm_message(f"[TRAPPOLA] {alert}")
                    from common.protocol import make_chat_broadcast, make_map_data_update_broadcast
                    broadcast(game_state, make_chat_broadcast("Sistema", alert))
                    broadcast(game_state, make_map_data_update_broadcast(game_state.current_map))
                    
                    if getattr(player, "conn", None):
                        from common.protocol import make_prompt_save
                        send_message(player.conn, make_prompt_save("DES", trap_dc, trap_dmg, True, trap_name, trap_dtype))
                    else:
                        from server.rules.combat import _process_save_result
                        from common.dice import roll_dice
                        mod = 0
                        if getattr(player, "full_sheet", None):
                            attr = player.full_sheet.get("attributes", {})
                            d_val = attr.get("DES", attr.get("DEX", 10))
                            try:
                                mod = (int(d_val) - 10) // 2
                            except (ValueError, TypeError):
                                mod = 0
                            p_saves = [str(s).upper() for s in player.full_sheet.get("saving_throw_proficiencies", [])]
                            if "DES" in p_saves or "DEX" in p_saves:
                                try:
                                    lvl = int(player.full_sheet.get("level", 1))
                                    mod += 2 + (lvl - 1) // 4
                                except (ValueError, TypeError):
                                    mod += 2
                        mod_str = f"+{mod}" if mod >= 0 else str(mod)
                        res = roll_dice(f"1d20{mod_str}")
                        is_crit = res["rolls"][0] == 20
                        is_fail = res["rolls"][0] == 1
                        _process_save_result(player.name, "DES", res["total"], is_crit, is_fail, trap_dc, trap_dmg, True, trap_name, game_state, trap_dtype)
        
        if getattr(game_state, "current_map", None):
            teleports = game_state.current_map.get("teleports", {})
            pos_key = f"{to_pos[0]},{to_pos[1]}"
            if pos_key in teleports:
                map_file = teleports[pos_key]
                maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "maps")
                map_path = os.path.join(maps_dir, map_file)
                if os.path.exists(map_path):
                    try:
                        with open(map_path, "r", encoding="utf-8") as f:
                            new_map_data = json.load(f)
                        if 'base_image_path' in new_map_data and new_map_data['base_image_path']:
                            with open(new_map_data['base_image_path'], "rb") as img_f:
                                new_map_data['bg_image_data'] = base64.b64encode(img_f.read()).decode('utf-8')
                        
                        game_state.load_map(new_map_data)
                        
                        from common.protocol import make_chat_broadcast, make_game_state, make_map_data_update_broadcast
                        broadcast(game_state, make_map_data_update_broadcast(new_map_data))
                        broadcast(game_state, make_game_state(game_state.get_state_dict()))
                        broadcast(game_state, make_chat_broadcast("Sistema", "Il gruppo è stato teletrasportato."))
                        game_state._trigger_gui_update()
                        return
                    except Exception as e:
                        print(f"Errore caricamento mappa teleport {map_file}: {e}")

        # Auto-explore FoW around the player's new position with true Line of Sight (LoS) and Dynamic Light
        auto_fow = True
        if hasattr(game_state, "automation_settings") and isinstance(game_state.automation_settings, dict):
            auto_fow = game_state.automation_settings.get("auto_explore_fow", True)

        if auto_fow and getattr(game_state, "current_map", None) and game_state.current_map.get("fow_enabled", False):
            changed = auto_explore_fow(player, game_state)
            if changed:
                game_state._trigger_gui_update()
                from common.protocol import make_fow_update_broadcast, make_player_move
                broadcast(game_state, make_player_move(player.name, to_pos))
                broadcast(game_state, make_fow_update_broadcast(game_state.current_map["fow_revealed"], game_state.current_map["fow_draft"], fow_enabled=True))
                return
                
        from common.protocol import make_player_move
        broadcast(game_state, make_player_move(player.name, to_pos))
