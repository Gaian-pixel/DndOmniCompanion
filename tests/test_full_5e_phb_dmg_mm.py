import os
import queue
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common.game_state import GameState, Player
from common.feats_and_classes import (
    apply_dark_ones_blessing,
    apply_savage_attacker_roll,
    attune_item_short_rest,
    consume_arcane_ward_hp,
    evaluate_armor_sleep,
    get_armor_nonproficiency_penalties,
    get_destroy_undead_cr_threshold,
    get_heavy_armor_master_reduction,
)
from common.encounter_calc import calculate_encounter_difficulty
from common.item_modifiers import STAT_MAP, get_effective_attribute_from_dict
from server.commands import command_handlers
from server.dm_generators import LootGenerator, RandomDungeonGenerator, SettlementGenerator
from server.dm_monster_engine import (
    apply_petrification_stage,
    cast_monster_spell,
    check_and_trigger_mythic_awakening,
    execute_lair_action,
    filter_swarm_condition,
    get_swarm_damage_divisor,
    handle_resolve_legendary_resistance_request,
    has_spider_climb,
    has_water_breathing,
    is_incapacitated_entity,
    is_incorporeal_entity,
    is_shapechanger_entity,
    parse_monster_spellcasting,
    register_regional_effects,
    sync_monster_spellcasting_to_sheet,
    trigger_lair_actions_if_crossed,
)
from server.dm_optional_tools import (
    adjust_renown_or_piety,
    apply_initiative_variant,
    calculate_sentient_ego,
    compute_speed_factor_modifier,
    cure_lingering_injury,
    evaluate_facing_attack,
    evaluate_morale_checks,
    get_hero_points_max,
    get_lingering_injury_penalties,
    handle_fear_or_horror_save,
    handle_harvest_poison,
    handle_healing_surge,
    handle_siege_action,
    handle_spend_hero_point,
    level_up_sidekick,
    register_complex_trap,
    resolve_bastion_turn,
    resolve_sentient_conflict,
    roll_artifact_properties,
    trigger_complex_traps_at_round_start,
)
from server.rules.character import trigger_group_long_rest
from server.rules.class_abilities import (
    handle_dmg_maneuver_request,
    handle_submerged_breath_request,
)
from server.rules.combat import (
    _process_save_result,
    advance_combat_turn,
    apply_damage,
    handle_apply_effect_request,
    handle_attack_request,
    handle_grapple_request,
    handle_shove_request,
    handle_spend_legendary_action_request,
)
from server.rules.downtime import resolve_downtime_activity
from server.rules.movement import handle_move_request
from server.rules.reaction_magic import _has_no_reactions_effect


def _make_pc(name="Eroe", cls="Guerriero", level=5, hp=40, ac=16, pos=(2, 2)):
    p = Player(name)
    p.is_party_member = True
    p.hp = hp
    p.max_hp = hp
    p.ac = ac
    p.speed = 30
    p.position = list(pos)
    p.full_sheet = {
        "name": name,
        "char_class": cls,
        "level": level,
        "hp_current": hp,
        "hp_max": hp,
        "ac": ac,
        "attributes": {"FOR": 16, "DES": 14, "COS": 14, "INT": 12, "SAG": 12, "CAR": 12},
        "proficiency_bonus": 2 + (level - 1) // 4,
        "features": "",
        "inventory_grid": [],
        "currency": {"gp": 100, "sp": 0, "cp": 0, "ep": 0, "pp": 0},
        "conditions": [],
    }
    return p


def _make_monster(name="Mostro", hp=60, ac=14, pos=(2, 3), features=None):
    m = Player(name)
    m.is_monster = True
    m.hp = hp
    m.max_hp = hp
    m.ac = ac
    m.speed = 30
    m.position = list(pos)
    m.full_sheet = {
        "name": name,
        "char_class": "Mostro/NPC",
        "level": 1,
        "hp_current": hp,
        "hp_max": hp,
        "ac": ac,
        "attributes": {"FOR": 16, "DES": 12, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10},
        "features": list(features or []),
        "actions": [],
        "conditions": [],
    }
    return m


class TestFull5ePhbDmgMm(unittest.TestCase):
    def setUp(self):
        self.q = queue.Queue()
        self.gs = GameState(self.q)
        self.gs.current_map = {"walls": [], "doors": [], "difficult_terrain": [], "grid_type": "hex"}

    # ------------------------------------------------------------------
    # BLOCK 1 & 2: PHB CORE, CLASSES, FEATS, ATTUNEMENT, ARMOR, DOWNTIME
    # ------------------------------------------------------------------
    def test_armor_nonproficiency_penalties_blocks_cast_and_flags_str_dex(self):
        wizard = _make_pc("Gale", "Mago", level=3, hp=20, ac=12)
        wizard.full_sheet["inventory_grid"] = [
            {"name": "Armatura a Piastre (Plate)", "type": "Armatura", "category": "Pesante", "container": "equipped", "ac_base": 18}
        ]
        pen = get_armor_nonproficiency_penalties(wizard)
        self.assertTrue(pen["non_proficient"])
        self.assertTrue(pen["cannot_cast_spells"])
        self.assertTrue(pen["disadvantage_str_dex"])

    def test_heavy_armor_master_reduces_before_resistance_and_arcane_ward(self):
        pal = _make_pc("Uther", "Paladino", level=5, hp=45, ac=18)
        pal.full_sheet["features"] = "Maestria nelle Armature Pesanti, Interdizione Arcana"
        pal.full_sheet["char_class"] = "Paladino"
        pal.full_sheet["classes"] = {"Paladino": 2, "Mago": 3}
        pal.full_sheet["subclass"] = "Abiurazione"
        pal.full_sheet["attributes"]["INT"] = 16
        pal.full_sheet["inventory_grid"] = [
            {"name": "Cotta di Maglia", "type": "Armatura", "category": "Pesante", "container": "equipped", "ac_base": 16}
        ]
        pal.damage_resistances = ["Tagliente"]
        pal.temp_hp = 4
        # HAM reduces 10 -> 7; Resistance halves 7 -> 3; Arcane Ward (2*3 + 3 = 9) absorbs 3 before Temp HP!
        final_dmg, note, temp_abs, dmg_hp = apply_damage(pal, 10, "Tagliente", self.gs, is_magical=False)
        self.assertIn("Armatura Pesante: -3", note)
        self.assertEqual(final_dmg, 0)
        self.assertEqual(temp_abs, 0)
        self.assertEqual(pal.hp, 45)
        self.assertEqual(pal.temp_hp, 4)

    def test_aura_of_warding_dark_ones_blessing_and_destroy_undead(self):
        ancients = _make_pc("Aelar", "Paladino", level=7, hp=60, pos=(2, 2))
        ancients.full_sheet["subclass"] = "Giuramento degli Antichi"
        ally = _make_pc("Lyra", "Ladro", level=5, hp=30, pos=(2, 3))
        self.gs.players = [ancients, ally]
        final_dmg, note, _, _ = apply_damage(ally, 20, "Fuoco", self.gs, is_spell=True)
        self.assertEqual(final_dmg, 10)
        self.assertIn("Aura di Custodia", note)

        fiend_lock = _make_pc("Wyll", "Warlock", level=4, hp=25, pos=(4, 4))
        fiend_lock.full_sheet["subclass"] = "Immondo"
        fiend_lock.full_sheet["attributes"]["CAR"] = 16  # +3
        dead_gob = _make_monster("Goblin", hp=0, pos=(4, 5))
        gain = apply_dark_ones_blessing(fiend_lock, dead_gob, self.gs)
        self.assertEqual(gain, 7)  # 4 level + 3 CHA
        self.assertEqual(get_destroy_undead_cr_threshold(17), 4.0)

    def test_short_rest_attunement_and_sleeping_in_armor_toggle(self):
        art = _make_pc("Tinker", "Artefice", level=6, hp=30)
        art.full_sheet["inventory_grid"] = [
            {"name": "Anello di Protezione", "requires_attunement": True, "attuned": False},
            {"name": "Anello di Protezione", "requires_attunement": True, "attuned": False},
            {"name": "Verga del Custode", "requires_attunement": True, "attuned_class": "Warlock", "attuned": False},
        ]
        ok1, _ = attune_item_short_rest(art, 0)
        self.assertTrue(ok1)
        ok_dup, msg_dup = attune_item_short_rest(art, 1)
        self.assertFalse(ok_dup)
        self.assertIn("due copie", msg_dup)
        ok_cls, _ = attune_item_short_rest(art, 2)
        self.assertFalse(ok_cls)

        # Sleeping in Heavy Armor with XGtE toggle OFF vs ON
        art.full_sheet["inventory_grid"].append(
            {"name": "Corazza di Piastre", "type": "Armatura", "category": "Pesante", "container": "equipped", "ac_base": 18}
        )
        art.sleeping_in_armor = True
        self.gs.automation_settings["opt_armor_sleep_xge"] = False
        self.assertFalse(evaluate_armor_sleep(art, self.gs)["penalized"])

        self.gs.automation_settings["opt_armor_sleep_xge"] = True
        res_on = evaluate_armor_sleep(art, self.gs)
        self.assertTrue(res_on["penalized"])
        self.assertEqual(res_on["hd_fraction"], 0.25)
        self.assertTrue(res_on["blocks_exhaustion_recovery"])

    def test_downtime_crafting_and_savage_attacker(self):
        pc = _make_pc("Artigiano", "Guerriero", level=3, hp=24)
        ok, msg = resolve_downtime_activity(
            pc,
            {"activity": "crafting", "item_name": "Pozione di Guarigione", "item_value_gp": 50, "days": 5, "lifestyle": "modest"},
            self.gs,
        )
        self.assertTrue(ok)
        self.assertIn("Pozione di Guarigione", msg)
        self.assertLess(pc.full_sheet["currency"]["gp"], 100)

        with patch("common.dice.roll_dice", side_effect=[{"total": 2}, {"total": 7}]):
            tot, detail = apply_savage_attacker_roll("1d8")
            self.assertEqual(tot, 7)
            self.assertIn("Attaccante Selvaggio", detail)

    # ------------------------------------------------------------------
    # BLOCK 3A & 3B: DMG ENCOUNTERS, LOOT, GENERATORS & OPTIONAL TOGGLES
    # ------------------------------------------------------------------
    def test_encounter_party_size_steps_and_generators_cr17(self):
        small_party = calculate_encounter_difficulty([5, 5], [450, 450])
        std_party = calculate_encounter_difficulty([5, 5, 5, 5], [450, 450])
        big_party = calculate_encounter_difficulty([5, 5, 5, 5, 5, 5], [450, 450])
        self.assertGreater(small_party["multiplier"], std_party["multiplier"])
        self.assertLess(big_party["multiplier"], std_party["multiplier"])

        hoard17 = LootGenerator.generate("GS 17+", "Tesoro della Tana")
        self.assertGreater(hoard17["total_value_gp"], 0)
        self.assertTrue(len(hoard17["gems"]) >= 1 or len(hoard17["art_objects"]) >= 1)

        dung = RandomDungeonGenerator.generate(rooms_count=4)
        self.assertEqual(len(dung["rooms"]), 4)
        sett = SettlementGenerator.generate()
        self.assertIn("government", sett)
        self.assertIn("tavern", sett)

    def test_slow_natural_healing_toggle(self):
        pc = _make_pc("ferito", hp=40)
        pc.hp = 12
        self.gs.players = [pc]
        self.gs.automation_settings["opt_slow_natural_healing"] = True
        trigger_group_long_rest(self.gs)
        self.assertEqual(pc.hp, 12)  # NOT auto-healed when Slow Natural Healing is ON

        self.gs.automation_settings["opt_slow_natural_healing"] = False
        trigger_group_long_rest(self.gs)
        self.assertEqual(pc.hp, 40)

    def test_side_initiative_and_speed_factor_variants(self):
        pc = _make_pc("Eroe", pos=(2, 2))
        gob = _make_monster("Goblin", pos=(3, 3))
        self.gs.players = [pc, gob]
        self.gs.automation_settings["opt_init_variant"] = "side"
        notes = apply_initiative_variant(self.gs, side_rolls=(16, 7))
        self.assertEqual(pc.initiative, 16)
        self.assertEqual(gob.initiative, 7)
        self.assertTrue(notes)

        self.gs.automation_settings["opt_init_variant"] = "speed_factor"
        pc.full_sheet["speed_factor_action"] = "heavy_weapon"
        self.assertEqual(compute_speed_factor_modifier(pc), -2)
        apply_initiative_variant(self.gs)
        self.gs.automation_settings["opt_init_variant"] = "standard"

    def test_facing_morale_hero_points_surges_honor_sanity_fear_climb(self):
        pc = _make_pc("Aiden", "Guerriero", level=6, hp=50, ac=18, pos=(2, 2))
        pc.hp = 20
        pc.facing = 0.0  # Facing East (+q)
        pc.full_sheet["inventory_grid"] = [{"name": "Scudo", "type": "Armatura", "category": "Scudo", "equipped": True, "ac_bonus": 2}]
        orc = _make_monster("Orco", hp=15, ac=13, pos=(1, 2))  # Directly West (behind Aiden!)
        orc.facing = 0.0
        self.gs.players = [pc, orc]

        # Facing helper geometric arc (rear -> ignore shield & grant advantage) + DM toggle gating in combat
        f_res = evaluate_facing_attack(orc, pc)
        self.assertEqual(f_res["arc"], "rear")
        self.assertTrue(f_res["grant_advantage"])
        self.assertTrue(f_res["ignore_shield"])
        pc.full_sheet["inventory_grid"][0]["container"] = "equipped"
        self.gs.automation_settings["opt_facing"] = False
        with patch("server.rules.combat.random.randint", return_value=14), \
             patch("server.rules.combat.roll_dice", return_value={"total": 5, "rolls": [5]}):
            # PC AC=18 + 2 shield or effective AC with shield=20 -> 14+3=17 misses when Facing OFF
            hp_before_off = pc.hp
            handle_attack_request({"target_name": "Aiden", "weapon_name": "Ascia", "hit_bonus": 3, "damage_formula": "1d8"}, orc, self.gs)
            self.assertEqual(pc.hp, hp_before_off)
        self.gs.automation_settings["opt_facing"] = True
        with patch("server.rules.combat.random.randint", side_effect=[15, 2]), \
             patch("server.rules.combat.roll_dice", return_value={"total": 5, "rolls": [5]}):
            # Shield (+2) bypassed & rear Advantage -> 15+3=18 hits base AC 18!
            handle_attack_request({"target_name": "Aiden", "weapon_name": "Ascia", "hit_bonus": 3, "damage_formula": "1d8"}, orc, self.gs)
            self.assertLess(pc.hp, hp_before_off)
        pc.hp = hp_before_off
        self.gs.automation_settings["opt_facing"] = False

        # Morale OFF vs ON
        self.assertEqual(evaluate_morale_checks(self.gs, "casualties", forced_save_roll=2), [])
        self.gs.automation_settings["opt_morale"] = True
        orc.hp = 5  # <= 50% HP
        m_notes = evaluate_morale_checks(self.gs, "casualties", forced_save_roll=3)
        self.assertTrue(m_notes)
        self.assertIn("Spaventato (Morale Rotto)", orc.conditions)

        # Hero Points OFF vs ON
        self.assertEqual(get_hero_points_max(pc), 8)  # 5 + 6//2
        ok_hp_off, _ = handle_spend_hero_point(pc, "roll_bonus", self.gs)
        self.assertFalse(ok_hp_off)
        self.gs.automation_settings["opt_hero_points"] = True
        ok_hp_on, _ = handle_spend_hero_point(pc, "roll_bonus", self.gs)
        self.assertTrue(ok_hp_on)
        self.assertEqual(pc.hero_points, 7)

        # Healing Surges OFF vs ON
        ok_hs_off, _ = handle_healing_surge(pc, 1, self.gs)
        self.assertFalse(ok_hs_off)
        self.gs.automation_settings["opt_healing_surges"] = True
        ok_hs_on, _ = handle_healing_surge(pc, 1, self.gs)
        self.assertTrue(ok_hs_on)
        self.assertGreater(pc.hp, 20)

        # Honor & Sanity STAT_MAP + Fear/Horror
        self.assertEqual(STAT_MAP["HON"], "ONO")
        self.assertEqual(STAT_MAP["SAN"], "SAN")
        pc.full_sheet["attributes"]["SAN"] = 14
        self.assertEqual(get_effective_attribute_from_dict(pc.full_sheet, "SAN"), 14)

        self.gs.automation_settings["opt_fear_horror"] = False
        ok_hr_off, _ = handle_fear_or_horror_save(pc, "horror", 15, self.gs, forced_roll=3)
        self.assertFalse(ok_hr_off)
        self.gs.automation_settings["opt_fear_horror"] = True
        self.gs.automation_settings["opt_honor_sanity"] = True
        ok_hr, msg_hr = handle_fear_or_horror_save(pc, "horror", 15, self.gs, forced_roll=3)
        self.assertTrue(ok_hr)
        self.assertIn("TS SAN", msg_hr)
        self.assertTrue(getattr(pc, "madness_effects", []))

        # Climb Onto Bigger Creature
        giant = _make_monster("Gigante", hp=120, ac=13, pos=(2, 3))
        giant.size = "Enorme"
        self.gs.players.append(giant)
        self.gs.automation_settings["opt_dmg_maneuvers"] = True
        self.gs.automation_settings["opt_climb_bigger"] = True
        with patch("server.rules.class_abilities.roll_dice", side_effect=[{"total": 22}, {"total": 8}]):
            handle_dmg_maneuver_request(
                {"maneuver": "climb_bigger", "target_name": "Gigante"},
                pc,
                self.gs,
            )
        self.assertEqual(pc.climbing_on_target, "Gigante")

    def test_lingering_injury_system_shock_and_dmg_special_tools(self):
        pc = _make_pc("Ferito", hp=40)
        pc.active_effects = [
            {"id": "inj1", "name": "Occhio Perso", "lingering_injury": True, "injury_key": "lose_eye"},
            {"id": "inj2", "name": "Zoppia", "lingering_injury": True, "injury_key": "limp"},
            {"id": "ss1", "name": "Shock Sistemico", "no_reactions": True},
        ]
        pen = get_lingering_injury_penalties(pc)
        self.assertTrue(pen["ranged_attack_disadvantage"])
        self.assertEqual(pen["speed_penalty_ft"], 5)
        self.assertTrue(_has_no_reactions_effect(pc))

        ok_c, _ = cure_lingering_injury(pc, method="regenerate")
        self.assertTrue(ok_c)
        self.assertEqual(get_lingering_injury_penalties(pc)["ranged_attack_disadvantage"], False)

        # Complex Trap init 20/10 on advance_combat_turn
        self.gs.combat_active = True
        self.gs.players = [pc]
        register_complex_trap(self.gs, {"name": "Lame Rotanti", "initiative": 20, "dc": 10, "save_stat": "DES", "damage_formula": "1d4"})
        msgs = trigger_complex_traps_at_round_start(self.gs, 20)
        self.assertEqual(len(msgs), 1)

        # Siege, Sentient Ego/Conflict, Artifacts, Poison, Sidekicks, Renown, Bastion, Command routing
        wall_tgt = _make_monster("Cancello", hp=50, ac=10, pos=(5, 5))
        self.gs.players.append(wall_tgt)
        ok_sg, _ = handle_siege_action("ballista", "Cancello", self.gs)
        self.assertIsInstance(ok_sg, bool)
        self.assertEqual(calculate_sentient_ego(16, 14, 18, 2), 11)
        ok_sc, _ = resolve_sentient_conflict(pc, "Spada Nera", 12, self.gs, forced_roll=1)
        self.assertFalse(ok_sc)
        art = roll_artifact_properties()
        self.assertEqual(len(art["minor_beneficial"]), 2)
        self.assertTrue(len(art["major_detrimental"]) == 1)

        wyvern = _make_monster("Viverna", hp=0, pos=(2, 3))
        self.gs.players.append(wyvern)
        ok_pv, _ = handle_harvest_poison(pc, "Viverna", "Veleno di Viverna", self.gs, forced_roll=20)
        self.assertTrue(ok_pv)

        sk = _make_monster("Droop", hp=10, pos=(1, 1))
        sk_res = level_up_sidekick(sk, "warrior", 3)
        self.assertEqual(sk_res["level"], 3)
        self.assertEqual(adjust_renown_or_piety(pc, "piety", 3, "Lathander"), 3)
        self.assertGreater(resolve_bastion_turn("treasury")["gold_dividend"], 0)
        self.assertIn("OPTIONAL_RULE_ACTION_REQUEST", command_handlers)
        self.assertIn("RESOLVE_LEGENDARY_RESISTANCE_REQUEST", command_handlers)

    # ------------------------------------------------------------------
    # BLOCK 4: MONSTER MANUAL ENGINE & WIRED HOOKS
    # ------------------------------------------------------------------
    def test_lair_actions_init20_anti_repeat_and_legendary_guard(self):
        hero = _make_pc("Hero", hp=40)
        hero.initiative = 22
        boss = _make_monster("Drago Rosso", hp=200)
        boss.initiative = 12
        boss.has_lair_actions = True
        boss.legendary_actions_max = 3
        boss.legendary_actions_current = 2
        self.gs.players = [hero, boss]
        self.gs.combat_active = True
        self.gs.turn_index = 0
        self.gs.round_number = 1

        # Crossing 22 -> 12 triggers Lair Action at Init 20 (losing ties)
        fired = trigger_lair_actions_if_crossed(self.gs, prev_init=22, next_init=12, round_advanced=False)
        self.assertTrue(fired)
        # Anti back-to-back repeat
        ok1, _ = execute_lair_action(boss, "Magma Eruttante", self.gs)
        self.assertTrue(ok1)
        ok2, msg2 = execute_lair_action(boss, "Magma Eruttante", self.gs)
        self.assertFalse(ok2)
        self.assertIn("due round consecutivi", msg2)

        # Incapacitated boss cannot spend Legendary Actions
        boss.conditions = ["Stordito"]
        self.assertTrue(is_incapacitated_entity(boss))
        handle_spend_legendary_action_request({"boss_name": "Drago Rosso", "action_name": "Coda", "cost": 1}, None, self.gs)
        self.assertEqual(boss.legendary_actions_current, 2)

    def test_pending_legendary_resistance_prompt_and_mythic_awakening(self):
        boss = _make_monster("Boss Mitico", hp=50)
        boss.legendary_resistances_max = 3
        boss.legendary_resistances_current = 3
        boss.is_mythic = True
        boss.full_sheet["mythic_actions"] = [{"name": "Colpo Stellare", "desc": "Melee +10 to hit"}]
        boss.full_sheet["mythic_hp"] = 80
        self.gs.players = [boss]

        # DM prompt mode ON
        self.gs.automation_settings["opt_legendary_res_prompt"] = True
        _process_save_result("Boss Mitico", "DES", 5, False, True, 18, "", False, "Palla di Fuoco", self.gs, "Fuoco")
        self.assertEqual(boss.legendary_resistances_current, 3)  # Not auto-spent yet!
        self.assertEqual(len(self.gs.pending_legendary_resistances), 1)
        lr_id = next(iter(self.gs.pending_legendary_resistances))
        handle_resolve_legendary_resistance_request({"pending_id": lr_id, "decision": "use"}, None, self.gs)
        self.assertEqual(boss.legendary_resistances_current, 2)
        self.assertEqual(len(self.gs.pending_legendary_resistances), 0)

        # Mythic Awakening at 0 HP
        self.gs.automation_settings["opt_legendary_res_prompt"] = False
        apply_damage(boss, 999, "Tagliente", self.gs)
        self.assertTrue(boss.mythic_phase_active)
        self.assertTrue(boss.mythic_actions_unlocked)
        self.assertEqual(boss.hp, 80)
        self.assertNotIn("Morto", boss.conditions)

    def test_monster_spellcasting_parse_sync_and_cast(self):
        mage = _make_monster("Arcimago Drow", hp=80)
        mage.full_sheet["features"] = [
            {
                "name": "Innate Spellcasting",
                "desc": "At will: dancing lights, detect magic\n3/day each: darkness, faerie fire\n1/day: levitate",
            },
            {
                "name": "Spellcasting",
                "desc": "1st level (4 slots): mage armor, shield\n3rd level (2 slots): fireball, counterspell",
            },
        ]
        self.gs.players = [mage]
        parsed = sync_monster_spellcasting_to_sheet(mage)
        self.assertIn("darkness", parsed["innate"])
        self.assertEqual(parsed["innate"]["darkness"]["max"], 3)
        self.assertEqual(parsed["slots"]["3"]["max"], 2)

        ok_i, _ = cast_monster_spell(mage, "darkness", self.gs)
        self.assertTrue(ok_i)
        self.assertEqual(mage.full_sheet["innate_spells"]["darkness"]["current"], 2)

        ok_s, _ = cast_monster_spell(mage, "fireball", self.gs, slot_level=3)
        self.assertTrue(ok_s)
        self.assertEqual(mage.full_sheet["spell_slots"]["3"]["current"], 1)

    def test_swarm_traits_incorporeal_damage_transfer_death_burst_petrification_water(self):
        # Swarm condition immunity & half damage at <=50% HP
        swarm = _make_monster("Sciame di Pipistrelli", hp=22, pos=(2, 2), features=[{"name": "Sciame", "desc": "Swarm of Tiny beasts"}])
        pc = _make_pc("Eroe", hp=40, ac=10, pos=(2, 3))
        self.gs.players = [swarm, pc]
        self.assertFalse(filter_swarm_condition(swarm, "Afferrato"))
        handle_apply_effect_request({"target_name": "Sciame di Pipistrelli", "effect": {"name": "Prono"}}, None, self.gs)
        self.assertEqual(len(swarm.active_effects), 0)
        with patch("server.rules.combat.random.randint", side_effect=[20, 20, 1, 1]):
            handle_grapple_request({"target_name": "Sciame di Pipistrelli"}, pc, self.gs)
        self.assertNotIn("Afferrato", swarm.conditions)
        with patch("server.rules.combat.random.randint", side_effect=[20, 20, 1, 1]):
            handle_shove_request({"target_name": "Sciame di Pipistrelli", "option": "prone"}, pc, self.gs)
        self.assertNotIn("Prono", swarm.conditions)

        swarm.hp = 10  # <= 50% of 22
        self.assertEqual(get_swarm_damage_divisor(swarm), 2)
        with patch("server.rules.combat.random.randint", return_value=15), \
             patch("server.rules.combat.roll_dice", return_value={"total": 12, "rolls": [6, 6]}):
            handle_attack_request(
                {"target_name": "Eroe", "weapon_name": "Morsi", "hit_bonus": 4, "damage_formula": "2d4", "damage_type": "Perforante"},
                swarm,
                self.gs,
            )
        self.assertEqual(pc.hp, 34)  # 12 // 2 = 6 damage

        # Incorporeal movement wall bypass + 1d10 wall end-of-turn damage
        ghost = _make_monster("Spettro", hp=45, pos=(0, 0), features=[{"name": "Movimento Incorporeo", "desc": "Incorporeal Movement through objects/walls"}])
        self.gs.current_map = {"walls": [[0, 1]], "doors": [], "difficult_terrain": [], "grid_type": "hex"}
        ghost.speed = 30
        self.gs.players = [ghost]
        self.gs.combat_active = False
        self.assertTrue(is_incorporeal_entity(ghost))
        handle_move_request({"to": [0, 1]}, ghost, self.gs)
        self.assertEqual(ghost.position, [0, 1])  # Moved onto wall!

        # End turn inside wall -> 1d10 Force damage
        self.gs.combat_active = True
        self.gs.turn_index = 0
        with patch("server.rules.combat.roll_dice", return_value={"total": 6, "rolls": [6]}):
            advance_combat_turn(self.gs, ending_player=ghost)
        self.assertEqual(ghost.hp, 39)

        # Shapechanger Polymorph block
        vamp = _make_monster("Vampiro", hp=90, features=[{"name": "Mutaforma", "desc": "Shapechanger"}])
        self.assertTrue(is_shapechanger_entity(vamp))
        handle_apply_effect_request({"target_name": "Vampiro", "effect": {"name": "Metamorfosi (Polymorph)"}}, None, self.gs)
        self.assertEqual(len(vamp.active_effects), 0)

        # Damage Transfer 50/50 split
        cloaker = _make_monster("Mantello", hp=60, features=[{"name": "Trasferimento del Danno", "desc": "Damage Transfer"}])
        victim = _make_pc("Vittima", hp=40)
        cloaker.damage_transfer_target = "Vittima"
        self.gs.players = [cloaker, victim]
        apply_damage(cloaker, 20, "Tagliente", self.gs)
        self.assertEqual(cloaker.hp, 50)
        self.assertEqual(victim.hp, 30)

        # Death Burst at 0 HP
        magmin = _make_monster("Magmin", hp=9, pos=(2, 2), features=[{"name": "Esplosione alla Morte", "desc": "Death Burst DC 12 (2d6) within 10 ft"}])
        bystander = _make_pc("Vicino", hp=30, pos=(2, 3))
        self.gs.players = [magmin, bystander]
        with patch("server.dm_monster_engine.roll_dice", return_value={"total": 1, "rolls": [1]}):
            apply_damage(magmin, 20, "Tagliente", self.gs)
        self.assertLess(bystander.hp, 30)

        # 2-stage Petrification
        target_pet = _make_pc("Pietra", hp=30)
        apply_petrification_stage(target_pet, failed_save=True, game_state=self.gs)
        self.assertIn("Trattenuto", target_pet.conditions)
        apply_petrification_stage(target_pet, failed_save=True, game_state=self.gs)
        self.assertIn("Pietrificato", target_pet.conditions)

        # Spider Climb & Water Breathing
        spider = _make_monster("Ragno Gigante", pos=(0, 0), features=[{"name": "Movimenti del Ragno", "desc": "Spider Climb"}])
        spider.speed = 5  # 1 hex only
        self.gs.current_map = {"walls": [], "doors": [], "difficult_terrain": [{"q": 0, "r": 1, "type": "rock"}], "grid_type": "hex"}
        self.gs.players.append(spider)
        self.gs.combat_active = False
        handle_move_request({"to": [0, 1]}, spider, self.gs)
        self.assertEqual(spider.position, [0, 1])  # Difficult terrain bypassed with 5ft speed!

        sahuagin = _make_monster("Sahuagin", features=[{"name": "Anfibio", "desc": "Water Breathing / Amphibious"}])
        self.gs.players.append(sahuagin)
        self.assertTrue(has_spider_climb(spider))
        self.assertTrue(has_water_breathing(sahuagin))
        sahuagin.breath_rounds_left = 1
        handle_submerged_breath_request({"actor_name": "Sahuagin", "action": "tick_round"}, None, self.gs)
        self.assertIsNone(sahuagin.breath_rounds_left)


if __name__ == "__main__":
    unittest.main()
