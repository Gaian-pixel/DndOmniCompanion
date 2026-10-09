import re

def fix_dm_log_calls():
    with open('server/dm_gui.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix PRIVATE_MESSAGE_RECEIVED log_to_chat
    content = content.replace(
        'self.log_to_chat(f"[{player_name}]: {text}", tab_name=player_name)',
        'self.log_to_chat(text, tab_name=player_name, sender=player_name, color="#5865F2")'
    )
    
    # Fix send_dm_chat
    content = content.replace(
        'self.log_to_chat(f"[DM -> Tutti]: {text}", tab_name="Sistema")',
        'self.log_to_chat(text, tab_name="Sistema", sender="DM", color="#EB459E")'
    )
    content = content.replace(
        'self.log_to_chat(f"[Tu -> {active_tab_name}]: {text}", tab_name=active_tab_name)',
        'self.log_to_chat(text, tab_name=active_tab_name, sender="DM", color="#EB459E")'
    )
    
    with open('server/dm_gui.py', 'w', encoding='utf-8') as f:
        f.write(content)

fix_dm_log_calls()
