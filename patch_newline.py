import re

def fix_newline():
    with open('client/client.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('if "\n" in message:', 'if "\\n" in message:')
    with open('client/client.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    with open('server/dm_gui.py', 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace('if "\n" in message:', 'if "\\n" in message:')
    with open('server/dm_gui.py', 'w', encoding='utf-8') as f:
        f.write(content)

fix_newline()
