from server.rules.combat import *
from server.rules.movement import *
from server.rules.map_interaction import *
from server.rules.inventory import *
from server.rules.character import *
from server.rules.chat import *
from server.rules.audio import handle_audio_track_request

command_handlers = {
    "DRAW_REQUEST": handle_draw_request,
    "CHAT": handle_chat,
    "WHISPER": handle_whisper,
    "ROLL_REQUEST": handle_roll_request,
    "MOVE_REQUEST": handle_move_request,
    "UPDATE_STATS_REQUEST": handle_update_stats_request,
    "UPDATE_FULL_SHEET_REQUEST": handle_update_full_sheet_request,
    "TARGETED_ACTION_REQUEST": handle_targeted_action,
    "ATTACK_REQUEST": handle_attack_request,
    "GIVE_ITEM_REQUEST": handle_give_item_request,
    "GIVE_GOLD_REQUEST": handle_give_gold_request,
    "CREATE_AOE_REQUEST": handle_create_aoe_request,
    "CLEAR_AOES_REQUEST": handle_clear_aoes_request,
    "SET_TRAVEL_ROLE_REQUEST": handle_set_travel_role_request,
    "START_COMBAT_REQUEST": handle_start_combat_request,
    "END_TURN_REQUEST": handle_end_turn_request,
    "SUBMIT_INITIATIVE": handle_submit_initiative,
    "PING_REQUEST": handle_ping_request,
    "FORCE_SAVE_REQUEST": handle_force_save_request,
    "SAVE_RESULT": handle_save_result_request,
    "TOGGLE_WALL_REQUEST": handle_toggle_wall_request,
    "TOGGLE_COVER_REQUEST": handle_toggle_cover_request,
    "TAKE_LOOT_REQUEST": handle_take_loot_request,
    "LONG_REST_REQUEST": handle_long_rest_request,
    "LONG_REST_VOTE": handle_long_rest_vote,
    "BUY_ITEM_REQUEST": handle_buy_item_request,
    "CUSTOM_SPELL_REQUEST": handle_custom_spell_request,
    "AUDIO_TRACK_REQUEST": handle_audio_track_request,
    "DASH_REQUEST": handle_dash_request,
    "DISENGAGE_REQUEST": handle_disengage_request,
    "DODGE_REQUEST": handle_dodge_request,
    "HELP_REQUEST": handle_help_request,
    "SHORT_REST_REQUEST": handle_short_rest_request,
    "SPEND_LEGENDARY_ACTION_REQUEST": handle_spend_legendary_action_request,
    "CURRENCY_REQUEST": handle_currency_request,
    "ITEM_APPROVAL_REQUEST": handle_item_approval_request,
    "JOURNAL_APPROVAL_REQUEST": handle_journal_approval_request,
    "CLEAR_DRAWINGS_REQUEST": handle_clear_drawings_request,
    "TOGGLE_DOOR_REQUEST": handle_toggle_door_request,
    "ROOM_PIN_REQUEST": handle_room_pin_request,
    "RESOLVE_AOE_REQUEST": handle_resolve_aoe_request,
    "BLIND_ROLL_REQUEST": handle_blind_roll_request,
    "REACTION_RESPONSE": handle_reaction_response,
    "SET_AUTOMATION_MODE_REQUEST": handle_set_automation_mode_request,
    "APPLY_PENDING_DAMAGE_REQUEST": handle_apply_pending_damage_request,
    "RESOLVE_PENDING_DOOR_REQUEST": handle_resolve_pending_door_request,
    "LEGENDARY_ACTION_REQUEST": handle_spend_legendary_action_request,
    "QUEST_ACTION_REQUEST": handle_quest_action_request,
    "HANDOUT_SHARE_REQUEST": handle_handout_share_request,
}


