"""
tests/test_phase7_combat_subclasses_monsters.py - TASK-052 Regression Suite.

Verifica le correzioni D&D 5e (2014 RAW) di Phase 7 su:
1. _get_entity_max_attacks multiclasse (Fighter 1-4 dip + Extra Attack da altra classe) e rollback azione su fuori portata.
2. Absorb Elements preservato su mancato e consumato solo su colpo in mischia a segno (pulisce remove_effect("absorb_elements")).
3. Ordine compute_combat_spell_modifiers prima di Allerta, Vista del Vero (Truesight), Sensi Ferini ed Elusivo.
4. Deduplicazione Uccisore di Colossi (Colossus Slayer) su un singolo +1d8 per turno.
5. Mage Armor & Corrosione Armatura sincronizzati in full_sheet["ac"] e combattimento; Cutting Words trova target via find_player e riduce hit_roll.
6. Reset booleani di sottoclasse a Riposo Breve/Lungo e Interdizione Arcana su Abjurer al Riposo Lungo.
7. Parità execute_monster_multiattack (full_sheet["ac"], Scudo/Velocità/Lentezza/Difesa Attacchi Multipli, Armi Magiche, condizioni Adv/Dis, auto-crit 1,5m) + LR "Sistema (Concentrazione" + Pietrificazione Stadio 1 a fine turno + Elemental Adept / is_spell su multi-raggio & Dardo Incantato.
"""

import queue
import unittest
from unittest.mock import patch

from common.character_schema import restore_entity_rest_resources
from common.game_state import GameState, Player
from common.spell_effects_engine import cast_iconic_spell
from common.subclass_and_race_rules import get_subclass_damage_mods, handle_subclass_active_power
from server.dm_monster_engine import (
    apply_monster_special_hit_effects,
    check_petrifying_gaze_at_turn_start,
    execute_monster_multiattack,
    handle_resolve_legendary_resistance_request,
)
from server.rules.character import _apply_player_long_rest
from server.rules.class_abilities import handle_cast_special_spell_request
from server.rules.combat import (
    _get_entity_max_attacks,
    advance_combat_turn,
    handle_attack_request,
)


def _mk(
    name: str,
    cls: str = "Guerriero",
    level: int = 5,
    hp: int = 50,
    max_hp: int = 50,
    ac: int = 15,
    party: bool = True,
    pos=(0, 0),
    features=None,
    conditions=None,
    classes=None,
    attrs=None,
    extra=None,
) -> Player:
    p = Player(name)
    p.is_party_member = party
    p.is_npc = not party
    p.char_class = cls
    p.level = level
    p.hp = hp
    p.max_hp = max_hp
    p.ac = ac
    p.position = list(pos)
    p.conditions = list(conditions or [])
    p.features = list(features or [])
    p.in_combat = True
    p.attributes = dict(attrs or {"FOR": 16, "DES": 14, "COS": 14, "INT": 14, "SAG": 12, "CAR": 14})
    cls_map = dict(classes or {cls: level})
    sheet = {
        "name": name,
        "char_class": cls,
        "level": sum(cls_map.values()),
        "classes": cls_map,
        "ac": ac,
        "hp_current": hp,
        "hp_max": max_hp,
        "attributes": dict(p.attributes),
        "features": list(p.features),
        "conditions": list(p.conditions),
        "spell_slots": {"1": {"current": 4, "max": 4}, "2": {"current": 3, "max": 3}, "3": {"current": 2, "max": 2}},
    }
    if extra:
        sheet.update(extra)
    p.full_sheet = sheet
    return p


class TestPhase7CombatSubclassesMonsters(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True
        self.gs.round_number = 1
        self.gs.automation_settings = {"strict_turn_lock": True, "auto_calc_advantage": True, "auto_apply_damage": True}

    def test_multiclass_extra_attack_takes_max_over_fighter_dip_and_range_rollback(self):
        f2_b5 = _mk("MulticlasseFB", cls="Barbaro", classes={"Guerriero": 2, "Barbaro": 5}, pos=(0, 0))
        self.assertEqual(_get_entity_max_attacks(f2_b5), 2)

        f2_bard6 = _mk("FighterValor", cls="Bardo", classes={"Guerriero": 2, "Bardo": 6}, extra={"subclass": "Collegio del Valore"})
        self.assertEqual(_get_entity_max_attacks(f2_bard6), 2)

        f2_wiz6 = _mk("FighterBladesinger", cls="Mago", classes={"Fighter": 2, "Wizard": 6}, extra={"subclass": "Cantore della Lama (Bladesinging)"})
        self.assertEqual(_get_entity_max_attacks(f2_wiz6), 2)

        f11_p5 = _mk("Fighter11Pal5", cls="Guerriero", classes={"Guerriero": 11, "Paladino": 5})
        self.assertEqual(_get_entity_max_attacks(f11_p5), 3)

        # Out-of-range ranged attack (> max range) restores action economy flags
        target = _mk("BersaglioLontano", party=False, pos=(200, 0))
        self.gs.players = [f2_b5, target]
        self.gs.turn_index = 0
        handle_attack_request(
            {"target_name": "BersaglioLontano", "weapon_name": "Pugnale da Lancio", "hit_bonus": 5, "damage_formula": "1d4+3", "is_ranged": True, "is_bonus_action": True},
            f2_b5,
            self.gs,
        )
        self.assertFalse(f2_b5.bonus_action_used_this_turn)
        self.assertFalse(f2_b5.has_acted_this_turn)
        self.assertEqual(getattr(f2_b5, "attacks_made_this_turn", 0), 0)

    def test_absorb_elements_preserved_on_miss_and_consumed_on_hit(self):
        att = _mk("MagoGuerriero", pos=(0, 0))
        att.absorb_elements_dice = 2
        att.absorb_elements_type = "Fuoco"
        att.conditions.append("Assorbire Elementi (Fuoco)")
        att.add_effect({"id": "absorb_elements", "name": "Assorbire Elementi (Fuoco, +2d6)", "duration_rounds": 1})
        tgt = _mk("Orco", ac=18, hp=40, max_hp=40, party=False, pos=(1, 0))
        self.gs.players = [att, tgt]
        self.gs.turn_index = 0
        self.gs.automation_settings["strict_turn_lock"] = False

        # Miss: 2 + 3 = 5 < 18 -> must NOT consume absorb_elements_dice / effect / condition!
        with patch("server.rules.combat.random.randint", return_value=2):
            handle_attack_request({"target_name": "Orco", "weapon_name": "Spada Lunga", "hit_bonus": 3, "damage_formula": "1d8+2"}, att, self.gs)
        self.assertEqual(att.absorb_elements_dice, 2)
        self.assertIsNotNone(att.get_effect("absorb_elements"))
        self.assertEqual(tgt.hp, 40)

        # Hit: 18 + 3 = 21 >= 18 -> deals extra 2d6 and consumes absorb_elements_dice + effect!
        with patch("server.rules.combat.random.randint", return_value=18):
            with patch("server.rules.combat.roll_dice", side_effect=[
                {"total": 5, "rolls": [5], "rerolled_notes": []},
                {"total": 9, "rolls": [4, 5], "rerolled_notes": []},
            ]):
                handle_attack_request({"target_name": "Orco", "weapon_name": "Spada Lunga", "hit_bonus": 3, "damage_formula": "1d8+2"}, att, self.gs)
        self.assertEqual(att.absorb_elements_dice, 0)
        self.assertIsNone(att.get_effect("absorb_elements"))
        self.assertEqual(tgt.hp, 26)  # 40 - (5 + 9)

    def test_spell_modifiers_before_alert_truesight_feral_elusive_and_colossus_dedup(self):
        self.gs.automation_settings["strict_turn_lock"] = False
        att = _mk("Assassino", cls="Ranger", level=18, pos=(0, 0), features=["Uccisore di Colossi", "Sensi Ferini (Feral Senses)"], extra={"subclass": "Cacciatore"})
        att.greater_invisibility = True

        # 1. Target con Allerta -> sopprime vantaggio da Invisibilità dell'attaccante (d20 chiamato 1 volta sola o non max)
        tgt_alert = _mk("Sentinella", ac=12, hp=40, max_hp=40, party=False, pos=(1, 0), features=["Allerta (Alert)"])
        self.gs.players = [att, tgt_alert]
        with patch("server.rules.combat.broadcast") as m_bc:
            with patch("server.rules.combat.random.randint", return_value=15):
                handle_attack_request({"target_name": "Sentinella", "weapon_name": "Spada Lunga", "hit_bonus": 5, "damage_formula": "1"}, att, self.gs)
        chat_logs = [str(c.args[1]["data"]["text"]) for c in m_bc.call_args_list if c.args[1].get("type") == "CHAT_BROADCAST"]
        self.assertFalse(any("Tiro con Vantaggio" in lg for lg in chat_logs))

        # 2. Target con Vista del Vero (Truesight) + Sfocatura sopprime sia Invisibile dell'attaccante sia Blur del bersaglio!
        tgt_ts = _mk("Angelo", ac=12, hp=40, max_hp=40, party=False, pos=(1, 0), features=["Vista del Vero (Truesight)"])
        tgt_ts.blur_active = True
        att_ts = _mk("TruesightAtt", cls="Ranger", level=18, pos=(0, 0), features=["Vista del Vero (Truesight)"])
        att_ts.greater_invisibility = True
        self.gs.players = [att_ts, tgt_ts]
        with patch("server.rules.combat.broadcast") as m_bc2:
            with patch("server.rules.combat.random.randint", return_value=15):
                handle_attack_request({"target_name": "Angelo", "weapon_name": "Spada Lunga", "hit_bonus": 5, "damage_formula": "1"}, att_ts, self.gs)
        chat_logs2 = [str(c.args[1]["data"]["text"]) for c in m_bc2.call_args_list if c.args[1].get("type") == "CHAT_BROADCAST"]
        self.assertFalse(any("Vantaggio" in lg or "Svantaggio" in lg for lg in chat_logs2))

        # 3. Target Elusivo (Ladro 18+) sopprime vantaggio da greater_invisibility
        att_gi = _mk("Invis", pos=(0, 0))
        att_gi.greater_invisibility = True
        tgt_elusive = _mk("Ladro18", cls="Ladro", level=18, ac=12, hp=40, max_hp=40, party=False, pos=(1, 0))
        self.gs.players = [att_gi, tgt_elusive]
        with patch("server.rules.combat.broadcast") as m_bc3:
            with patch("server.rules.combat.random.randint", return_value=15):
                handle_attack_request({"target_name": "Ladro18", "weapon_name": "Pugnale", "hit_bonus": 5, "damage_formula": "1"}, att_gi, self.gs)
        chat_logs3 = [str(c.args[1]["data"]["text"]) for c in m_bc3.call_args_list if c.args[1].get("type") == "CHAT_BROADCAST"]
        self.assertFalse(any("Tiro con Vantaggio" in lg for lg in chat_logs3))

        # 4. Colossus Slayer non viene applicato 2 volte dallo stesso colpo
        ranger = _mk("Hunter", cls="Ranger", level=5, pos=(0, 0), features=["Uccisore di Colossi"], extra={"subclass": "Cacciatore"})
        wounded = _mk("TrollFerito", ac=10, hp=30, max_hp=40, party=False, pos=(1, 0))
        self.gs.players = [ranger, wounded]
        with patch("server.rules.combat.random.randint", return_value=15):
            with patch("server.rules.combat.roll_dice", side_effect=[
                {"total": 5, "rolls": [5], "rerolled_notes": []},  # base 1d8
                {"total": 6, "rolls": [6], "rerolled_notes": []},  # colossus 1d8
            ]):
                handle_attack_request({"target_name": "TrollFerito", "weapon_name": "Arco Lungo", "hit_bonus": 5, "damage_formula": "1d8"}, ranger, self.gs)
        self.assertEqual(wounded.hp, 19)  # 30 - (5 + 6), solo 1x Colossus Slayer
        sub_dmg = get_subclass_damage_mods(ranger, wounded, is_weapon_attack=True)
        self.assertEqual(sub_dmg["dice_formulas"], [])

    def test_mage_armor_rust_armor_full_sheet_sync_and_cutting_words(self):
        wiz = _mk("Gale", cls="Mago", level=5, ac=10, attrs={"FOR": 8, "DES": 16, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10}, pos=(0, 0))
        cast_iconic_spell(wiz, wiz, "Armatura Magica", 1, self.gs)
        self.assertEqual(wiz.ac, 16)
        self.assertEqual(wiz.full_sheet["ac"], 16)

        # Corrosione armatura riduce sia target.ac che target.full_sheet["ac"]
        rust_m = _mk("Ruggine", cls="Mostro", party=False, pos=(1, 0), features=["Corrodere il Metallo"])
        knight = _mk("Cavaliere", ac=18, party=True, pos=(0, 0))
        notes = apply_monster_special_hit_effects(rust_m, knight, "Antenne", "corrode metal antennae", 0, game_state=self.gs)
        self.assertTrue(any("CORROSIONE" in n for n in notes))
        self.assertEqual(knight.ac, 17)
        self.assertEqual(knight.full_sheet["ac"], 17)

        # Cutting Words tramite find_player applica penalità al hit_roll
        bard = _mk("LoreBard", cls="Bardo", level=5, party=True, extra={"subclass": "Collegio della Sapienza", "custom_resources": [{"name": "Ispirazione Bardica", "current": 3, "max": 3}]})
        orco = _mk("Orco", ac=12, party=False, pos=(1, 0))
        self.gs.players = [bard, knight, orco]
        self.gs.automation_settings["strict_turn_lock"] = False
        with patch("common.subclass_and_race_rules.random.randint", return_value=5):
            cw_res = handle_subclass_active_power(bard, "cutting_words", self.gs, {"target": "Orco"})
        self.assertTrue(cw_res["ok"])
        self.assertEqual(orco.cutting_words_penalty, 5)
        # Orco d20=15 + 4 = 19, con -5 Cutting Words = 14 < CA 17 di knight -> MANCA!
        with patch("server.rules.combat.random.randint", return_value=15):
            handle_attack_request({"target_name": "Cavaliere", "weapon_name": "Ascia", "hit_bonus": 4, "damage_formula": "8"}, orco, self.gs)
        self.assertEqual(knight.hp, 50)
        self.assertEqual(orco.cutting_words_penalty, 0)

    def test_rest_resets_subclass_booleans_and_abjurer_arcane_ward(self):
        wl = _mk("Wyll", cls="Warlock", level=6, extra={"subclass": "Hexblade", "benign_transposition_used": True})
        for fl in ("hexblade_curse_used", "fey_presence_used", "misty_escape_used", "entropic_ward_used", "illusory_self_used", "benign_transposition_used"):
            setattr(wl, fl, True)
            wl.full_sheet[fl] = True
        wl.hexblade_curse_target = "Goblin"
        wl.full_sheet["hexblade_curse_target"] = "Goblin"

        restore_entity_rest_resources(wl, rest_type="short")
        for fl in ("hexblade_curse_used", "fey_presence_used", "misty_escape_used", "entropic_ward_used", "illusory_self_used"):
            self.assertFalse(getattr(wl, fl))
            self.assertFalse(wl.full_sheet[fl])
        self.assertIsNone(wl.hexblade_curse_target)
        self.assertTrue(wl.benign_transposition_used)

        restore_entity_rest_resources(wl, rest_type="long")
        self.assertFalse(wl.benign_transposition_used)
        self.assertFalse(wl.full_sheet["benign_transposition_used"])

        abj = _mk("Abiuratore", cls="Mago", level=5, attrs={"FOR": 8, "DES": 12, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10}, extra={"subclass": "Scuola di Abiurazione"})
        abj.arcane_ward_hp = 2
        abj.full_sheet["arcane_ward_hp"] = 2
        _apply_player_long_rest(abj, self.gs)
        self.assertEqual(abj.arcane_ward_hp, 14)  # 2 * 5 + 4 INT
        self.assertEqual(abj.full_sheet["arcane_ward_hp"], 14)

    def test_monster_multiattack_lr_prefix_petrification_turn_end_and_multiray_spells(self):
        # 1. execute_monster_multiattack legge full_sheet["ac"], Shield +5, Magic Weapons, Auto-Crit 1.5m vs Paralizzato
        knight = _mk("Difensore", ac=10, hp=60, max_hp=60, party=True, pos=(1, 0), conditions=["Scudo", "Paralizzato"], extra={"ac": 14})
        dragon = _mk(
            "Demone", cls="Mostro", party=False, pos=(0, 0), features=["Armi Magiche (Magic Weapons)"],
            extra={
                "multiattack": "Multiattack: makes two claw attacks",
                "actions": [
                    {"name": "Multiattack", "desc": "The demon makes two claw attacks."},
                    {"name": "Claw", "desc": "Melee Weapon Attack: +6 to hit, reach 5 ft., one target. Hit: 10 (2d6 + 3) slashing damage."},
                ],
            },
        )
        knight.damage_resistances = ["tagliente"]
        self.gs.players = [dragon, knight]
        # d20=14 + 6 = 20 vs CA 19 (14 full_sheet + 5 Scudo) -> COLPITO + Auto-Crit 2d6 extra + bypass resistenza nonmagica!
        with patch("server.dm_monster_engine.roll_dice", return_value={"total": 14, "rolls": [14]}):
            res = execute_monster_multiattack(dragon, game_state=self.gs, target=knight)
        self.assertTrue(res["ok"])
        self.assertTrue(all(r["is_crit"] and r["hit"] for r in res["rolls"]))
        self.assertLess(knight.hp, 60)

        # 2. LR "Sistema (Concentrazione - Svantaggio Sterminatore di Maghi)" spezza concentrazione
        caster = _mk("Elminster", hp=50, max_hp=50)
        caster.concentrating_on = "Muro di Fuoco"
        caster.conditions = ["Concentrazione"]
        caster.legendary_resistances_current = 1
        self.gs.players = [caster]
        self.gs.pending_legendary_resistances = {
            "lr_1": {
                "target": "Elminster", "stat": "COS", "dc": 15, "source": "Sistema (Concentrazione - Svantaggio Sterminatore di Maghi)",
                "deferred_save": {"source_name": "Sistema (Concentrazione - Svantaggio Sterminatore di Maghi)", "raw_damage": 0},
            }
        }
        handle_resolve_legendary_resistance_request({"pending_id": "lr_1", "decision": "decline"}, None, self.gs)
        self.assertIsNone(caster.concentrating_on)
        self.assertNotIn("Concentrazione", caster.conditions)

        # 3. Pietrificazione Stadio 1 ripete il TS a fine turno -> Stadio 2 Pietrificato se fallisce
        medusa = _mk("Medusa", party=False, pos=(1, 0), extra={"traits": [{"name": "Sguardo Pietrificante", "desc": "CD 14 COS"}]})
        victim = _mk("Vittima", hp=40, max_hp=40, party=True, pos=(0, 0), attrs={"FOR": 10, "DES": 10, "COS": 10, "INT": 10, "SAG": 10, "CAR": 10})
        self.gs.players = [victim, medusa]
        self.gs.turn_index = 0
        self.gs.automation_settings["strict_turn_lock"] = False
        check_petrifying_gaze_at_turn_start(victim, self.gs, forced_roll=5)
        self.assertEqual(victim.petrification_stage, 1)
        self.assertIn("Trattenuto", victim.conditions)
        with patch("server.dm_monster_engine.roll_dice", return_value={"total": 4, "rolls": [4]}):
            advance_combat_turn(self.gs, ending_player=victim)
        self.assertEqual(victim.petrification_stage, 2)
        self.assertIn("Pietrificato", victim.conditions)

        # 4. Scorching Ray & Magic Missile & Eldritch Blast passano is_spell=True e Elemental Adept senza mutare target.damage_resistances
        pyro = _mk("Pyro", cls="Mago", level=5, features=["Adepto Elementale (Fuoco)"])
        fiend = _mk("Diavolo", hp=100, max_hp=100, ac=10, party=False)
        fiend.damage_resistances = ["fuoco"]
        self.gs.players = [pyro, fiend]
        _orig_ad = __import__("server.rules.combat", fromlist=["apply_damage"]).apply_damage
        with patch("server.rules.combat.apply_damage", wraps=_orig_ad) as m_ad:
            with patch("server.rules.class_abilities.roll_dice", return_value={"total": 15, "rolls": [15], "natural_roll": 15}):
                handle_cast_special_spell_request(
                    {"spell_name": "Raggio Rovente", "target_name": "Diavolo", "base_level": 2, "cast_level": 2},
                    pyro,
                    self.gs,
                )
        self.assertEqual(fiend.damage_resistances, ["fuoco"])
        self.assertTrue(any(c.kwargs.get("is_spell") and c.kwargs.get("ignore_resistance") and c.kwargs.get("attacker") is pyro for c in m_ad.call_args_list))

        with patch("server.rules.combat.apply_damage", wraps=_orig_ad) as m_mm:
            pyro.has_acted_this_turn = False
            handle_cast_special_spell_request(
                {"spell_name": "Dardo Incantato", "target_name": "Diavolo", "base_level": 1, "cast_level": 1},
                pyro,
                self.gs,
            )
        self.assertTrue(any(c.kwargs.get("is_spell") and c.kwargs.get("attacker") is pyro for c in m_mm.call_args_list))


if __name__ == "__main__":
    unittest.main()
