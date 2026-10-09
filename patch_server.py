import io
with io.open('server/commands.py', 'r', encoding='utf-8') as f:
    content = f.read()

t1 = '''command_handlers['TAKE_LOOT_REQUEST'] = handle_take_loot_request'''
r1 = '''def handle_long_rest_request(data, player, game_state):
    if getattr(game_state, "combat_active", False):
        from common.network_utils import send_message
        if getattr(player, "conn", None): send_message(player.conn, {"type": "ERROR_REPLY", "data": {"text": "Non puoi riposare durante il combattimento!"}})
        return
        
    players = getattr(game_state, "players", [])
    active_conns = len([p for p in players if getattr(p, "conn", None)])
    if active_conns == 0: return
        
    game_state.ongoing_rest_vote = {"initiator": player.name, "votes_needed": active_conns, "votes_received": 0}
    game_state.log_dm_message(f"[Sistema] {player.name} ha proposto un Riposo Lungo. In attesa di approvazione da {active_conns} giocatori.")
    from common.network_utils import send_message
    for p in players:
        if getattr(p, "conn", None):
            send_message(p.conn, {"type": "PROMPT_LONG_REST_VOTE", "data": {"initiator": player.name}})

def handle_long_rest_vote(data, player, game_state):
    vote = data.get("vote", False)
    vote_data = getattr(game_state, "ongoing_rest_vote", None)
    if not vote_data: return
    
    if not vote:
        game_state.log_dm_message(f"[Sistema] {player.name} ha RIFIUTATO il riposo lungo. Votazione annullata.")
        from common.protocol import make_chat_broadcast
        broadcast(game_state, make_chat_broadcast("Sistema", f"Il Riposo Lungo proposto da {vote_data['initiator']} e' stato annullato perche' {player.name} non ha approvato."))
        game_state.ongoing_rest_vote = None
        return
        
    vote_data["votes_received"] += 1
    if vote_data["votes_received"] >= vote_data["votes_needed"]:
        game_state.log_dm_message(f"[Sistema] Tutti i giocatori hanno approvato il Riposo Lungo!")
        from common.protocol import make_chat_broadcast
        broadcast(game_state, make_chat_broadcast("Sistema", f"Il gruppo si e' accampato per un Riposo Lungo. Tutti recuperano HP e Slot."))
        from common.network_utils import send_message
        for p in getattr(game_state, "players", []):
            if getattr(p, "conn", None):
                send_message(p.conn, {"type": "DO_LONG_REST", "data": {}})
        game_state.ongoing_rest_vote = None

command_handlers['TAKE_LOOT_REQUEST'] = handle_take_loot_request
command_handlers['LONG_REST_REQUEST'] = handle_long_rest_request
command_handlers['LONG_REST_VOTE'] = handle_long_rest_vote'''

if t1 in content:
    with io.open('server/commands.py', 'w', encoding='utf-8') as f:
        f.write(content.replace(t1, r1))
    print("Patched server/commands.py")
else:
    print("Target not found")
