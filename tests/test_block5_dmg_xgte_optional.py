# -*- coding: utf-8 -*-
import os
import queue
import sys
import unittest

os.environ["DND_MOCK_AUDIO"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.game_state import GameState, Player
from common.spell_effects_engine import maybe_trigger_wild_magic_surge
from server.dm_dmg_systems import (
    adjust_npc_loyalty,
    apply_vehicle_damage,
    calculate_monster_cr_dmg,
    create_vehicle_state,
    resolve_mob_attack,
    resolve_social_check,
    resolve_spell_scroll_use,
    resolve_wilderness_hazard,
    resolve_wilderness_travel_checks,
    roll_potion_miscibility,
)
from server.dm_optional_tools import handle_optional_rule_action_request
from server.rules.downtime import resolve_downtime_activity


class TestBlock5DmgXgteOptionalRules(unittest.TestCase):
    def test_cr_calculator_dmg_accuracy_and_modifiers(self):
        # HP 100 -> row CR 2 (AC 13); actual AC 17 -> +4 AC (+2 shift -> CR 4 Def).
        # DPR 24 -> row CR 3 (Atk +4); actual Atk +4 -> CR 3 Off. Avg (4+3)/2=3.5 -> rounds up to CR 4.
        res = calculate_monster_cr_dmg(hp=100, ac=17, dpr=24, attack_bonus=4)
        self.assertEqual(res["defensive_cr"], "4")
        self.assertEqual(res["offensive_cr"], "3")
        self.assertEqual(res["final_cr"], "4")
        self.assertEqual(res["xp"], 1100)

        # Low-CR resistance doubles effective HP, magic resistance adds +2 effective AC
        res_mr = calculate_monster_cr_dmg(hp=40, ac=13, dpr=10, attack_bonus=3, has_resistances=True, magic_resistance=True)
        self.assertEqual(res_mr["effective_hp"], 80)
        self.assertEqual(res_mr["effective_ac"], 15)

    def test_mob_attack_table_and_dispatch(self):
        self.assertEqual(resolve_mob_attack(10, attack_bonus=5, target_ac=10, damage_per_hit=4)["hits"], 10)  # need 5 -> 1/hit
        self.assertEqual(resolve_mob_attack(8, attack_bonus=4, target_ac=15, damage_per_hit=5)["hits"], 4)    # need 11 -> 2/hit
        self.assertEqual(resolve_mob_attack(10, attack_bonus=0, target_ac=19, damage_per_hit=6)["hits"], 1)   # need 19 -> 10/hit
        self.assertEqual(resolve_mob_attack(19, attack_bonus=0, target_ac=25, damage_per_hit=6)["hits"], 0)   # need 20 -> 20/hit

        gs = GameState(queue.Queue())
        hero = Player("Valen")
        hero.hp = 30
        hero.max_hp = 30
        hero.ac = 15
        gs.add_player(hero)
        handle_optional_rule_action_request(
            {"action": "mob_attack", "target_name": "Valen", "num_attackers": 8, "attack_bonus": 4, "damage_per_hit": 5, "apply_damage": True},
            hero,
            gs,
        )
        self.assertEqual(hero.hp, 10)

    def test_potion_miscibility_and_spell_scroll_mishap_toggle(self):
        exp = roll_potion_miscibility(d100_roll=1)
        self.assertEqual(exp["code"], "EXPLOSION")
        self.assertGreaterEqual(exp["self_damage"], 6)
        self.assertEqual(roll_potion_miscibility(d100_roll=50)["code"], "NORMAL")
        self.assertEqual(roll_potion_miscibility(d100_roll=100)["code"], "PERMANENT")

        # Off-list spell scroll is unintelligible
        off = resolve_spell_scroll_use(3, on_class_list=False, max_castable_level=5)
        self.assertTrue(off["unintelligible"])
        self.assertFalse(off["scroll_consumed"])

        # Failed check + failed DC 10 WIS save with mishap enabled triggers 1..6 table
        fail_mishap = resolve_spell_scroll_use(
            3, on_class_list=True, max_castable_level=1, caster_ability_mod=2,
            check_roll=5, mishap_save_mod=0, mishap_save_roll=4, mishap_table_roll=1, trigger_mishap_on_fail=True
        )
        self.assertFalse(fail_mishap["success"])
        self.assertIsNotNone(fail_mishap["mishap"])
        self.assertGreaterEqual(fail_mishap["mishap"]["damage"], 3)

        # Mishap disabled when DM turns opt_scroll_mishap off
        no_mishap = resolve_spell_scroll_use(
            3, on_class_list=True, max_castable_level=1, caster_ability_mod=2,
            check_roll=5, trigger_mishap_on_fail=False
        )
        self.assertFalse(no_mishap["success"])
        self.assertIsNone(no_mishap["mishap"])

    def test_social_thresholds_loyalty_and_vehicles(self):
        self.assertEqual(resolve_social_check("friendly", 10)["outcome_code"], "MINOR_RISK")
        self.assertEqual(resolve_social_check("indifferent", 10)["outcome_code"], "HELPS_NO_RISK")
        self.assertEqual(resolve_social_check("hostile", 10)["outcome_code"], "NEUTRAL_NO_HELP")
        self.assertEqual(resolve_social_check("hostile", 20)["outcome_code"], "HELPS_NO_RISK")

        gs = GameState(queue.Queue())
        npc = Player("Mercenary")
        npc.hp = 20
        npc.max_hp = 20
        npc.npc_loyalty = 8
        gs.add_player(npc)
        handle_optional_rule_action_request({"action": "social_loyalty", "target_name": "Mercenary", "loyalty_delta": -15}, npc, gs)
        self.assertEqual(npc.npc_loyalty, 0)
        self.assertEqual(adjust_npc_loyalty(15, 10)["loyalty"], 20)

        ship = create_vehicle_state("sailing_ship", custom_name="Aurora")
        # Hull DT is 15 -> 14 dmg blocked
        r_block = apply_vehicle_damage(ship, 14, component="hull")
        self.assertTrue(r_block["blocked_by_threshold"])
        self.assertEqual(ship["hull"]["hp"], 300)
        # Sails 0 HP halves speed
        apply_vehicle_damage(ship, 100, component="sails")
        self.assertEqual(ship["speed_ft"], 17)
        # Helm 0 HP -> unsteerable
        apply_vehicle_damage(ship, 50, component="helm")
        self.assertTrue(ship["unsteerable"])
        # Hull 0 HP -> sinking
        apply_vehicle_damage(ship, 300, component="hull")
        self.assertTrue(ship["sinking"])

    def test_wilderness_navigation_foraging_and_hazards(self):
        lost = resolve_wilderness_travel_checks("forest", nav_roll_total=12, forage_roll_total=12, pace="fast")
        self.assertTrue(lost["got_lost"])  # 12 - 5 = 7 < DC 15
        self.assertFalse(lost["can_forage"])

        ranger_ok = resolve_wilderness_travel_checks("forest", nav_roll_total=5, forage_roll_total=12, wis_mod=3, pace="slow", has_ranger_natural_explorer=True)
        self.assertFalse(ranger_ok["got_lost"])
        self.assertTrue(ranger_ok["forage_success"])
        self.assertGreaterEqual(ranger_ok["food_pounds"], 8)  # 2x (1d6+3)

        mold = resolve_wilderness_hazard("brown_mold", save_total=8)
        self.assertFalse(mold["saved"])
        self.assertGreaterEqual(mold["damage"], 4)

    def test_xgte_downtime_and_optional_toggles_preserved(self):
        gs = GameState(queue.Queue())
        gs.automation_settings["opt_xgte_downtime_complications"] = True
        gs.automation_settings["opt_wild_magic_surge"] = False
        # Preset change must preserve DMG/XGtE/TCE optional flags
        gs.set_automation_mode("manual")
        self.assertTrue(gs.automation_settings["opt_xgte_downtime_complications"])
        self.assertFalse(gs.automation_settings["opt_wild_magic_surge"])

        # Wild magic surge respects opt_wild_magic_surge=False
        sorc = Player("Lyra")
        sorc.hp = 20
        sorc.max_hp = 20
        sorc.subclass = "Magia Selvaggia"
        sorc.currency = {"pp": 0, "gp": 500, "ep": 0, "sp": 0, "cp": 0}
        self.assertIsNone(maybe_trigger_wild_magic_surge(sorc, spell_level=1, game_state=gs, forced_d20=1))

        ok, msg = resolve_downtime_activity(
            sorc,
            {
                "activity": "crafting_magic",
                "days": 7,
                "lifestyle": "modest",
                "item_name": "Pozione di Volo",
                "rarity": "non comune",
                "consumable": True,
                "forced_complication_roll": 5,
            },
            game_state=gs,
        )
        self.assertTrue(ok)
        self.assertIn("Forgia Magica", msg)
        self.assertIn("Complicazione XGtE", msg)

        ok_pit, msg_pit = resolve_downtime_activity(
            sorc,
            {"activity": "pit_fighting", "days": 7, "lifestyle": "wretched", "forced_wins": 3, "skip_complication": True},
            game_state=gs,
        )
        self.assertTrue(ok_pit)
        self.assertIn("200.0 mo", msg_pit)


if __name__ == "__main__":
    unittest.main()
