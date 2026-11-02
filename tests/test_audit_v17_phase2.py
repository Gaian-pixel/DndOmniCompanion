import unittest
from unittest.mock import MagicMock, patch
import os
import json
import html
import queue

from common.game_state import GameState, Player
from common.network_utils import sanitize_map_for_players
from common.dice import roll_dice
from common.session_chronicle import SessionLedger, ChronicleGenerator
from client.character_sheet_ui import CharacterSheetFrame
import server.rules.inventory as inventory_rules
import server.rules.character as character_rules
import server.rules.combat as combat_rules
import server.rules.movement as movement_rules


class TestAuditV17Phase2(unittest.TestCase):
    def setUp(self):
        self.gui_queue = queue.Queue()
        self.game_state = GameState(self.gui_queue)

    def test_2_1_game_state_sanitization_for_players(self):
        # Setup map with FoW
        self.game_state.current_map = {
            "fow_enabled": True,
            "fow_revealed": [[0, 0], [0, 1]]
        }

        # Party token
        party_player = Player("Eroe")
        party_player.position = [0, 0]
        party_player.is_party_member = True
        party_player.full_sheet = {
            "name": "Eroe",
            "actions": ["Attacco Spada"]
        }
        self.game_state.add_player(party_player)

        # Monster visible in revealed FoW
        monster = Player("Goblin")
        monster.position = [0, 1]
        monster.is_party_member = False
        monster.full_sheet = {
            "name": "Goblin",
            "actions": ["Attacco Furtivo Mortale", "Multiattacco"],
            "features": ["Scatto Astuto"],
            "special_abilities": ["Legame Telepatico"],
            "dm_notes": "Debole al fuoco"
        }
        self.game_state.add_player(monster)

        # Hidden token
        assassin = Player("Assassino")
        assassin.position = [0, 0]
        assassin.is_hidden = True
        assassin.full_sheet = {"name": "Assassino"}
        self.game_state.add_player(assassin)

        # GM layer token
        gm_trap = Player("TrappolaGM")
        gm_trap.position = [0, 0]
        gm_trap.layer = "gm"
        gm_trap.full_sheet = {"name": "TrappolaGM"}
        self.game_state.add_player(gm_trap)

        # Non-party token outside revealed FoW
        dragon = Player("DragoNascosto")
        dragon.position = [10, 10]
        dragon.is_party_member = False
        dragon.full_sheet = {"name": "DragoNascosto"}
        self.game_state.add_player(dragon)

        # Test as DM
        dm_state = self.game_state.get_state_dict(is_dm=True)
        dm_players = {p["name"]: p for p in dm_state["players"]}
        self.assertIn("Assassino", dm_players)
        self.assertIn("TrappolaGM", dm_players)
        self.assertIn("DragoNascosto", dm_players)
        self.assertIn("actions", dm_players["Goblin"]["full_sheet"])

        # Test as Player (not DM)
        player_state = self.game_state.get_state_dict(is_dm=False)
        players = {p["name"]: p for p in player_state["players"]}
        self.assertNotIn("Assassino", players, "Hidden tokens must be omitted for players")
        self.assertNotIn("TrappolaGM", players, "GM layer tokens must be omitted for players")
        self.assertNotIn("DragoNascosto", players, "Tokens in unrevealed FoW must be omitted for players")
        self.assertIn("Eroe", players)
        self.assertIn("Goblin", players)

        # Sensitive stats stripped from non-party full_sheet
        goblin_sheet = players["Goblin"].get("full_sheet", {})
        self.assertNotIn("actions", goblin_sheet)
        self.assertNotIn("features", goblin_sheet)
        self.assertNotIn("special_abilities", goblin_sheet)
        self.assertNotIn("dm_notes", goblin_sheet)

        # Party token sheet should NOT be stripped
        hero_sheet = players["Eroe"].get("full_sheet", {})
        self.assertIn("actions", hero_sheet)

        # Campaign folder hidden
        self.assertIsNone(player_state.get("active_campaign_folder"))

    def test_2_1_sanitize_map_for_players(self):
        full_map = {
            "grid_type": "hex",
            "walls": ["0,0|0,1"],
            "doors": [
                {"edge": "0,0|0,1", "is_secret": True, "discovered": False},
                {"edge": "1,1|1,2", "is_secret": False, "discovered": True}
            ],
            "traps": [
                {"q": 0, "r": 0, "hidden": True, "triggered": False, "name": "Fossa Nascosta"},
                {"q": 1, "r": 1, "hidden": False, "triggered": True, "name": "Fossa Attivata"}
            ],
            "room_pins": [
                {"id": 1, "dm_notes": "Qui c'è il tesoro segreto", "title": "Stanza 1", "secret": True},
                {"id": 2, "dm_notes": "Nota master", "title": "Stanza 2"}
            ],
            "pois": {
                "10": {"dm_notes": "PNG segreto", "title": "Taverna", "secret": True},
                "20": {"dm_notes": "Nota DM", "title": "Mercato"}
            },
            "loots": [
                {"q": 0, "r": 0, "gold": 100},
                {"q": 5, "r": 5, "gold": 500}
            ],
            "fow_enabled": True,
            "fow_revealed": [[0, 0]]
        }

        # Sanitize for player
        clean = sanitize_map_for_players(full_map)

        # Secret door removed from doors, but wall edge preserved for LoS
        clean_door_edges = [d.get("edge") for d in clean["doors"]]
        self.assertNotIn("0,0|0,1", clean_door_edges, "Secret door must not be in player doors")
        self.assertIn("1,1|1,2", clean_door_edges)
        self.assertIn("0,0|0,1", clean["walls"], "Secret door wall edge must remain in walls for collision/LoS")

        # Traps: hidden untriggered trap must be removed
        traps = clean["traps"]
        self.assertEqual(len(traps), 1)
        self.assertEqual(traps[0]["name"], "Fossa Attivata")

        # Room pins: secret pin removed, dm_notes stripped
        self.assertEqual(len(clean["room_pins"]), 1)
        self.assertEqual(clean["room_pins"][0]["title"], "Stanza 2")
        self.assertNotIn("dm_notes", clean["room_pins"][0])

        # POI: secret POI removed, dm_notes stripped
        self.assertEqual(len(clean["pois"]), 1)
        self.assertIn("20", clean["pois"])
        self.assertNotIn("10", clean["pois"])
        self.assertNotIn("dm_notes", clean["pois"]["20"])

        # Loot: loot at 5,5 is outside fow_revealed, must be filtered
        loot_positions = [(l.get("q"), l.get("r")) for l in clean["loots"]]
        self.assertIn((0, 0), loot_positions)
        self.assertNotIn((5, 5), loot_positions)

    def test_2_3_teleport_path_traversal_protection(self):
        player = Player("TestPlayer", None, MagicMock())
        self.game_state.add_player(player)
        self.game_state.current_map = {
            "fow_enabled": False,
            "teleports": {"1,1": "../../sensitive_file.json"}
        }
        with patch("server.rules.movement.os.path.exists", return_value=True), \
             patch("server.rules.movement.broadcast") as mock_bcast, \
             patch("builtins.open") as mock_open:
            movement_rules.handle_move_request({"to_pos": [1, 1], "is_teleport": True}, player, self.game_state)
            # Ensure open() was not called with directory traversal path
            if mock_open.called:
                opened_path = mock_open.call_args[0][0]
                self.assertNotIn("..", opened_path)

    def test_2_4_trade_validations(self):
        p1 = Player("Sender", None, MagicMock())
        p1.full_sheet = {
            "name": "SenderChar",
            "inventory": [{"id": "item1", "name": "Spada Lunga", "quantity": 1}],
            "currency": {"MO": 50}
        }
        self.game_state.add_player(p1)

        p2 = Player("Receiver", None, MagicMock())
        p2.full_sheet = {
            "name": "ReceiverChar",
            "inventory": [],
            "currency": {"MO": 10}
        }
        self.game_state.add_player(p2)

        # 1. Negative or zero amount gold transfer
        with patch("server.rules.inventory.send_message") as mock_send:
            inventory_rules.handle_give_gold_request({"target_name": "Receiver", "amount": -10}, p1, self.game_state)
            self.assertEqual(p1.full_sheet["currency"]["MO"], 50, "Negative gold transfer must be rejected")
            self.assertEqual(p2.full_sheet["currency"]["MO"], 10)

            inventory_rules.handle_give_gold_request({"target_name": "Receiver", "amount": 0}, p1, self.game_state)
            self.assertEqual(p1.full_sheet["currency"]["MO"], 50, "Zero gold transfer must be rejected")

        # 2. Negative or zero item quantity transfer
        with patch("server.rules.inventory.send_message") as mock_send:
            inventory_rules.handle_give_item_request({"target_name": "Receiver", "item_name": "Spada Lunga", "quantity": -1}, p1, self.game_state)
            self.assertEqual(len(p1.full_sheet["inventory"]), 1, "Negative item quantity must be rejected")
            self.assertEqual(len(p2.full_sheet["inventory"]), 0)

            inventory_rules.handle_give_item_request({"target_name": "Receiver", "item_name": "Spada Lunga", "quantity": 0}, p1, self.game_state)
            self.assertEqual(len(p1.full_sheet["inventory"]), 1, "Zero item quantity must be rejected")

    def test_2_4_permissions_authority(self):
        player1 = Player("Alice", None, MagicMock())
        player1.role = "Player"

        player2 = Player("Bob", None, MagicMock())
        player2.role = "Player"
        player2.owner = "Bob"
        player2.hp = 20
        player2.elevation = 0

        self.game_state.add_player(player1)
        self.game_state.add_player(player2)

        # Alice attempts to modify Bob's token stats
        with patch("server.rules.character.send_message") as mock_send:
            character_rules.handle_update_stats_request(
                {"token_name": "Bob", "hp": 1}, player1, self.game_state
            )
            self.assertEqual(player2.hp, 20, "Non-owner player must not modify stats")

        # Alice attempts to change elevation of Bob's token
        with patch("server.rules.character.send_message") as mock_send:
            character_rules.handle_set_elevation_request(
                {"token_name": "Bob", "elevation": 30}, player1, self.game_state
            )
            self.assertEqual(player2.elevation, 0, "Non-owner player must not set elevation")

        # Non-DM player attempts to force save
        with patch("server.rules.combat.send_message") as mock_send:
            combat_rules.handle_force_save_request(
                {"targets": ["Bob"], "stat": "COS", "dc": 20}, player1, self.game_state
            )
            mock_send.assert_not_called()

        # DM player can force save
        dm = Player("DM", None, None)
        dm.role = "DM"
        with patch("server.rules.combat.send_message") as mock_send:
            combat_rules.handle_force_save_request(
                {"targets": ["Bob"], "stat": "COS", "dc": 20}, dm, self.game_state
            )
            mock_send.assert_called_once()

    def test_2_4_dice_dos_protection(self):
        # Dice rolling group cap > 100
        with self.assertRaises(ValueError):
            roll_dice("1000d6")

        # Dice rolling sides cap > 1000
        with self.assertRaises(ValueError):
            roll_dice("1d2000")

        # Valid roll within caps
        res = roll_dice("2d6+3")
        self.assertGreaterEqual(res["total"], 5)
        self.assertLessEqual(res["total"], 15)

    def test_2_4_html_escaping(self):
        # 1. Session chronicle
        ledger = SessionLedger("Campagna <script>alert(1)</script>")
        ledger.record_loot("Spada <img src=x onerror=alert(2)>")
        html_output = ChronicleGenerator.generate_html(ledger)
        self.assertNotIn("<script>", html_output)
        self.assertIn("&lt;script&gt;", html_output)
        self.assertNotIn("<img src=x onerror=alert(2)>", html_output)
        self.assertIn("&lt;img src=x onerror=alert(2)&gt;", html_output)

        # 2. Character sheet HTML export
        malicious_char = {
            "name": "Eroe <script>evil()</script>",
            "race": "Umano <b>grassetto</b>",
            "char_class": "Guerriero",
            "custom_resources": [{"name": "<svg onload=alert(3)>", "current": 1, "max": 1, "reset_on": "Lungo"}],
            "weapons": [{"name": "<iframe src=evil>", "bonus": 3, "damage_dice": "1d8", "damage_type": "tagliente"}],
            "spellbook": [{"name": "<body onload=alert(4)>", "level": 1, "time": "1 azione", "range": "9m"}]
        }
        char_html = CharacterSheetFrame._generate_character_html(malicious_char)
        self.assertNotIn("<script>evil()</script>", char_html)
        self.assertIn("&lt;script&gt;evil()&lt;/script&gt;", char_html)
        self.assertNotIn("<svg onload=alert(3)>", char_html)
        self.assertIn("&lt;svg onload=alert(3)&gt;", char_html)
        self.assertNotIn("<iframe src=evil>", char_html)
        self.assertIn("&lt;iframe src=evil&gt;", char_html)
        self.assertNotIn("<body onload=alert(4)>", char_html)
        self.assertIn("&lt;body onload=alert(4)&gt;", char_html)


if __name__ == "__main__":
    unittest.main()
