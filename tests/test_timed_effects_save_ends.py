import unittest
from unittest.mock import patch, MagicMock
import queue

from common.game_state import GameState, Player
from common.effects_data import get_effect_presets, create_effect_instance, EFFECT_PRESETS
from common.protocol import make_apply_effect_request, make_remove_effect_request
from server.rules.combat import (
    advance_combat_turn, drop_concentration,
    handle_apply_effect_request, handle_remove_effect_request,
    _process_save_result
)

class TestTimedEffectsAndSaveEnds(unittest.TestCase):

    def setUp(self):
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.p1 = Player("Gildor")
        self.p1.hp = 30
        self.p1.max_hp = 30
        self.p1.initiative = 20
        self.p1.is_party_member = True
        self.p1.full_sheet = {
            "attributes": {"FOR": 10, "DES": 14, "COS": 12, "INT": 10, "SAG": 16, "CAR": 10},
            "saving_throws": ["SAG", "WIS"],
            "proficiency_bonus": 3
        }

        self.p2 = Player("Goblin")
        self.p2.hp = 12
        self.p2.max_hp = 12
        self.p2.initiative = 10
        self.p2.is_party_member = False
        self.p2.full_sheet = {
            "attributes": {"FOR": 8, "DES": 14, "COS": 10, "INT": 10, "SAG": 8, "CAR": 8},
            "saving_throws": [],
            "proficiency_bonus": 2
        }

        self.gs.players = [self.p1, self.p2]

    def test_effect_presets_and_creation(self):
        presets = get_effect_presets(lang="it")
        self.assertGreater(len(presets), 5)
        keys = [p["key"] for p in presets]
        self.assertIn("bless", keys)
        self.assertIn("hold_person", keys)
        self.assertIn("shield", keys)

        # Creazione istanza Bless
        bless_fx = create_effect_instance("bless", source="Chierico")
        self.assertEqual(bless_fx["name"], "Benedizione")
        self.assertEqual(bless_fx["duration_rounds"], 10)
        self.assertEqual(bless_fx["decrement_timing"], "round_end")
        self.assertEqual(bless_fx["concentration_caster"], "Chierico")

        # Creazione istanza Hold Person con CD custom
        hp_fx = create_effect_instance("hold_person", source="Mago", dc=15)
        self.assertEqual(hp_fx["name"], "Blocca Persone")
        self.assertEqual(hp_fx["condition"], "Paralizzato")
        self.assertIsNotNone(hp_fx["save_ends"])
        self.assertEqual(hp_fx["save_ends"]["dc"], 15)
        self.assertEqual(hp_fx["save_ends"]["stat"], "SAG")

        # Creazione istanza Shield
        shield_fx = create_effect_instance("shield")
        self.assertEqual(shield_fx["duration_rounds"], 1)
        self.assertEqual(shield_fx["decrement_timing"], "start_of_turn")

    def test_player_add_and_remove_effect(self):
        hp_fx = create_effect_instance("hold_person", source="Mago", dc=14)
        self.p2.add_effect(hp_fx)

        # Condizione "Paralizzato" deve essere automaticamente sincronizzata
        self.assertIn("Paralizzato", self.p2.conditions)
        self.assertEqual(len(self.p2.active_effects), 1)
        self.assertIn(hp_fx["name"], self.p2.condition_durations)

        # Serializzazione e deserializzazione
        p_dict = self.p2.to_dict()
        self.assertIn("active_effects", p_dict)
        self.assertEqual(len(p_dict["active_effects"]), 1)

        restored = Player.from_dict(p_dict)
        self.assertEqual(len(restored.active_effects), 1)
        self.assertEqual(restored.active_effects[0]["name"], "Blocca Persone")

        # Rimozione effetto
        removed = self.p2.remove_effect(hp_fx["name"])
        self.assertIsNotNone(removed)
        self.assertEqual(len(self.p2.active_effects), 0)
        self.assertNotIn("Paralizzato", self.p2.conditions)
        self.assertNotIn(hp_fx["name"], self.p2.condition_durations)

    def test_timed_effects_round_expiration(self):
        self.gs.combat_active = True
        self.gs.turn_index = 0
        self.gs.round_number = 1

        fx = {
            "id": "fx_custom_2r",
            "name": "Effetto Breve",
            "icon": "✨",
            "duration_rounds": 2,
            "decrement_timing": "round_end",
            "save_ends": None
        }
        self.p1.add_effect(fx)
        self.assertEqual(self.p1.active_effects[0]["duration_rounds"], 2)

        # Fine turno p1 -> p2
        self.gs.next_turn()
        self.assertEqual(self.gs.turn_index, 1)
        self.assertEqual(self.gs.round_number, 1)
        self.assertEqual(self.p1.active_effects[0]["duration_rounds"], 2)

        # Fine turno p2 -> inizio round 2
        self.gs.next_turn()
        self.assertEqual(self.gs.turn_index, 0)
        self.assertEqual(self.gs.round_number, 2)
        self.assertEqual(self.p1.active_effects[0]["duration_rounds"], 1)

        # Turno p1 -> p2
        self.gs.next_turn()
        # Fine turno p2 -> inizio round 3 -> durata arriva a 0 ed effetto scade
        self.gs.next_turn()
        self.assertEqual(self.gs.round_number, 3)
        self.assertEqual(len(self.p1.active_effects), 0)

    def test_timed_effects_start_of_turn_expiration(self):
        self.gs.combat_active = True
        self.gs.turn_index = 0
        self.gs.round_number = 1

        shield_fx = create_effect_instance("shield")
        self.p1.add_effect(shield_fx)
        self.assertIn("Scudo", self.p1.conditions)
        self.assertEqual(len(self.p1.active_effects), 1)

        # Turno p1 termina -> tocca a p2
        self.gs.next_turn()
        self.assertEqual(self.gs.turn_index, 1)
        # Scudo deve essere ancora attivo durante il turno dei nemici!
        self.assertIn("Scudo", self.p1.conditions)
        self.assertEqual(len(self.p1.active_effects), 1)

        # Turno p2 termina -> tocca di nuovo a p1 (all'inizio del suo turno Scudo scade!)
        self.gs.next_turn()
        self.assertEqual(self.gs.turn_index, 0)
        self.assertNotIn("Scudo", self.p1.conditions)
        self.assertEqual(len(self.p1.active_effects), 0)

    @patch("server.rules.combat.roll_dice")
    def test_save_ends_auto_resolution_success(self, mock_roll):
        # Goblin affetto da Hold Person (TS SAG CD 12)
        hp_fx = create_effect_instance("hold_person", source="Mago", dc=12)
        self.p2.add_effect(hp_fx)
        self.assertIn("Paralizzato", self.p2.conditions)

        self.gs.combat_active = True
        self.gs.turn_index = 1 # Turno di Goblin

        # Mock del tiro: Goblin tira d20 -> risultato totale 14 (successo)
        mock_roll.return_value = {"total": 14, "rolls": [15]}

        # Chiamata diretta per sincronismo
        _process_save_result(
            self.p2.name, "SAG", 14, False, False, 12, "", False,
            "Save-Ends: Blocca Persone", self.gs
        )

        # Verifica che il successo abbia rimosso l'effetto e la condizione Paralizzato
        self.assertEqual(len(self.p2.active_effects), 0)
        self.assertNotIn("Paralizzato", self.p2.conditions)

    @patch("server.rules.combat.roll_dice")
    def test_save_ends_auto_resolution_failure(self, mock_roll):
        hp_fx = create_effect_instance("hold_person", source="Mago", dc=15)
        self.p2.add_effect(hp_fx)
        self.assertIn("Paralizzato", self.p2.conditions)

        # Mock del tiro: Goblin tira d20 -> totale 8 (fallimento)
        mock_roll.return_value = {"total": 8, "rolls": [9]}

        _process_save_result(
            self.p2.name, "SAG", 8, False, False, 15, "", False,
            "Save-Ends: Blocca Persone", self.gs
        )

        # Verifica che il fallimento mantenga l'effetto attivo
        self.assertEqual(len(self.p2.active_effects), 1)
        self.assertIn("Paralizzato", self.p2.conditions)

    def test_concentration_break_removes_linked_effects(self):
        wizard = Player("Mago")
        wizard.conditions = ["Concentrazione"]
        self.gs.players.append(wizard)

        # Mago lancia Benedizione su Gildor e Hold Person su Goblin
        bless = create_effect_instance("bless", concentration_caster="Mago")
        hold = create_effect_instance("hold_person", concentration_caster="Mago")

        self.p1.add_effect(bless)
        self.p2.add_effect(hold)

        self.assertEqual(len(self.p1.active_effects), 1)
        self.assertEqual(len(self.p2.active_effects), 1)
        self.assertIn("Paralizzato", self.p2.conditions)

        # La concentrazione del Mago si spezza
        drop_concentration(wizard, self.gs, notify=False)

        # Entrambi gli effetti devono essere rimossi automaticamente
        self.assertEqual(len(self.p1.active_effects), 0)
        self.assertEqual(len(self.p2.active_effects), 0)
        self.assertNotIn("Paralizzato", self.p2.conditions)

    def test_protocol_apply_and_remove_effect_handlers(self):
        # Test handle_apply_effect_request
        fx_payload = create_effect_instance("haste", source="Mago")
        req_apply = make_apply_effect_request("Gildor", fx_payload)

        handle_apply_effect_request(req_apply["data"], None, self.gs)
        self.assertEqual(len(self.p1.active_effects), 1)
        self.assertEqual(self.p1.active_effects[0]["name"], "Velocità")

        # Test handle_remove_effect_request
        req_remove = make_remove_effect_request("Gildor", self.p1.active_effects[0]["id"])
        handle_remove_effect_request(req_remove["data"], None, self.gs)
        self.assertEqual(len(self.p1.active_effects), 0)

if __name__ == "__main__":
    unittest.main()

