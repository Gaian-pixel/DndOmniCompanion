# protocol.py

# --- Messaggi Client -> Server ---
def make_join(name, position=None):
    data = {"name": name}
    if position:
        data["position"] = position
    return {"type": "JOIN", "data": data}

def make_chat(text):
    return {"type": "CHAT", "data": {"text": text}}

def make_whisper(to, text):
    return {"type": "WHISPER", "data": {"to": to, "text": text}}

def make_roll_request(formula, reason=""):
    return {"type": "ROLL_REQUEST", "data": {"formula": formula, "reason": reason}}

def make_move_request(x, y):
    # Attualmente non usato, ma lo teniamo per il futuro
    return {"type": "MOVE_REQUEST", "data": {"to": [x, y]}}

def make_targeted_action_request(target_name, action_type, formula, reason=""):
    return {"type": "TARGETED_ACTION_REQUEST", "data": {
        "target_name": target_name,
        "action_type": action_type,
        "formula": formula,
        "reason": reason
    }}

def make_ping_request(q, r, color="yellow"):
    return {"type": "PING_REQUEST", "data": {"q": q, "r": r, "color": color}}

# --- Messaggi Server -> Client ---
def make_simple_reply(text):
    return {"type": "SIMPLE_REPLY", "data": {"text": text}}

def make_error_reply(text):
    return {"type": "ERROR_REPLY", "data": {"text": text}}

def make_chat_broadcast(sender, text, is_whisper=False):
    return {"type": "CHAT_BROADCAST", "data": {"sender": sender, "text": text, "is_whisper": is_whisper}}

def make_ping_broadcast(q, r, color="yellow"):
    return {"type": "PING_BROADCAST", "data": {"q": q, "r": r, "color": color}}

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

def make_update_stats_request(hp, max_hp, initiative, conditions=None):
    if conditions is None: conditions = []
    return {"type": "UPDATE_STATS_REQUEST", "data": {"hp": hp, "max_hp": max_hp, "initiative": initiative, "conditions": conditions}}

def make_player_stats_update(player_name, hp, max_hp, initiative, conditions=None):
    if conditions is None: conditions = []
    return {"type": "PLAYER_STATS_UPDATE", "data": {
        "name": player_name, "hp": hp, "max_hp": max_hp, "initiative": initiative, "conditions": conditions
    }}

def make_update_full_sheet_request(character_data):
    return {"type": "UPDATE_FULL_SHEET_REQUEST", "data": {"character": character_data}}

def make_receive_item(item_dict):
    return {"type": "RECEIVE_ITEM", "data": {"item": item_dict}}

def make_give_item_request(target_name, item_dict):
    return {"type": "GIVE_ITEM_REQUEST", "data": {"target_name": target_name, "item": item_dict}}

def make_create_aoe_request(aoe_data):
    return {"type": "CREATE_AOE_REQUEST", "data": {"aoe_data": aoe_data}}

def make_clear_aoes_request():
    return {"type": "CLEAR_AOES_REQUEST", "data": {}}

def make_set_travel_role_request(role):
    return {"type": "SET_TRAVEL_ROLE_REQUEST", "data": {"role": role}}

def make_start_combat_request(initiator_name=None):
    return {"type": "START_COMBAT_REQUEST", "data": {"initiator": initiator_name}}

def make_end_turn_request():
    return {"type": "END_TURN_REQUEST", "data": {}}

def make_request_initiative():
    return {"type": "REQUEST_INITIATIVE", "data": {}}

def make_submit_initiative(initiative_total):
    return {"type": "SUBMIT_INITIATIVE", "data": {"initiative": initiative_total}}
def make_attack_request(target_name, weapon_name, hit_bonus, damage_formula):
    return {"type": "ATTACK_REQUEST", "data": {"target_name": target_name, "weapon_name": weapon_name, "hit_bonus": hit_bonus, "damage_formula": damage_formula}}


def make_force_save_request(targets, stat, dc, damage_formula, half_on_success):
    return {"type": "FORCE_SAVE_REQUEST", "data": {"targets": targets, "stat": stat, "dc": dc, "damage_formula": damage_formula, "half_on_success": half_on_success}}

def make_prompt_save(stat, dc, damage_formula, half_on_success, source_name):
    return {"type": "PROMPT_SAVE", "data": {"stat": stat, "dc": dc, "damage_formula": damage_formula, "half_on_success": half_on_success, "source_name": source_name}}

def make_save_result(stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name):
    return {"type": "SAVE_RESULT", "data": {"stat": stat, "roll_total": roll_total, "is_crit": is_crit, "is_fail": is_fail, "dc": dc, "damage_formula": damage_formula, "half_on_success": half_on_success, "source_name": source_name}}



def make_handout_broadcast(title, image_b64=None, content=None):
    return {"type": "HANDOUT_BROADCAST", "data": {"title": title, "image_b64": image_b64, "content": content}}

def make_toggle_wall_request(q, r):
    return {"type": "TOGGLE_WALL_REQUEST", "data": {"q": q, "r": r}}

def make_fow_update_broadcast(fow_revealed, fow_draft):
    return {"type": "FOW_UPDATE_BROADCAST", "data": {"fow_revealed": fow_revealed, "fow_draft": fow_draft}}

def make_map_data_update_broadcast(map_data):
    return {"type": "MAP_DATA_UPDATE", "data": {"map": map_data}}

def make_combat_state_update_broadcast(combat_active, turn_index, round_number, active_aoes):
    return {"type": "COMBAT_STATE_UPDATE", "data": {"combat_active": combat_active, "turn_index": turn_index, "round_number": round_number, "active_aoes": active_aoes}}

def make_audio_play_broadcast(url_or_name):
    return {"type": "AUDIO_PLAY_BROADCAST", "data": {"url": url_or_name}}

def make_custom_spell_request(spell_dict):
    return {"type": "CUSTOM_SPELL_REQUEST", "data": {"spell": spell_dict}}

def make_custom_spell_response(player_name, spell_dict, approved, reason=""):
    return {"type": "CUSTOM_SPELL_RESPONSE", "data": {"player_name": player_name, "spell": spell_dict, "approved": approved, "reason": reason}}

def make_campaign_starter_granted(items, full_sheet=None):
    return {"type": "CAMPAIGN_STARTER_GRANTED", "data": {"items": items, "full_sheet": full_sheet}}
