# commands.py
from common.protocol import *
from common.dice import roll_dice
from common.network_utils import send_message, broadcast # MODIFICATO

def handle_chat(data, player, game_state):
    text = data.get("text", "").strip()
    if not text: return
    game_state.log_dm_message(f"[{player.name}]: {text}")
    broadcast(game_state, make_chat_broadcast(player.name, text))

def handle_whisper(data, player, game_state):
    to_name = data.get("to"); text = data.get("text")
    if to_name.lower() == "dm":
        # Invece di un log generico, invia un messaggio strutturato alla GUI del DM
        game_state.gui_queue.put({
            "type": "PRIVATE_MESSAGE_RECEIVED",
            "payload": {
                "from": player.name,
                "text": text
            }
        })
        # Invia la conferma di lettura al giocatore
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

command_handlers = {
    "CHAT": handle_chat,
    "WHISPER": handle_whisper,
    "ROLL_REQUEST": handle_roll_request,
}