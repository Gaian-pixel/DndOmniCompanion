import unittest
import queue
from unittest.mock import MagicMock, patch
from common.hex_utils import Hex, hex_distance, grid_distance, get_cover_between, has_line_of_sight
from common.game_state import GameState, Player
from common.protocol import make_shove_request, make_grapple_request, make_attack_request
from server.rules.combat import (
    handle_attack_request, handle_shove_request, handle_grapple_request,
    _get_entity_ability_mod, _get_entity_skill_bonus, _get_entity_size_rank
)

class TestTacticalCombat(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(gui_queue=queue.Queue())
        self.game_state.current_map = {
            "grid_type": "hex",
            "hex_size": 30,
            "walls": [[2, 2]],
            "half_cover": [[1, 1]],
            "three_quarters_cover": [[3, 3]],
            "difficult_terrain": {}
        }
        self.game_state.automation_settings["enable_flanking"] = True

        # Crea Attaccante
        self.attacker = Player(name="Guerriero", conn=MagicMock())
        self.attacker.hp = 30
        self.attacker.max_hp = 30
        self.attacker.position = [0, 0]
        self.attacker.full_sheet = {
            "level": 3,
            "attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 12, "CAR": 10},
            "skills": {"Atletica": 1, "Acrobazia": 0},
            "size": "Medium",
            "ac": 16
        }

        # Crea Difensore / Bersaglio
        self.target = Player(name="Orco", conn=None)
        self.target.hp = 25
        self.target.max_hp = 25
        self.target.position = [1, 0]
        self.target.full_sheet = {
            "level": 2,
            "attributes": {"FOR": 14, "DES": 10, "COS": 14, "INT": 8, "SAG": 10, "CAR": 8},
            "skills": {"Atletica": 0, "Acrobazia": 0},
            "size": "Medium",
            "ac": 13
        }

        # Crea Alleato per Flanking (opposto all'attaccante rispetto al bersaglio: 2*q_t - q_a = 2, 0)
        self.ally = Player(name="Ladro", conn=MagicMock())
        self.ally.hp = 20
        self.ally.max_hp = 20
        self.ally.position = [2, 0]
        self.ally.full_sheet = {
            "level": 3,
            "attributes": {"FOR": 10, "DES": 16, "COS": 12, "INT": 14, "SAG": 10, "CAR": 12},
            "skills": {"Atletica": 0, "Acrobazia": 1},
            "size": "Medium",
            "ac": 14
        }

        self.game_state.players = [self.attacker, self.target, self.ally]

    def test_entity_helpers(self):
        mod_for = _get_entity_ability_mod(self.attacker, "FOR")
        self.assertEqual(mod_for, 3) # (16 - 10) // 2

        ath_bonus = _get_entity_skill_bonus(self.attacker, "Atletica", "Athletics", "FOR")
        self.assertEqual(ath_bonus, 5) # 3 FOR + 2 PB

        size_rank = _get_entity_size_rank(self.attacker)
        self.assertEqual(size_rank, 2) # Medium = 2

    def test_flanking_advantage_melee(self):
        """Verifica che due alleati sui lati opposti concedano Vantaggio per Fiancheggiamento in mischia."""
        with patch("server.rules.combat.broadcast") as mock_bcast, \
             patch("random.randint", side_effect=[10, 15, 6]): # roll1=10, roll2=15 (max=15), dmg=6
            handle_attack_request({
                "target_name": "Orco",
                "weapon_name": "Spada Lunga",
                "hit_bonus": 5,
                "damage_formula": "1d8+3",
                "damage_type": "Tagliente",
                "is_ranged": False
            }, self.attacker, self.game_state)

            # Trova il messaggio di chat inviato
            found_flank = False
            for call_args in mock_bcast.call_args_list:
                msg = call_args[0][1]
                if msg.get("type") == "CHAT_BROADCAST":
                    txt = msg.get("data", {}).get("text", "")
                    if "Fiancheggiamento" in txt:
                        found_flank = True
            self.assertTrue(found_flank, "Dovrebbe rilevare Fiancheggiamento (DMG p. 251)")

    def test_flanking_disabled_by_setting(self):
        """Se enable_flanking è False, non concede vantaggio per fiancheggiamento."""
        self.game_state.automation_settings["enable_flanking"] = False
        with patch("server.rules.combat.broadcast") as mock_bcast, \
             patch("random.randint", side_effect=[12, 5]):
            handle_attack_request({
                "target_name": "Orco",
                "weapon_name": "Spada Lunga",
                "hit_bonus": 5,
                "damage_formula": "1d8+3",
                "damage_type": "Tagliente",
                "is_ranged": False
            }, self.attacker, self.game_state)

            found_flank = False
            for call_args in mock_bcast.call_args_list:
                msg = call_args[0][1]
                if msg.get("type") == "CHAT_BROADCAST":
                    txt = msg.get("data", {}).get("text", "")
                    if "Fiancheggiamento" in txt:
                        found_flank = True
            self.assertFalse(found_flank, "Non dovrebbe rilevare fiancheggiamento se disattivato")

    def test_flanking_ranged_weapon_not_applicable(self):
        """Un'arma a distanza non gode del fiancheggiamento in mischia."""
        with patch("server.rules.combat.broadcast") as mock_bcast, \
             patch("random.randint", side_effect=[12, 5]):
            handle_attack_request({
                "target_name": "Orco",
                "weapon_name": "Arco Corto",
                "hit_bonus": 3,
                "damage_formula": "1d6+1",
                "damage_type": "Perforante",
                "is_ranged": True
            }, self.attacker, self.game_state)

            found_flank = False
            for call_args in mock_bcast.call_args_list:
                msg = call_args[0][1]
                if msg.get("type") == "CHAT_BROADCAST":
                    txt = msg.get("data", {}).get("text", "")
                    if "Fiancheggiamento" in txt:
                        found_flank = True
            self.assertFalse(found_flank, "L'arco a distanza non deve ricevere fiancheggiamento")

    def test_shove_prone_success(self):
        """Attaccante vince la contesa e atterra il bersaglio Prono."""
        # attacker rolls 15 + 5 = 20, defender rolls 8 + 2 = 10 -> attacker wins
        with patch("random.randint", side_effect=[15, 10, 8, 5]):
            handle_shove_request({"target_name": "Orco", "option": "prone"}, self.attacker, self.game_state)
            self.assertIn("Prono", self.target.conditions)

    def test_shove_push_success(self):
        """Attaccante vince la contesa e spinge indietro il bersaglio di 1 casella."""
        # Attacker [0,0], Target [1,0] -> spinto a [2,0] ma [2,0] è occupato dall'alleato o libero?
        # Muoviamo l'alleato lontano per testare il push pulito
        self.ally.position = [5, 5]
        with patch("random.randint", side_effect=[15, 10, 8, 5]):
            handle_shove_request({"target_name": "Orco", "option": "push"}, self.attacker, self.game_state)
            self.assertEqual(self.target.position, [2, 0])

    def test_shove_wall_blocked(self):
        """Spingere verso un muro ferma la creatura senza attraversare il muro."""
        # Attacker [1,2], Target [1,1] -> muro in [1,0]
        self.attacker.position = [1, 2]
        self.target.position = [1, 1]
        self.game_state.current_map["walls"] = [[1, 0]]
        with patch("random.randint", side_effect=[18, 10, 5, 5]):
            handle_shove_request({"target_name": "Orco", "option": "push"}, self.attacker, self.game_state)
            # Rimane in [1, 1] perché la destinazione [1, 0] è un muro
            self.assertEqual(self.target.position, [1, 1])

    def test_shove_defender_wins(self):
        """Difensore vince la contesa: la spinta fallisce e non viene applicato Prono."""
        # attacker rolls 4 + 5 = 9, defender rolls 16 + 2 = 18 -> defender wins
        with patch("random.randint", side_effect=[4, 2, 16, 12]):
            handle_shove_request({"target_name": "Orco", "option": "prone"}, self.attacker, self.game_state)
            self.assertNotIn("Prono", self.target.conditions)

    def test_shove_size_too_large(self):
        """Creatura di 2+ taglie superiore non può essere spinta (es. Gargantuan vs Medium)."""
        self.target.full_sheet["size"] = "Gargantuan"
        with patch("server.rules.combat.broadcast") as mock_bcast:
            handle_shove_request({"target_name": "Orco", "option": "prone"}, self.attacker, self.game_state)
            self.assertNotIn("Prono", self.target.conditions)
            found_err = False
            for call_args in mock_bcast.call_args_list:
                msg = call_args[0][1]
                if "troppo grande" in msg.get("data", {}).get("text", ""):
                    found_err = True
            self.assertTrue(found_err)

    def test_grapple_success(self):
        """Attaccante vince la contesa di Lotta: bersaglio riceve Afferrato e grappled_by."""
        with patch("random.randint", side_effect=[16, 10, 6, 4]):
            handle_grapple_request({"target_name": "Orco"}, self.attacker, self.game_state)
            self.assertIn("Afferrato", self.target.conditions)
            self.assertEqual(getattr(self.target, "grappled_by", None), "Guerriero")

    def test_grapple_defender_wins(self):
        """Difensore vince la contesa di Lotta: bersaglio rimane libero."""
        with patch("random.randint", side_effect=[5, 2, 15, 12]):
            handle_grapple_request({"target_name": "Orco"}, self.attacker, self.game_state)
            self.assertNotIn("Afferrato", self.target.conditions)

    def test_dynamic_cover_and_los(self):
        """Verifica il calcolo di mezza copertura (+2), 3/4 copertura (+5) e LoS da muri."""
        orig = Hex(0, 0)
        target = Hex(2, 2)
        # Linea da (0,0) a (2,2) attraversa (1,1) che è in half_cover
        bonus, name = get_cover_between(orig, target, half_cover=[[1, 1]])
        self.assertEqual(bonus, 2)
        self.assertIn("Mezza Copertura", name)

        # Tre quarti di copertura
        target3 = Hex(4, 4)
        bonus3, name3 = get_cover_between(orig, target3, three_quarters=[[2, 2]])
        self.assertEqual(bonus3, 5)
        self.assertIn("Tre Quarti", name3)

        # Muro blocca la linea di vista
        has_los = has_line_of_sight(orig, target, walls=[[1, 1]])
        self.assertFalse(has_los)

if __name__ == "__main__":
    unittest.main()
