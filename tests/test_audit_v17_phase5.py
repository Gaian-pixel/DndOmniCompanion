"""
Test Suite per Fase 5 della Remediation Audit v17:
- 5.1: i18n, collisione Incapacitated, Artificer starting kit & bilingual aliases, _t keys
- 5.2: CampaignJournal integration, GameState.load_session & Player serialization completeness, debounced save
- 5.3: Packaging safety in build_release.py (exclusion of private manuals/campaigns/audio)
"""

import os
import sys
import unittest
import queue
import tempfile
import json

from common.i18n import (
    is_condition_active,
    translate_condition,
    CONDITIONS_EN_TO_IT,
    CONDITIONS_IT_TO_EN,
    _t,
    set_language
)
from common.starter_equipment import (
    CLASS_STARTING_KITS,
    CLASS_STARTING_SPELLS,
    CLASS_DEFAULT_SKILLS
)
from common.game_state import GameState, Player


class TestAuditV17Phase5(unittest.TestCase):
    def setUp(self):
        self.q = queue.Queue()
        self.gs = GameState(self.q)

    def test_5_1_i18n_incapacitated_and_conditions(self):
        """5.1 Verifica che Incapacitato e Privo di Sensi non collidano e siano correttamente risolti."""
        self.assertEqual(CONDITIONS_EN_TO_IT.get("Incapacitated"), "Incapacitato")
        self.assertEqual(CONDITIONS_EN_TO_IT.get("Unconscious"), "Incosciente")

        # Test bidirezionale con is_condition_active
        self.assertTrue(is_condition_active(["Incapacitato"], "Incapacitated"))
        self.assertTrue(is_condition_active(["Incapacitated"], "Incapacitato"))
        self.assertTrue(is_condition_active(["Privo di Sensi"], "Unconscious"))
        self.assertTrue(is_condition_active(["Incosciente"], "Unconscious"))
        self.assertTrue(is_condition_active(["Unconscious"], "Privo di Sensi"))
        self.assertTrue(is_condition_active(["Prono"], "Prone"))
        self.assertTrue(is_condition_active(["Prone"], "Prono"))
        self.assertTrue(is_condition_active(["Ira"], "Rage"))
        self.assertTrue(is_condition_active(["Benedizione"], "Bless"))
        self.assertFalse(is_condition_active(["Incapacitato"], "Unconscious"))

    def test_5_1_starter_equipment_bilingual_and_artificer(self):
        """5.1 Verifica presenza Artefice / Artificer e alias bilingui in starter_equipment."""
        self.assertIn("Artefice", CLASS_STARTING_KITS)
        self.assertIn("Artificer", CLASS_STARTING_KITS)
        self.assertIn("Artificer", CLASS_DEFAULT_SKILLS)
        
        artificer_kit = CLASS_STARTING_KITS["Artefice"]
        self.assertEqual(artificer_kit["ac_base"], 14)
        item_names = [it["name"] for it in artificer_kit["items"]]
        self.assertIn("Corazza a Scaglie", item_names)
        self.assertIn("Strumenti da Scasso", item_names)

        # Verifica classi bilingui
        for en_cls in ["Fighter", "Rogue", "Wizard", "Cleric", "Barbarian", "Bard", "Paladin", "Ranger", "Druid", "Monk", "Sorcerer", "Warlock", "Artificer"]:
            self.assertIn(en_cls, CLASS_STARTING_KITS, f"Manca starter kit per {en_cls}")

    def test_5_1_wizard_filter_classes_i18n_key(self):
        """5.1 Verifica chiave _t('wizard_filter_classes') in IT e EN."""
        set_language("it")
        self.assertEqual(_t("wizard_filter_classes"), "Filtra per Ruolo:")
        set_language("en")
        self.assertEqual(_t("wizard_filter_classes"), "Filter by Role:")
        set_language("it")

    def test_5_2_player_serialization_and_load_session(self):
        """5.2 Verifica ripristino integrale in GameState.load_session() e Player.to_dict/from_dict."""
        p = Player("TestHero")
        p.position = [4, 5]
        p.elevation = 20
        p.ac = 18
        p.size = 2
        p.is_hidden = True
        p.concentrating_on = "Benedizione"
        p.in_combat = True
        p.death_save_successes = 2
        p.death_save_failures = 1
        p.combat_initiative = 17
        p.active_effects = [{"name": "Benedizione", "type": "buff", "duration_rounds": 10}]
        
        d = p.to_dict()
        self.assertEqual(d["ac"], 18)
        self.assertEqual(d["elevation"], 20)
        self.assertEqual(d["size"], 2)
        self.assertTrue(d["is_hidden"])
        self.assertEqual(d["concentrating_on"], "Benedizione")
        self.assertTrue(d["in_combat"])
        self.assertEqual(d["death_save_successes"], 2)
        self.assertEqual(d["death_save_failures"], 1)
        self.assertEqual(d["combat_initiative"], 17)

        p2 = Player.from_dict(d)
        self.assertEqual(p2.ac, 18)
        self.assertEqual(p2.size, 2)
        self.assertEqual(p2.concentrating_on, "Benedizione")
        self.assertEqual(p2.death_save_successes, 2)

        # Test GameState.load_session
        self.gs.players.append(p)
        self.gs.active_aoes = [{"type": "circle", "radius": 4, "center": [4, 5]}]
        self.gs.drawn_lines = [{"points": [0, 0, 10, 10], "color": "red"}]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            temp_path = tf.name

        try:
            self.gs.save_session(temp_path)
            
            # Crea un nuovo GameState con giocatore pre-esistente connesso
            new_gs = GameState(queue.Queue())
            connected_p = Player("TestHero")
            new_gs.players.append(connected_p)

            new_gs.load_session(temp_path)

            self.assertEqual(len(new_gs.players), 1)
            hero = new_gs.players[0]
            self.assertEqual(hero.ac, 18)
            self.assertEqual(hero.size, 2)
            self.assertTrue(hero.is_hidden)
            self.assertEqual(hero.concentrating_on, "Benedizione")
            self.assertTrue(hero.in_combat)
            self.assertEqual(hero.death_save_successes, 2)
            self.assertEqual(len(new_gs.active_aoes), 1)
            self.assertEqual(len(new_gs.drawn_lines), 1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_5_2_campaign_journal_recording(self):
        """5.2 Verifica registrazione eventi in CampaignJournal da GameState."""
        evt = self.gs.record_journal_event("exploration", "Caverna Buia", "Il party entra nella caverna", actor="Party")
        self.assertIsNotNone(evt)
        self.assertIsNotNone(self.gs.campaign_journal)
        events = self.gs.campaign_journal.get_all_events()
        self.assertTrue(any(e.title == "Caverna Buia" for e in events))

    def test_5_3_build_release_packaging_safety(self):
        """5.3 Verifica che build_release.py escluda cartelle private (manuals, campaigns, audio_library)."""
        import inspect
        import build_release
        source = inspect.getsource(build_release.run_pyinstaller)
        # Deve includere srd_data e maps
        self.assertIn('("srd_data", "srd_data")', source)
        self.assertIn('("maps", "maps")', source)
        # Non deve includere manuals o audio_library nei datas grezzi di pyinstaller
        self.assertNotIn('("manuals", "manuals")', source)
        self.assertNotIn('("audio_library", "audio_library")', source)
        self.assertNotIn('("campaigns", "campaigns")', source)
        # Deve creare i template README
        self.assertIn("user_template_dirs", source)


if __name__ == "__main__":
    unittest.main()

