import unittest
import tkinter as tk
from client.character_manager import Character
from client.progression_ui import LevelUpDialog, CLASS_MAP, HIT_DICE_MAP


class TestLevelUpProgression(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_fighter_subclass_and_features_progression(self):
        """Verifica che un Guerriero che sale al livello 3 possa scegliere l'Archetipo e riceva i privilegi corretti."""
        fgt = Character(name="Gildor")
        fgt.char_class = "Guerriero"
        fgt.level = 2
        fgt.hp_max = 20
        fgt.hp_current = 20
        fgt.attributes["COS"] = 14 # Mod +2

        applied = []
        dlg = LevelUpDialog(self.root, fgt, lambda: applied.append(True))
        dlg.withdraw()

        # Verifica dado vita e opzioni
        self.assertEqual(dlg.hit_die, 10)
        self.assertEqual(dlg.avg_hp, 6)

        # Seleziona sottoclasse Campione
        champ = [s for s in dlg.matching_subclasses if "Campione" in s["name"]][0]
        dlg.subclass_choice_var.set(champ["name"])
        dlg._on_subclass_selected()

        # Applica
        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(fgt.level, 3)
        self.assertEqual(fgt.hp_max, 28) # 20 + 6 (media) + 2 (COS) = 28
        self.assertIn("Campione", fgt.subclass)
        self.assertIn("Critico Migliorato", fgt.features)

    def test_wizard_spell_selection_on_level_up(self):
        """Verifica che un Mago al livello 3 sblocchi gli incantesimi di 2° cerchio e possa selezionarli nel Grimorio."""
        wiz = Character(name="Elminster")
        wiz.char_class = "Mago"
        wiz.level = 2
        wiz.hp_max = 14
        wiz.hp_current = 14
        wiz.attributes = {"FOR": 8, "DES": 14, "COS": 12, "INT": 16, "SAG": 12, "CAR": 10}
        wiz.spellbook = [{"name": "Dardo Incantato", "level": 1}]

        applied = []
        dlg = LevelUpDialog(self.root, wiz, lambda: applied.append(True))
        dlg.withdraw()

        # Verifica che gli incantesimi idonei fino al 2° cerchio siano stati caricati
        self.assertGreater(len(dlg.all_eligible_spells), 100)
        acid_arrow = [s for s in dlg.all_eligible_spells if "Acid Arrow" in s["name"] or "Freccia Acida" in s.get("name_it", "")][0]
        dlg.selected_spells.append(acid_arrow)

        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(wiz.level, 3)
        self.assertEqual(wiz.spell_slots["1"]["max"], 4)
        self.assertEqual(wiz.spell_slots["2"]["max"], 2)
        # Verifica aggiunta incantesimo al Grimorio
        self.assertTrue(any("Freccia Acida" in s["name"] or "Acid Arrow" in s["name"] for s in wiz.spellbook))

    def test_asi_ability_score_improvement_at_level_4(self):
        """Verifica che al livello 4 l'ASI aumenti correttamente la statistica scelta."""
        rogue = Character(name="Shadow")
        rogue.char_class = "Ladro"
        rogue.level = 3
        rogue.hp_max = 24
        rogue.hp_current = 24
        rogue.attributes = {"FOR": 10, "DES": 16, "COS": 14, "INT": 12, "SAG": 12, "CAR": 10}

        applied = []
        dlg = LevelUpDialog(self.root, rogue, lambda: applied.append(True))
        dlg.withdraw()

        self.assertTrue(dlg.has_asi)
        dlg.asi_choice_var.set("single")
        dlg.asi_single_stat.set("DES")
        dlg.apply()

        self.assertEqual(len(applied), 1)
        self.assertEqual(rogue.level, 4)
        self.assertEqual(rogue.attributes["DES"], 18)

    def test_multiclass_hit_die_refresh_feat_list_and_warlock_no_duplication(self):
        fgt = Character(name="Eldrin")
        fgt.char_class = "Guerriero"
        fgt.classes = {"Guerriero": 3}
        fgt.level = 3
        fgt.hp_max = 28
        fgt.hp_current = 28
        fgt.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 14, "SAG": 10, "CAR": 10}
        fgt.starting_kit_applied = True

        dlg = LevelUpDialog(self.root, fgt, lambda: None)
        dlg.withdraw()
        self.assertEqual(dlg.hit_die, 10)
        dlg.target_class_var.set("Mago")
        dlg._on_multiclass_selected()
        self.assertEqual(dlg.hit_die, 6)
        self.assertEqual(dlg.avg_hp, 4)
        def _collect_texts(w):
            txts = []
            for ch in w.winfo_children():
                try:
                    t = ch.cget("text")
                    if t:
                        txts.append(str(t))
                except Exception:
                    pass
                txts.extend(_collect_texts(ch))
            return txts
        hp_texts = " ".join(_collect_texts(dlg.tab_health))
        self.assertIn("1d6", hp_texts)
        dlg.destroy()

        # Feat selection updates character.feats too
        fgt2 = Character(name="Bruenor", char_class="Guerriero", level=3)
        fgt2.classes = {"Guerriero": 3}
        fgt2.attributes = {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10}
        fgt2.starting_kit_applied = True
        dlg2 = LevelUpDialog(self.root, fgt2, lambda: None)
        dlg2.withdraw()
        dlg2.asi_choice_var.set("feat")
        feat_opts = list(dlg2.asi_feat_choice["values"]) if hasattr(dlg2, "asi_feat_choice") else []
        if feat_opts:
            chosen_f = feat_opts[0]
            dlg2.asi_feat_choice.set(chosen_f)
            dlg2.apply()
            self.assertIn(chosen_f, fgt2.feats)
        else:
            dlg2.destroy()

        # Warlock level-up keeps Pact Magic strictly in pact_slots, never duplicated into spell_slots
        war = Character(name="Malakor", char_class="Warlock", level=1)
        war.classes = {"Warlock": 1}
        war.pact_slots = {"max": 1, "current": 1, "level": 1}
        war.starting_kit_applied = True
        dlg3 = LevelUpDialog(self.root, war, lambda: None)
        dlg3.withdraw()
        dlg3.api_data = {"spellcasting": {"spell_slots_level_1": 2}}
        dlg3.apply()
        self.assertEqual(war.pact_slots.get("max"), 2)
        self.assertEqual(war.spell_slots["1"]["max"], 0)

    def test_wizard_en_4d6_tce_swap_and_warlock_lv1(self):
        import time
        import urllib.request
        from unittest.mock import MagicMock, patch
        from common.i18n import get_language, set_language
        from client.character_creation_wizard import CharacterCreationWizardFrame
        old_lang = get_language()
        wiz = None
        try:
            set_language("en")
            created = []
            wiz = CharacterCreationWizardFrame(self.root, manager=MagicMock(), on_complete_callback=lambda c: created.append(c))
            wiz.char_data["char_class"] = "Warlock"
            wiz.char_data["race"] = "Umano"
            wiz.char_data["tasha_origin"] = True
            wiz.char_data["tasha_prof_swap"] = "Athletics -> Stealth"
            wiz.current_step = 2
            wiz.show_step()
            wiz.gen_method_var.set("Roll 4d6 (Drop Lowest)")
            wiz.rolled_pool = [15, 14, 14, 12, 10, 8]
            for idx, attr in enumerate(["FOR", "DES", "COS", "INT", "SAG", "CAR"]):
                wiz.attr_vars[attr].set(wiz.rolled_pool[idx])
            with patch("common.messagebox.messagebox.showerror") as mock_err, \
                 patch("common.messagebox.messagebox.showinfo"), \
                 patch("urllib.request.urlopen", side_effect=OSError("offline")):
                wiz.next_step()
                mock_err.assert_not_called()
                self.assertEqual(wiz.current_step, 3)

                # Step 4 (Background): rolling RP traits in English must resolve localized background
                wiz.bg_name_var.set("Soldier")
                wiz._roll_all_roleplay_traits()
                from client.character_creation_wizard import BACKGROUNDS
                self.assertIn(wiz.trait_var.get(), BACKGROUNDS["Soldato"]["traits"])

                wiz.char_data["name"] = "Hexen"
                wiz.finish_creation()
                for _ in range(40):
                    if created:
                        break
                    time.sleep(0.05)
                    self.root.update()
            self.assertEqual(len(created), 1)
            pg = created[0]
            self.assertIn("[Origine TCE - Scambio Competenze]: Athletics -> Stealth", pg.features)
            self.assertEqual(pg.skills.get("Furtività"), 1)
            self.assertEqual(pg.pact_slots.get("max"), 1)
            self.assertEqual(pg.spell_slots["1"]["max"], 0)
        finally:
            if wiz is not None:
                try:
                    wiz.destroy()
                except Exception:
                    pass
            set_language(old_lang)

    def test_server_full_sheet_authority_qty0_multiclass_asi_and_levelup_hp(self):
        import queue
        from common.game_state import GameState, Player
        from common.protocol import make_update_full_sheet_request
        from server.rules.character import handle_update_full_sheet_request
        import copy

        gs = GameState(queue.Queue())
        p = Player("MulticlassTester")
        p.hp = 26
        p.max_hp = 26
        p.ac = 14
        p.full_sheet = {
            "name": "MulticlassTester",
            "char_class": "Guerriero / Mago",
            "classes": {"Guerriero": 2, "Mago": 3},
            "level": 5,
            "hp_current": 26,
            "hp_max": 26,
            "ac": 14,
            "attributes": {"FOR": 14, "DES": 12, "COS": 14, "INT": 16, "SAG": 10, "CAR": 10},
            "inventory_grid": [{"name": "Frecce", "qty": 10, "type": "Munizione"}] + [None] * 24,
            "weapons": [],
            "spellbook": [],
            "currency": {"MR": 0, "MA": 0, "ME": 0, "MO": 10, "MP": 0},
            "starting_kit_applied": True,
            "campaign_starter_received": True,
        }
        gs.players = [p]

        # 1. Non-DM setting stack qty=0 must stay 0 (not bounce to 1)
        payload_qty0 = copy.deepcopy(p.full_sheet)
        payload_qty0["inventory_grid"][0]["qty"] = 0
        handle_update_full_sheet_request(make_update_full_sheet_request(payload_qty0)["data"], p, gs)
        self.assertEqual(p.full_sheet["inventory_grid"][0]["qty"], 0)

        # 2. Guerriero 2 / Mago 3 -> Guerriero 2 / Mago 4 (tot 6): Mago Lv4 earns ASI (+2 INT) and HP max increases cleanly
        payload_lvlup = copy.deepcopy(p.full_sheet)
        payload_lvlup["classes"] = {"Guerriero": 2, "Mago": 4}
        payload_lvlup["level"] = 6
        payload_lvlup["attributes"]["INT"] = 18
        payload_lvlup["hp_max"] = 32
        payload_lvlup["hp_current"] = 32
        handle_update_full_sheet_request(make_update_full_sheet_request(payload_lvlup)["data"], p, gs)
        self.assertEqual(p.full_sheet["level"], 6)
        self.assertEqual(p.full_sheet["attributes"]["INT"], 18)
        self.assertEqual(p.full_sheet["hp_max"], 32)
        self.assertEqual(p.max_hp, 32)

        # 3. Non-ASI multiclass total level 4 (Guerriero 3 / Mago 1) cannot claim ASI
        p2 = Player("NoAsiYet")
        p2.hp = 24
        p2.max_hp = 24
        p2.full_sheet = {
            "name": "NoAsiYet",
            "char_class": "Guerriero",
            "classes": {"Guerriero": 3},
            "level": 3,
            "hp_current": 24,
            "hp_max": 24,
            "attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 14, "SAG": 10, "CAR": 10},
            "inventory_grid": [None] * 25,
            "starting_kit_applied": True,
            "campaign_starter_received": True,
        }
        gs.players.append(p2)
        payload_mc4 = copy.deepcopy(p2.full_sheet)
        payload_mc4["classes"] = {"Guerriero": 3, "Mago": 1}
        payload_mc4["level"] = 4
        payload_mc4["attributes"]["FOR"] = 18
        payload_mc4["hp_max"] = 30
        handle_update_full_sheet_request(make_update_full_sheet_request(payload_mc4)["data"], p2, gs)
        self.assertEqual(p2.full_sheet["attributes"]["FOR"], 16)
        self.assertEqual(p2.full_sheet["hp_max"], 30)

    def test_draconic_hp_gated_to_sorcerer_levels_and_magic_preview_target(self):
        from client.character_manager import Character
        from client.progression_ui import LevelUpDialog

        # Guerriero 1 / Stregone 1 (Stirpe Draconica): taking Guerriero 2 must NOT add Draconic +1 HP
        c = Character(name="Kaelen", char_class="Stregone / Guerriero", level=2)
        c.classes = {"Stregone": 1, "Guerriero": 1}
        c.subclass = "Stirpe Draconica"
        c.subclasses = {"Stregone": "Stirpe Draconica"}
        c.attributes = {"FOR": 14, "DES": 12, "COS": 12, "INT": 10, "SAG": 10, "CAR": 16}
        c.hp_max = 16
        c.hp_current = 16
        c.starting_kit_applied = True

        dlg = LevelUpDialog(self.root, c, lambda: None)
        dlg.withdraw()
        dlg.target_class_var.set("Guerriero")
        dlg._on_multiclass_selected()
        # Fighter d10 avg 6 + COS +1 = +7 HP (NOT +8 from Draconic Sorcerer)
        dlg.hp_choice.set("media")
        dlg.apply()
        self.assertEqual(c.hp_max, 23)


if __name__ == "__main__":
    unittest.main()

