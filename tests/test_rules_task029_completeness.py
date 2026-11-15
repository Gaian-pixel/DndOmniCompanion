"""Regression suite for TASK-029 D&D 5e (2014) rules completeness & combat/magic/MM integration."""

import queue
import unittest
from unittest.mock import MagicMock, patch

from client.character_manager import Character
from client.sheet_panels.spells_panel import SpellsPanel
from common.dnd5e_tables import entity_has_elemental_adept
from common.encounter_calc import calculate_encounter_difficulty
from common.game_state import GameState, Player
from common.item_modifiers import compute_death_save_flat_bonus
from common.protocol import make_death_save_request
from common.subclass_and_race_rules import get_implicit_racial_resistances
from server.commands import command_handlers
from server.dm_monster_engine import (
    execute_monster_multiattack,
    roll_beholder_eye_rays,
    trigger_lair_actions_if_crossed,
)
from server.rules.character import handle_update_full_sheet_request
from server.rules.class_abilities import handle_cast_special_spell_request, handle_class_feature_request
from server.rules.combat import (
    _process_save_result,
    apply_damage,
    handle_attack_request,
    handle_grapple_request,
    handle_reaction_response,
    handle_shove_request,
    resolve_falling,
)
from server.rules.map_interaction import handle_resolve_aoe_request


def _make_player(name, hp=30, max_hp=30, ac=15, pos=(0, 0), is_party=True, sheet=None):
    p = Player(name)
    p.hp = hp
    p.max_hp = max_hp
    p.ac = ac
    p.position = list(pos)
    p.is_party_member = is_party
    p.conditions = []
    p.active_effects = []
    p.full_sheet = sheet if sheet is not None else {}
    return p


class TestTask029RulesCompleteness(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True

    def test_cr10_cr25_xp_misty_step_ritual_and_radioso_resistance(self):
        diff10 = calculate_encounter_difficulty([10], [10, 10, 10, 10])
        diff25 = calculate_encounter_difficulty([10], [25, 25, 25, 25])
        self.assertGreaterEqual(diff10["adjusted_xp"], 5900)
        self.assertGreaterEqual(diff25["adjusted_xp"], 75000)

        self.assertFalse(SpellsPanel.is_ritual_spell({"name": "Passo Velato", "ritual": False}))
        self.assertFalse(SpellsPanel.is_ritual_spell("Passo Velato"))
        self.assertTrue(SpellsPanel.is_ritual_spell("Individuazione del Magico"))

        aasimar = _make_player("Celestiale", sheet={"race": "Aasimar", "level": 3})
        res = get_implicit_racial_resistances(aasimar)
        self.assertIn("radiante", res)
        self.assertIn("radioso", res)
        target = _make_player("Angiolo", hp=40, max_hp=40, sheet={"race": "Aasimar", "damage_resistances": ["Radioso"]})
        dealt, _, _, _ = apply_damage(target, 16, "Radiante", self.gs)
        self.assertEqual(dealt, 8)
        target2 = _make_player("Santo", hp=40, max_hp=40, sheet={"damage_resistances": ["Radiant"]})
        dealt2, _, _, _ = apply_damage(target2, 16, "Radioso", self.gs)
        self.assertEqual(dealt2, 8)

    def test_smite_separated_from_physical_and_resource_guards(self):
        pal = _make_player(
            "Uther",
            pos=(0, 0),
            sheet={
                "char_class": "Paladino",
                "level": 11,
                "attributes": {"FOR": 16},
                "spell_slots": {"1": {"max": 4, "current": 1}},
            },
        )
        gargoyle = _make_player(
            "Golem",
            hp=60,
            max_hp=60,
            ac=10,
            pos=(1, 0),
            is_party=False,
            sheet={"damage_immunities": ["Tagliente"], "type": "Costrutto"},
        )
        self.gs.players = [pal, gargoyle]
        with patch("random.randint", return_value=5):
            handle_attack_request(
                {
                    "target_name": "Golem",
                    "weapon_name": "Spada Lunga",
                    "hit_bonus": 15,
                    "damage_formula": "1d8+3",
                    "damage_type": "Tagliente",
                    "smite_slot": 1,
                },
                pal,
                self.gs,
            )
        # Immune to non-magical slashing (0) + Improved Divine Smite (1d8=5) + Divine Smite (2d8=10) = 15 radiant
        self.assertEqual(gargoyle.hp, 45)
        self.assertEqual(pal.full_sheet["spell_slots"]["1"]["current"], 0)
        self.assertEqual((getattr(gargoyle, "death_saves", None) or {}).get("failures", 0), 0)

        # Next swing with 0 slots left must NOT apply Divine Smite (still Improved Divine Smite 5)
        pal.has_acted_this_turn = False
        pal.attacks_made_this_turn = 0
        with patch("random.randint", return_value=5):
            handle_attack_request(
                {
                    "target_name": "Golem",
                    "weapon_name": "Spada Lunga",
                    "hit_bonus": 15,
                    "damage_formula": "1d8+3",
                    "damage_type": "Tagliente",
                    "smite_slot": 1,
                },
                pal,
                self.gs,
            )
        self.assertEqual(gargoyle.hp, 40)

        # Same-hit slashing + Improved Divine Smite crossing 0 HP must NOT add post-0HP death save failures
        pc_victim = _make_player("Bardo", hp=6, max_hp=40, ac=10, pos=(0, 1), is_party=False)
        self.gs.players = [pal, pc_victim]
        pal.has_acted_this_turn = False
        pal.attacks_made_this_turn = 0
        with patch("random.randint", return_value=6):
            handle_attack_request(
                {
                    "target_name": "Bardo",
                    "weapon_name": "Spada Lunga",
                    "hit_bonus": 15,
                    "damage_formula": "1d8+3",
                    "damage_type": "Tagliente",
                },
                pal,
                self.gs,
            )
        self.assertEqual(pc_victim.hp, 0)
        self.assertEqual((getattr(pc_victim, "death_saves", None) or {}).get("failures", 0), 0)

        # Monk Stunning Strike with 0 Ki points must NOT stun target
        monk = _make_player(
            "Lee",
            pos=(0, 0),
            sheet={"char_class": "Monaco", "level": 5, "attributes": {"DES": 18, "SAG": 16}, "ki_current": 0},
        )
        orc = _make_player("Orco", hp=40, max_hp=40, ac=10, pos=(1, 0), is_party=False)
        self.gs.players = [monk, orc]
        with patch("random.randint", return_value=5):
            handle_attack_request(
                {
                    "target_name": "Orco",
                    "weapon_name": "Colpo Senz'Armi",
                    "hit_bonus": 15,
                    "damage_formula": "1d6+4",
                    "damage_type": "Contundente",
                    "use_stunning_strike": True,
                },
                monk,
                self.gs,
            )
        self.assertNotIn("Stordito", orc.conditions)

    def test_falling_and_periodic_damage_route_through_apply_damage(self):
        barb = _make_player(
            "Grog",
            hp=30,
            max_hp=30,
            sheet={"damage_resistances": ["Contundente", "Fuoco"]},
        )
        barb.temp_hp = 5
        self.gs.players = [barb]
        with patch("random.randint", return_value=5):
            resolve_falling(barb, 20, self.gs)  # 2d6 = 10 -> resisted to 5 -> temp_hp absorbs all 5
        self.assertEqual(barb.temp_hp, 0)
        self.assertEqual(barb.hp, 30)

        # Periodic fire damage should respect Fire Resistance via apply_damage
        barb.active_effects = [
            {"id": "burn", "name": "Fuoco Persistente", "duration_rounds": 2, "periodic_damage": "10", "periodic_damage_type": "Fuoco", "decrement_timing": "start_of_turn"}
        ]
        other = _make_player("Other")
        self.gs.players = [other, barb]
        self.gs.turn_index = 0
        self.gs.next_turn()  # switches to barb -> start-of-turn periodic damage 10 Fuoco resisted to 5
        self.assertEqual(barb.hp, 25)

    def test_wild_shape_long_rest_order_and_combat_heal_sync(self):
        c = Character(name="Radagast", char_class="Druido", level=4)
        c.hp_max = 28
        c.hp_current = 28
        c.enter_wild_shape("Orso Bruno", beast_hp=34, beast_ac=11, beast_speed=40)
        c.hp_current = 5
        c.long_rest()
        self.assertFalse(c.wild_shape.get("active", False))
        self.assertEqual(c.hp_max, 28)
        self.assertEqual(c.hp_current, 28)

        druid = _make_player(
            "Luna",
            hp=10,
            max_hp=34,
            sheet={
                "char_class": "Druido",
                "subclass": "Circolo della Luna",
                "level": 4,
                "hp_max": 28,
                "hp_current": 10,
                "spell_slots": {"1": {"max": 4, "current": 2}},
            },
        )
        druid.wild_shape = {"active": True, "beast_name": "Orso", "beast_hp": 10, "beast_hp_max": 34}
        self.gs.players = [druid]
        with patch("common.dice.random.randint", return_value=6):
            handle_class_feature_request({"feature": "combat_wild_shape_heal", "slot_level": 1}, druid, self.gs)
        self.assertEqual(druid.hp, 16)
        self.assertEqual(druid.wild_shape["beast_hp"], 16)
        self.assertEqual(druid.full_sheet["hp_current"], 16)

    def test_rage_flag_cleared_on_unconscious_and_lethal_reaction_rescues(self):
        barb = _make_player("Conan", hp=10, max_hp=30, sheet={"char_class": "Barbaro", "level": 3, "class_resources": {"rage_current": 2}})
        self.gs.players = [barb]
        handle_class_feature_request({"feature": "rage"}, barb, self.gs)
        self.assertTrue(barb.is_raging)
        self.assertIn("Ira", barb.conditions)
        apply_damage(barb, 40, "Psichico", self.gs)
        self.assertEqual(barb.hp, 0)
        self.assertFalse(barb.is_raging)
        self.assertNotIn("Ira", barb.conditions)

        # Lethal hit rescue with SHIELD_SPELL when +5 AC makes hit miss (and doesn't over-heal past old_hp=5)
        wiz = _make_player(
            "Elminster",
            hp=5,
            max_hp=20,
            ac=12,
            pos=(0, 0),
            sheet={"char_class": "Mago", "level": 3, "spell_slots": {"1": {"max": 4, "current": 2}}},
        )
        goblin = _make_player("Goblin", pos=(1, 0), is_party=False)
        self.gs.players = [wiz, goblin]
        with patch("random.randint", side_effect=[14, 14, 7]):  # d20 r1=14, r2=14 (hits 12, misses 17 w/ Shield), dmg=7 -> 0 HP
            handle_attack_request(
                {"target_name": "Elminster", "weapon_name": "Scimitarra", "hit_bonus": 0, "damage_formula": "1d8", "damage_type": "Tagliente"},
                goblin,
                self.gs,
            )
        self.assertEqual(wiz.hp, 0)
        self.assertIn("Incosciente", wiz.conditions)
        handle_reaction_response({"reaction_type": "SHIELD_SPELL", "accepted": True, "details": {}}, wiz, self.gs)
        self.assertEqual(wiz.hp, 5)
        self.assertNotIn("Incosciente", wiz.conditions)
        self.assertIn("Scudo", wiz.conditions)
        self.assertEqual(wiz.full_sheet["spell_slots"]["1"]["current"], 1)

    def test_absorb_elements_upcast_temp_expiry_and_no_double_roll(self):
        tiefling_eldritch = _make_player(
            "Zariel",
            hp=10,
            max_hp=30,
            ac=10,
            pos=(0, 0),
            sheet={
                "race": "Tiefling",
                "char_class": "Mago",
                "level": 5,
                "damage_resistances": ["Fuoco"],
                "spell_slots": {"2": {"max": 2, "current": 2}},
            },
        )
        tiefling_eldritch.damage_resistances = ["Fuoco"]
        tiefling_eldritch.initiative = 20
        gob = _make_player("Pyro", hp=50, max_hp=50, ac=10, pos=(1, 0), is_party=False)
        gob.initiative = 10
        tiefling_eldritch._last_hit_for_reaction = {"attacker": "Pyro", "dmg_to_hp": 10, "damage_type": "Fulmine", "old_hp": 20}
        self.gs.players = [tiefling_eldritch, gob]

        handle_reaction_response(
            {"reaction_type": "ABSORB_ELEMENTS", "accepted": True, "details": {"damage_type": "Fulmine", "slot_level": 2}},
            tiefling_eldritch,
            self.gs,
        )
        self.assertEqual(tiefling_eldritch.full_sheet["spell_slots"]["2"]["current"], 1)
        self.assertEqual(tiefling_eldritch.hp, 15)  # +5 retroactive half
        self.assertEqual(tiefling_eldritch.absorb_elements_dice, 2)
        self.assertIn("Fulmine", tiefling_eldritch.damage_resistances)

        # Next melee hit should roll bonus 2d6 ONCE (not 2d6 + 1d6 duplicate!)
        with patch("random.randint", side_effect=[15, 15, 4, 3, 2]):  # hit=(15,15), weapon 1d8=4, ae 2d6=3+2=5 -> total 9
            handle_attack_request(
                {"target_name": "Pyro", "weapon_name": "Daga", "hit_bonus": 5, "damage_formula": "1d8", "damage_type": "Perforante"},
                tiefling_eldritch,
                self.gs,
            )
        self.assertEqual(gob.hp, 41)
        self.assertEqual(tiefling_eldritch.absorb_elements_dice, 0)

        # Start of Zariel's next turn must remove temporary Fulmine resistance but keep permanent Tiefling Fuoco
        self.gs.turn_index = 1  # gob's turn -> next_turn wraps to Zariel (init 20)
        self.gs.next_turn()
        self.assertNotIn("Fulmine", tiefling_eldritch.damage_resistances)
        self.assertIn("Fuoco", tiefling_eldritch.damage_resistances)

    def test_counterspell_joat_abjurer_slot_guard_and_aoe_abort(self):
        abjurer = _make_player(
            "Abj",
            sheet={
                "char_class": "Mago",
                "subclass": "Scuola di Abiurazione",
                "level": 10,
                "attributes": {"INT": 18},  # +4 INT, +4 PB = +8
                "spell_slots": {"3": {"max": 2, "current": 1}},
            },
        )
        bard = _make_player(
            "Bardo",
            sheet={
                "char_class": "Bardo",
                "level": 5,
                "attributes": {"CAR": 16},  # +3 CAR, +1 JoAT (3//2) = +4
                "spell_slots": {"3": {"max": 2, "current": 0}},
            },
        )
        evoker = _make_player("Evoc", sheet={"char_class": "Mago", "level": 7, "spell_slots": {"4": {"max": 1, "current": 1}}})
        evoker.conn = MagicMock()
        self.gs.players = [abjurer, bard, evoker]

        # Bard with 0 level-3 slots must be rejected cleanly
        handle_reaction_response(
            {"reaction_type": "COUNTERSPELL", "accepted": True, "target_name": "Evoc", "details": {"spell_level": 4, "slot_level": 3}},
            bard,
            self.gs,
        )
        self.assertFalse(bard.has_reacted_this_turn)

        # Abjurer Lv 10 counterspells Lv 5 spell using Lv 3 slot: d20=7 + 8 = 15 >= 15 -> countered!
        with patch("random.randint", return_value=7):
            handle_reaction_response(
                {"reaction_type": "COUNTERSPELL", "accepted": True, "target_name": "Evoc", "details": {"spell_level": 5, "slot_level": 3, "cast_id": "cast_xyz"}},
                abjurer,
                self.gs,
            )
        self.assertIn("cast_xyz", self.gs._cancelled_cast_ids)
        self.assertEqual(abjurer.full_sheet["spell_slots"]["3"]["current"], 0)

        # Direct special spell cast aborted when Counterspell hook marks cast_id canceled
        with patch("server.rules.reaction_magic.maybe_prompt_counterspell_reactions") as m_cs_sp:
            def _cancel_sp(*_a, **kw):
                self.gs._cancelled_cast_ids.add(kw["cast_id"])
            m_cs_sp.side_effect = _cancel_sp
            handle_cast_special_spell_request(
                {"spell_name": "Tempesta di Ghiaccio", "level": 4},
                evoker,
                self.gs,
            )
        # AoE canceled by Counterspell reaction hook must not damage target
        victim = _make_player("Vict", hp=40, max_hp=40, pos=(3, 0))
        self.gs.players = [abjurer, evoker, victim]
        with patch("server.rules.reaction_magic.maybe_prompt_counterspell_reactions") as m_cs:
            def _cancel(*_args, **kwargs):
                self.gs._cancelled_cast_ids.add(kwargs["cast_id"])
            m_cs.side_effect = _cancel
            handle_resolve_aoe_request(
                {"shape": "Sfera", "origin": [3, 0], "size": 2, "save_stat": "DES", "dc": 15, "damage_formula": "8d6", "damage_type": "Fuoco", "spell_name": "Palla di Fuoco", "spell_level": 3},
                evoker,
                self.gs,
            )
        self.assertEqual(victim.hp, 40)

    def test_font_of_magic_monk_unarmed_shove_extra_attack_and_elemental_adept(self):
        # Font of Magic requires Lv 3 for Metamagic & consumes Bonus Action for slot conversion
        sorc2 = _make_player(
            "Sorc2",
            sheet={"char_class": "Stregone", "level": 2, "sorcery_points_current": 2, "sorcery_points_max": 2, "spell_slots": {"1": {"max": 3, "current": 2}}},
        )
        sorc2.conn = MagicMock()
        self.gs.players = [sorc2]
        handle_class_feature_request({"feature": "font_of_magic", "mode": "set_metamagic", "metamagic": "Incantesimo Rapido", "cost": 2}, sorc2, self.gs)
        self.assertEqual(sorc2.full_sheet["sorcery_points_current"], 2)  # rejected Lv < 3
        handle_class_feature_request({"feature": "font_of_magic", "mode": "to_slot", "slot_level": 1}, sorc2, self.gs)
        self.assertTrue(sorc2.bonus_action_used_this_turn)
        self.assertEqual(sorc2.full_sheet["spell_slots"]["1"]["current"], 3)
        self.assertEqual(sorc2.full_sheet["sorcery_points_current"], 0)

        # Monk unarmed fallback uses max(FOR, DES)
        monk = _make_player("Monk", pos=(0, 0), sheet={"char_class": "Monaco", "level": 2, "attributes": {"FOR": 8, "DES": 16}})
        foe = _make_player("Foe", hp=30, max_hp=30, ac=10, pos=(1, 0), is_party=False)
        self.gs.players = [monk, foe]
        with patch("random.randint", side_effect=[10, 10, 4]):  # hit=(10,10); dmg 1d4(4) + 3 DES = 7
            handle_attack_request({"target_name": "Foe", "weapon_name": "Colpo Senz'Armi", "hit_bonus": 0, "damage_formula": "", "damage_type": "Contundente"}, monk, self.gs)
        self.assertEqual(foe.hp, 23)

        # Fighter Lv 5 Attack + Grapple uses Extra Attack slots, Shield Master allows BA Shove
        f5 = _make_player(
            "F5",
            pos=(0, 0),
            sheet={"char_class": "Guerriero", "level": 5, "attributes": {"FOR": 18}, "features": ["Maestro di Scudi"]},
        )
        foe2 = _make_player("Foe2", hp=40, max_hp=40, ac=10, pos=(1, 0), is_party=False)
        self.gs.players = [f5, foe2]
        with patch("random.randint", return_value=15):
            handle_attack_request({"target_name": "Foe2", "weapon_name": "Spada", "hit_bonus": 5, "damage_formula": "1d8", "damage_type": "Tagliente"}, f5, self.gs)
        self.assertFalse(f5.has_acted_this_turn)
        with patch("random.randint", side_effect=[18, 10, 2, 2]):
            handle_grapple_request({"target_name": "Foe2"}, f5, self.gs)
        self.assertTrue(f5.has_acted_this_turn)
        self.assertIn("Afferrato", foe2.conditions)
        # Shield Master BA Shove still allowed after Attack Action
        with patch("random.randint", side_effect=[18, 10, 2, 2]):
            handle_shove_request({"target_name": "Foe2", "option": "prone"}, f5, self.gs)
        self.assertTrue(f5.bonus_action_used_this_turn)
        self.assertIn("Prono", foe2.conditions)

        # Elemental Adept: matches specific element (Fuoco), does NOT match Freddo
        pyro = _make_player("Pyro", pos=(0, 0), sheet={"features": ["Adepto Elementale (Fuoco)"]})
        self.assertTrue(entity_has_elemental_adept(pyro, "Fuoco"))
        self.assertFalse(entity_has_elemental_adept(pyro, "Freddo"))
        fire_res = _make_player("Demon", hp=40, max_hp=40, sheet={"damage_resistances": ["Fuoco", "Freddo"]})
        self.gs.players = [pyro, fire_res]
        with patch("server.rules.combat.roll_dice", return_value={"total": 12}):
            _process_save_result("Demon", "DES", 5, False, False, 15, "2d6", True, "Pyro", self.gs, damage_type="Fuoco")
        self.assertEqual(fire_res.hp, 28)  # Fuoco resistance ignored!
        with patch("server.rules.combat.roll_dice", return_value={"total": 12}):
            _process_save_result("Demon", "COS", 5, False, False, 15, "2d6", True, "Pyro", self.gs, damage_type="Freddo")
        self.assertEqual(fire_res.hp, 22)  # Freddo resistance still applies!

    def test_ranged_ammo_monster_fixes_ac_recalc_and_death_save(self):
        # Ranged ammo decrement vs already_decremented flag
        archer = _make_player(
            "Legolas",
            pos=(0, 0),
            sheet={"inventory_grid": [{"name": "Frecce", "qty": 2}]},
        )
        orc = _make_player("Orc", hp=40, max_hp=40, ac=10, pos=(3, 0), is_party=False)
        self.gs.players = [archer, orc]
        with patch("random.randint", return_value=15):
            handle_attack_request({"target_name": "Orc", "weapon_name": "Arco Lungo", "hit_bonus": 5, "damage_formula": "1d8", "damage_type": "Perforante", "is_ranged": True}, archer, self.gs)
        self.assertEqual(archer.full_sheet["inventory_grid"][0]["qty"], 1)
        with patch("random.randint", return_value=15):
            handle_attack_request({"target_name": "Orc", "weapon_name": "Arco Lungo", "hit_bonus": 5, "damage_formula": "1d8", "damage_type": "Perforante", "is_ranged": True, "ammo_already_decremented": True}, archer, self.gs)
        self.assertEqual(archer.full_sheet["inventory_grid"][0]["qty"], 1)

        # Lair Init 20 wait when faster creature goes first
        boss = _make_player("Drago", is_party=False)
        boss.initiative = 25
        boss.has_lair_actions = True
        boss.lair_actions = ["Scossa"]
        hero = _make_player("Hero")
        hero.initiative = 15
        self.gs.players = [boss, hero]
        self.assertFalse(trigger_lair_actions_if_crossed(self.gs, prev_init=None, next_init=25, round_advanced=True))
        self.assertTrue(trigger_lair_actions_if_crossed(self.gs, prev_init=25, next_init=15, round_advanced=False))

        # Multiattack elemental & Beholder Ray 9/10 instant death at 0 HP
        elemental_boss = _make_player(
            "ElemLord",
            sheet={
                "actions": [
                    {"name": "Multiattacco", "desc": "Multiattacco: 1 Fiammata e 1 Artiglio Gelido"},
                    {"name": "Fiammata", "attack_bonus": 8, "damage_dice": "1d6+2", "desc": "Colpito: (1d6+2) danni da fuoco."},
                    {"name": "Artiglio Gelido", "attack_bonus": 8, "damage_dice": "1d6+2", "desc": "Colpito: (1d6+2) danni da freddo."},
                ],
            },
        )
        t_vic = _make_player("Vict", hp=40, max_hp=40, ac=10, sheet={"damage_resistances": ["Fuoco"]})
        with patch("server.dm_monster_engine.roll_dice", return_value={"total": 10, "rolls": [10], "raw_total": 10}):
            ma_res = execute_monster_multiattack(elemental_boss, self.gs, target=t_vic)
        self.assertEqual({r["damage_type"] for r in ma_res["rolls"]}, {"Fuoco", "Freddo"})
        self.assertEqual(t_vic.hp, 25)  # 5 fire (halved) + 10 cold = 15 dmg

        beh = _make_player("Xanathar", is_party=False)
        low_pc = _make_player("Squishy", hp=5, max_hp=30)
        with patch("server.dm_monster_engine.roll_dice", side_effect=[{"total": 35, "rolls": [35], "raw_total": 35}, {"total": 4, "rolls": [4], "raw_total": 4}]):
            ray_res = roll_beholder_eye_rays(beh, targets=[low_pc], game_state=self.gs, count=1, forced_indices=[9])
        self.assertEqual(low_pc.hp, 0)
        self.assertIn("Morto", low_pc.conditions)
        self.assertIn("POLVERIZZATO", ray_res["summary"])

        # Server AC recalculates downward when armor is unequipped
        fighter = _make_player("Tank", ac=18, sheet={"attributes": {"DES": 14}, "inventory_grid": [{"name": "Armatura a Piastre", "type": "Armatura", "container": "equipped", "ac_base": 18}]})
        self.gs.players = [fighter]
        handle_update_full_sheet_request({"character": {"attributes": {"DES": 14}, "ac": 18, "inventory_grid": []}}, fighter, self.gs)
        self.assertEqual(fighter.ac, 12)  # 10 + 2 DEX after unequipping Plate!

        # Server DEATH_SAVE_REQUEST with Paladin Aura + Diamond Soul + Item bonus_saves
        pal_aura = _make_player("PalAura", pos=(0, 0), sheet={"char_class": "Paladino", "level": 6, "attributes": {"CAR": 16}})
        dying_monk = _make_player(
            "DyingMonk",
            hp=0,
            max_hp=60,
            pos=(1, 0),
            sheet={"char_class": "Monaco", "level": 14, "inventory_grid": [{"name": "Anello di Protezione", "type": "Anello", "equipped": True, "attuned": True, "ac_bonus": 1, "save_bonus": 1}]},
        )
        dying_monk.death_saves = {"successes": 0, "failures": 0}
        self.gs.players = [pal_aura, dying_monk]
        bonus_val, _ = compute_death_save_flat_bonus(dying_monk)
        self.assertGreaterEqual(bonus_val, 6)  # +5 PB (Lv14 Diamond Soul) + 1 Ring
        # Raw d20=2 + 5 (Diamond Soul) + 1 (Ring) + 3 (Aura) = 11 >= 10 -> Success!
        self.assertIn("DEATH_SAVE_REQUEST", command_handlers)
        command_handlers["DEATH_SAVE_REQUEST"](make_death_save_request(manual_roll=2, actor_name="DyingMonk")["data"], dying_monk, self.gs)
        self.assertEqual(dying_monk.death_saves["successes"], 1)

    def test_task033_shield_of_faith_3d_aoe_square_los_ammo_primal_and_attunement(self):
        from common.spell_effects_engine import cast_iconic_spell, get_spell_ac_bonus
        from server.rules.combat import drop_concentration, recover_expended_ammunition
        from server.rules.map_interaction import handle_create_aoe_request
        from server.rules.character import handle_update_full_sheet_request
        from client.character_sheet_ui import CharacterSheetUI
        from client.character_manager import Character
        import tkinter as tk

        # 1. Shield of Faith: single concentration cleanup + dynamic +2 CA (not permanent mutation)
        cleric = _make_player("Chierico", pos=(0, 0), sheet={"char_class": "Chierico", "level": 3, "attributes": {"SAG": 16}})
        cleric.concentrating_on = "Benedizione"
        self.gs.active_aoes = [{"id": "old_aoe", "caster": "Chierico", "concentration": True, "origin": [0, 0], "type": "sfera", "size": 1}]
        ally = _make_player("Paladino", hp=40, max_hp=40, ac=16, pos=(1, 0), sheet={"ac": 16})
        bandit = _make_player("Bandito", hp=30, max_hp=30, ac=12, pos=(2, 0), is_party=False)
        self.gs.players = [cleric, ally, bandit]

        cast_iconic_spell(cleric, ally, "Scudo della Fede", 1, self.gs)
        self.assertEqual(self.gs.active_aoes, [])
        self.assertEqual(cleric.concentrating_on, "Scudo della Fede")
        self.assertIn("Concentrazione", cleric.conditions)
        self.assertEqual(ally.ac, 16)
        self.assertEqual(get_spell_ac_bonus(ally), 2)

        with patch("server.rules.combat.random.randint", return_value=17):
            handle_attack_request({"target_name": "Paladino", "weapon_name": "Spada", "hit_bonus": 0, "damage_formula": "1d6"}, bandit, self.gs)
        self.assertEqual(ally.hp, 40)  # 17 < 16 + 2 -> MISS!

        drop_concentration(cleric, self.gs)
        self.assertIsNone(ally.get_effect("shield_of_faith"))
        self.assertEqual(get_spell_ac_bonus(ally), 0)
        self.assertNotIn("Concentrazione", cleric.conditions)

        bandit.has_acted_this_turn = False
        with patch("server.rules.combat.random.randint", return_value=17):
            handle_attack_request({"target_name": "Paladino", "weapon_name": "Spada", "hit_bonus": 0, "damage_formula": "1d6"}, bandit, self.gs)
        self.assertLess(ally.hp, 40)  # 17 >= 16 -> HIT!

        # 2. 3D AoE elevation bounds
        ground_hero = _make_player("Pedone", hp=40, max_hp=40, pos=(0, 0))
        ground_hero.elevation = 10
        flying_dragon = _make_player("DragoVolante", hp=80, max_hp=80, pos=(0, 0), is_party=False)
        flying_dragon.elevation = 35
        self.gs.players = [cleric, ground_hero, flying_dragon]
        self.gs.current_map = {"grid_type": "hex", "walls": [], "doors": []}
        with patch("server.rules.map_interaction.broadcast"), patch("server.rules.combat.broadcast"), \
             patch("common.dice.roll_dice", return_value={"total": 5, "rolls": [5], "raw_total": 5}):
            handle_create_aoe_request({
                "aoe_data": {"origin": [0, 0], "type": "sfera", "size": 4, "elevation": 0, "dmg": "12", "stat": "DES", "dc": 30, "req_save": True}
            }, cleric, self.gs)
        self.assertLess(ground_hero.hp, 40)
        self.assertEqual(flying_dragon.hp, 80)

        # 3. Square-grid LoS wall parity in handle_attack_request
        sq_atk = _make_player("Tiratore", hp=30, max_hp=30, pos=(0, 0))
        sq_tgt = _make_player("Orco", hp=30, max_hp=30, ac=10, pos=(2, 2), is_party=False)
        self.gs.players = [sq_atk, sq_tgt]
        self.gs.current_map = {"grid_type": "square", "walls": [[1, 1]], "doors": []}
        with patch("server.rules.combat.random.randint", return_value=15):
            handle_attack_request({"target_name": "Orco", "weapon_name": "Arco", "hit_bonus": 5, "damage_formula": "1d8"}, sq_atk, self.gs)
        self.assertEqual(sq_tgt.hp, 30)  # Blocked by diagonal square wall at (1,1)!

        # 4. Client-decremented ammo sync prevents inflation on recovery
        archer = _make_player("Arc", pos=(0, 0), sheet={"inventory_grid": [{"name": "Frecce", "qty": 2}]})
        self.gs.players = [archer, sq_tgt]
        self.gs.current_map = {"grid_type": "square", "walls": [], "doors": []}
        with patch("server.rules.combat.random.randint", return_value=15):
            handle_attack_request({"target_name": "Orco", "weapon_name": "Arco", "hit_bonus": 5, "damage_formula": "1d4", "is_ranged": True, "ammo_already_decremented": True, "ammo_remaining": 1, "ammo_item_name": "Frecce"}, archer, self.gs)
        archer.has_acted_this_turn = False
        with patch("server.rules.combat.random.randint", return_value=15):
            handle_attack_request({"target_name": "Orco", "weapon_name": "Arco", "hit_bonus": 5, "damage_formula": "1d4", "is_ranged": True, "ammo_already_decremented": True, "ammo_remaining": 0, "ammo_item_name": "Frecce"}, archer, self.gs)
        self.assertEqual(archer.full_sheet["inventory_grid"][0]["qty"], 0)
        recover_expended_ammunition(archer, self.gs)
        self.assertEqual(archer.full_sheet["inventory_grid"][0]["qty"], 1)  # Never inflates above 2

        # 5. Barbarian Level 20 Primal Champion (+4 FOR / +4 COS up to 24) accepted by server
        barb = _make_player(
            "Grog",
            hp=200,
            max_hp=200,
            sheet={"char_class": "Barbaro", "level": 19, "hp_current": 200, "hp_max": 200, "attributes": {"FOR": 20, "DES": 14, "COS": 18, "INT": 8, "SAG": 10, "CAR": 10}},
        )
        self.gs.players = [barb]
        with patch("random.randint", return_value=12):
            handle_update_full_sheet_request({
                "character": {
                    "char_class": "Barbaro",
                    "level": 20,
                    "hp_max": 260,
                    "hp_current": 260,
                    "attributes": {"FOR": 24, "DES": 14, "COS": 22, "INT": 8, "SAG": 10, "CAR": 10},
                }
            }, barb, self.gs)
        self.assertEqual(barb.full_sheet["attributes"]["FOR"], 24)
        self.assertEqual(barb.full_sheet["attributes"]["COS"], 22)

        # 6. Compendium item import sets requires_attunement explicitly
        root = tk.Tk()
        root.withdraw()
        try:
            sent_items = []
            c_obj = Character("Tester")
            sheet_ui = CharacterSheetUI(
                root,
                character=c_obj,
                manager=None,
                is_connected=True,
                request_item_callback=lambda entry, idx: sent_items.append(entry),
            )
            sheet_ui.withdraw()
            with patch("client.character_sheet_ui.messagebox.showinfo"):
                sheet_ui.import_from_compendium_to_slot({"name": "Elmo dell'Acquaticità", "weight": 2.0, "requires_attunement": False}, "Oggetti Meravigliosi", 0)
                sheet_ui.import_from_compendium_to_slot({"name": "Anello di Protezione", "weight": 0.1, "requires_attunement": "requires attunement"}, "Anelli", 1)
            self.assertIs(sent_items[0]["requires_attunement"], False)
            self.assertIs(sent_items[1]["requires_attunement"], True)
            sheet_ui.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
