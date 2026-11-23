"""
tests/test_phase7_rules_concentration_saves.py - TASK-051 Regression Suite.

Verifica le correzioni D&D 5e (2014 RAW) di Phase 7 su:
1. Concentrazione (handle_cast_special_spell_request replacement/sync, tutti i 9 incantesimi iconici
   in cast_iconic_spell via _start_concentration con concentration_caster + condition tags,
   pulizia attributi in drop_concentration e scadenza in GameState.next_turn).
2. Tiri Salvezza (pre-valutazione Adv/Dis senza consumare pending_hero_bonus su AoE create/resolve,
   Force Save, Save-Ends, Trappole non-magiche vs magiche, Spiriti Guardiani; preservazione
   source_name con copertura AoE).
3. Forma Selvatica assorbita con TS Concentrazione, Ira bilingue ("Ira"/"Rage") senza falsi positivi
   ("Ispirato") + Ira Incosciente Berserker, Fortuna Halfling vs talento Fortunato su TS contro Morte,
   pulizia bilingue 0->HP positivi (apply_damage, _apply_hp_change, Lay on Hands, Healer, Short Rest,
   Long Rest) e sincronia death_save_failures / full_sheet.
"""

import queue
import unittest
from unittest.mock import patch

from common.game_state import GameState, Player
from common.spell_effects_engine import cast_iconic_spell
from common.subclass_and_race_rules import _is_entity_raging, get_subclass_save_mods
from server.rules.character import _apply_player_long_rest
from server.rules.class_abilities import (
    handle_cast_special_spell_request,
    handle_healer_feat_request,
    handle_lay_on_hands_request,
)
from server.rules.combat import (
    _apply_hp_change,
    _evaluate_save_bonuses_and_flags,
    _process_save_result,
    apply_damage,
    drop_concentration,
    handle_death_save_request,
    handle_force_save_request,
    handle_short_rest_request,
)
from server.rules.map_interaction import handle_create_aoe_request, handle_resolve_aoe_request
from server.rules.movement import handle_move_request


def _mk_player(
    name: str,
    cls: str = "Mago",
    level: int = 5,
    hp: int = 30,
    max_hp: int = 30,
    party: bool = True,
    race: str = "Umano",
    pos=(0, 0),
    features=None,
    conditions=None,
    attrs=None,
    extra_sheet=None,
) -> Player:
    p = Player(name)
    p.is_party_member = party
    p.is_npc = not party
    p.char_class = cls
    p.level = level
    p.hp = hp
    p.max_hp = max_hp
    p.ac = 14
    p.race = race
    p.position = list(pos)
    p.conditions = list(conditions or [])
    p.features = list(features or [])
    p.in_combat = True
    p.attributes = dict(attrs or {"FOR": 10, "DES": 14, "COS": 14, "INT": 16, "SAG": 12, "CAR": 10})
    sheet = {
        "name": name,
        "char_class": cls,
        "level": level,
        "classes": {cls: level},
        "hp_current": hp,
        "hp_max": max_hp,
        "race": race,
        "attributes": dict(p.attributes),
        "features": list(p.features),
        "conditions": list(p.conditions),
        "spell_slots": {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 2, "max": 2}},
        "death_saves": {"successes": 0, "failures": 0},
        "hit_dice": "5d8",
        "hit_dice_max": 5,
        "hit_dice_current": 5,
        "hit_dice_pools": {"d8": {"current": 5, "max": 5}},
    }
    if extra_sheet:
        sheet.update(extra_sheet)
    p.full_sheet = sheet
    return p


class _DummyConn:
    def __init__(self):
        self.sent_packets = []


class TestPhase7RulesConcentrationSaves(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True
        self.gs.round_number = 1
        self.gs.automation_settings = {"strict_turn_lock": False, "auto_concentration_check": True}

    def test_handle_cast_special_spell_prior_concentration_drop_and_sync(self):
        caster = _mk_player("Gale", cls="Mago", level=5)
        ally = _mk_player("Shadowheart", cls="Chierico", level=5, pos=(1, 0))
        self.gs.add_player(caster)
        self.gs.add_player(ally)

        caster.concentrating_on = "Benedizione"
        caster.concentrating_spell = "Benedizione"
        caster.conditions.append("Concentrazione")
        ally.add_effect({"id": "bless_old", "name": "Benedizione", "concentration_caster": "Gale", "duration_rounds": 10})
        self.gs.active_aoes.append({"id": "old_aoe", "caster": "Gale", "concentration": True, "name": "Vecchia AoE", "origin": [0, 0], "size": 2})

        handle_cast_special_spell_request(
            {
                "spell_name": "Sfocatura",
                "base_level": 2,
                "cast_level": 2,
                "concentration": True,
                "duration": "1 minuto",
                "casting_time": "1 azione",
            },
            caster,
            self.gs,
        )

        self.assertEqual(self.gs.active_aoes, [])
        self.assertIsNone(ally.get_effect("bless_old"))
        self.assertEqual(caster.concentrating_on, "Sfocatura")
        self.assertEqual(caster.concentrating_spell, "Sfocatura")
        self.assertEqual(caster.full_sheet.get("concentrating_on"), "Sfocatura")
        self.assertEqual(caster.concentration_rounds_remaining, 10)
        self.assertIn("Concentrazione", caster.conditions)

    def test_all_iconic_concentration_spells_drop_prior_and_cleanup_on_break_and_expiry(self):
        caster = _mk_player("Mago", cls="Mago", level=9, attrs={"FOR": 10, "DES": 14, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10})
        enemy = _mk_player("Orco", cls="Guerriero", level=3, hp=40, max_hp=40, party=False, pos=(2, 0))
        self.gs.add_player(caster)
        self.gs.add_player(enemy)

        # 1. Blocca Persone (fail save -> Paralizzato + concentration_caster; drop clears Paralizzato)
        with patch("common.spell_effects_engine._roll_spell_effect_save", return_value=(False, 5)):
            cast_iconic_spell(caster, enemy, "Blocca Persone", 2, self.gs)
        self.assertIn("Concentrazione", caster.conditions)
        self.assertEqual(caster.concentrating_spell, "Blocca Persone")
        self.assertIn("Paralizzato", enemy.conditions)
        fx_hp = enemy.get_effect("hold_person")
        self.assertEqual(fx_hp.get("concentration_caster"), "Mago")

        # 2. Invisibilità Superiore su alleato/sé sostituisce Blocca Persone
        cast_iconic_spell(caster, enemy, "Invisibilità Superiore", 4, self.gs)
        self.assertNotIn("Paralizzato", enemy.conditions)
        self.assertIsNone(enemy.get_effect("hold_person"))
        self.assertTrue(getattr(enemy, "greater_invisibility", False))
        self.assertIn("Invisibile", enemy.conditions)

        # Drop concentration pulisce greater_invisibility e Invisibile + full_sheet
        drop_concentration(caster, self.gs, notify=False)
        self.assertFalse(getattr(enemy, "greater_invisibility", False))
        self.assertNotIn("Invisibile", enemy.conditions)
        self.assertNotIn("Invisibile", enemy.full_sheet.get("conditions", []))
        self.assertIsNone(caster.concentrating_on)
        self.assertIsNone(caster.concentrating_spell)

        # 3. Blur, Hunter's Mark, Hex, Heat Metal, Web, Spike Growth, Hunger of Hadar, Wall of Fire
        for sp_name, exp_attr in (
            ("Sfocatura", "blur_active"),
            ("Marchio del Cacciatore", "hunters_mark_target"),
            ("Sortilegio (Hex)", "hex_target"),
        ):
            cast_iconic_spell(caster, enemy, sp_name, 2, self.gs)
            self.assertIn("Concentrazione", caster.conditions)
            self.assertTrue(getattr(caster, exp_attr))
            drop_concentration(caster, self.gs, notify=False)
            self.assertFalse(getattr(caster, exp_attr))

        cast_iconic_spell(caster, enemy, "Riscaldare il Metallo", 2, self.gs)
        self.assertEqual(enemy.get_effect("heat_metal").get("concentration_caster"), "Mago")
        with patch("common.spell_effects_engine._roll_spell_effect_save", return_value=(False, 5)):
            cast_iconic_spell(caster, enemy, "Ragnatela", 2, self.gs)
        self.assertIsNone(enemy.get_effect("heat_metal"))
        self.assertIn("Trattenuto", enemy.conditions)
        self.assertEqual(len(self.gs.active_aoes), 1)

        # Scadenza in next_turn (fine round -> round_advanced=True) chiama drop_concentration e rimuove AoE/condizione/Concentrazione
        caster.concentration_rounds_remaining = 1
        self.gs.turn_index = 1
        self.gs.next_turn()
        self.assertEqual(self.gs.active_aoes, [])
        self.assertNotIn("Trattenuto", enemy.conditions)
        self.assertNotIn("Concentrazione", caster.conditions)
        self.assertIsNone(caster.concentrating_on)
        self.assertIsNone(caster.concentrating_spell)

        for sp_aoe in ("Crescita di Spine", "Fame di Hadar", "Muro di Fuoco"):
            cast_iconic_spell(caster, enemy, sp_aoe, 4, self.gs)
            self.assertIn("Concentrazione", caster.conditions)
            self.assertEqual(len(self.gs.active_aoes), 1)
        drop_concentration(caster, self.gs, notify=False)
        self.assertEqual(self.gs.active_aoes, [])

    def test_save_preeval_adv_dis_hero_points_and_aoe_cover_source_name(self):
        # Evocation wizard + Barbaro Lv2 con Danger Sense e Hero Point in copertura 1/2
        caster = _mk_player("Evoker", cls="Mago", level=5, pos=(0, 0), extra_sheet={"subclass": "Scuola di Invocazione"})
        barb = _mk_player(
            "Conan", cls="Barbaro", level=2, hp=30, max_hp=30, party=True, pos=(2, 0),
            attrs={"FOR": 16, "DES": 12, "COS": 14, "INT": 8, "SAG": 10, "CAR": 10},
        )
        barb.conn = _DummyConn()
        barb.pending_hero_bonus = 5
        npc_mr = _mk_player("Imp", cls="Mostro", level=3, hp=40, max_hp=40, party=False, pos=(2, 0), features=["Resistenza alla Magia"])
        self.gs.add_player(caster)
        self.gs.add_player(barb)
        self.gs.add_player(npc_mr)
        self.gs.current_map = {"hexes": {}, "half_cover": [[1, 0]], "three_quarters_cover": [], "grid_type": "hex"}

        # Hero Point non viene consumato dalla pre-valutazione
        ev = _evaluate_save_bonuses_and_flags(barb, "DES", game_state=self.gs, consume_hero_bonus=False)
        self.assertTrue(ev["has_advantage"])
        self.assertEqual(barb.pending_hero_bonus, 5)

        sent_packets = []
        with patch("server.rules.map_interaction.send_message", side_effect=lambda c, p: sent_packets.append(p)):
            rolled_formulas = []
            orig_roll = __import__("common.dice", fromlist=["roll_dice"]).roll_dice

            def _spy_roll(formula, *a, **kw):
                rolled_formulas.append(str(formula))
                return orig_roll(formula, *a, **kw)

            with patch("common.dice.roll_dice", side_effect=_spy_roll):
                handle_create_aoe_request(
                    {"aoe_data": {"type": "sfera", "origin": [0, 0], "size": 3, "stat": "DES", "dc": 15, "dmg": "10", "school": "Evocation", "is_spell": True, "req_save": True}},
                    caster,
                    self.gs,
                )

        # Source name preservato con copertura + has_advantage=True + Hero Point ancora intatto fino al TS
        self.assertEqual(len(sent_packets), 1)
        pdata = sent_packets[0]["data"]
        self.assertEqual(pdata["source_name"], "Evoker")
        self.assertEqual(pdata["dc"], 13)  # 15 - 2 mezza copertura
        self.assertTrue(pdata.get("has_advantage"))
        self.assertEqual(barb.pending_hero_bonus, 5)
        self.assertTrue(any("adv" in f for f in rolled_formulas))

        # _process_save_result consuma pending_hero_bonus senza doppio conteggio
        _process_save_result("Conan", "DES", 10, False, False, 15, "10", True, "Evoker", self.gs, "Fuoco", cover="half")
        self.assertEqual(barb.pending_hero_bonus, 0)

        # handle_resolve_aoe_request & handle_force_save_request applicano Adv/Dis anche a NPC
        sent_fs = []
        npc_mr.conditions = []
        restrained_pc = _mk_player("MagoRestr", cls="Mago", level=5, party=True, conditions=["Trattenuto"])
        restrained_pc.conn = _DummyConn()
        self.gs.add_player(restrained_pc)
        with patch("server.rules.combat.send_message", side_effect=lambda c, p: sent_fs.append(p)):
            with patch("server.rules.combat.roll_dice", return_value={"total": 12, "rolls": [12]}) as m_roll_fs:
                handle_force_save_request(
                    {"targets": ["Imp", "MagoRestr"], "stat": "DES", "dc": 14, "damage_formula": "4", "is_spell": True},
                    None,
                    self.gs,
                )
        self.assertEqual(sent_fs[0]["data"].get("has_disadvantage"), True)
        self.assertTrue(any("adv" in str(c.args[0]) for c in m_roll_fs.call_args_list))

        # Save-Ends e Spiriti Guardiani (Conjuration: Magic Resistance dà Advantage sul TS)
        npc_mr.add_effect({"id": "hold_person", "name": "Paralizzato", "duration_rounds": 5, "save_ends": {"stat": "SAG", "dc": 15, "timing": "end_of_turn"}, "source": "Evoker"})
        caster.add_effect({"id": "spirit_guardians", "name": "Spiriti Guardiani", "duration_rounds": 10})
        enemy_sg = _mk_player("NemicoSG", cls="Mostro", level=3, pos=(1, 0), party=False, features=["Resistenza alla Magia"])
        self.gs.add_player(enemy_sg)
        self.gs.players = [npc_mr, enemy_sg, caster]
        self.gs.turn_index = 0
        with patch("server.rules.combat.roll_dice", return_value={"total": 4, "rolls": [4]}) as m_sg_roll:
            with patch("server.rules.combat.threading.Timer"):
                from server.rules.combat import advance_combat_turn
                advance_combat_turn(self.gs, ending_player=npc_mr)
        self.assertTrue(any("adv" in str(c.args[0]) for c in m_sg_roll.call_args_list))
        self.assertLess(enemy_sg.hp, enemy_sg.max_hp)

        # Trappola NON magica non concede Magic Resistance advantage; Dodge sì; trappola magica sì
        self.gs.current_map = {
            "walls": [],
            "traps": [
                {"q": 1, "r": 0, "name": "Fossa Meccanica", "dc": 14, "damage": "1d6", "damage_type": "Perforante", "is_magic": False},
                {"q": 2, "r": 0, "name": "Runa Esplosiva", "dc": 14, "damage": "1d6", "damage_type": "Fuoco", "is_magic": True},
            ],
        }
        npc_mr.position = [0, 0]
        npc_mr.movement_spent_this_turn = 0
        with patch("common.dice.roll_dice", return_value={"total": 15, "rolls": [15]}) as m_trap_mech:
            handle_move_request({"to": [1, 0]}, npc_mr, self.gs)
        self.assertFalse(any("adv" in str(c.args[0]) for c in m_trap_mech.call_args_list if "1d20" in str(c.args[0])))

        with patch("common.dice.roll_dice", return_value={"total": 15, "rolls": [15]}) as m_trap_mag:
            handle_move_request({"to": [2, 0]}, npc_mr, self.gs)
        self.assertTrue(any("adv" in str(c.args[0]) for c in m_trap_mag.call_args_list if "1d20" in str(c.args[0])))

        # handle_resolve_aoe_request applica Vantaggio/Svantaggio sui bersagli nell'AoE
        if restrained_pc not in self.gs.players:
            self.gs.add_player(restrained_pc)
        sent_res = []
        with patch("server.rules.map_interaction.send_message", side_effect=lambda c, p: sent_res.append(p)):
            handle_resolve_aoe_request(
                {"aoe_index": 0, "stat": "DES", "dc": 14, "damage_formula": "6"},
                caster,
                self.gs,
            )
        res_by_dis = [pkt["data"].get("has_disadvantage") for pkt in sent_res if pkt.get("type") == "PROMPT_SAVE"]
        self.assertTrue(any(res_by_dis))

    def test_wild_shape_absorbed_hit_triggers_concentration_save(self):
        druid = _mk_player("Halsin", cls="Druido", level=5, hp=24, max_hp=24)
        druid.wild_shape = {"active": True, "beast_hp": 24, "beast_max_hp": 24, "original_hp": 30, "original_max_hp": 30, "original_ac": 14, "original_speed": 30}
        druid.concentrating_on = "Intralciare"
        druid.conditions.append("Concentrazione")
        self.gs.add_player(druid)

        with patch("server.rules.combat._trigger_concentration_check") as m_conc:
            apply_damage(druid, 10, "Tagliente", self.gs)
        self.assertEqual(druid.wild_shape["beast_hp"], 14)
        m_conc.assert_called_once()
        self.assertEqual(m_conc.call_args[0][1], 10)

    def test_rage_bilingual_and_substring_safety(self):
        barb_en = _mk_player(
            "Grog", cls="Barbaro", level=6, hp=60, max_hp=60,
            conditions=["Rage"], extra_sheet={"subclass": "Berserker"},
        )
        fin, _, _, _ = apply_damage(barb_en, 10, "Tagliente", self.gs)
        self.assertEqual(fin, 5)
        self.assertTrue(_is_entity_raging(barb_en))
        mods = get_subclass_save_mods(barb_en, None, "SAG", effect_tags=("Frightened",))
        self.assertTrue(mods["immune"])

        inspired = _mk_player("Bardo", cls="Bardo", level=5, hp=30, max_hp=30, conditions=["Ispirato"])
        self.assertFalse(_is_entity_raging(inspired))
        fin_i, _, _, _ = apply_damage(inspired, 10, "Tagliente", self.gs)
        self.assertEqual(fin_i, 10)

    def test_death_save_halfling_luck_vs_lucky_feat_and_zero_hp_cleanup(self):
        # Umano con talento "Fortunato (Lucky)" NON ritira automaticamente l'1 naturale sul TS contro la Morte
        human_lucky = _mk_player("Umano", hp=0, max_hp=20, race="Umano", features=["Fortunato (Lucky)"], conditions=["Incosciente"])
        self.gs.add_player(human_lucky)
        with patch("server.rules.combat.random.randint", side_effect=[1, 18]):
            handle_death_save_request({}, human_lucky, self.gs)
        self.assertEqual(human_lucky.death_saves["failures"], 2)

        # Halfling ritira l'1 naturale (1 -> 18 -> 1 successo!)
        halfling = _mk_player("Bilbo", hp=0, max_hp=20, race="Halfling", conditions=["Incosciente"])
        self.gs.add_player(halfling)
        with patch("server.rules.combat.random.randint", side_effect=[1, 18]):
            handle_death_save_request({}, halfling, self.gs)
        self.assertEqual(halfling.death_saves["failures"], 0)
        self.assertEqual(halfling.death_saves["successes"], 1)

        # Danno a 0 HP sincronizza death_save_failures e full_sheet["death_saves"]
        apply_damage(halfling, 3, "Tagliente", self.gs)
        self.assertEqual(halfling.death_saves["failures"], 1)
        self.assertEqual(halfling.death_save_failures, 1)
        self.assertEqual(halfling.full_sheet["death_saves"]["failures"], 1)

        _apply_hp_change(halfling, -5, self.gs)
        self.assertEqual(halfling.death_saves["failures"], 2)
        self.assertEqual(halfling.death_save_failures, 2)
        self.assertEqual(halfling.full_sheet["death_saves"]["failures"], 2)

        # Recupero 0 -> >0 HP pulisce condizioni IT+EN e azzera death_saves in tutti i percorsi
        paladin = _mk_player("Paladino", cls="Paladino", level=4, features=["Guaritore"], extra_sheet={"custom_resources": [{"name": "Mani Curative", "current": 20, "max": 20}]})
        self.gs.add_player(paladin)

        def _reset_to_zero_en():
            halfling.hp = 0
            halfling.conditions = ["Unconscious", "Stable", "Prono"]
            halfling.death_saves = {"successes": 2, "failures": 2}
            halfling.death_save_successes = 2
            halfling.death_save_failures = 2
            halfling.full_sheet["conditions"] = list(halfling.conditions)
            halfling.full_sheet["death_saves"] = dict(halfling.death_saves)

        def _assert_cleared():
            self.assertGreater(halfling.hp, 0)
            for tag in ("Incosciente", "Unconscious", "Stabilizzato", "Stable"):
                self.assertNotIn(tag, halfling.conditions)
                self.assertNotIn(tag, halfling.full_sheet.get("conditions", []))
            self.assertEqual(halfling.death_saves, {"successes": 0, "failures": 0})
            self.assertEqual(halfling.death_save_successes, 0)
            self.assertEqual(halfling.death_save_failures, 0)
            self.assertEqual(halfling.full_sheet["death_saves"], {"successes": 0, "failures": 0})

        _reset_to_zero_en()
        _apply_hp_change(halfling, 5, self.gs)
        _assert_cleared()

        _reset_to_zero_en()
        handle_lay_on_hands_request({"target_name": "Bilbo", "mode": "heal", "amount": 5}, paladin, self.gs)
        _assert_cleared()

        _reset_to_zero_en()
        paladin.has_acted_this_turn = False
        handle_healer_feat_request({"target_name": "Bilbo"}, paladin, self.gs)
        _assert_cleared()

        _reset_to_zero_en()
        self.gs.combat_active = False
        handle_short_rest_request({"die_counts": {"d6": 1}, "hp_recovered": 4}, halfling, self.gs)
        _assert_cleared()

        _reset_to_zero_en()
        _apply_player_long_rest(halfling, self.gs)
        _assert_cleared()
        self.assertNotIn("Prono", halfling.conditions)


if __name__ == "__main__":
    unittest.main()
