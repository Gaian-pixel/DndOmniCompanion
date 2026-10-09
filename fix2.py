import io
with io.open('client/client.py', 'r', encoding='utf-8') as f:
    content = f.read()

t = '''        if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\n\nSei d'accordo?"):'''
r = '''        if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\\n\\nSei d'accordo?"):'''
content = content.replace(t, r)
with io.open('client/client.py', 'w', encoding='utf-8') as f:
    f.write(content)
