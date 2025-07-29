import json

### --- Costruttori di messaggi ---

def make_join(name):
    return json.dumps({
        "type": "JOIN",
        "data": {"name": name}
    })

def make_chat(text):
    return json.dumps({
        "type": "CHAT",
        "data": {"text": text}
    })

def make_whisper(to, text):
    return json.dumps({
        "type": "WHISPER",
        "data": {
            "to": to,
            "text": text
        }
    })

def make_roll(formula, reason=None):
    data = {"formula": formula}
    if reason:
        data["reason"] = reason
    return json.dumps({
        "type": "ROLL",
        "data": data
    })

def make_move(x, y):
    return json.dumps({
        "type": "MOVE",
        "data": {
            "to": [x, y]
        }
    })

def make_start_combat(initiative_required=True):
    return json.dumps({
        "type": "START_COMBAT",
        "data": {
            "initiative": initiative_required
        }
    })

def make_server_reply(text):
    return json.dumps({
        "type": "SERVER_REPLY",
        "data": {"text": text}
    })

def make_notify(text):
    return json.dumps({
        "type": "NOTIFY",
        "data": {"text": text}
    })

def make_error(message):
    return json.dumps({
        "type": "ERROR",
        "data": {"text": message}
    })

### --- Parsing messaggi ricevuti ---

def parse_message(json_string):
    try:
        return json.loads(json_string)
    except json.JSONDecodeError:
        return {
            "type": "ERROR",
            "data": {"text": "Messaggio non valido"}
        }
