import unittest
import tkinter as tk
from unittest.mock import MagicMock
from common.srd_offline import extract_and_normalize_attributes
from server.dm_dialogs import CustomNPCDialog
from components.statblock_view import StatblockCardView


class TestCustomMonsterAttributes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            cls.root.destroy()

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter display not available")

    def test_custom_npc_dialog_ability_scores_and_modifiers(self):
        saved_sheet = {}

        def on_saved(sheet):
            saved_sheet.update(sheet)

        dialog = CustomNPCDialog(master=self.root, on_save_callback=on_saved)

        # Inserimento dati generali
        dialog.name_entry.delete(0, tk.END)
        dialog.name_entry.insert(0, "Capo Orco Feroce")

        dialog.hp_entry.delete(0, tk.END)
        dialog.hp_entry.insert(0, "45")

        dialog.ac_entry.delete(0, tk.END)
        dialog.ac_entry.insert(0, "16")

        dialog.cr_entry.delete(0, tk.END)
        dialog.cr_entry.insert(0, "3")

        dialog.xp_entry.delete(0, tk.END)
        dialog.xp_entry.insert(0, "700")

        # Modifica caratteristiche: FOR=18 (+4), DES=14 (+2), COS=16 (+3), INT=8 (-1), SAG=12 (+1), CAR=10 (+0)
        scores = {
            "FOR": "18",
            "DES": "14",
            "COS": "16",
            "INT": "8",
            "SAG": "12",
            "CAR": "10",
        }
        for code, val in scores.items():
            entry, var = dialog.stat_entries[code]
            var.set(val)

        # Verifica calcolo dinamico badge modificatori
        self.assertEqual(dialog.stat_mod_labels["FOR"].cget("text"), "(+4)")
        self.assertEqual(dialog.stat_mod_labels["DES"].cget("text"), "(+2)")
        self.assertEqual(dialog.stat_mod_labels["COS"].cget("text"), "(+3)")
        self.assertEqual(dialog.stat_mod_labels["INT"].cget("text"), "(-1)")
        self.assertEqual(dialog.stat_mod_labels["SAG"].cget("text"), "(+1)")
        self.assertEqual(dialog.stat_mod_labels["CAR"].cget("text"), "(+0)")

        # Verifica auto-aggiornamento iniziativa da Destrezza
        self.assertEqual(dialog.init_entry.get(), "2")

        # Salvataggio
        dialog.on_save()

        # Verifiche scheda salvata
        self.assertEqual(saved_sheet.get("name"), "Capo Orco Feroce")
        self.assertEqual(saved_sheet.get("hp"), 45)
        self.assertEqual(saved_sheet.get("ac"), 16)
        self.assertEqual(saved_sheet.get("initiative"), 2)
        self.assertEqual(saved_sheet.get("cr"), "3")
        self.assertEqual(saved_sheet.get("xp"), 700)

        # Verifiche caratteristiche 5e
        attrs = saved_sheet.get("attributes", {})
        self.assertEqual(attrs.get("FOR"), 18)
        self.assertEqual(attrs.get("STR"), 18)
        self.assertEqual(attrs.get("DES"), 14)
        self.assertEqual(attrs.get("DEX"), 14)
        self.assertEqual(attrs.get("COS"), 16)
        self.assertEqual(attrs.get("CON"), 16)
        self.assertEqual(attrs.get("INT"), 8)
        self.assertEqual(attrs.get("SAG"), 12)
        self.assertEqual(attrs.get("WIS"), 12)
        self.assertEqual(attrs.get("CAR"), 10)
        self.assertEqual(attrs.get("CHA"), 10)

        self.assertEqual(saved_sheet.get("strength"), 18)
        self.assertEqual(saved_sheet.get("dexterity"), 14)
        self.assertEqual(saved_sheet.get("constitution"), 16)
        self.assertEqual(saved_sheet.get("intelligence"), 8)
        self.assertEqual(saved_sheet.get("wisdom"), 12)
        self.assertEqual(saved_sheet.get("charisma"), 10)

    def test_compendium_custom_monster_statblock_rendering(self):
        # Simula un mostro custom salvato dal compendio
        custom_stats = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 13, "CAR": 8}
        full_attrs = extract_and_normalize_attributes({"attributes": custom_stats}, "Guerriero Coboldo")

        monster_data = {
            "name": "Guerriero Coboldo",
            "hp": 22,
            "hit_points": 22,
            "ac": 14,
            "armor_class": 14,
            "speed": "30 ft",
            "cr": "1/2",
            "challenge_rating": "1/2",
            "attributes": full_attrs,
            "strength": 16,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 10,
            "wisdom": 13,
            "charisma": 8,
            "desc": "Un guerriero coboldo armato di lancia arrugginita.",
            "is_custom": True,
        }

        # Rendering su StatblockCardView
        card = StatblockCardView(self.root)
        card.show_monster(monster_data)

        # Verifichiamo che i dati correnti del cardview contengano le statistiche
        self.assertIsNotNone(card.current_data)
        self.assertEqual(card.current_data["attributes"]["FOR"], 16)
        self.assertEqual(card.current_data["attributes"]["DES"], 12)
        self.assertEqual(card.current_data["strength"], 16)
        card.destroy()

    def test_campaign_editor_monster_manual_entry(self):
        from server.campaign_editor_ui import CampaignEncounterDialog
        enc_dialog = CampaignEncounterDialog(master=self.root)

        # Simula salvataggio tramite CustomNPCDialog callback invocato in add_monster_manual
        custom_monster_sheet = {
            "name": "Guardia d'Elite",
            "hp": 32,
            "ac": 16,
            "initiative": 1,
            "xp": 200,
            "attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 11, "CAR": 12},
            "strength": 16,
            "dexterity": 12,
            "constitution": 14,
            "intelligence": 10,
            "wisdom": 11,
            "charisma": 12
        }

        enc_dialog.monsters.append({
            "name": custom_monster_sheet["name"],
            "count": 1,
            "hp": custom_monster_sheet["hp"],
            "initiative": custom_monster_sheet["initiative"],
            "xp": custom_monster_sheet["xp"],
            "ac": custom_monster_sheet["ac"],
            "attributes": custom_monster_sheet["attributes"],
            "strength": custom_monster_sheet["strength"],
            "dexterity": custom_monster_sheet["dexterity"],
            "constitution": custom_monster_sheet["constitution"],
            "intelligence": custom_monster_sheet["intelligence"],
            "wisdom": custom_monster_sheet["wisdom"],
            "charisma": custom_monster_sheet["charisma"],
            "sheet": custom_monster_sheet
        })
        enc_dialog.refresh_monsters_list()

        self.assertEqual(len(enc_dialog.monsters), 1)
        m = enc_dialog.monsters[0]
        self.assertEqual(m["name"], "Guardia d'Elite")
        self.assertEqual(m["strength"], 16)
        self.assertEqual(m["dexterity"], 12)
        self.assertEqual(m["ac"], 16)

        enc_dialog.destroy()


if __name__ == "__main__":
    unittest.main()
