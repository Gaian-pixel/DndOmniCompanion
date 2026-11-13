import os
import queue
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["DND_MOCK_AUDIO"] = "1"
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from client.character_manager import Character
from common.feats_and_classes import check_tool_synergy_xgte, get_jack_or_remarkable_bonus
from common.game_state import GameState, Player
from common.item_modifiers import compute_effective_ac
from common.subclass_and_race_rules import (
    apply_crusher_piercer_slasher_on_hit,
    check_elven_accuracy_eligible,
    get_implicit_racial_resistances,
    get_passive_observant_bonus,
    get_powerful_build_multiplier,
    get_racial_save_adv_reasons,
    get_subclass_damage_mods,
    get_subclass_initiative_bonus,
    get_subclass_save_mods,
    handle_subclass_active_power,
    has_halfling_nimbleness,
    has_no_oa_against,
    register_melee_attack_no_oa,
)
from server.rules.class_abilities import handle_class_feature_request
from server.rules.combat import (
    _process_save_result,
    apply_damage,
    handle_attack_request,
    handle_reaction_response,
)
from server.rules.reaction_magic import check_passive_perception


def _mk_player(name: str, cls: str = "Guerriero", lvl: int = 5, race: str = "Umano", subclass: str = "", **attrs) -> Player:
    p = Player(name)
    p.hp = 50
    p.max_hp = 50
    p.ac = 14
    p.is_party_member = True
    base_attrs = {"FOR": 14, "DES": 14, "COS": 14, "INT": 12, "SAG": 12, "CAR": 14}
    base_attrs.update(attrs)
    p.full_sheet = {
        "name": name,
        "char_class": cls,
        "classes": {cls: lvl},
        "level": lvl,
        "race": race,
        "subclass": subclass,
        "attributes": base_attrs,
        "skills": {},
        "proficiencies": {"tools": []},
        "features": [],
        "custom_resources": [],
        "inventory_grid": [],
    }
    p.race = race
    p.subclass = subclass
    return p


class TestBlock3RacesFeatsSubclasses(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.players.clear()

    def test_racial_save_advantages_and_sleep_immunity(self):
        elf = _mk_player("Elrond", race="Elfo")
        r_charm = get_racial_save_adv_reasons(elf, "SAG", is_magic=True, effect_tags=("Affascinato",))
        self.assertTrue(r_charm["advantage"])
        self.assertTrue(r_charm["magic_sleep_immune"])

        gnome = _mk_player("Fizz", race="Gnomo")
        r_magic = get_racial_save_adv_reasons(gnome, "INT", is_magic=True)
        self.assertTrue(r_magic["advantage"])
        self.assertIn("Astuzia Gnomesca", r_magic["reasons"][0])

        half = _mk_player("Pippin", race="Halfling")
        r_fear = get_racial_save_adv_reasons(half, "SAG", effect_tags=("Spaventato",))
        self.assertTrue(r_fear["advantage"])
        self.assertTrue(has_halfling_nimbleness(half))

        dwarf = _mk_player("Thorin", race="Nano")
        r_pois = get_racial_save_adv_reasons(dwarf, "COS", effect_tags=("Veleno",))
        self.assertTrue(r_pois["advantage"])

        # Sleep immunity inside _process_save_result
        elf.hp = 20
        self.gs.add_player(elf)
        _process_save_result("Elrond", "SAG", 2, False, True, 18, "4d8", False, "Incantesimo Sonno", self.gs)
        self.assertEqual(elf.hp, 20)

    def test_tortle_ac_powerful_build_and_implicit_resistances_plus_stones_endurance(self):
        tortle = Character(name="Oogway", race="Tortle", char_class="Druido", level=3)
        tortle.attributes["DES"] = 8
        self.assertEqual(compute_effective_ac(tortle), 17)
        tortle.inventory_grid = [{"name": "Scudo", "type": "Scudo", "container": "equipped", "ac_bonus": 2}]
        self.assertEqual(compute_effective_ac(tortle), 19)

        goliath = Character(name="Grog", race="Goliath", char_class="Barbaro", level=3)
        goliath.attributes["FOR"] = 18  # 18*5=90 base -> x2 Powerful Build = 180 normal
        self.assertEqual(get_powerful_build_multiplier(goliath), 2.0)
        goliath.inventory_grid = [{"name": "Masso", "weight": 150.0, "qty": 1}]
        self.assertEqual(goliath.get_encumbrance_status()["tier"], "normal")

        tief = _mk_player("Morthos", race="Tiefling")
        self.assertIn("fuoco", get_implicit_racial_resistances(tief))
        tief.stones_endurance_shield = 10
        fin, note, _, _ = apply_damage(tief, 30, "Fuoco", self.gs)
        # 30 halved by fire resistance -> 15; Stone's Endurance absorbs 10 -> 5
        self.assertEqual(fin, 5)
        self.assertIn("Tenacia della Pietra assorbe 10", note)

    def test_initiative_remarkable_athlete_subclass_and_tool_synergy(self):
        champ = Character(name="Leonidas", char_class="Guerriero", subclass="Campione", level=7)
        champ.attributes["DES"] = 14  # +2; PB=3 -> Remarkable Athlete ceil(3/2)=+2 -> +4 Init
        self.assertEqual(get_jack_or_remarkable_bonus(champ, "INIT", is_proficient=False), 2)
        self.assertEqual(champ.get_initiative_bonus(), 4)

        gloom = _mk_player("Drizzt", cls="Ranger", lvl=3, subclass="Gloom Stalker", SAG=16)
        swash = _mk_player("Inigo", cls="Ladro", lvl=3, subclass="Swashbuckler", CAR=18)
        b_gs, _ = get_subclass_initiative_bonus(gloom)
        b_sw, _ = get_subclass_initiative_bonus(swash)
        self.assertEqual(b_gs, 3)
        self.assertEqual(b_sw, 4)

        inv_rogue = _mk_player("Holmes", cls="Ladro", lvl=3)
        inv_rogue.full_sheet["skills"] = {"Indagare": 1}
        inv_rogue.full_sheet["proficiencies"] = {"tools": ["Arnesi da Scasso"]}
        self.assertTrue(check_tool_synergy_xgte(inv_rogue, "Indagare"))

    def test_observant_elven_accuracy_crusher_piercer_slasher_mobile_and_defensive_duelist(self):
        obs = _mk_player("Argus", SAG=14)
        obs.full_sheet["features"] = ["Osservatore (Observant)"]
        obs.full_sheet["skills"] = {"Percezione": 1}  # +2 mod + 3 PB + 10 + 5 Obs = 20
        self.assertEqual(get_passive_observant_bonus(obs, "Percezione"), 5)
        self.assertEqual(check_passive_perception(obs, self.gs, sight_based=True), 20)

        ea_elf = _mk_player("Legolas", race="Elfo", DES=18)
        ea_elf.full_sheet["features"] = ["Precisione Elfica"]
        self.assertTrue(check_elven_accuracy_eligible(ea_elf, True, "DES"))
        self.assertFalse(check_elven_accuracy_eligible(ea_elf, True, "FOR"))

        crusher_target = _mk_player("Orc")
        crusher_target.position = [1, 0]
        crusher_pc = _mk_player("Thor", FOR=18)
        crusher_pc.position = [0, 0]
        crusher_pc.full_sheet["features"] = ["Frantumatore (Crusher)", "Perforatore (Piercer)", "Fendente (Slasher)", "Mobilità (Mobile)"]
        register_melee_attack_no_oa(crusher_pc, crusher_target)
        self.assertTrue(has_no_oa_against(crusher_pc, crusher_target))

        with patch("common.subclass_and_race_rules.random.randint", return_value=7):
            c_res = apply_crusher_piercer_slasher_on_hit(crusher_pc, crusher_target, "Contundente", [6], is_crit=True)
            self.assertEqual(c_res["push_hexes"], 1)
            self.assertTrue(crusher_target.crusher_crit_vulnerable)
            p_res = apply_crusher_piercer_slasher_on_hit(crusher_pc, crusher_target, "Perforante", [2, 6], die_sides=8, is_crit=True)
            self.assertEqual(p_res["piercer_reroll_delta"], 5)
            self.assertEqual(p_res["piercer_extra_crit_die"], 7)
            s_res = apply_crusher_piercer_slasher_on_hit(crusher_pc, crusher_target, "Tagliente", [5], is_crit=True)
            self.assertEqual(s_res["slasher_slow_ft"], 10)
            self.assertTrue(crusher_target.slasher_crit_disadvantage)

        # Defensive Duelist reaction restores HP retroactively when AC + PB exceeds hit roll
        duelist = _mk_player("Fiora", cls="Guerriero", lvl=5, DES=18)
        duelist.full_sheet["features"] = ["Duellante Difensivo (Defensive Duelist)"]
        duelist.hp = 35
        duelist._last_hit_for_reaction = {"hit_roll": 15, "base_ac": 14, "is_crit": False, "dmg_to_hp": 10, "temp_absorbed": 0}
        self.gs.add_player(duelist)
        handle_reaction_response({"reaction_type": "DEFENSIVE_DUELIST", "accepted": True, "target_name": "Orc", "details": {}}, duelist, self.gs)
        self.assertEqual(duelist.hp, 45)

    def test_subclasses_passive_and_active_mechanics(self):
        # Berserker Mindless Rage + Frenzy
        bers = _mk_player("Guts", cls="Barbaro", lvl=6, subclass="Berserker")
        bers.is_raging = True
        self.assertTrue(get_subclass_save_mods(bers, None, "SAG", effect_tags=("Affascinato",))["immune"])
        f_res = handle_subclass_active_power(bers, "frenzy_attack", self.gs)
        self.assertTrue(f_res["ok"])
        self.assertTrue(bers.frenzy_exhaustion_pending)

        # Zealot Divine Fury + Hexblade Curse + Draconic Affinity + Light Potent + War Cleric Divine Strike
        zeal = _mk_player("Kratos", cls="Barbaro", lvl=6, subclass="Zelota")
        zeal.is_raging = True
        dm_z = get_subclass_damage_mods(zeal, None, is_weapon_attack=True)
        self.assertEqual(dm_z["flat_bonus"], 3)
        self.assertEqual(dm_z["dice_formulas"][0][0], "1d6")

        hex_w = _mk_player("Erel", cls="Warlock", lvl=5, subclass="Hexblade")
        foe = _mk_player("Goblin")
        handle_subclass_active_power(hex_w, "hexblade_curse", self.gs, {"target": "Goblin"})
        dm_h = get_subclass_damage_mods(hex_w, foe, is_weapon_attack=True)
        self.assertEqual(dm_h["flat_bonus"], 3)  # PB=3

        drac = _mk_player("Ignis", cls="Stregone", lvl=6, subclass="Draconico Fuoco", CAR=18)
        dm_d = get_subclass_damage_mods(drac, foe, damage_type="Fuoco", is_spell=True)
        self.assertEqual(dm_d["flat_bonus"], 4)

        light = _mk_player("Solaris", cls="Chierico", lvl=8, subclass="Luce", SAG=18)
        dm_l = get_subclass_damage_mods(light, foe, is_spell=True, is_cantrip=True)
        self.assertEqual(dm_l["flat_bonus"], 4)

        # Arcane Trickster Lv9 hidden forces disadvantage on enemy saves
        trick = _mk_player("Loki", cls="Ladro", lvl=9, subclass="Mistificatore Arcano")
        trick.is_hidden = True
        self.assertTrue(get_subclass_save_mods(foe, trick, "DES", is_spell=True)["disadvantage"])

        # Class ability router delegates Flash of Genius cleanly
        art = _mk_player("Tink", cls="Artefice", lvl=7, INT=16)
        self.gs.add_player(art)
        handle_class_feature_request({"feature": "flash_of_genius", "target": "Tink"}, art, self.gs)
        self.assertEqual(art.full_sheet["custom_resources"][0]["current"], 2)


if __name__ == "__main__":
    unittest.main()
