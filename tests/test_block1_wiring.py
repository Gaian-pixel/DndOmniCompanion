import os
import queue
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.game_state import GameState, Player
from common.item_modifiers import recharge_item_dict, use_item_charge_dict
from common.protocol import make_buy_item_request, make_stand_up_request
from server.dm_monster_engine import (
    check_swallow_internal_regurgitation,
    is_recharge_ability,
    mark_monster_ability_used,
)
from server.dm_optional_tools import (
    handle_optional_rule_action_request,
    open_optional_rules_tools_dialog,
)


class TestBlock1WiringAndGaps(unittest.TestCase):
    def test_protocol_helpers(self):
        self.assertEqual(make_stand_up_request(), {"type": "STAND_UP_REQUEST", "data": {}})
        buy = make_buy_item_request("Armeria", "Spada Lunga")
        self.assertEqual(buy["type"], "BUY_ITEM_REQUEST")
        self.assertEqual(buy["data"], {"shop_name": "Armeria", "item_name": "Spada Lunga"})

    def test_wand_zero_charges_d20_1_destroys_magic(self):
        item = {"name": "Bacchetta dei Dardi", "charges_current": 1, "charges_max": 7, "attuned": True}
        with patch("common.dice.roll_dice", return_value={"total": 1}):
            ok, msg = use_item_charge_dict(item, 1)
        self.assertTrue(ok)
        self.assertIn("1d20 = 1", msg)
        self.assertTrue(item.get("magic_destroyed"))
        self.assertEqual(item["charges_max"], 0)
        self.assertFalse(item["attuned"])
        self.assertIn("[Senza Magia]", item["name"])

        self.assertIsNone(recharge_item_dict(item))
        ok_after, _ = use_item_charge_dict(item, 1)
        self.assertFalse(ok_after)

        safe_item = {"name": "Bastone Sicuro", "charges_current": 1, "charges_max": 5, "no_destroy_on_zero": True}
        with patch("common.dice.roll_dice", return_value={"total": 1}):
            ok_safe, msg_safe = use_item_charge_dict(safe_item, 1)
        self.assertTrue(ok_safe)
        self.assertFalse(safe_item.get("magic_destroyed", False))
        self.assertIn("resta intatto", msg_safe)
        self.assertEqual(safe_item["charges_current"], 0)

    def test_recharge_4_to_6_and_expended_tracking(self):
        act = {"name": "Soffio di Fuoco (Ricarica 4-6)", "desc": "Recharge 4-6 fire breath"}
        self.assertTrue(is_recharge_ability(act))

        gs = GameState(queue.Queue())
        drake = Player("Drago")
        drake.is_party_member = False
        drake.hp = 60
        drake.max_hp = 60
        drake.initiative = 15
        drake.swallow_damage_taken = 25
        drake.full_sheet = {"actions": [dict(act)]}
        hero = Player("Hero")
        hero.hp = 30
        hero.max_hp = 30
        hero.initiative = 20
        gs.players = [hero, drake]
        gs.combat_active = True
        gs.turn_order = ["Hero", "Drago"]
        gs.current_turn_index = 0

        already_exp, note = mark_monster_ability_used(drake, drake.full_sheet["actions"][0])
        self.assertFalse(already_exp)
        self.assertIn("RICARICA", note)
        self.assertTrue(drake.full_sheet["actions"][0]["expended"])

        already_exp2, warn2 = mark_monster_ability_used(drake, drake.full_sheet["actions"][0])
        self.assertTrue(already_exp2)
        self.assertIn("SCARICA", warn2)

        # Roll 4 -> recharges 4-6 ability and resets swallow_damage_taken
        with patch("random.randint", return_value=4):
            gs.next_turn()
        self.assertEqual(gs.get_current_turn_player().name, "Drago")
        self.assertFalse(drake.full_sheet["actions"][0].get("expended", False))
        self.assertEqual(drake.swallow_damage_taken, 0)

    def test_swallow_internal_damage_regurgitation(self):
        gs = GameState(queue.Queue())
        gs.broadcast_queue = []
        toad = Player("Rospo Gigante")
        toad.hp = 80
        toad.max_hp = 80
        toad.swallow_regurg_threshold = 20
        toad.swallow_regurg_dc = 15
        hero = Player("Guerriero")
        hero.hp = 35
        hero.max_hp = 35
        hero.conditions = ["Ingoiato (Swallowed)"]
        hero.swallowed_by = "Rospo Gigante"
        gs.players = [toad, hero]

        with patch("common.dice.roll_dice", return_value={"total": 8}):
            msg = check_swallow_internal_regurgitation(toad, hero, 24, gs)
        self.assertIsNotNone(msg)
        self.assertIn("RIGURGITO", msg)
        self.assertNotIn("Ingoiato (Swallowed)", hero.conditions)
        self.assertIsNone(getattr(hero, "swallowed_by", None))

    def test_optional_rule_client_actions_and_workbench_export(self):
        self.assertTrue(callable(open_optional_rules_tools_dialog))
        gs = GameState(queue.Queue())
        p = Player("Ayla")
        p.hp = 20
        p.max_hp = 25
        p.full_sheet = {"attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 14}, "level": 3}
        gs.players = [p]

        handle_optional_rule_action_request({"action": "declare_speed_factor", "speed_action": "light"}, p, gs)
        self.assertEqual(p.speed_factor_declared_action, "light")

        handle_optional_rule_action_request({"action": "toggle_squeeze"}, p, gs)
        self.assertTrue(p.is_squeezing)
        self.assertTrue(any("spremere" in c.lower() for c in p.conditions))
        handle_optional_rule_action_request({"action": "toggle_squeeze"}, p, gs)
        self.assertFalse(p.is_squeezing)

        handle_optional_rule_action_request({"action": "jump_check", "running_start": True}, p, gs)
        handle_optional_rule_action_request({"action": "racial_trait", "trait": "healing_hands", "target_name": "Ayla"}, p, gs)
        self.assertEqual(p.hp, 23)


if __name__ == "__main__":
    unittest.main()
