import io
with io.open('client/client.py', 'r', encoding='utf-8') as f:
    content = f.read()

t1 = '''        self.sheet_ui = CharacterSheetUI(self.master, self.active_character, self.character_manager, 
                         on_save_callback=self.on_character_saved, 
                         roll_callback=self.do_roll, 
                         trade_callback=self.do_trade, attack_callback=self.on_attack_action, 
                         players_list_callback=self.get_player_names)'''
r1 = '''        self.sheet_ui = CharacterSheetUI(self.master, self.active_character, self.character_manager, 
                         on_save_callback=self.on_character_saved, 
                         roll_callback=self.do_roll, 
                         trade_callback=self.do_trade, attack_callback=self.on_attack_action, 
                         players_list_callback=self.get_player_names, long_rest_callback=self.request_long_rest)'''
content = content.replace(t1, r1)

t2 = '''    def request_move(self, clicked_hex):'''
r2 = '''    def request_long_rest(self):
        if not self.is_connected: return
        self.network.send({"type": "LONG_REST_REQUEST", "data": {}})

    def request_move(self, clicked_hex):'''
content = content.replace(t2, r2)

t3 = '''            elif msg_type == "LOOT_TAKEN":
                pass # Handled by inventory update logic if needed'''
r3 = '''            elif msg_type == "PROMPT_LONG_REST_VOTE":
                initiator = msg_data.get("initiator", "Qualcuno")
                if messagebox.askyesno("Voto Riposo Lungo", f"{initiator} propone un Riposo Lungo. Questo resettera' slot, salute e dadi vita.\\n\\nSei d'accordo?"):
                    self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": True}})
                else:
                    self.network.send({"type": "LONG_REST_VOTE", "data": {"vote": False}})
            elif msg_type == "DO_LONG_REST":
                if self.active_character:
                    self.active_character.long_rest()
                    self.character_manager.update_character(self.active_character)
                    from common.protocol import make_update_full_sheet_request
                    self.network.send(make_update_full_sheet_request(self.active_character.to_dict()))
                    messagebox.showinfo("Riposo Lungo Completato", "Il gruppo ha completato un Riposo Lungo. Hai recuperato le tue statistiche.")
                    if getattr(self, "sheet_ui", None) and self.sheet_ui.winfo_exists():
                        self.sheet_ui.load_data()
            elif msg_type == "LOOT_TAKEN":
                pass # Handled by inventory update logic if needed'''
if "PROMPT_LONG_REST_VOTE" not in content:
    content = content.replace(t3, r3)

with io.open('client/client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched client.py')
