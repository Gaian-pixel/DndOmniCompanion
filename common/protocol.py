# protocol.py

# --- Messaggi Client -> Server ---
def make_join(name):
    return {"type": "JOIN", "data": {"name": name}}

def make_chat(text):
    return {"type": "CHAT", "data": {"text": text}}

def make_whisper(to, text):
    return {"type": "WHISPER", "data": {"to": to, "text": text}}

def make_roll_request(formula, reason=""):
    return {"type": "ROLL_REQUEST", "data": {"formula": formula, "reason": reason}}

def make_move_request(x, y):
    # Attualmente non usato, ma lo teniamo per il futuro
    return {"type": "MOVE_REQUEST", "data": {"to": [x, y]}}

# --- Messaggi Server -> Client ---
def make_simple_reply(text):
    return {"type": "SIMPLE_REPLY", "data": {"text": text}}

def make_error_reply(text):
    return {"type": "ERROR_REPLY", "data": {"text": text}}

def make_chat_broadcast(sender, text, is_whisper=False):
    return {"type": "CHAT_BROADCAST", "data": {"sender": sender, "text": text, "is_whisper": is_whisper}}

def make_game_state(state_dict):
    return {"type": "GAME_STATE", "data": state_dict}

def make_player_joined(player_dict):
    return {"type": "PLAYER_JOINED", "data": player_dict}

def make_player_left(player_name):
    return {"type": "PLAYER_LEFT", "data": {"name": player_name}}

def make_player_move(player_name, position):
    return {"type": "PLAYER_MOVE", "data": {"name": player_name, "position": position}}

def make_dice_roll_result(player_name, formula, reason, result):
    return {"type": "DICE_ROLL_RESULT", "data": {
        "player_name": player_name,
        "formula": formula,
        "reason": reason,
        "result": result
    }}