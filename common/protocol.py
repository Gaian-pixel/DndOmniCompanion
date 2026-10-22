# protocol.py
from typing import TypedDict, Any, Optional, Dict, List, Union

# ==============================================================================
# TYPED DICTIONARIES PER LA VALIDAZIONE STATICA DEL PROTOCOLLO (mypy / IDE)
# ==============================================================================

class ProtocolMessage(TypedDict):
    type: str
    data: Dict[str, Any]

class JoinData(TypedDict, total=False):
    name: str
    position: Optional[List[int]]

class ChatData(TypedDict, total=False):
    text: str
    sender: Optional[str]
    is_whisper: Optional[bool]

class WhisperData(TypedDict):
    to: str
    text: str

class RollRequestData(TypedDict):
    formula: str
    reason: str

class MoveRequestData(TypedDict):
    to: List[int]

class TargetedActionData(TypedDict):
    target_name: str
    action_type: str
    formula: str
    reason: str
    damage_type: str

class PingData(TypedDict):
    q: int
    r: int
    color: str

class AttackRequestData(TypedDict):
    target_name: str
    weapon_name: str
    hit_bonus: int
    damage_formula: str
    damage_type: str

class PromptSaveData(TypedDict):
    stat: str
    dc: int
    damage_formula: str
    half_on_success: bool
    source_name: str
    damage_type: str

class SaveResultData(TypedDict):
    stat: str
    roll_total: int
    is_crit: bool
    is_fail: bool
    dc: int
    damage_formula: str
    half_on_success: bool
    source_name: str
    damage_type: str

class PromptReactionData(TypedDict):
    reaction_type: str
    source_name: str
    target_name: str
    details: Dict[str, Any]

class ReactionResponseData(TypedDict):
    reaction_type: str
    accepted: bool
    source_name: str
    target_name: str
    details: Dict[str, Any]

class ResolveAoEData(TypedDict):
    aoe_index: int
    stat: str
    dc: int
    damage_formula: str
    half_on_success: bool
    damage_type: str

class DoorRequestData(TypedDict, total=False):
    q: int
    r: int
    state: Optional[str]
    method: str
    key_item: Optional[str]

class RoomPinData(TypedDict):
    pin: Dict[str, Any]
    action: str

class BlindRollData(TypedDict):
    formula: str
    reason: str

class AutomationSettingsData(TypedDict):
    mode: str
    settings: Dict[str, Any]

class ApplyPendingDamageData(TypedDict, total=False):
    pending_id: str
    action: str
    custom_amount: Optional[int]

class ResolvePendingDoorData(TypedDict):
    pending_id: str
    outcome: str

# --- Messaggi Client -> Server ---
def make_join(name: str, position: Optional[List[int]] = None) -> ProtocolMessage:
    data: Dict[str, Any] = {"name": name}
    if position:
        data["position"] = position
    return {"type": "JOIN", "data": data}

def make_chat(text: str) -> ProtocolMessage:
    return {"type": "CHAT", "data": {"text": text}}

def make_whisper(to: str, text: str) -> ProtocolMessage:
    return {"type": "WHISPER", "data": {"to": to, "text": text}}

def make_roll_request(formula, reason=""):
    return {"type": "ROLL_REQUEST", "data": {"formula": formula, "reason": reason}}

def make_move_request(x, y):
    return {"type": "MOVE_REQUEST", "data": {"to": [x, y]}}

def make_targeted_action_request(target_name, action_type, formula, reason="", damage_type="Tagliente"):
    return {"type": "TARGETED_ACTION_REQUEST", "data": {
        "target_name": target_name,
        "action_type": action_type,
        "formula": formula,
        "reason": reason,
        "damage_type": damage_type
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

def make_update_stats_request(hp, max_hp, initiative, conditions=None, temp_hp=0, light_radius=None, light_color=None, name=None):
    if conditions is None: conditions = []
    d = {"hp": hp, "max_hp": max_hp, "initiative": initiative, "conditions": conditions, "temp_hp": temp_hp}
    if light_radius is not None: d["light_radius"] = light_radius
    if light_color is not None: d["light_color"] = light_color
    if name is not None: d["name"] = name
    return {"type": "UPDATE_STATS_REQUEST", "data": d}

def make_player_stats_update(player_name, hp, max_hp, initiative, conditions=None, temp_hp=0, light_radius=None, light_color=None):
    if conditions is None: conditions = []
    d = {"name": player_name, "hp": hp, "max_hp": max_hp, "initiative": initiative, "conditions": conditions, "temp_hp": temp_hp}
    if light_radius is not None: d["light_radius"] = light_radius
    if light_color is not None: d["light_color"] = light_color
    return {"type": "PLAYER_STATS_UPDATE", "data": d}


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

def make_set_travel_role_request(role, marching_order="Centro"):
    return {"type": "SET_TRAVEL_ROLE_REQUEST", "data": {"role": role, "marching_order": marching_order}}

def make_start_combat_request(initiator_name=None):
    return {"type": "START_COMBAT_REQUEST", "data": {"initiator": initiator_name}}

def make_end_turn_request():
    return {"type": "END_TURN_REQUEST", "data": {}}

def make_dash_request():
    return {"type": "DASH_REQUEST", "data": {}}

def make_disengage_request():
    return {"type": "DISENGAGE_REQUEST", "data": {}}

def make_dodge_request():
    return {"type": "DODGE_REQUEST", "data": {}}

def make_help_request(target_name):
    return {"type": "HELP_REQUEST", "data": {"target_name": target_name}}

def make_short_rest_request(hd_spent=1, hp_recovered=0):
    return {"type": "SHORT_REST_REQUEST", "data": {"hd_spent": hd_spent, "hp_recovered": hp_recovered}}

def make_opportunity_alert(target_name, message=None):
    return {"type": "OPPORTUNITY_ALERT", "data": {"target_name": target_name, "message": message}}

def make_request_initiative():
    return {"type": "REQUEST_INITIATIVE", "data": {}}

def make_submit_initiative(initiative_total):
    return {"type": "SUBMIT_INITIATIVE", "data": {"initiative": initiative_total}}

def make_attack_request(target_name, weapon_name, hit_bonus, damage_formula, damage_type="Tagliente", cover="auto"):
    return {"type": "ATTACK_REQUEST", "data": {
        "target_name": target_name, "weapon_name": weapon_name,
        "hit_bonus": hit_bonus, "damage_formula": damage_formula,
        "damage_type": damage_type, "cover": cover
    }}


def make_force_save_request(targets, stat, dc, damage_formula, half_on_success, damage_type="Fuoco"):
    return {"type": "FORCE_SAVE_REQUEST", "data": {
        "targets": targets, "stat": stat, "dc": dc, "damage_formula": damage_formula,
        "half_on_success": half_on_success, "damage_type": damage_type
    }}

def make_prompt_save(stat, dc, damage_formula, half_on_success, source_name, damage_type="Fuoco"):
    return {"type": "PROMPT_SAVE", "data": {
        "stat": stat, "dc": dc, "damage_formula": damage_formula,
        "half_on_success": half_on_success, "source_name": source_name, "damage_type": damage_type
    }}

def make_save_result(stat, roll_total, is_crit, is_fail, dc, damage_formula, half_on_success, source_name, damage_type="Fuoco"):
    return {"type": "SAVE_RESULT", "data": {
        "stat": stat, "roll_total": roll_total, "is_crit": is_crit, "is_fail": is_fail,
        "dc": dc, "damage_formula": damage_formula, "half_on_success": half_on_success,
        "source_name": source_name, "damage_type": damage_type
    }}

def make_handout_broadcast(title, image_b64=None, content=None):
    return {"type": "HANDOUT_BROADCAST", "data": {"title": title, "image_b64": image_b64, "content": content}}

def make_toggle_wall_request(q, r):
    return {"type": "TOGGLE_WALL_REQUEST", "data": {"q": q, "r": r}}

def make_fow_update_broadcast(fow_revealed, fow_draft, fow_enabled=None):
    data = {"fow_revealed": fow_revealed, "fow_draft": fow_draft}
    if fow_enabled is not None:
        data["fow_enabled"] = fow_enabled
    return {"type": "FOW_UPDATE_BROADCAST", "data": data}

def make_map_data_update_broadcast(map_data):
    return {"type": "MAP_DATA_UPDATE", "data": {"map": map_data}}

def make_combat_state_update_broadcast(combat_active, turn_index, round_number, active_aoes, turn_player_name=""):
    return {"type": "COMBAT_STATE_UPDATE", "data": {
        "combat_active": combat_active,
        "turn_index": turn_index,
        "round_number": round_number,
        "active_aoes": active_aoes,
        "turn_player_name": turn_player_name
    }}

def make_audio_play_broadcast(url_or_name):
    return {"type": "AUDIO_PLAY_BROADCAST", "data": {"url": url_or_name}}

def make_custom_spell_request(spell_dict):
    return {"type": "CUSTOM_SPELL_REQUEST", "data": {"spell": spell_dict}}

def make_custom_spell_response(player_name, spell_dict, approved, reason=""):
    return {"type": "CUSTOM_SPELL_RESPONSE", "data": {"player_name": player_name, "spell": spell_dict, "approved": approved, "reason": reason}}

def make_campaign_starter_granted(items, full_sheet=None):
    return {"type": "CAMPAIGN_STARTER_GRANTED", "data": {"items": items, "full_sheet": full_sheet}}

# --- Tracce audio caricate dal DM ---
def make_audio_track_play(track_id, name, ext, size, channel="music", loop=False, volume=1.0):
    return {"type": "AUDIO_TRACK_PLAY", "data": {"track_id": track_id, "name": name, "ext": ext, "size": size,
                                                  "channel": channel, "loop": loop, "volume": volume}}

def make_audio_stop(channel="all"):
    return {"type": "AUDIO_STOP", "data": {"channel": channel}}

def make_audio_track_request(track_id):
    return {"type": "AUDIO_TRACK_REQUEST", "data": {"track_id": track_id}}

def make_audio_track_chunk(track_id, index, total, data_b64, ext=None):
    return {"type": "AUDIO_TRACK_CHUNK", "data": {"track_id": track_id, "index": index, "total": total, "data": data_b64, "ext": ext}}

def make_update_inspiration(has_inspiration: bool):
    return {"type": "UPDATE_INSPIRATION", "data": {"has_inspiration": has_inspiration}}

def make_give_gold_request(target_name: str, amount: int):
    return {"type": "GIVE_GOLD_REQUEST", "data": {"target_name": target_name, "amount": amount}}

def make_currency_request(coin: str, amount: int, reason: str = ""):
    return {"type": "CURRENCY_REQUEST", "data": {"coin": coin, "amount": amount, "reason": reason}}

def make_currency_response(player_name: str, coin: str, amount: int, approved: bool, reason: str = ""):
    return {"type": "CURRENCY_RESPONSE", "data": {"player_name": player_name, "coin": coin, "amount": amount, "approved": approved, "reason": reason}}

def make_item_approval_request(item: dict, slot_idx: int = None):
    return {"type": "ITEM_APPROVAL_REQUEST", "data": {"item": item, "slot_idx": slot_idx}}

def make_item_approval_response(player_name: str, item: dict, slot_idx: int, approved: bool, reason: str = ""):
    return {"type": "ITEM_APPROVAL_RESPONSE", "data": {"player_name": player_name, "item": item, "slot_idx": slot_idx, "approved": approved, "reason": reason}}

def make_journal_approval_request(field_name: str, content: str, title: str = ""):
    return {"type": "JOURNAL_APPROVAL_REQUEST", "data": {"field_name": field_name, "content": content, "title": title}}

def make_journal_approval_response(player_name: str, field_name: str, content: str, approved: bool, reason: str = ""):
    return {"type": "JOURNAL_APPROVAL_RESPONSE", "data": {"player_name": player_name, "field_name": field_name, "content": content, "approved": approved, "reason": reason}}

def make_clear_drawings_request():
    return {"type": "CLEAR_DRAWINGS_REQUEST", "data": {}}

def make_clear_drawings_broadcast():
    return {"type": "CLEAR_DRAWINGS_BROADCAST", "data": {}}

# --- Porte Interattive & Spille di Mappa ---
def make_toggle_door_request(q: int, r: int, state: str = None, method: str = "lockpick", key_item: str = None):
    return {"type": "TOGGLE_DOOR_REQUEST", "data": {"q": q, "r": r, "state": state, "method": method, "key_item": key_item}}

def make_room_pin_request(pin_dict: dict, action: str = "add"):
    return {"type": "ROOM_PIN_REQUEST", "data": {"pin": pin_dict, "action": action}}

def make_blind_roll_request(formula: str, reason: str = ""):
    return {"type": "BLIND_ROLL_REQUEST", "data": {"formula": formula, "reason": reason}}

# --- Reazioni 5e & Risoluzione AoE ---
def make_prompt_reaction(reaction_type: str, source_name: str, target_name: str, details: dict = None):
    return {"type": "PROMPT_REACTION", "data": {
        "reaction_type": reaction_type,
        "source_name": source_name,
        "target_name": target_name,
        "details": details or {}
    }}

def make_reaction_response(reaction_type: str, accepted: bool, source_name: str, target_name: str, details: dict = None):
    return {"type": "REACTION_RESPONSE", "data": {
        "reaction_type": reaction_type,
        "accepted": accepted,
        "source_name": source_name,
        "target_name": target_name,
        "details": details or {}
    }}

def make_resolve_aoe_request(aoe_index: int, stat: str, dc: int, damage_formula: str, half_on_success: bool = True, damage_type: str = "Fuoco"):
    return {"type": "RESOLVE_AOE_REQUEST", "data": {
        "aoe_index": aoe_index,
        "stat": stat,
        "dc": dc,
        "damage_formula": damage_formula,
        "half_on_success": half_on_success,
        "damage_type": damage_type
    }}

# --- Modalità Gestione Campagna (Tavolo Tradizionale vs Full Automation) ---
def make_set_automation_mode_request(mode: str, settings: dict = None):
    return {"type": "SET_AUTOMATION_MODE_REQUEST", "data": {"mode": mode, "settings": settings or {}}}

def make_automation_settings_broadcast(mode: str, settings: dict):
    return {"type": "AUTOMATION_SETTINGS_BROADCAST", "data": {"mode": mode, "settings": settings}}

def make_apply_pending_damage_request(pending_id: str, action: str = "apply", custom_amount: int = None):
    return {"type": "APPLY_PENDING_DAMAGE_REQUEST", "data": {"pending_id": pending_id, "action": action, "custom_amount": custom_amount}}

def make_resolve_pending_door_request(pending_id: str, outcome: str = "open"):
    return {"type": "RESOLVE_PENDING_DOOR_REQUEST", "data": {"pending_id": pending_id, "outcome": outcome}}

# --- Registro Missioni (Quest Log) & Documenti Condivisi (Handouts) ---
def make_quest_list_update(quests: list):
    return {"type": "QUEST_LIST_UPDATE", "data": {"quests": quests}}

def make_quest_action_request(action: str, quest_data: dict):
    return {"type": "QUEST_ACTION_REQUEST", "data": {"action": action, "quest": quest_data}}

def make_handout_share_broadcast(title: str, content: str, image_path: str = "", sender: str = "Dungeon Master"):
    return {"type": "HANDOUT_SHARE_BROADCAST", "data": {
        "title": title,
        "content": content,
        "image_path": image_path,
        "sender": sender
    }}

def make_legendary_action_request(boss_name: str, action_name: str = "Azione Leggendaria", cost: int = 1):
    return {"type": "LEGENDARY_ACTION_REQUEST", "data": {
        "boss_name": boss_name,
        "action_name": action_name,
        "cost": cost
    }}


