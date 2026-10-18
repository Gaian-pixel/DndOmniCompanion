import unittest
import os
import sys
import queue

os.environ["DND_MOCK_AUDIO"] = "1"

from common.game_state import GameState, Player
from common.hex_utils import Hex, get_sphere_hexes
from common.protocol import *
from server.rules.map_interaction import (
    handle_toggle_door_request,
    handle_room_pin_request,
    handle_resolve_aoe_request
)
from server.rules.movement import handle_move_request, get_effective_map_walls
from server.rules.chat import handle_blind_roll_request
from server.rules.combat import handle_attack_request, handle_reaction_response, _process_save_result
from client.character_manager import Character

class TestAuthentic5eFeatures(unittest.TestCase):
    def setUp(self):
        self.game_state = GameState(gui_queue=queue.Queue())
        self.game_state.current_map = {
            "name": "Dungeon Test",
            "hexes": [[0, 0], [1, 0], [2, 0], [0, 1], [1, 1], [2, 1], [0, 2], [1, 2], [2, 2]],
            "walls": [],
            "doors": [],
            "room_pins": [],
            "fow_revealed": [[0, 0], [1, 0]],
            "fow_draft": []
        }

    def test_interactive_doors_and_movement(self):
        # 1. DM creates a closed door at (1, 0)
        p_dm = Player("DM")
        p_dm.role = "DM"
        p_dm.position = [0, 0]
        handle_toggle_door_request({"q": 1, "r": 0}, p_dm, self.game_state)
        doors = self.game_state.current_map.get("doors", [])
        self.assertEqual(len(doors), 1)
        self.assertEqual(doors[0]["state"], "closed")

        # 2. Player cannot move through closed door
        player = Player("Guerriero")
        player.position = [0, 0]
        player.speed = 30
        self.game_state.players = [player]
        handle_move_request({"to": [1, 0]}, player, self.game_state)
        self.assertEqual(player.position, [0, 0]) # Blocked!

        # 3. Player opens door (adjacent)
        handle_toggle_door_request({"q": 1, "r": 0}, player, self.game_state)
        self.assertEqual(doors[0]["state"], "open")

        # 4. Player can now walk through open door
        handle_move_request({"to": [1, 0]}, player, self.game_state)
        self.assertEqual(player.position, [1, 0])

    def test_door_effective_walls(self):
        # Closed, locked, and secret doors act as walls for LoS / FoW
        self.game_state.current_map["walls"] = [[5, 5]]
        self.game_state.current_map["doors"] = [
            {"q": 1, "r": 0, "state": "closed"},
            {"q": 2, "r": 0, "state": "open"},
            {"q": 3, "r": 0, "state": "locked"},
            {"q": 4, "r": 0, "state": "secret"}
        ]
        walls = get_effective_map_walls(self.game_state.current_map)
        self.assertIn([5, 5], walls)
        self.assertIn([1, 0], walls)
        self.assertNotIn([2, 0], walls) # Open door is NOT a wall!
        self.assertIn([3, 0], walls)
        self.assertIn([4, 0], walls)

    def test_room_pins_crud(self):
        # DM adds a room pin
        pin = {"id": "pin_1", "q": 1, "r": 1, "title": "Cripta dei Re", "read_aloud": "L'aria è gelida...", "dm_notes": "2 Ghoul nella tomba"}
        handle_room_pin_request({"action": "add", "pin": pin}, None, self.game_state)
        pins = self.game_state.current_map.get("room_pins", [])
        self.assertEqual(len(pins), 1)
        self.assertEqual(pins[0]["title"], "Cripta dei Re")

        # Update pin
        pin_up = {"id": "pin_1", "q": 1, "r": 1, "title": "Cripta Antica", "read_aloud": "Spirito vendicativo", "dm_notes": "Trappola a dardo"}
        handle_room_pin_request({"action": "update", "pin": pin_up}, None, self.game_state)
        self.assertEqual(self.game_state.current_map["room_pins"][0]["title"], "Cripta Antica")

        # Delete pin
        handle_room_pin_request({"action": "delete", "pin": {"id": "pin_1"}}, None, self.game_state)
        self.assertEqual(len(self.game_state.current_map["room_pins"]), 0)

    def test_blind_roll(self):
        # Blind roll request creates a private DM roll notification in GUI queue
        player = Player("Ladro")
        player.position = [0, 0]
        handle_blind_roll_request({"formula": "1d20+7", "reason": "Furtività"}, player, self.game_state)
        found = False
        while not self.game_state.gui_queue.empty():
            item = self.game_state.gui_queue.get_nowait()
            if item.get("type") == "PRIVATE_MESSAGE_RECEIVED" and item.get("payload", {}).get("from") == "Tiro Segreto":
                found = True
                self.assertIn("Furtività", item.get("payload", {}).get("text", ""))
        self.assertTrue(found)

    def test_evasion_and_incapacitated_save(self):
        # Evasion: Rogue takes 0 dmg on success, half on failure
        rogue = Player("Ladro")
        rogue.position = [0, 0]
        rogue.hp = 30
        rogue.max_hp = 30
        rogue.full_sheet = {"features": ["Elusione (Evasion)"], "attributes": {"DES": 18}}
        self.game_state.players = [rogue]

        # Success on DC 14 (rolled 16)
        _process_save_result("Ladro", "DES", 16, False, False, 14, "20", True, "Drago", self.game_state)
        self.assertEqual(rogue.hp, 30) # 0 damage on success!

        # Failure on DC 14 (rolled 10)
        _process_save_result("Ladro", "DES", 10, False, False, 14, "20", True, "Drago", self.game_state)
        self.assertEqual(rogue.hp, 20) # 10 damage (half) on fail!

    def test_opportunity_and_shield_reactions(self):
        player = Player("Mago")
        player.position = [0, 0]
        player.conditions = []
        player.has_reacted_this_turn = False
        self.game_state.players = [player]

        # Shield reaction grants +5 AC and adds Scudo condition
        handle_reaction_response({"reaction_type": "SHIELD_SPELL", "accepted": True, "target_name": "Orco"}, player, self.game_state)
        self.assertTrue(player.has_reacted_this_turn)
        self.assertIn("Scudo", player.conditions)

        # Cannot react twice in the same turn
        handle_reaction_response({"reaction_type": "SHIELD_SPELL", "accepted": True, "target_name": "Orco"}, player, self.game_state)
        self.assertEqual(player.conditions.count("Scudo"), 1)

    def test_sneak_attack_automation(self):
        rogue = Player("Ladro")
        rogue.position = [0, 0]
        rogue.full_sheet = {"level": 5, "char_class": "Ladro"}
        ally = Player("Paladino")
        ally.position = [1, 0]
        ally.hp = 30
        target = Player("Orco")
        target.position = [0, 1]
        target.hp = 50
        target.max_hp = 50
        target.full_sheet = {"ac": 10}
        self.game_state.players = [rogue, ally, target]

        # Rogue attacks with rapier (finesse), ally is adjacent to target -> Sneak Attack triggers!
        handle_attack_request({
            "target_name": "Orco",
            "weapon_name": "Stocco",
            "hit_bonus": 20, # Guaranteed hit
            "damage_formula": "1d8+4",
            "damage_type": "Perforante"
        }, rogue, self.game_state)

        # Base 1d8+4 (5-12) + Sneak Attack 3d6 (3-18) = 8 to 30 damage
        dmg_dealt = 50 - target.hp
        self.assertGreaterEqual(dmg_dealt, 8)
        self.assertTrue(getattr(rogue, "sneak_attack_used_this_turn", False))

    def test_campaign_time_advance_and_condition_decay(self):
        self.game_state.time_second = 0
        self.game_state.time_minute = 0
        self.game_state.time_hour = 8
        self.game_state.time_day = 1
        self.game_state.time_month = 1

        p = Player("Guerriero")
        p.position = [0, 0]
        p.condition_durations = {"Benedizione": 2}
        p.has_reacted_this_turn = True
        self.game_state.players = [p]
        self.game_state.combat_active = True
        self.game_state.turn_order = ["Guerriero"]
        self.game_state.turn_index = 0

        # Advance turn (+6s)
        self.game_state.next_turn()
        self.assertEqual(self.game_state.time_second, 6)
        self.assertEqual(p.condition_durations["Benedizione"], 1)
        self.assertFalse(p.has_reacted_this_turn) # Reset reaction

        # Next turn decays condition to 0 and removes it
        self.game_state.next_turn()
        self.assertNotIn("Benedizione", p.condition_durations)

    def test_subclass_and_attunement_bonuses(self):
        char = Character(name="Eroe")
        char.char_class = "Guerriero"
        char.subclass = "Campione"
        self.assertEqual(char.subclass, "Campione")

        # Attunement calculations
        char.ac = 14
        char.attributes["FOR"] = 12
        char.attributes["COS"] = 14
        char.inventory_grid = [
            {"name": "Anello di Protezione", "attuned": True, "desc": "+1 alla CA e ai tiri salvezza"},
            {"name": "Guanti della Forza dell'Orco", "attuned": True, "desc": "Imposta la Forza a 19"},
            {"name": "Amuleto della Salute", "attuned": True, "desc": "Imposta la Costituzione a 19"}
        ]

        bonuses = char.get_attunement_bonuses()
        self.assertEqual(bonuses["bonus_ac"], 1)
        self.assertEqual(bonuses["bonus_saves"], 1)
        self.assertEqual(bonuses["set_stats"]["FOR"], 19)
        self.assertEqual(bonuses["set_stats"]["COS"], 19)

        # Effective attributes and AC
        self.assertEqual(char.get_effective_ac(), 15) # 14 + 1
        self.assertEqual(char.get_effective_attribute("FOR"), 19)
        self.assertEqual(char.get_effective_attribute("COS"), 19)

if __name__ == "__main__":
    unittest.main()
