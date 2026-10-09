import io
with io.open('client/character_sheet_ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

t1 = 'def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, players_list_callback=None, attack_callback=None):'
r1 = 'def __init__(self, master, character, manager, on_save_callback=None, roll_callback=None, trade_callback=None, players_list_callback=None, attack_callback=None, long_rest_callback=None):'
content = content.replace(t1, r1)

t2 = 'self.roll_callback = roll_callback'
r2 = 'self.roll_callback = roll_callback\n        self.long_rest_callback = long_rest_callback'
content = content.replace(t2, r2)

t3 = 'command=self.recover_spell_slots'
r3 = 'command=self.long_rest'
content = content.replace(t3, r3)

t4 = '''    def long_rest(self):
        if messagebox.askyesno("Riposo Lungo", "Effettuare un riposo lungo?"):
            self.character.long_rest()
            self.load_data()
            self.manager.update_character(self.character)
            messagebox.showinfo("Riposo Lungo", "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.")'''
            
r4 = '''    def long_rest(self):
        if hasattr(self, 'long_rest_callback') and self.long_rest_callback:
            self.long_rest_callback()
        else:
            if messagebox.askyesno("Riposo Lungo", "Effettuare un riposo lungo?"):
                self.character.long_rest()
                self.load_data()
                self.manager.update_character(self.character)
                messagebox.showinfo("Riposo Lungo", "Hai effettuato un riposo lungo! HP, Dadi Vita, Tiri contro la Morte e Slot Incantesimo sono stati recuperati.")'''
content = content.replace(t4, r4)

with io.open('client/character_sheet_ui.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched character_sheet_ui.py')
