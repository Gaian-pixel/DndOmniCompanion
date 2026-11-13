import os
import queue
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.character_manager import Character
from client.sheet_panels.spells_panel import SpellsPanel
from common.character_schema import filter_non_stacking_multiclass_features
from common.game_state import GameState, Player
from common.spell_effects_engine import (
    WILD_MAGIC_SURGE_TABLE,
    apply_metamagic_to_cast,
    apply_spell_movement_hazards,
    cast_iconic_spell,
    get_metamagic_cost,
    lookup_wild_magic_entry,
    maybe_trigger_wild_magic_surge,
    tick_active_spell_aoes_for_entity,
)
from server.rules.class_abilities import handle_cast_special_spell_request, validate_spell_casting_rules
from server.rules.combat import handle_attack_request, handle_reaction_response


class TestBlock2SpellsAndMulticlass(unittest.TestCase):
    def test_ritual_restrictions_and_spell_resources(self):
        wiz = Character(name="Gandalf", char_class="Mago", level=5)
        self.assertTrue(SpellsPanel.can_cast_as_ritual(wiz))
        self.assertTrue(SpellsPanel.spell_preparation_required(wiz))

        sorc = Character(name="Pyra", char_class="Stregone", level=5)
        sorc.sorcery_points_max = 5
        sorc.sorcery_points_current = 5
        self.assertFalse(SpellsPanel.can_cast_as_ritual(sorc))
        self.assertFalse(SpellsPanel.spell_preparation_required(sorc))

        # Sorcerer cannot cast ritual unless Ritual Caster feat
        sp_rit = {"name": "Individuazione del Magico", "level": 1, "ritual": True}
        ok_r, _, err_r = SpellsPanel.execute_spell_resource_cost(sorc, sp_rit, 1, is_ritual=True)
        self.assertFalse(ok_r)
        self.assertIn("Rituale", err_r)

        sorc.features = "Talento: Incantatore Rituale (Ritual Caster)"
        self.assertTrue(SpellsPanel.can_cast_as_ritual(sorc))

        # Warlock pact slot + Metamagic spending
        war = Character(name="Wyll", char_class="Warlock", level=5)
        war.pact_slots = {"max": 2, "current": 2, "level": 3}
        war.sorcery_points_max = 4
        war.sorcery_points_current = 4
        ok_w, tags_w, err_w = SpellsPanel.execute_spell_resource_cost(
            war, {"name": "Hex", "level": 1}, 1, use_pact=True, metamagic_key="twinned"
        )
        self.assertTrue(ok_w, err_w)
        self.assertEqual(war.pact_slots["current"], 1)
        self.assertEqual(war.sorcery_points_current, 1)  # cast at pact level 3 => twinned costs 3!

        # Material component consumption (inventory + fallback MO)
        wiz.inventory_grid = [{"name": "Diamante da 300 mo", "qty": 2}]
        msg_mat = SpellsPanel.consume_material_component(wiz, {"name": "Rinascita", "desc": "diamante da 300 mo consumato"}, 300)
        self.assertIn("Diamante", msg_mat)
        self.assertEqual(wiz.inventory_grid[0]["qty"], 1)

        # Spell points DMG limit on 6th+ level once per long rest
        wiz.spell_points_max = 60
        wiz.spell_points_current = 60
        ok1, _, _ = SpellsPanel.execute_spell_resource_cost(wiz, {"name": "Disintegrazione", "level": 6}, 6, use_spell_points=True)
        self.assertTrue(ok1)
        ok2, _, err2 = SpellsPanel.execute_spell_resource_cost(wiz, {"name": "Disintegrazione", "level": 6}, 6, use_spell_points=True)
        self.assertFalse(ok2)
        self.assertIn("DMG p. 288", err2)

    def test_multiclass_non_stacking_features(self):
        c = Character(name="Grog", char_class="Barbaro", level=5)
        c.features = "- Attacco Extra\n- Difesa Senza Armatura"
        kept, skipped = filter_non_stacking_multiclass_features(
            c, ["Attacco Extra", "Difesa Senza Armatura", "Azione Impetuosa", "Attacco Extra (2)"]
        )
        self.assertEqual(kept, ["Azione Impetuosa", "Attacco Extra (2)"])
        self.assertEqual(len(skipped), 2)

    def test_wild_magic_table_completeness_and_trigger(self):
        # Verify exact full coverage 1..100
        covered = set()
        for lo, hi, desc, code in WILD_MAGIC_SURGE_TABLE:
            self.assertGreater(len(desc), 5)
            self.assertTrue(code)
            for n in range(lo, hi + 1):
                self.assertNotIn(n, covered)
                covered.add(n)
        self.assertEqual(covered, set(range(1, 101)))

        desc_100, code_100 = lookup_wild_magic_entry(100)
        self.assertEqual(code_100, "regain_all_sp")

        gs = GameState(queue.Queue())
        gs.broadcast_queue = []
        sorc = Player("Zara")
        sorc.hp = 10
        sorc.max_hp = 30
        sorc.subclass = "Magia Selvaggia"
        sorc.sorcery_points_max = 4
        sorc.sorcery_points_current = 0
        sorc.wild_magic_tides_used = True
        gs.players = [sorc]

        # Tides of Chaos forces surge without needing d20=1 and recharges Tides
        res = maybe_trigger_wild_magic_surge(sorc, 2, gs, forced_d20=15, forced_d100=39)
        self.assertTrue(res["triggered"])
        self.assertFalse(sorc.wild_magic_tides_used)
        self.assertGreater(sorc.hp, 10)  # heal_2d10 ran!

    def test_metamagic_subtle_bypasses_silence_and_iconic_spells(self):
        self.assertEqual(get_metamagic_cost("twinned", 4), 4)
        self.assertEqual(get_metamagic_cost("heightened", 1), 3)

        gs = GameState(queue.Queue())
        gs.broadcast_queue = []
        gs.active_aoes = []
        mage = Player("Elminster")
        mage.hp = 40
        mage.max_hp = 40
        mage.ac = 11
        mage.position = [0, 0]
        mage.conditions = ["Silenzio"]
        mage.full_sheet = {"attributes": {"FOR": 10, "DES": 14, "COS": 12, "INT": 18, "SAG": 12, "CAR": 14}, "level": 5}
        orc = Player("Orco")
        orc.hp = 35
        orc.max_hp = 35
        orc.ac = 13
        orc.position = [1, 0]
        orc.full_sheet = {"attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 8, "SAG": 10, "CAR": 8}, "level": 3}
        gs.players = [mage, orc]

        # Normal verbal blocked in Silence
        ok_n, _ = validate_spell_casting_rules(mage, 1, "action", True, gs, is_subtle=False)
        self.assertFalse(ok_n)
        # Subtle spell passes!
        ok_s, _ = validate_spell_casting_rules(mage, 1, "action", True, gs, is_subtle=True)
        self.assertTrue(ok_s)

        # Iconic spells runtime
        cast_iconic_spell(mage, mage, "Armatura Magica", 1, gs)
        self.assertEqual(mage.ac, 15)  # 13 + 2 DEX

        cast_iconic_spell(mage, mage, "Armatura di Agathys", 2, gs)
        self.assertEqual(mage.temp_hp, 10)
        self.assertEqual(mage.agathys_cold_dmg, 10)

        cast_iconic_spell(mage, orc, "Sortilegio (Hex)", 1, gs)
        self.assertEqual(mage.hex_target, "Orco")

        # Orc attacks Mage wearing Armor of Agathys -> takes 10 Cold retaliation!
        with patch("server.rules.combat.random.randint", return_value=18):
            handle_attack_request({"target_name": "Elminster", "weapon_name": "Ascia", "hit_bonus": 5, "damage_formula": "1d8+3"}, orc, gs)
        self.assertEqual(orc.hp, 25)

        # Mirror Image intercepts hit & loses duplicate
        mage.mirror_images = 3
        with patch("common.spell_effects_engine.random.randint", return_value=15), patch("server.rules.combat.random.randint", return_value=18):
            handle_attack_request({"target_name": "Elminster", "weapon_name": "Ascia", "hit_bonus": 5, "damage_formula": "1d8+3"}, orc, gs)
        self.assertEqual(mage.mirror_images, 2)

        # Sanctuary blocks failed WIS save attacker
        mage.sanctuary_dc = 25
        hp_before = mage.hp
        with patch("common.dice.roll_dice", return_value={"total": 2, "rolls": [2]}):
            handle_attack_request({"target_name": "Elminster", "weapon_name": "Ascia", "hit_bonus": 10, "damage_formula": "1d8+3"}, orc, gs)
        self.assertEqual(mage.hp, hp_before)

        # Spike Growth movement + Hunger of Hadar turn tick
        cast_iconic_spell(mage, orc, "Crescita di Spine", 2, gs)
        haz = apply_spell_movement_hazards(orc, [0, 0], [1, 0], gs)
        self.assertTrue(haz and "CRESCITA DI SPINE" in haz[0])

        cast_iconic_spell(mage, orc, "Fame di Hadar", 3, gs)
        tick = tick_active_spell_aoes_for_entity(orc, "start_of_turn", gs)
        self.assertTrue(tick and "FAME DI HADAR" in tick[0])

        # Hellish Rebuke & Silvery Barbs reactions
        mage.has_reacted_this_turn = False
        handle_reaction_response({"reaction_type": "HELLISH_REBUKE", "accepted": True, "target_name": "Orco", "details": {"slot_consumed": True, "slot_level": 1}}, mage, gs)
        mage.has_reacted_this_turn = False
        handle_reaction_response({"reaction_type": "SILVERY_BARBS", "accepted": True, "target_name": "Orco", "details": {"slot_consumed": True}}, mage, gs)
        self.assertTrue(getattr(mage, "silvery_advantage", False))


if __name__ == "__main__":
    unittest.main()
