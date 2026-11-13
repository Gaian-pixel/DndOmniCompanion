# -*- coding: utf-8 -*-
import os
import queue
import sys
import unittest

os.environ["DND_MOCK_AUDIO"] = "1"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.game_state import GameState, Player
from server.dm_monster_engine import (
    apply_monster_special_hit_effects,
    apply_rust_metal_melee_retaliation,
    check_petrifying_gaze_at_turn_start,
    execute_monster_multiattack,
    is_in_beholder_antimagic_cone,
    parse_monster_multiattack,
    restore_drain_penalties,
    roll_beholder_eye_rays,
    toggle_antimagic_cone,
)
from server.rules.class_abilities import validate_spell_casting_rules
from server.rules.combat import apply_damage


class TestBlock6MonsterManual(unittest.TestCase):
    def test_multiattack_parser_and_one_click_executor(self):
        gs = GameState(queue.Queue())
        dragon = Player("Drago Giovane")
        dragon.hp = 120
        dragon.max_hp = 120
        dragon.full_sheet = {
            "actions": [
                {"name": "Multiattack", "desc": "The dragon makes three attacks: one with its bite and two with its claws."},
                {"name": "Bite", "attack_bonus": 7, "damage_dice": "2d10+4", "desc": "Melee Weapon Attack: +7 to hit. Hit: 15 (2d10 + 4) piercing damage."},
                {"name": "Claw", "attack_bonus": 7, "damage_dice": "2d6+4", "desc": "Melee Weapon Attack: +7 to hit. Hit: 11 (2d6 + 4) slashing damage."},
            ]
        }
        seq = parse_monster_multiattack(dragon)
        self.assertEqual(len(seq), 2)
        self.assertEqual(seq[0][0]["name"], "Bite")
        self.assertEqual(seq[0][1], 1)
        self.assertEqual(seq[1][0]["name"], "Claw")
        self.assertEqual(seq[1][1], 2)

        res = execute_monster_multiattack(dragon, game_state=gs)
        self.assertTrue(res["ok"])
        self.assertEqual(len(res["rolls"]), 3)
        self.assertGreater(res["total_damage"], 0)

    def test_undead_fortitude_triggers_except_crit_and_radiant(self):
        gs = GameState(queue.Queue())
        z1 = Player("Zombie 1")
        z1.hp = 5
        z1.max_hp = 22
        z1.full_sheet = {"attributes": {"COS": 16}, "features": ["Undead Fortitude. If damage reduces the zombie to 0 hit points..."]}
        gs.add_player(z1)

        # Radiant bypasses Undead Fortitude
        apply_damage(z1, 8, damage_type="Radioso", game_state=gs)
        self.assertEqual(z1.hp, 0)

        # Critical hit bypasses Undead Fortitude
        z2 = Player("Zombie 2")
        z2.hp = 5
        z2.max_hp = 22
        z2.full_sheet = {"attributes": {"COS": 16}, "features": ["Tenacia dei Non Morti"]}
        gs.add_player(z2)
        apply_damage(z2, 8, damage_type="Tagliente", game_state=gs, is_crit=True)
        self.assertEqual(z2.hp, 0)

        # Normal non-radiant hit with very high CON save (+30) passes DC (5 + 6 = 11) -> stays at 1 HP
        z3 = Player("Zombie 3")
        z3.hp = 5
        z3.max_hp = 22
        z3.full_sheet = {"attributes": {"COS": 70}, "features": ["Undead Fortitude"]}
        gs.add_player(z3)
        apply_damage(z3, 6, damage_type="Tagliente", game_state=gs, is_crit=False)
        self.assertEqual(z3.hp, 1)

    def test_life_drain_strength_drain_and_rust_metal(self):
        wight = Player("Wight")
        shadow = Player("Ombra")
        shadow.full_sheet = {"features": ["Strength Drain"]}
        rust_mon = Player("Mostro della Ruggine")
        rust_mon.full_sheet = {"features": ["Rust Metal", "Antennae"]}

        hero = Player("Kael")
        hero.hp = 30
        hero.max_hp = 30
        hero.ac = 16
        hero.attributes = {"FOR": 8}
        hero.full_sheet = {"attributes": {"FOR": 8, "COS": 10}, "max_hp": 30, "hp_current": 30}

        # Life Drain fails save -> max_hp reduced
        notes = apply_monster_special_hit_effects(
            wight, hero, attack_name="Life Drain", attack_desc="DC 15 Constitution saving throw",
            damage_dealt=10, forced_save_roll=3
        )
        self.assertEqual(hero.max_hp, 20)
        self.assertEqual(hero.hp, 20)
        self.assertTrue(any("RISUCCHIO DI VITA" in n for n in notes))

        # Rust/Corrode armor lowers AC
        apply_monster_special_hit_effects(rust_mon, hero, attack_name="Antennae", attack_desc="rusts nonmagical armor")
        self.assertEqual(hero.ac, 15)

        # Rust Monster passive retaliation reduces hero's weapon damage cumulatively
        msg_ret = apply_rust_metal_melee_retaliation(hero, rust_mon, is_ranged=False, is_magical=False)
        self.assertIsNotNone(msg_ret)
        self.assertEqual(hero.rust_weapon_penalty, 1)

        # Strength Drain draining STR -> restores on short rest; Life Drain restores on long rest
        apply_monster_special_hit_effects(shadow, hero, attack_name="Strength Drain", attack_desc="1d4", forced_drain_roll=3)
        self.assertEqual(hero.attributes["FOR"], 5)
        restore_drain_penalties(hero, rest_type="short")
        self.assertEqual(hero.attributes["FOR"], 8)
        self.assertEqual(hero.max_hp, 20)  # still reduced until long rest
        restore_drain_penalties(hero, rest_type="long")
        self.assertEqual(hero.max_hp, 30)

        # Fatal Strength Drain -> STR <= 0 kills target
        apply_monster_special_hit_effects(shadow, hero, attack_name="Strength Drain", attack_desc="1d4", forced_drain_roll=10)
        self.assertIn("Morto", hero.conditions)
        self.assertEqual(hero.hp, 0)

    def test_beholder_eye_rays_antimagic_cone_and_petrifying_gaze(self):
        gs = GameState(queue.Queue())
        beholder = Player("Beholder")
        beholder.hp = 180
        beholder.max_hp = 180
        beholder.position = [0, 0]
        gs.add_player(beholder)

        mage = Player("Elminster")
        mage.hp = 50
        mage.max_hp = 50
        mage.is_party_member = True
        mage.position = [4, 0]  # Directly along +x (angle 0 deg, distance 4 hexes)
        mage.full_sheet = {"attributes": {"COS": 10, "DES": 10, "SAG": 10}}
        gs.add_player(mage)

        # Toggle Antimagic Cone pointing 0 deg -> Mage inside cannot cast spells
        self.assertTrue(toggle_antimagic_cone(beholder, gs, active=True, direction_deg=0.0, range_hexes=30))
        self.assertTrue(is_in_beholder_antimagic_cone(mage, gs))
        ok_cast, err_cast = validate_spell_casting_rules(mage, spell_level=3, game_state=gs)
        self.assertFalse(ok_cast)
        self.assertIn("Antimagia", err_cast)

        # Turning cone away (180 deg) frees mage
        toggle_antimagic_cone(beholder, gs, active=True, direction_deg=180.0, range_hexes=30)
        self.assertFalse(is_in_beholder_antimagic_cone(mage, gs))
        self.assertTrue(validate_spell_casting_rules(mage, spell_level=3, game_state=gs)[0])

        # 3 Random Eye Rays (forced indices 5, 8, 9)
        ray_res = roll_beholder_eye_rays(beholder, targets=[mage], game_state=gs, forced_indices=[5, 8, 9])
        self.assertEqual(len(ray_res["rays"]), 3)
        self.assertEqual([r["ray_number"] for r in ray_res["rays"]], [5, 8, 9])

        # Petrifying Gaze: averting_eyes prevents save check; un-averted triggers petrification stage 1 on fail
        basilisk = Player("Basilisco")
        basilisk.hp = 52
        basilisk.max_hp = 52
        basilisk.position = [1, 0]
        basilisk.full_sheet = {"special_abilities": [{"name": "Petrifying Gaze", "desc": "DC 12 Constitution saving throw"}]}
        gs.add_player(basilisk)

        fighter = Player("Tordek")
        fighter.hp = 40
        fighter.max_hp = 40
        fighter.is_party_member = True
        fighter.position = [2, 0]
        fighter.full_sheet = {"attributes": {"COS": 10}}
        fighter.averting_eyes = True
        gs.add_player(fighter)

        av_msg = check_petrifying_gaze_at_turn_start(fighter, gs, forced_roll=1)
        self.assertIn("distoglie lo sguardo", av_msg.lower())
        self.assertEqual(getattr(fighter, "petrification_stage", 0), 0)

        fighter.averting_eyes = False
        gaze_msg = check_petrifying_gaze_at_turn_start(fighter, gs, forced_roll=2)
        self.assertIn("PIETRIFICAZIONE STADIO 1", gaze_msg)
        self.assertEqual(fighter.petrification_stage, 1)
        self.assertIn("Trattenuto", fighter.conditions)


if __name__ == "__main__":
    unittest.main()
