import unittest
import queue
from unittest.mock import MagicMock, patch
from common.hex_utils import Hex, grid_distance_3d, distance_3d_feet
from common.game_state import GameState, Player
from common.protocol import make_set_elevation_request
from server.rules.combat import (
    resolve_falling, drop_concentration, handle_attack_request, handle_shove_request
)
from server.rules.character import handle_set_elevation_request
from server.rules.chat import handle_chat

class TestElevationAndConcentration(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(gui_queue=queue.Queue())
        self.game_state.current_map = {
            "grid_type": "hex",
            "hex_size": 30,
            "walls": []
        }

        self.caster = Player(name="Mago", conn=MagicMock())
        self.caster.hp = 20
        self.caster.max_hp = 20
        self.caster.position = [0, 0]
        self.caster.elevation = 0
        self.caster.conditions = ["Concentrazione"]
        self.caster.full_sheet = {
            "class": "Mago",
            "level": 5,
            "attributes": {"FOR": 10, "DES": 14, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10},
            "conditions": ["Concentrazione"]
        }

        self.target = Player(name="Guerriero", conn=MagicMock())
        self.target.hp = 30
        self.target.max_hp = 30
        self.target.position = [1, 0]
        self.target.elevation = 0
        self.target.conditions = []
        self.target.full_sheet = {
            "class": "Guerriero",
            "level": 5,
            "attributes": {"FOR": 16, "DES": 12, "COS": 16, "INT": 10, "SAG": 12, "CAR": 10},
            "skills": {"Atletica": 1},
            "conditions": [],
            "ac": 16
        }

        self.monster = Player(name="Arpia", conn=None)
        self.monster.hp = 38
        self.monster.max_hp = 38
        self.monster.position = [1, 0]
        self.monster.elevation = 30 # Vola a 30 ft
        self.monster.conditions = []
        self.monster.full_sheet = {
            "class": "Mostro",
            "level": 3,
            "attributes": {"FOR": 12, "DES": 14, "COS": 12, "INT": 8, "SAG": 10, "CAR": 12},
            "skills": {"Atletica": 0, "Acrobazia": 0},
            "conditions": [],
            "ac": 13,
            "size": "Medium"
        }

        self.game_state.players = [self.caster, self.target, self.monster]

    def test_3d_distance_calculation(self):
        """Verifica il calcolo della distanza 3D euclidea tra punti a quote differenti."""
        # 0 ft orizzontale, 30 ft verticale -> 6 celle (30 ft)
        dist_cells = grid_distance_3d(Hex(0, 0), Hex(0, 0), z_a=0, z_b=30, grid_type="hex")
        self.assertEqual(dist_cells, 6.0)
        self.assertEqual(distance_3d_feet(Hex(0, 0), Hex(0, 0), z_a=0, z_b=30), 30.0)

        # 40 ft orizzontale (8 celle) e 30 ft verticale -> hypot(40, 30) = 50 ft (10 celle)
        dist_cells_diag = grid_distance_3d(Hex(0, 0), Hex(8, 0), z_a=0, z_b=30, grid_type="hex")
        self.assertEqual(dist_cells_diag, 10.0)
        self.assertEqual(distance_3d_feet(Hex(0, 0), Hex(8, 0), z_a=0, z_b=30), 50.0)

    def test_falling_raw_damage_and_prone(self):
        """Caduta da 30 ft infligge 3d6 danni contundenti e atterra Prono (PHB p. 183)."""
        self.monster.elevation = 30
        with patch("random.randint", side_effect=[4, 3, 5]): # 4+3+5 = 12 danni
            dmg = resolve_falling(self.monster, 30, self.game_state)
            self.assertEqual(dmg, 12)
            self.assertEqual(self.monster.hp, 26)
            self.assertEqual(self.monster.elevation, 0)
            self.assertIn("Prono", self.monster.conditions)

    def test_falling_cap_20d6(self):
        """Caduta da 250 ft è limitata a 20d6 massimi (PHB p. 183)."""
        self.target.elevation = 250
        with patch("random.randint", return_value=3) as mock_rand:
            dmg = resolve_falling(self.target, 250, self.game_state)
            self.assertEqual(mock_rand.call_count, 20)
            self.assertEqual(dmg, 60) # 20 * 3
            self.assertEqual(self.target.elevation, 0)

    def test_falling_under_10ft_no_damage(self):
        """Caduta inferiore a 10 ft non infligge danni e non atterra Prono."""
        self.target.elevation = 8
        dmg = resolve_falling(self.target, 8, self.game_state)
        self.assertEqual(dmg, 0)
        self.assertNotIn("Prono", self.target.conditions)

    def test_monk_slow_fall(self):
        """Monaco di 5° livello riduce il danno da caduta di 5 x livello = 25 danni."""
        monk = Player(name="Monaco", conn=None)
        monk.hp = 35
        monk.max_hp = 35
        monk.elevation = 40
        monk.full_sheet = {"class": "Monaco", "level": 5, "conditions": []}
        self.game_state.players.append(monk)

        with patch("random.randint", side_effect=[6, 6, 6, 6]): # 24 danni grezzi
            dmg = resolve_falling(monk, 40, self.game_state)
            # 24 grezzi - 25 riduzione monaco = 0 danni!
            self.assertEqual(dmg, 0)
            self.assertEqual(monk.hp, 35)
            self.assertNotIn("Prono", monk.conditions) # Non subisce danni -> non è prono

    def test_feather_fall_negates_damage(self):
        """L'effetto Caduta Morbida (Feather Fall) annulla completamente il danno da caduta."""
        self.target.elevation = 80
        self.target.active_effects = [{"name": "Caduta Morbida"}]
        dmg = resolve_falling(self.target, 80, self.game_state)
        self.assertEqual(dmg, 0)
        self.assertEqual(self.target.elevation, 0)
        self.assertNotIn("Prono", self.target.conditions)

    def test_shove_prone_flying_creature_falls(self):
        """Spingere a terra una creatura volante a 30 ft fa precipitare la creatura."""
        self.monster.position = [1, 0]
        self.monster.elevation = 30
        self.target.position = [0, 0]
        self.target.elevation = 30 # Attaccante in volo alla stessa quota
        # Spinta con successo: ar1=15, ar2=10, dr1=8, dr2=5, poi caduta 3d6: 3, 4, 3 = 10
        with patch("random.randint", side_effect=[15, 10, 8, 5, 3, 4, 3]):
            handle_shove_request({"target_name": "Arpia", "option": "prone"}, self.target, self.game_state)
            self.assertIn("Prono", self.monster.conditions)
            self.assertEqual(self.monster.elevation, 0)

    def test_concentration_loss_drops_flight_and_triggers_fall(self):
        """Interruzione della concentrazione su Volare fa precipitare il bersaglio."""
        self.target.elevation = 40
        self.target.active_effects = [{
            "id": "fx_fly",
            "name": "Volare",
            "concentration_caster": "Mago"
        }]
        # Mago perde concentrazione
        with patch("random.randint", side_effect=[4, 4, 4, 4]): # 4d6 = 16 danni
            drop_concentration(self.caster, self.game_state, notify=True)
            self.assertNotIn("Concentrazione", self.caster.conditions)
            self.assertEqual(len(self.target.active_effects), 0) # Effetto rimosso
            self.assertEqual(self.target.elevation, 0) # Precipitato a terra
            self.assertIn("Prono", self.target.conditions)

    def test_melee_attack_out_of_reach_due_to_elevation(self):
        """Un bersaglio Prono a 30 ft di quota non concede vantaggio in mischia a chi sta a terra."""
        self.target.position = [0, 0]
        self.target.elevation = 0
        self.monster.position = [1, 0]
        self.monster.elevation = 30 # 30 ft in volo
        self.monster.conditions = ["Prono"]

        with patch("server.rules.combat.broadcast") as mock_bcast, \
             patch("random.randint", side_effect=[12, 5]):
            handle_attack_request({
                "target_name": "Arpia",
                "weapon_name": "Spada Lunga",
                "hit_bonus": 5,
                "damage_formula": "1d8+3",
                "damage_type": "Tagliente",
                "is_ranged": False
            }, self.target, self.game_state)

            found_prone_adv = False
            for call_args in mock_bcast.call_args_list:
                msg = call_args[0][1]
                if msg.get("type") == "CHAT_BROADCAST":
                    txt = msg.get("data", {}).get("text", "")
                    if "Bersaglio Prono (Mischia)" in txt:
                        found_prone_adv = True
            self.assertFalse(found_prone_adv, "Non deve avere vantaggio in mischia contro un bersaglio volante a 30 ft!")

    def test_chat_commands_quota_and_caduta(self):
        """Verifica i comandi chat /quota e /caduta."""
        handle_chat({"text": "/quota 45"}, self.target, self.game_state)
        self.assertEqual(self.target.elevation, 45)

        with patch("random.randint", side_effect=[3, 3, 3, 3]): # 4d6 per 40ft = 12
            handle_chat({"text": f"/caduta 40 Guerriero"}, self.caster, self.game_state)
            self.assertEqual(self.target.elevation, 5) # 45 - 40 = 5
            self.assertEqual(self.target.hp, 18) # 30 - 12 = 18

if __name__ == "__main__":
    unittest.main()

