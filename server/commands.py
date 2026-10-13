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
}
