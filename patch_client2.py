import io
with io.open('client/client.py', 'r', encoding='utf-8') as f:
    content = f.read()

t1 = '''            "PING_BROADCAST": self.handle_ping_broadcast,
            "DRAW_BROADCAST": self.handle_draw_broadcast
        }'''
r1 = '''            "PING_BROADCAST": self.handle_ping_broadcast,
            "DRAW_BROADCAST": self.handle_draw_broadcast,
            "PROMPT_LONG_REST_VOTE": self.handle_prompt_long_rest_vote,
            "DO_LONG_REST": self.handle_do_long_rest
        }'''
content = content.replace(t1, r1)

t2 = '''    def handle_draw_broadcast(self, data):'''
r2 = '''    def handle_prompt_long_rest_vote(self, data):
        initiator = data.get("initiator", "Qualcuno")
        if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\n\nSei d'accordo?"):
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": True}})
        else:
            self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": False}})

    def handle_do_long_rest(self, data):
        if self.active_character:
            self.active_character.long_rest()
            self.character_manager.update_character(self.active_character)
            from common.protocol import make_update_full_sheet_request
            self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
            messagebox.showinfo("Riposo Lungo Completato", "Il gruppo ha completato un Riposo Lungo. Hai recuperato le tue statistiche.")
            if getattr(self, "sheet_ui", None) and self.sheet_ui.winfo_exists():
                self.sheet_ui.load_data()

    def handle_draw_broadcast(self, data):'''
content = content.replace(t2, r2)

with io.open('client/client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched client.py 2')
