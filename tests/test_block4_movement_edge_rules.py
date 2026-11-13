import os
import queue
import sys
import unittest
from pathlib import Path

os.environ["DND_MOCK_AUDIO"] = "1"
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.game_state import GameState, Player
from server.rules.combat import _process_save_result
from server.rules.movement import handle_move_request
from server.rules.reaction_magic import check_passive_perception


def _mk(name: str, pos, size: str = "Media", party: bool = True, speed: int = 30, race: str = "Umano") -> Player:
    p = Player(name)
    p.position = list(pos)
    p.size = size
    p.is_party_member = party
    p.speed = speed
    p.hp = 30
    p.max_hp = 30
    p.race = race
    p.full_sheet = {"name": name, "race": race, "size": size, "attributes": {"FOR": 10, "DES": 12, "COS": 12, "INT": 10, "SAG": 14, "CAR": 10}, "skills": {}}
    return p


class TestBlock4MovementEdgeRules(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.players.clear()
        self.gs.combat_active = True
        self.gs.automation_settings["strict_movement_limits"] = True
        self.gs.automation_settings["strict_turn_lock"] = False

    def test_squeezing_double_movement_cost_and_dex_save_note(self):
        hero = _mk("Hero", [0, 0], speed=30)  # 6 hexes max
        hero.is_squeezing = True
        self.gs.add_player(hero)

        handle_move_request({"to": [2, 0]}, hero, self.gs)  # costs 4 hexes
        self.assertEqual(hero.position, [2, 0])
        self.assertEqual(hero.movement_spent_this_turn, 4)

        # Trying 2 more hexes = +4 -> total 8 > 6: blocked
        handle_move_request({"to": [4, 0]}, hero, self.gs)
        self.assertEqual(hero.position, [2, 0])

        logs = []
        self.gs.log_dm_message = lambda m: logs.append(m)
        _process_save_result("Hero", "DES", 12, False, False, 15, "2d6", False, "Trappola", self.gs)
        self.assertTrue(any("Squeezed" in m for m in logs))

    def test_creature_space_traversal_allies_enemies_size_and_halfling(self):
        hero = _mk("Hero", [0, 0], size="Media", party=True, speed=30)
        ally = _mk("Ally", [1, 0], size="Media", party=True)
        foe_med = _mk("Orc", [2, 0], size="Media", party=False)
        foe_huge = _mk("Dragon", [0, 2], size="Enorme", party=False)
        self.gs.players.extend([hero, ally, foe_med, foe_huge])

        # Can't end on ally hex
        handle_move_request({"to": [1, 0]}, hero, self.gs)
        self.assertEqual(hero.position, [0, 0])

        # Through ally at [1,0] to empty [2, -1]? Let's test straight path across ally -> foe_med blocked!
        self.gs.players.remove(foe_med)
        handle_move_request({"to": [2, 0]}, hero, self.gs)
        self.assertEqual(hero.position, [2, 0])
        # Crossing ally cost 2 + empty step cost 1 = 3 hexes
        self.assertEqual(hero.movement_spent_this_turn, 3)

        # Put hostile Medium Orc in the middle [1, 0] -> blocked!
        hero.position = [0, 0]
        hero.movement_spent_this_turn = 0
        self.gs.players.remove(ally)
        foe_mid = _mk("Goblin", [1, 0], size="Media", party=False)
        self.gs.add_player(foe_mid)
        handle_move_request({"to": [2, 0]}, hero, self.gs)
        self.assertEqual(hero.position, [0, 0])

        # Overrun / Tumble flag allows passing through foe_mid once!
        hero.overrun_tumble_through_target = "Goblin"
        handle_move_request({"to": [2, 0]}, hero, self.gs)
        self.assertEqual(hero.position, [2, 0])
        self.assertIsNone(hero.overrun_tumble_through_target)

        # >= 2 sizes diff (Small halfling vs Huge dragon) OR Halfling Nimbleness (Small halfling vs Medium orc)
        self.gs.players.remove(hero)
        halfling = _mk("Bilbo", [0, 0], size="Piccola", party=True, race="Halfling", speed=25)
        self.gs.add_player(halfling)
        # Goblin is at [1, 0] (Medium -> 1 size larger than Small Halfling -> Halfling Nimbleness allows pass!)
        handle_move_request({"to": [2, 0]}, halfling, self.gs)
        self.assertEqual(halfling.position, [2, 0])

    def test_jump_distance_and_deafened_audio_perception(self):
        jumper = _mk("Mario", [0, 0], speed=30)
        jumper.full_sheet["attributes"]["FOR"] = 10  # Max running long jump = 10 ft (2 hexes)
        self.gs.add_player(jumper)

        handle_move_request({"to": [3, 0], "is_jump": True, "running_start": True}, jumper, self.gs)
        self.assertEqual(jumper.position, [0, 0])  # 15 ft > 10 ft

        handle_move_request({"to": [2, 0], "is_jump": True, "running_start": True}, jumper, self.gs)
        self.assertEqual(jumper.position, [2, 0])  # 10 ft <= 10 ft

        # Deafened returns 0 for non-sight passive Perception
        jumper.conditions = ["Assordato"]
        self.assertEqual(check_passive_perception(jumper, self.gs, sight_based=False), 0)
        self.assertGreater(check_passive_perception(jumper, self.gs, sight_based=True), 0)


if __name__ == "__main__":
    unittest.main()
