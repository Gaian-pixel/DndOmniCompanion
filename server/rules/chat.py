import re
import random
from common.protocol import *
from common.hex_utils import Hex, hex_distance, get_sphere_hexes, hex_linedraw
from common.network_utils import send_message, broadcast
import math
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
                
                # Reveal FoW for torch
                if game_state.current_map.get("fow_enabled", False):
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

    game_state.log_dm_message(f"[{player.name}]: {text}")
    broadcast(game_state, make_chat_broadcast(player.name, text))

def handle_whisper(data, player, game_state):
    from common.network_utils import send_message, broadcast
    from common.protocol import make_chat_broadcast, make_error_reply
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
            crit_badge = " 🌟 SUCCESSO CRITICO! [20 Naturale]"
        elif result.get("is_fumble"):
            crit_badge = " 💀 FALLIMENTO CRITICO! [1 Naturale]"
        reason_part = f" ({reason})" if reason else ""
        log_msg = f"{player.name} tira {formula}{reason_part} e ottiene {result['total']} (dadi: {result.get('rolls')}, mod: {result.get('modifier')}){crit_badge}"
        game_state.log_dm_message(f"[ROLL] {log_msg}")
        broadcast(game_state, make_dice_roll_result(player.name, formula, reason, result))
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
        
        # 2. Conferma per il giocatore che ha tirato (senza rivelare il totale numerico!)
        if getattr(player, "conn", None):
            from common.protocol import make_chat_broadcast
            send_message(player.conn, make_chat_broadcast("Sistema", f"🎲 Hai effettuato un Tiro Segreto per il DM{reason_part} ({formula}). Solo il Master può vederne l'esito!", is_whisper=True))
    except ValueError as e:
        if getattr(player, "conn", None):
            send_message(player.conn, make_error_reply(str(e)))



