import unittest
import queue
from unittest.mock import patch

from common.game_state import GameState, Player
from common.dice import roll_dice
from common.item_modifiers import (
    get_effective_save_bonus_from_dict,
    is_item_cursed,
    can_unattune_item,
    lift_curse_on_inventory,
)
from common.dnd5e_tables import (
    calculate_jump_distances,
    get_breath_hold_rounds,
    get_suffocation_rounds,
    calculate_spell_points_max,
    roll_system_shock,
    roll_lingering_injury,
    roll_madness,
    REST_VARIANTS,
    DMG_POISONS,
    DMG_DISEASES,
    OBJECT_MATERIALS_AC,
    OBJECT_SIZE_HP,
    evaluate_object_damage,
    get_max_free_dashes,
)
from client.character_manager import Character
from server.rules.combat import (
    handle_attack_request,
    apply_damage,
    handle_short_rest_request,
    handle_reaction_response,
    _process_save_result,
)
from server.rules.movement import handle_move_request
from server.rules.character import trigger_group_long_rest
from server.rules.class_abilities import (
    is_immune_to_frightened_by_aura,
    handle_lay_on_hands_request,
    handle_reckless_attack_request,
    handle_bardic_inspiration_request,
    handle_turn_undead_request,
    handle_divine_intervention_request,
    handle_indomitable_request,
    handle_maneuver_request,
    handle_hide_request,
    handle_cunning_action_request,
    handle_ki_ability_request,
    handle_mystic_arcanum_request,
    validate_spell_casting_rules,
    handle_cast_special_spell_request,
    handle_toggle_non_lethal_request,
    handle_healer_feat_request,
    handle_inspiring_leader_request,
    handle_frightful_presence_request,
    handle_swallow_request,
    handle_dmg_maneuver_request,
    handle_madness_request,
    handle_apply_poison_or_disease_request,
    handle_chase_dash_request,
    handle_survival_tick_request,
    handle_mount_request,
    handle_surprise_request,
    handle_submerged_breath_request,
)


class MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


def _make_player(name, cls="Guerriero", level=5, hp=40, ac=15, pos=(0, 0), party=True, **sheet_extra):
    p = Player(name, conn=(MockConn() if party else None))
    p.hp = hp
    p.max_hp = hp
    p.ac = ac
    p.position = list(pos)
    p.is_party_member = party
    p.speed = 30
    sheet = {
        "name": name,
        "char_class": cls,
        "level": level,
        "attributes": {"FOR": 16, "DES": 14, "COS": 14, "INT": 12, "SAG": 14, "CAR": 14},
        "hp_current": hp,
        "hp_max": hp,
        "ac": ac,
        "features": [],
        "feats": [],
        "custom_resources": [],
        "inventory_grid": [],
        "weapons": [{"name": "Spada Lunga", "hit_bonus": "+6", "damage": "1d8+3", "damage_type": "Tagliente"}],
        "conditions": [],
    }
    sheet.update(sheet_extra)
    p.full_sheet = sheet
    return p


class TestPHBClassFeaturesAndFeats(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.current_map = {"grid_type": "hex", "hex_size": 60, "walls": [], "doors": [], "difficult_terrain": {}}

    def test_barbarian_reckless_danger_relentless_and_bear_totem(self):
        barb = _make_player(
            "Grog",
            cls="Barbaro",
            level=11,
            hp=100,
            features=["Attacco Irruento", "Percezione del Pericolo", "Totem dell'Orso", "Ira Implacabile"],
        )
        orc = _make_player("Orc", cls="Mostro", level=5, hp=30, pos=(1, 0), party=False)
        self.gs.players = [barb, orc]
        self.gs.combat_active = True

        # Reckless Attack ON & Bear Totem Rage damage halving (even vs Fire!)
        barb.conditions = ["Ira"]
        dmg_fire, _, _, _ = apply_damage(barb, 12, "Fuoco", self.gs)
        self.assertEqual(dmg_fire, 6)
        dmg_psy, _, _, _ = apply_damage(barb, 8, "Psichico", self.gs)
        self.assertEqual(dmg_psy, 8)

        # Relentless Rage keeps Barbarian at 1 HP on first drop (non-massive damage)
        with patch("common.dice.random.randint", return_value=18):
            barb.hp = 5
            apply_damage(barb, 20, "Psichico", self.gs)
            self.assertEqual(barb.hp, 1)
            self.assertEqual(barb.relentless_rage_uses, 1)

        handle_reckless_attack_request({"active": True}, barb, self.gs)
        self.assertTrue(barb.reckless_attack_active)

    def test_bard_inspiration_and_song_of_rest(self):
        bard = _make_player("Scanlan", cls="Bardo", level=5, hp=30, pos=(0, 0))
        ally = _make_player("Vax", cls="Ladro", level=5, hp=15, pos=(1, 0))
        ally.max_hp = 35
        self.gs.players = [bard, ally]

        handle_bardic_inspiration_request({"action": "grant", "target_name": "Vax"}, bard, self.gs)
        self.assertEqual(ally.bardic_inspiration_die, "d8")
        handle_bardic_inspiration_request({"action": "use"}, ally, self.gs)
        self.assertIsNone(ally.bardic_inspiration_die)

        # Short rest heals extra from Song of Rest
        with patch("random.randint", return_value=4):
            handle_short_rest_request({"hd_spent": 1, "hp_recovered": 6}, ally, self.gs)
        self.assertEqual(ally.hp, 25)  # 15 + 6 + 4 Song of Rest

    def test_cleric_turn_and_destroy_undead_plus_divine_intervention(self):
        cleric = _make_player("Pike", cls="Chierico", level=5, hp=40, pos=(0, 0))
        cleric.full_sheet["custom_resources"] = [{"name": "Incanala Divinità", "current": 2, "max": 2, "reset_on": "short"}]
        skel = _make_player("Scheletro", cls="Non Morto", level=1, hp=13, pos=(1, 0), party=False, creature_type="Non Morto", cr="1/4")
        self.gs.players = [cleric, skel]

        with patch("common.dice.random.randint", return_value=1):
            handle_turn_undead_request({"dc": 15}, cleric, self.gs)
        # CR 1/4 <= CR 1/2 threshold for Cleric Lv 5 -> Destroyed!
        self.assertEqual(skel.hp, 0)
        self.assertIn("Morto", skel.conditions)

        # Divine Intervention Lv 10 auto-succeeds on roll <= 10
        cleric10 = _make_player("Pike10", cls="Chierico", level=10, hp=60)
        self.gs.players.append(cleric10)
        handle_divine_intervention_request({"forced_roll": 8}, cleric10, self.gs)
        msgs = [m.get("payload", "") for m in list(self.gs.gui_queue.queue) if isinstance(m, dict)]
        self.assertTrue(any("INTERVENTO DIVINO RIUSCITO" in str(m) for m in msgs))

    def test_fighter_indomitable_and_maneuvers(self):
        ftr = _make_player("Percy", cls="Guerriero", level=9, hp=60, pos=(0, 0), features=["Indomito", "Maestro di Battaglia"])
        ftr.full_sheet["custom_resources"] = [
            {"name": "Indomito", "current": 1, "max": 1, "reset_on": "long"},
            {"name": "Dadi di Superiorità", "current": 4, "max": 4, "die": "d8", "reset_on": "short"},
        ]
        goblin = _make_player("Goblin", cls="Mostro", level=1, hp=20, pos=(1, 0), party=False)
        self.gs.players = [ftr, goblin]

        handle_indomitable_request({"stat": "COS", "dc": 15}, ftr, self.gs)
        self.assertEqual(ftr.full_sheet["custom_resources"][0]["current"], 0)

        with patch("common.dice.random.randint", return_value=1):
            handle_maneuver_request({"maneuver": "trip", "target_name": "Goblin"}, ftr, self.gs)
        self.assertIn("Prono", goblin.conditions)

    def test_rogue_cunning_action_hide_and_uncanny_dodge(self):
        rogue = _make_player("Vax", cls="Ladro", level=5, hp=40, pos=(0, 0), skills={"Furtività": 1})
        enemy = _make_player("Orc", cls="Mostro", level=3, hp=30, pos=(2, 0), party=False)
        enemy.full_sheet["passive_perception"] = 10
        self.gs.players = [rogue, enemy]
        self.gs.combat_active = True

        handle_cunning_action_request({"sub_action": "dash"}, rogue, self.gs)
        self.assertTrue(rogue.bonus_action_used_this_turn)
        self.assertIn("Scatto", rogue.conditions)

        rogue.bonus_action_used_this_turn = False
        with patch("common.dice.random.randint", return_value=18):
            handle_hide_request({"as_bonus_action": True}, rogue, self.gs)
        self.assertGreaterEqual(rogue.stealth_score, 20)
        self.assertIn("Nascosto", rogue.conditions)

        # Uncanny Dodge reaction halves damage taken
        rogue.hp = 20
        rogue.has_reacted_this_turn = False
        handle_reaction_response({"reaction_type": "UNCANNY_DODGE", "accepted": True, "target_name": "Orc", "details": {"damage_taken": 14, "dmg_to_hp": 14}}, rogue, self.gs)
        self.assertEqual(rogue.hp, 27)

    def test_monk_ki_and_diamond_soul(self):
        monk = _make_player("Beau", cls="Monaco", level=14, hp=80, pos=(0, 0))
        monk.full_sheet["custom_resources"] = [{"name": "Punti Ki", "current": 14, "max": 14, "reset_on": "short"}]
        self.gs.players = [monk]
        # Diamond Soul gives proficiency on INT save even if unlisted
        int_save = get_effective_save_bonus_from_dict(monk, "INT")
        self.assertGreaterEqual(int_save, 1 + 5)  # +1 INT mod + 5 PB (level 14)

        handle_ki_ability_request({"ability": "patient_defense"}, monk, self.gs)
        self.assertIn("Schivata", monk.conditions)
        self.assertEqual(monk.full_sheet["custom_resources"][0]["current"], 13)

    def test_paladin_lay_on_hands_and_aura_of_courage(self):
        pal = _make_player("VexPal", cls="Paladino", level=11, hp=70, pos=(0, 0), features=["Ira", "Aura di Coraggio", "Punizione Divina Migliorata"])
        pal.full_sheet["custom_resources"] = [{"name": "Mani Curative (Lay on Hands)", "current": 55, "max": 55, "reset_on": "long"}]
        ally = _make_player("Keyleth", cls="Druido", level=11, hp=30, pos=(1, 0))
        ally.max_hp = 60
        self.gs.players = [pal, ally]

        handle_lay_on_hands_request({"target_name": "Keyleth", "amount": 15}, pal, self.gs)
        self.assertEqual(ally.hp, 45)
        self.assertEqual(pal.full_sheet["custom_resources"][0]["current"], 40)

        immune, src = is_immune_to_frightened_by_aura(ally, self.gs)
        self.assertTrue(immune)
        self.assertEqual(src, "VexPal")

    def test_warlock_mystic_arcanum_and_eldritch_blast(self):
        wl = _make_player("Wyll", cls="Warlock", level=17, hp=80, pos=(0, 0), features=["Esplosione Agonizzante", "Esplosione Respingente"])
        wl.full_sheet["attributes"]["CAR"] = 18
        target = _make_player("Cultista", cls="Mostro", level=3, hp=100, ac=5, pos=(1, 0), party=False)
        self.gs.players = [wl, target]

        handle_mystic_arcanum_request({"level": 6, "spell_name": "Cerchio di Morte"}, wl, self.gs)
        self.assertTrue(any(r.get("current") == 0 for r in wl.full_sheet["custom_resources"] if "Arcanum" in r.get("name", "")))

        with patch("server.rules.class_abilities.roll_dice") as mock_roll:
            mock_roll.return_value = {"total": 10, "rolls": [10]}
            handle_cast_special_spell_request({"spell_name": "Deflagrazione Occulta", "target_name": "Cultista", "base_level": 0}, wl, self.gs)
        # Level 17 = 4 rays!
        self.assertLess(target.hp, 100)

    def test_feats_tough_alert_elemental_adept_healer_inspiring_leader_sentinel_pam(self):
        c = Character(name="Talented")
        c.level = 10
        c.attributes["DES"] = 14
        c.feats = ["Robusto", "Allerta", "Adepto Elementale (Fuoco)"]
        self.assertEqual(c.get_tough_bonus_hp(), 20)
        self.assertGreaterEqual(c.get_alert_initiative_bonus(), 5)
        self.assertEqual(c.get_initiative_bonus(), 2 + 5)
        self.assertTrue(c.has_elemental_adept("Fuoco"))

        # Elemental Adept dice floor + Resistance bypass
        with patch("common.dice.random.randint", return_value=1):
            res = roll_dice("2d6", elemental_adept=True)
        self.assertEqual(res["rolls"], [2, 2])
        fire_res_mob = _make_player("Demone", cls="Mostro", level=5, hp=40, pos=(1, 0), party=False, damage_resistances=["Fuoco"])
        self.gs.players = [fire_res_mob]
        dmg, _, _, _ = apply_damage(fire_res_mob, 10, "Fuoco", self.gs, ignore_resistance=True)
        self.assertEqual(dmg, 10)

        # Healer & Inspiring Leader feats
        h = _make_player("Dottore", cls="Ladro", level=6, hp=30, pos=(0, 0), feats=["Guaritore", "Condottiero Ispiratore"])
        patient = _make_player("Ferito", cls="Guerriero", level=4, hp=10, pos=(1, 0))
        patient.max_hp = 40
        self.gs.players = [h, patient]
        handle_healer_feat_request({"target_name": "Ferito"}, h, self.gs)
        self.assertGreater(patient.hp, 10)
        handle_inspiring_leader_request({}, h, self.gs)
        self.assertGreater(patient.temp_hp, 0)

        # Polearm Master + Sentinel movement triggers
        pam_enemy = _make_player("GuardiaPAM", cls="Mostro", level=5, hp=40, ac=15, pos=(4, 0), party=False, features=["Maestro d'Armi Astate", "Sentinella"])
        pam_enemy.reach = 2
        mover = _make_player("Ladruncolo", cls="Ladro", level=5, hp=35, pos=(1, 0), party=True)
        mover.conditions = ["Disimpegno"]
        self.gs.players = [pam_enemy, mover]
        self.gs.combat_active = True
        handle_move_request({"to": [2, 0]}, mover, self.gs)
        msgs = [m.get("payload", "") for m in list(self.gs.gui_queue.queue) if isinstance(m, dict)]
        self.assertTrue(any("Maestro d'Armi Astate" in str(m) for m in msgs))


class TestCombatEdgeRulesAndMonsters(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.current_map = {"grid_type": "hex", "hex_size": 60, "walls": [], "doors": [], "difficult_terrain": {}}

    def test_magic_missile_vs_shield_and_bonus_action_spell_rule_and_silence(self):
        wiz = _make_player("Gale", cls="Mago", level=5, hp=30, pos=(0, 0))
        target = _make_player("Schild", cls="Mostro", level=3, hp=30, pos=(2, 0), party=False)
        target.conditions = ["Scudo"]
        self.gs.players = [wiz, target]

        handle_cast_special_spell_request({"spell_name": "Dardo Incantato", "cast_level": 1, "target_name": "Schild"}, wiz, self.gs)
        self.assertEqual(target.hp, 30)  # Blocked by Shield

        target.conditions = []
        handle_cast_special_spell_request({"spell_name": "Dardo Incantato", "cast_level": 2, "target_name": "Schild"}, wiz, self.gs)
        self.assertLess(target.hp, 30)  # Auto-hit 4 darts

        # Bonus action spell rule
        wiz.spell_cast_bonus_action_this_turn = True
        ok_ba, _ = validate_spell_casting_rules(wiz, spell_level=3, casting_time="action", has_verbal=False, game_state=self.gs)
        self.assertFalse(ok_ba)
        ok_cantrip, _ = validate_spell_casting_rules(wiz, spell_level=0, casting_time="action", has_verbal=False, game_state=self.gs)
        self.assertTrue(ok_cantrip)

        # Silence blocks verbal spell
        wiz.conditions = ["Silenziato"]
        ok_sil, _ = validate_spell_casting_rules(wiz, spell_level=0, casting_time="action", has_verbal=True, game_state=self.gs)
        self.assertFalse(ok_sil)

    def test_surprise_non_lethal_submerged_breath_mount_grapple_drag(self):
        p = _make_player("Hero", cls="Guerriero", level=5, hp=40, pos=(0, 0))
        gob = _make_player("Gob", cls="Mostro", level=1, hp=10, ac=10, pos=(1, 0), party=False)
        horse = _make_player("Cavallo", cls="Cavalcatura", level=1, hp=25, pos=(0, 0), party=True)
        self.gs.players = [p, gob, horse]
        self.gs.combat_active = True

        # Surprise blocks movement
        handle_surprise_request({"target_name": "Hero", "surprised": True}, None, self.gs)
        self.assertTrue(p.surprised)
        handle_move_request({"to": [1, 0]}, p, self.gs)
        self.assertEqual(p.position, [0, 0])  # Blocked!
        self.gs.current_turn_index = 0
        self.gs.next_turn()  # Auto clears surprise at end of first turn
        self.assertFalse(p.surprised)

        # Non-Lethal Attack KO
        handle_toggle_non_lethal_request({"non_lethal": True}, p, self.gs)
        apply_damage(gob, 25, "Contundente", self.gs, is_non_lethal=True)
        self.assertEqual(gob.hp, 0)
        self.assertIn("Stabilizzato", gob.conditions)
        self.assertNotIn("Morto", gob.conditions)

        # Mount + Submerged breath
        handle_mount_request({"mount_name": "Cavallo"}, p, self.gs)
        handle_move_request({"to": [2, 0]}, horse, self.gs)
        self.assertEqual(p.position, [2, 0])

        handle_submerged_breath_request({"action": "toggle_submerged", "submerged": True}, p, self.gs)
        self.assertTrue(p.is_submerged)
        self.assertEqual(get_breath_hold_rounds(2), 30)
        self.assertEqual(get_suffocation_rounds(2), 2)
        dmg_sub, _, _, _ = apply_damage(p, 10, "Fuoco", self.gs)
        self.assertEqual(dmg_sub, 5)  # Underwater fire resistance

        # Jump calculator & Dragging grappled target
        j = calculate_jump_distances(18, running_start=True)
        self.assertEqual(j["long_jump_ft"], 18)
        self.assertEqual(j["high_jump_ft"], 7)

    def test_monster_traits_frightful_swallow_ooze_flyby_magic_res(self):
        dragon = _make_player("Smaug", cls="Drago", level=15, hp=200, pos=(0, 0), party=False, features=["Presenza Terrificante", "Resistenza alla Magia", "Inghiottire"])
        hero = _make_player("BardoHero", cls="Ladro", level=5, hp=40, pos=(1, 0), party=True)
        ooze = _make_player("CuboGelatinoso", cls="Melma", level=4, hp=40, pos=(3, 0), party=False, features=["Scissione"])
        ooze.size = "Grande"
        self.gs.players = [dragon, hero, ooze]
        self.gs.combat_active = True

        with patch("common.dice.random.randint", return_value=1):
            handle_frightful_presence_request({"actor_name": "Smaug", "dc": 18}, None, self.gs)
        self.assertIn("Spaventato", hero.conditions)

        # Swallow + turn acid + regurgitation when dragon drops to 0 HP
        handle_swallow_request({"actor_name": "Smaug", "target_name": "BardoHero"}, None, self.gs)
        self.assertEqual(hero.swallowed_by, "Smaug")
        self.assertIn("Inghiottito", hero.conditions)
        apply_damage(dragon, 500, "Forza", self.gs)
        self.assertIsNone(hero.swallowed_by)
        self.assertNotIn("Inghiottito", hero.conditions)
        self.assertIn("Prono", hero.conditions)

        # Ooze Split on Slashing damage
        apply_damage(ooze, 10, "Tagliente", self.gs)
        self.assertEqual(len([pl for pl in self.gs.players if "CuboGelatinoso" in pl.name]), 2)


class TestDMGOptionalRulesSelectable(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.current_map = {"grid_type": "hex", "hex_size": 60, "walls": [], "doors": [], "difficult_terrain": {}}

    def test_all_dmg_rules_respect_dm_automation_toggles(self):
        # By default all optional DMG rules are OFF
        for key in ("opt_cleaving", "opt_massive_damage", "opt_lingering_injuries", "opt_madness", "opt_dmg_maneuvers", "opt_spell_points", "opt_hunger_thirst_weather"):
            self.assertFalse(self.gs.automation_settings[key])
        self.assertEqual(self.gs.automation_settings["opt_rest_variant"], "standard")

        # Calling Madness / DMG Maneuver when OFF rejects gracefully
        target = _make_player("Victim", cls="Guerriero", level=5, hp=40, pos=(1, 0), party=True)
        att = _make_player("Att", cls="Guerriero", level=5, hp=40, pos=(0, 0), party=False)
        self.gs.players = [att, target]
        handle_madness_request({"target_name": "Victim", "tier": "short"}, None, self.gs)
        self.assertEqual(len(target.madness_effects), 0)

        # Enable all optional DMG rules in automation_settings
        for key in ("opt_cleaving", "opt_massive_damage", "opt_lingering_injuries", "opt_madness", "opt_dmg_maneuvers", "opt_spell_points", "opt_hunger_thirst_weather"):
            self.gs.automation_settings[key] = True

        handle_madness_request({"target_name": "Victim", "tier": "short", "roll_val": 5}, None, self.gs)
        self.assertEqual(len(target.madness_effects), 1)

        with patch("common.dice.random.randint", side_effect=[20, 1]):
            handle_dmg_maneuver_request({"actor_name": "Att", "target_name": "Victim", "maneuver": "disarm"}, None, self.gs)
        self.assertIn("Disarmato", target.conditions)

        # Objects, Damage Threshold & Poisons/Diseases & Chases
        self.assertEqual(OBJECT_MATERIALS_AC["Ferro / Acciaio"], 19)
        self.assertIn("Grande (Large)", OBJECT_SIZE_HP)
        dmg0, _ = evaluate_object_damage(8, "Tagliente", damage_threshold=10)
        self.assertEqual(dmg0, 0)
        dmg12, _ = evaluate_object_damage(12, "Tagliente", damage_threshold=10)
        self.assertEqual(dmg12, 12)

        with patch("common.dice.random.randint", return_value=2):
            handle_apply_poison_or_disease_request({"target_name": "Victim", "kind": "poison", "name": list(DMG_POISONS.keys())[0]}, None, self.gs)
        self.assertIn("Avvelenato", target.conditions)

        self.assertEqual(get_max_free_dashes(2), 5)
        with patch("common.dice.random.randint", return_value=2):
            for _ in range(7):
                handle_chase_dash_request({"actor_name": "Victim"}, None, self.gs)
        self.assertGreaterEqual(target.exhaustion_level, 1)

        with patch("common.dice.random.randint", return_value=2):
            handle_survival_tick_request({"event": "day_pass", "fed_players": [], "watered_players": []}, None, self.gs)
        self.assertGreaterEqual(target.exhaustion_level, 2)  # No water -> +1 exhaustion

    def test_cursed_item_blocks_unattune_until_remove_curse(self):
        wiz = _make_player("ChiericoCurse", cls="Chierico", level=5, hp=40, pos=(0, 0))
        cursed_hero = _make_player("Maledetto", cls="Guerriero", level=5, hp=40, pos=(1, 0))
        cursed_ring = {"name": "Anello della Goetia", "cursed": True, "attuned": True, "desc": "Oggetto maledetto."}
        cursed_hero.full_sheet["inventory_grid"] = [cursed_ring]
        self.gs.players = [wiz, cursed_hero]

        self.assertTrue(is_item_cursed(cursed_ring))
        ok_un, _ = can_unattune_item(cursed_ring)
        self.assertFalse(ok_un)

        handle_cast_special_spell_request({"spell_name": "Rimuovi Maledizione", "cast_level": 3, "target_name": "Maledetto"}, wiz, self.gs)
        ok_after, _ = can_unattune_item(cursed_ring)
        self.assertTrue(ok_after)

    def test_spell_points_and_rest_variants(self):
        wiz_c = Character(name="Archmage")
        wiz_c.char_class = "Mago"
        wiz_c.level = 5
        sp_max = calculate_spell_points_max(wiz_c)
        self.assertEqual(sp_max, 27)
        wiz_c.spell_points_max = sp_max
        wiz_c.spell_points_current = sp_max
        ok, msg_sp = wiz_c.spend_spell_points(3)
        self.assertTrue(ok)
        self.assertEqual(wiz_c.spell_points_current, 22)
        self.assertIn("5 Punti", msg_sp)

        self.gs.automation_settings["opt_rest_variant"] = "gritty_realism"
        h0 = self.gs.time_hour
        d0 = self.gs.time_day
        p = _make_player("Sleepy", cls="Mago", level=5, hp=20, pos=(0, 0), spell_points_max=27, spell_points_current=0)
        self.gs.players = [p]
        handle_short_rest_request({"hd_spent": 1, "hp_recovered": 4}, p, self.gs)
        self.assertEqual((self.gs.time_hour - h0) % 24, 8)
        trigger_group_long_rest(self.gs)
        self.assertEqual(p.full_sheet["spell_points_current"], 27)
        self.assertGreater(self.gs.time_day, d0)

    def test_attack_cleaving_pack_tactics_charge_flyby_massive_injuries_and_commands(self):
        from server.commands import command_handlers
        for req in (
            "LAY_ON_HANDS_REQUEST", "RECKLESS_ATTACK_REQUEST", "BARDIC_INSPIRATION_REQUEST",
            "TURN_UNDEAD_REQUEST", "DIVINE_INTERVENTION_REQUEST", "INDOMITABLE_REQUEST",
            "MANEUVER_REQUEST", "HIDE_REQUEST", "CUNNING_ACTION_REQUEST", "KI_ABILITY_REQUEST",
            "MYSTIC_ARCANUM_REQUEST", "CAST_SPECIAL_SPELL_REQUEST", "TOGGLE_NON_LETHAL_REQUEST",
            "HEALER_FEAT_REQUEST", "INSPIRING_LEADER_REQUEST", "FRIGHTFUL_PRESENCE_REQUEST",
            "SWALLOW_REQUEST", "DMG_MANEUVER_REQUEST", "MADNESS_REQUEST",
            "APPLY_POISON_DISEASE_REQUEST", "CHASE_DASH_REQUEST", "SURVIVAL_TICK_REQUEST",
            "MOUNT_REQUEST", "SURPRISE_REQUEST", "SUBMERGED_BREATH_REQUEST",
        ):
            self.assertIn(req, command_handlers)

        # Cleaving (opt_cleaving) + Massive Damage / Lingering Injuries
        self.gs.automation_settings["opt_cleaving"] = True
        self.gs.automation_settings["opt_massive_damage"] = True
        self.gs.automation_settings["opt_lingering_injuries"] = True
        self.gs.combat_active = True

        pal = _make_player("Paladin", cls="Paladino", level=11, hp=80, pos=(0, 0), features=["Tattiche di Branco", "Punizione Divina Migliorata"])
        pal.full_sheet["weapons"] = [{"name": "Spadone", "hit_bonus": "+10", "damage": "30", "damage_type": "Tagliente"}]
        gob1 = _make_player("Gob1", cls="Mostro", level=1, hp=10, ac=5, pos=(1, 0), party=False)
        gob2 = _make_player("Gob2", cls="Mostro", level=1, hp=25, ac=5, pos=(0, 1), party=False)
        self.gs.players = [pal, gob1, gob2]

        with patch("common.dice.random.randint", return_value=15):
            handle_attack_request({"target_name": "Gob1", "weapon_name": "Spadone", "hit_bonus": 10, "damage_formula": "30", "damage_type": "Tagliente"}, pal, self.gs)
        self.assertEqual(gob1.hp, 0)
        self.assertLess(gob2.hp, 25)  # Cleaving excess carried over!

        # Massive Damage + Lingering Injury on large single-hit loss (>= half max_hp)
        victim = _make_player("Rugged", cls="Guerriero", level=5, hp=40, pos=(3, 0), party=True)
        self.gs.players.append(victim)
        with patch("common.dice.random.randint", return_value=1), patch("common.dnd5e_tables.random.randint", return_value=5):
            apply_damage(victim, 25, "Tagliente", self.gs, is_crit=True)
        self.assertGreaterEqual(len(victim.injuries), 1)

        # Flyby skips OA while moving away from enemy
        owl = _make_player("Gufo", cls="Bestia", level=1, hp=10, pos=(1, 0), party=True, features=["Volo Radente"])
        guard = _make_player("OrcOA", cls="Mostro", level=2, hp=20, pos=(0, 0), party=False)
        self.gs.players = [owl, guard]
        self.gs.gui_queue = queue.Queue()
        handle_move_request({"to": [4, 0]}, owl, self.gs)
        msgs = [str(m.get("payload", "")) for m in list(self.gs.gui_queue.queue) if isinstance(m, dict)]
        self.assertFalse(any("OPPORTUNITÀ" in m and "Gufo" in m for m in msgs))

        # Grapple drag syncs grappled victim position & costs double movement
        hero = _make_player("Forzuto", cls="Guerriero", level=5, hp=50, pos=(0, 0), party=True)
        grappled = _make_player("Prigioniero", cls="Mostro", level=1, hp=20, pos=(1, 0), party=False)
        grappled.conditions = ["Afferrato"]
        grappled.grappled_by = "Forzuto"
        self.gs.players = [hero, grappled]
        handle_move_request({"to": [2, 0]}, hero, self.gs)
        self.assertEqual(grappled.position, [1, 0])  # Dragged behind hero on 2-step path
        self.assertEqual(hero.movement_spent_this_turn, 4)  # 2 hexes * 2 dragging cost!


if __name__ == "__main__":
    unittest.main()
