from common.protocol import (
    make_chat_broadcast,
    make_dice_roll_result,
    make_error_reply,
    make_game_state,
)
from common.hex_utils import Hex, get_visible_hexes
from common.network_utils import send_message, broadcast


def _reveal_light_fow(cur_map: dict, origin: Hex, radius: int) -> None:
    """Rivela la FoW per una sorgente luminosa rispettando `grid_type`, porte chiuse/segrete e `fow_draft`."""
    if not isinstance(cur_map, dict) or not cur_map.get("fow_enabled", False) or radius <= 0:
        return
    from server.rules.movement import get_effective_map_walls
    grid_type = cur_map.get("grid_type", "hex")
    walls = get_effective_map_walls(cur_map)
    visible = get_visible_hexes(origin, int(radius), walls, grid_type=grid_type)
    fow_rev = cur_map.setdefault("fow_revealed", [])
    fow_draft = cur_map.setdefault("fow_draft", []) if "fow_draft" in cur_map or isinstance(cur_map.get("fow_draft"), list) else None
    rev_set = {(int(item[0]), int(item[1])) for item in fow_rev if isinstance(item, (list, tuple)) and len(item) >= 2}
    draft_set = {(int(item[0]), int(item[1])) for item in (fow_draft or []) if isinstance(item, (list, tuple)) and len(item) >= 2}
    for rh in visible:
        key = (int(rh.q), int(rh.r))
        entry = [key[0], key[1]]
        if key not in rev_set:
            rev_set.add(key)
            fow_rev.append(entry)
        if fow_draft is not None and key not in draft_set:
            draft_set.add(key)
            fow_draft.append(list(entry))
def handle_chat(data, player, game_state):
    text = data.get("text", "").strip()
    if not text: return
    is_dm = (player is None or getattr(player, "role", "") == "DM" or getattr(player, "conn", None) is None)
    
    if text.startswith("/setsize "):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /setsize riservato al Dungeon Master."))
            return
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            try:
                size_val = int(parts[2])
                target = game_state.find_player(p_name)
                if target:
                    target.size = size_val
                    game_state._trigger_gui_update()
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata size {size_val} per {p_name}")
            except ValueError:
                pass
        return
        
    if text.startswith("/setaura "):
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            if not is_dm and p_name.lower() != player.name.lower():
                if getattr(player, "conn", None):
                    send_message(player.conn, make_error_reply("Puoi modificare solo la tua aura."))
                return
            try:
                aura_rad = int(parts[2])
                color = parts[3] if len(parts) >= 4 else "yellow"
                target = game_state.find_player(p_name)
                if target:
                    target.aura_radius = aura_rad
                    target.aura_color = color
                    game_state._trigger_gui_update()
                    broadcast(game_state, make_game_state(game_state.get_state_dict()))
                    game_state.log_dm_message(f"[SISTEMA] Impostata aura {aura_rad} ({color}) per {p_name}")
            except ValueError:
                pass
        return

    if text.startswith("/vision "):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /vision riservato al Dungeon Master."))
            return
        parts = text.split(" ")
        if len(parts) >= 3:
            p_name = parts[1]
            try:
                vis_rad = int(parts[2])
                target = game_state.find_player(p_name)
                if target:
                    target.vision_radius = vis_rad
                    game_state._trigger_gui_update()
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
                _reveal_light_fow(game_state.current_map, Hex(pos[0], pos[1]), 6)
                game_state._trigger_gui_update()
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
        return
        
    if text.startswith("/light "):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /light riservato al Dungeon Master (usa /torch per accendere una torcia)."))
            return
        parts = text.split(" ")
        if len(parts) >= 4 and getattr(game_state, "current_map", None):
            try:
                q = int(parts[1])
                r = int(parts[2])
                radius = int(parts[3])
                lights = game_state.current_map.setdefault("lights", [])
                lights.append({"q": q, "r": r, "radius": radius, "color": "yellow"})
                game_state.log_dm_message(f"[Sistema] Luce piazzata in {q}, {r} raggio {radius}.")
                _reveal_light_fow(game_state.current_map, Hex(q, r), radius)
                game_state._trigger_gui_update()
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
            except ValueError:
                pass
        return
        
    if text.startswith("/loot "):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /loot riservato al Dungeon Master."))
            return
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
                broadcast(game_state, make_game_state(game_state.get_state_dict()))
            except ValueError:
                pass
        return
        
    if text.startswith("/meteo ") or text.startswith("/weather "):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /meteo riservato al Dungeon Master."))
            return
        parts = text.split(" ", 1)
        if len(parts) >= 2:
            raw_w = parts[1].strip()
            from common.i18n import WEATHER_EN_TO_IT, translate_weather
            new_weather = WEATHER_EN_TO_IT.get(raw_w.capitalize(), raw_w.capitalize())
            game_state.weather = new_weather
            game_state._trigger_gui_update()
            broadcast(game_state, make_game_state(game_state.get_state_dict()))
            game_state.log_dm_message(f"[SISTEMA] Meteo cambiato in: {new_weather}")
            broadcast(game_state, make_chat_broadcast("Sistema", f"Il meteo è cambiato in: {translate_weather(new_weather)}"))
        return

    if text.strip() in ("/darkness", "/oscurita", "/oscurità"):
        if not is_dm:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Comando /darkness riservato al Dungeon Master."))
            return
        cur_w = str(getattr(game_state, "weather", "Sereno")).strip().lower()
        if cur_w in ("oscurita", "oscurità", "darkness", "buio"):
            new_weather = "Sereno"
            msg = "☀️ Filtro Oscurità disattivato. L'ambiente torna Sereno / Illuminato."
        else:
            new_weather = "Oscurità"
            msg = "🌑 Filtro Oscurità D&D 5e attivato! (Svantaggio all'attacco per chi non vede, Vantaggio per chi possiede Scurovisione)."
        game_state.weather = new_weather
        game_state._trigger_gui_update()
        broadcast(game_state, make_game_state(game_state.get_state_dict()))
        game_state.log_dm_message(f"[SISTEMA] {msg}")
        broadcast(game_state, make_chat_broadcast("Sistema", msg))
        return

    # Interpellazione dei Manuali di Gioco (PHB, DMG, MM, Espansioni, Custom)
    if any(text.lower().startswith(cmd) for cmd in ["/manuale", "/manual", "/regola", "/rule"]):
        parts = text.split(" ", 1)
        query = parts[1].strip() if len(parts) > 1 else ""
        from common.manuals_manager import ManualsManager
        mgr = ManualsManager()
        if not query:
            reply = "📖 [MANUALI 5e] Sintassi: `/manuale <argomento>` (es. `/manuale concentrazione`, `/manuale sfinimento`, `/manuale opportunita`, `/manuale copertura`)"
        else:
            match = mgr.quick_lookup(query)
            if match:
                ref = match.get("page_ref", "Manuale 5e")
                title = match.get("title", query.title())
                summary = match.get("summary", "")
                reply = f"📖 [{ref}] {title}:\n{summary}"
            else:
                reply = f"📖 [MANUALI] Nessuna regola trovata per '{query}'. Apri il menu Manuali per consultare l'indice completo o cercare altri argomenti."
        
        game_state.log_dm_message(f"[{player.name} -> Regola]: {reply}")
        broadcast(game_state, make_chat_broadcast("Manuali 5e", reply))
        return
        
    # Sussurri privati (/w, /whisper, /sussurra)
    if text.startswith("/w ") or text.startswith("/whisper ") or text.startswith("/sussurra "):
        parts = text.split(" ", 2)
        if len(parts) >= 3:
            target_name = parts[1].strip()
            whisper_text = parts[2].strip()
            handle_whisper({"to": target_name, "text": whisper_text}, player, game_state)
            return
        else:
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Sintassi sussurro: `/w <nome> <messaggio>`"))
            return

    # Tiri di dado rapidi da chat (/roll, /r)
    if text.lower().startswith("/roll ") or text.lower().startswith("/r ") or text.lower() in ("/roll", "/r"):
        cmd_len = 5 if text.lower().startswith("/roll") else 2
        rest = text[cmd_len:].strip()
        if not rest:
            formula, reason = "1d20", ""
        else:
            # Supporta "1d20+5 adv Percepire" oppure "1d20+5 Percepire"
            tokens = rest.split()
            if len(tokens) >= 2 and tokens[1].lower() in ("adv", "dis", "vantaggio", "svantaggio"):
                formula = f"{tokens[0]} {tokens[1]}"
                reason = " ".join(tokens[2:])
            else:
                formula = tokens[0]
                reason = " ".join(tokens[1:])
        handle_roll_request({"formula": formula, "reason": reason}, player, game_state)
        return

    # Tiri segreti del DM (/broll, /blindroll, /segreto)
    if text.lower().startswith(("/broll ", "/blindroll ", "/segreto ", "/broll", "/blindroll", "/segreto")):
        cmd_word = text.split()[0].lower()
        rest = text[len(cmd_word):].strip()
        if not rest:
            formula, reason = "1d20", "Tiro Segreto"
        else:
            tokens = rest.split()
            if len(tokens) >= 2 and tokens[1].lower() in ("adv", "dis", "vantaggio", "svantaggio"):
                formula = f"{tokens[0]} {tokens[1]}"
                reason = " ".join(tokens[2:])
            else:
                formula = tokens[0]
                reason = " ".join(tokens[1:]) if len(tokens) > 1 else "Tiro Segreto"
        handle_blind_roll_request({"formula": formula, "reason": reason}, player, game_state)
        return

    # Manovre tattiche 5e: Spinta (/spingi, /shove) e Lotta (/lotta, /grapple)
    if text.lower().startswith(("/spingi ", "/shove ")):
        parts = text.split()
        if len(parts) >= 2:
            target_name = parts[1]
            opt = parts[2].lower() if len(parts) >= 3 else "prone"
            from server.rules.combat import handle_shove_request
            handle_shove_request({"target_name": target_name, "option": opt}, player, game_state)
            return

    if text.lower().startswith(("/lotta ", "/grapple ")):
        parts = text.split()
        if len(parts) >= 2:
            target_name = parts[1]
            from server.rules.combat import handle_grapple_request
            handle_grapple_request({"target_name": target_name}, player, game_state)
            return

    # Quota 3D & Elevazione (/quota, /elevation, /vola, /fly)
    if text.lower().startswith(("/quota ", "/elevation ", "/vola ", "/fly ")):
        parts = text.split()
        if len(parts) >= 2:
            raw_val = parts[1].lower()
            target_name = parts[2] if len(parts) >= 3 else player.name
            try:
                if raw_val.endswith("m"):
                    val = int(float(raw_val.replace("m", "")) * 3.28)
                else:
                    val = int(raw_val.replace("ft", ""))
                from server.rules.character import handle_set_elevation_request
                handle_set_elevation_request({"elevation": val, "target_name": target_name}, player, game_state)
                return
            except ValueError:
                pass

    # Caduta RAW 5e (/caduta, /fall) — riservato al DM (previene danni/cadute arbitrarie cross-player)
    if text.lower().startswith(("/caduta ", "/fall ")):
        from common.network_utils import is_dm_actor
        if not is_dm_actor(player):
            if getattr(player, "conn", None):
                send_message(player.conn, make_error_reply("Solo il Dungeon Master può applicare danni da caduta con /caduta o /fall."))
            return
        parts = text.split()
        if len(parts) >= 2:
            try:
                dist_ft = int(parts[1].replace("ft", "").replace("m", ""))
                target_name = parts[2] if len(parts) >= 3 else player.name
                target_obj = None
                for p in getattr(game_state, "players", []):
                    if p.name.lower() == target_name.lower():
                        target_obj = p
                        break
                if target_obj:
                    from server.rules.combat import resolve_falling
                    gs_lock = getattr(game_state, "lock", None)
                    if gs_lock is not None:
                        with gs_lock:
                            resolve_falling(target_obj, dist_ft, game_state)
                    else:
                        resolve_falling(target_obj, dist_ft, game_state)
                    return
            except ValueError:
                pass

    # Recupero Munizioni 50% RAW (PHB p. 146)
    if text.lower().startswith(("/recupera_munizioni", "/ammo_recover", "/munizioni")):
        from server.rules.combat import recover_expended_ammunition
        recover_expended_ammunition(player, game_state)
        return

    game_state.log_dm_message(f"[{player.name}]: {text}")
    broadcast(game_state, make_chat_broadcast(player.name, text))

def handle_whisper(data, player, game_state):
    to_name = data.get("to")
    text = data.get("text")
    if not to_name or not text:
        return
    if to_name.lower() == player.name.lower():
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply("Non puoi sussurrare a te stesso."))
        return
    if to_name.lower() == "dm" or to_name.lower() == "master":
        game_state.gui_queue.put({"type": "PRIVATE_MESSAGE_RECEIVED", "payload": {"from": player.name, "text": text}})
        if getattr(player, "conn", None):
            send_message(player.conn, make_chat_broadcast("Tu -> DM", text, is_whisper=True))
        game_state.log_dm_message(f"[SUSSURRO A DM] [{player.name}]: {text}")
        return
    target_player = game_state.find_player(to_name)
    if target_player:
        if getattr(target_player, "conn", None):
            send_message(target_player.conn, make_chat_broadcast(player.name, text, is_whisper=True))
        if getattr(player, "conn", None):
            send_message(player.conn, make_chat_broadcast(f"Tu -> {target_player.name}", text, is_whisper=True))
        game_state.log_dm_message(f"[SUSSURRO] [{player.name} -> {target_player.name}]: {text}")
    else:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(f"Giocatore '{to_name}' non trovato."))

def handle_roll_request(data, player, game_state):
    formula = data.get("formula"); reason = data.get("reason", "")
    if not formula or str(formula).strip().lower() == "0d0":
        if reason:
            game_state.log_dm_message(f"[{player.name}]: {reason}")
            broadcast(game_state, make_chat_broadcast(player.name, reason))
        return
    try:
        from common.dice import roll_dice
        result = roll_dice(formula)
        crit_badge = ""
        if result.get("is_crit"):
            crit_badge = " 🌟 [20 Naturale]"
        elif result.get("is_fumble"):
            crit_badge = " 💀 [1 Naturale]"
        reason_part = f" ({reason})" if reason else ""
        log_msg = f"{player.name} tira {formula}{reason_part} e ottiene {result['total']} (dadi: {result.get('rolls')}, mod: {result.get('modifier')}){crit_badge}"
        game_state.log_dm_message(f"[ROLL] {log_msg}")
        broadcast(game_state, make_dice_roll_result(player.name, formula, reason, result))
        if hasattr(game_state, "gui_queue") and game_state.gui_queue:
            game_state.gui_queue.put({
                "type": "DICE_ROLL_RESULT",
                "payload": {
                    "player": player.name,
                    "formula": formula,
                    "reason": reason,
                    "result": result
                }
            })
    except ValueError as e:
        send_message(player.conn, make_error_reply(str(e)))

def handle_blind_roll_request(data, player, game_state):
    """Gestisce un tiro segreto per il DM: formula e dadi sono visibili solo al DM."""
    formula = data.get("formula", "1d20")
    reason = data.get("reason", "Tiro Segreto")
    try:
        from common.dice import roll_dice
        result = roll_dice(formula)
        p_name = player.name if player else "Giocatore"
        crit_badge = ""
        if result.get("is_crit"):
            crit_badge = " 🌟 CRITICO 20!"
        elif result.get("is_fumble"):
            crit_badge = " 💀 FALLIMENTO 1!"
        reason_part = f" [{reason}]" if reason else ""
        
        # 1. Messaggio per il DM (formula, dadi e risultato esatto)
        dm_msg = f"🙈 [TIRO SEGRETO] {p_name} tira {formula}{reason_part} -> Totale: {result['total']} (dadi: {result.get('rolls')}, mod: {result.get('modifier')}){crit_badge}"
        game_state.log_dm_message(dm_msg)
        game_state.gui_queue.put({"type": "PRIVATE_MESSAGE_RECEIVED", "payload": {"from": "Tiro Segreto", "text": dm_msg}})
        game_state.gui_queue.put({
            "type": "BLIND_ROLL_RESULT",
            "payload": {
                "player": p_name,
                "formula": formula,
                "reason": f"🙈 [Segreto] {reason}" if reason else "🙈 [Tiro Segreto]",
                "result": result
            }
        })
        
        # 2. Conferma per il giocatore che ha tirato (senza rivelare il totale numerico!)
        if getattr(player, "conn", None):
            from common.protocol import make_chat_broadcast
            send_message(player.conn, make_chat_broadcast("Sistema", f"🎲 Hai effettuato un Tiro Segreto per il DM{reason_part} ({formula}). Solo il Master può vederne l'esito!", is_whisper=True))
    except ValueError as e:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(str(e)))



