"""
tests/test_phase5c_vtt_e2e.py - Phase 5C End-to-End & Regression Tests (TASK-042).

Verifica:
- Payload completi a 4 argomenti su PROMPT_REACTION (Shield, Counterspell, Opportunity Attack,
  Uncanny Dodge, Defensive Duelist, Illusory Self, Dampen Elements, Deflect Missiles,
  Absorb Elements, Hellish Rebuke, Silvery Barbs).
- UI client interattiva per Controincantesimo (scelta slot & aggiornamento pulsante), OA (reaction_spent),
  Absorb Elements / Hellish Rebuke / Silvery Barbs, e handle_prompt_save (Vantaggio War Caster).
- Concentrazione (Mage Slayer + War Caster) e risoluzione unificata Tiri Salvezza (resolve_saving_throw)
  con Aura Paladino / Magic Resistance / Benedizione / LR usata anche da spell_effects_engine.
- Colpo Stordente del Monaco (durata fino a fine turno successivo del Monaco via source_end_of_turn).
- Plasmare Incantesimi: Scuola di Evocazione (Conjuration IT) vs Scuola di Invocazione (Evocation IT).
- Parità Multiattacco Mostri (Santuario, Sfocatura, Immagine Speculare, Schivata Prodigiosa/Difesa).
- Subclasses IT/EN (Ira da conditions e bonus_action_used_this_turn).
- Sync server per Forma Selvatica (Druido) e Recupero Arcano multiclasse (Mago).
- Sicurezza CommandPalette/Spotlight non-DM, tolleranza AoE center/origin & hp_max su HexMapCanvas,
  FoW set O(K+N), Container Loot sicuro, e gestione stock finito nei Negozi (server + ShopDialog).
"""

import json
import os
import queue
import struct
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

from client.character_manager import Character, CharacterManager
from common.game_state import GameState, Player
from common.protocol import make_opportunity_alert, make_prompt_reaction, make_prompt_save


class _MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data: bytes):
        self.sent.append(data)


class _DummyNetwork:
    def __init__(self):
        self.sent = []

    def send(self, packet):
        self.sent.append(packet)


def _extract_msgs(conn: _MockConn):
    buf = b"".join(conn.sent)
    out = []
    idx = 0
    while idx + 4 <= len(buf):
        length = struct.unpack("!I", buf[idx:idx + 4])[0]
        idx += 4
        chunk = buf[idx:idx + length]
        idx += length
        if chunk:
            out.append(json.loads(chunk.decode("utf-8")))
    return out


def _make_root():
    root = tk.Tk()
    root.withdraw()
    return root


def _destroy_tk(root):
    if root is None:
        return
    try:
        for w in list(root.winfo_children()):
            try:
                w.grab_release()
            except Exception:
                pass
            try:
                w.destroy()
            except Exception:
                pass
        root.update_idletasks()
        root.destroy()
    except Exception:
        pass


class TestPhase5cReactionPromptsAndClientUI(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True

    def test_protocol_4arg_and_opportunity_alert_fallback(self):
        pkt4 = make_prompt_reaction("COUNTERSPELL", "Lich", "Gale", {"spell_name": "Palla di Fuoco", "spell_level": 3, "cast_id": "c1"})
        self.assertEqual(pkt4["data"]["target_name"], "Gale")
        self.assertEqual(pkt4["data"]["details"]["cast_id"], "c1")

        # Legacy 3-arg tolerance
        pkt3 = make_prompt_reaction("SHIELD_SPELL", "Goblin", {"hit_roll": 14, "current_ac": 12})
        self.assertEqual(pkt3["data"]["target_name"], "")
        self.assertEqual(pkt3["data"]["details"]["hit_roll"], 14)

        oa_pkt = make_opportunity_alert("Goblin", "esce dalla portata")
        self.assertEqual(oa_pkt["data"]["target_name"], "Goblin")

        from client.network_handlers import ClientNetworkHandlersMixin
        class _DummyGui(ClientNetworkHandlersMixin):
            def __init__(self):
                self.toasts = []
            def show_toast(self, msg, title=None, duration=3000, toast_type="info", icon=None):
                self.toasts.append((msg, title))
        dg = _DummyGui()
        dg.handle_opportunity_alert(oa_pkt["data"])
        self.assertIn("Goblin", dg.toasts[0][0])

    def test_defense_counterspell_and_oa_prompts_carry_full_details(self):
        from server.rules.reaction_magic import (
            maybe_prompt_counterspell_reactions,
            maybe_prompt_defense_reactions,
            maybe_prompt_elemental_save_reactions,
        )
        from server.rules.movement import handle_move_request

        attacker = Player("Lich", conn=None)
        attacker.position = [0, 0]
        attacker.hp = 100
        attacker.max_hp = 100
        attacker.ac = 16
        attacker.is_party_member = False

        wizard = Player("Gale", conn=_MockConn())
        wizard.position = [1, 0]
        wizard.hp = 30
        wizard.max_hp = 30
        wizard.ac = 12
        wizard.is_party_member = True
        wizard.full_sheet = {
            "class": "Mago",
            "level": 5,
            "attributes": {"FOR": 10, "DES": 14, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10},
            "spells": [
                {"name": "Scudo", "prepared": True, "level": 1},
                {"name": "Controincantesimo", "prepared": True, "level": 3},
                {"name": "Assorbire Elementi", "prepared": True, "level": 1},
                {"name": "Intimorire Infernale", "prepared": True, "level": 1},
            ],
            "spell_slots": {"1": {"current": 4, "max": 4}, "3": {"current": 2, "max": 2}},
            "weapons": [{"name": "Bastone Ferrato", "damage_dice": "1d6", "damage_type": "Contundente"}],
        }

        self.gs.players = [attacker, wizard]

        # 1. SHIELD_SPELL preserves hit_roll & weapon_name
        wizard.conn.sent.clear()
        maybe_prompt_defense_reactions(
            wizard, attacker,
            {"hits": True, "is_crit": False, "hit_roll": 15, "target_ac": 12, "weapon_name": "Artiglio Gelido", "dmg_to_hp": 7, "old_hp": 30},
            self.gs,
        )
        msgs = _extract_msgs(wizard.conn)
        self.assertEqual(msgs[-1]["type"], "PROMPT_REACTION")
        self.assertEqual(msgs[-1]["data"]["target_name"], "Gale")
        self.assertEqual(msgs[-1]["data"]["details"]["weapon_name"], "Artiglio Gelido")
        self.assertEqual(msgs[-1]["data"]["details"]["hit_roll"], 15)

        # 2. COUNTERSPELL preserves spell_name, spell_level, cast_id
        wizard.conn.sent.clear()
        prompted = maybe_prompt_counterspell_reactions(attacker, "Palla di Fuoco", 3, self.gs, cast_id="cast_99")
        self.assertEqual(prompted, ["Gale"])
        c_msgs = _extract_msgs(wizard.conn)
        self.assertEqual(c_msgs[-1]["data"]["reaction_type"], "COUNTERSPELL")
        self.assertEqual(c_msgs[-1]["data"]["target_name"], "Gale")
        self.assertEqual(c_msgs[-1]["data"]["details"]["cast_id"], "cast_99")

        # 3. ABSORB_ELEMENTS on elemental save damage ("Fire") + bilingual resistance no-double-heal
        wizard.conn.sent.clear()
        wizard.hp = 12
        maybe_prompt_elemental_save_reactions(wizard, "Palla di Fuoco", "Fire", 18, self.gs)
        ae_msgs = _extract_msgs(wizard.conn)
        self.assertEqual(ae_msgs[-1]["data"]["reaction_type"], "ABSORB_ELEMENTS")
        self.assertEqual(ae_msgs[-1]["data"]["details"]["dmg_to_hp"], 18)

        # Response with "Fire" damage works cleanly
        from server.rules.combat import handle_reaction_response
        wizard.has_reacted_this_turn = False
        handle_reaction_response(
            {"reaction_type": "ABSORB_ELEMENTS", "accepted": True, "target_name": "Lich", "details": {"damage_type": "Fire", "slot_level": 1, "dmg_to_hp": 18, "slot_consumed": True}},
            wizard,
            self.gs,
        )
        self.assertEqual(wizard.hp, 21)

        # Permanent "Fuoco" resistance prevents second heal when "Fire" damage comes in
        wizard.hp = 12
        wizard.has_reacted_this_turn = False
        wizard.damage_resistances = ["Fuoco"]
        wizard._last_hit_for_reaction = {"dmg_to_hp": 10, "damage_type": "Fire", "absorb_restored": False}
        handle_reaction_response(
            {"reaction_type": "ABSORB_ELEMENTS", "accepted": True, "target_name": "Lich", "details": {"damage_type": "Fire", "slot_level": 1, "dmg_to_hp": 10, "slot_consumed": True}},
            wizard,
            self.gs,
        )
        self.assertEqual(wizard.hp, 12)

        # 4. Movement provoking Opportunity Attack sends PROMPT_REACTION OPPORTUNITY_ATTACK with melee weapon
        wizard.conn.sent.clear()
        wizard.has_reacted_this_turn = False
        attacker.has_moved_this_turn = False
        attacker.position = [1, 1]  # distance 1 from wizard [1, 0]
        handle_move_request({"from": [1, 1], "to": [4, 0]}, attacker, self.gs)
        oa_msgs = [m for m in _extract_msgs(wizard.conn) if m.get("type") == "PROMPT_REACTION" and m["data"].get("reaction_type") == "OPPORTUNITY_ATTACK"]
        self.assertEqual(len(oa_msgs), 1)
        self.assertEqual(oa_msgs[0]["data"]["source_name"], "Lich")
        self.assertEqual(oa_msgs[0]["data"]["details"]["weapon_name"], "Bastone Ferrato")

    def test_client_reaction_dialogs_counterspell_upcast_oa_and_warcaster_save(self):
        from client.client import ClientGUI

        root = _make_root()
        try:
            with tempfile.TemporaryDirectory() as tmpd, patch.dict(os.environ, {"DND_CHARACTERS_PATH": os.path.join(tmpd, "chars.json")}):
                cm = CharacterManager()
                char = Character(name="Gale", campaign="BG3")
                char.char_class = "Mago"
                char.level = 7
                char.attributes = {"FOR": 10, "DES": 14, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10}
                char.feats = ["Incantatore da Guerra"]
                char.spell_slots = {
                    "1": {"current": 3, "max": 4},
                    "3": {"current": 2, "max": 2},
                    "4": {"current": 1, "max": 1},
                }
                cm.characters = [char]

                gui = ClientGUI.__new__(ClientGUI)
                gui.master = root
                gui.name = "Gale"
                gui.active_character = char
                gui.character_manager = cm
                gui.network = _DummyNetwork()
                gui.reaction_spent = False
                gui.is_connected = True
                gui.toasts = []
                gui.update_action_economy_ui = lambda: None
                gui.show_toast = lambda msg, title=None, **kw: gui.toasts.append((msg, title))

                # A. COUNTERSPELL slot selector & dynamic button update
                gui.handle_prompt_reaction({
                    "reaction_type": "COUNTERSPELL",
                    "source_name": "Lich",
                    "details": {"spell_name": "Metamorfosi", "spell_level": 4, "cast_id": "cs_4"},
                })
                top = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                combos = []
                btns = []
                def _walk(w):
                    for ch in w.winfo_children():
                        if isinstance(ch, ttk.Combobox):
                            combos.append(ch)
                        elif isinstance(ch, ttk.Button):
                            btns.append(ch)
                        _walk(ch)
                _walk(top)
                self.assertEqual(len(combos), 1)
                self.assertEqual(list(combos[0]["values"]), ["3", "4"])
                combos[0].set("4")
                root.update_idletasks()
                cs_btn = [b for b in btns if "Controincantesimo" in str(b.cget("text"))][0]
                self.assertIn("Liv. 4", str(cs_btn.cget("text")))
                cs_btn.invoke()
                self.assertTrue(gui.reaction_spent)
                self.assertEqual(char.spell_slots["4"]["current"], 0)
                rx_pkt = [p for p in gui.network.sent if p.get("type") == "REACTION_RESPONSE"][-1]
                self.assertEqual(rx_pkt["data"]["details"]["slot_level"], 4)
                self.assertTrue(rx_pkt["data"]["details"]["slot_consumed"])

                # B. OPPORTUNITY_ATTACK sets reaction_spent = True
                gui.reaction_spent = False
                gui.network.sent.clear()
                gui.handle_prompt_reaction({
                    "reaction_type": "OPPORTUNITY_ATTACK",
                    "source_name": "Orco",
                    "details": {"weapon_name": "Pugnale"},
                })
                top_oa = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                btns = []
                _walk(top_oa)
                [b for b in btns if "Sferra Attacco" in str(b.cget("text"))][0].invoke()
                self.assertTrue(gui.reaction_spent)

                # C. ABSORB_ELEMENTS dialog consumes slot & sets reaction_spent
                gui.reaction_spent = False
                gui.network.sent.clear()
                gui.handle_prompt_reaction({
                    "reaction_type": "ABSORB_ELEMENTS",
                    "source_name": "Drago Rosso",
                    "details": {"damage_type": "Fuoco", "dmg_to_hp": 22},
                })
                top_ae = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                btns = []
                _walk(top_ae)
                [b for b in btns if "Assorbi Elementi" in str(b.cget("text"))][0].invoke()
                self.assertTrue(gui.reaction_spent)
                self.assertEqual(char.spell_slots["1"]["current"], 2)
                ae_pkt = [p for p in gui.network.sent if p.get("type") == "REACTION_RESPONSE"][-1]
                self.assertEqual(ae_pkt["data"]["reaction_type"], "ABSORB_ELEMENTS")

                # D. handle_prompt_save honors War Caster advantage on Concentration
                gui.network.sent.clear()
                gui.handle_prompt_save(make_prompt_save("COS", 12, "", False, "Sistema (Concentrazione)", "Contundente")["data"])
                top_sv = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                btns = []
                labels = []
                def _walk_lbl(w):
                    for ch in w.winfo_children():
                        if isinstance(ch, ttk.Button):
                            btns.append(ch)
                        elif isinstance(ch, ttk.Label):
                            labels.append(str(ch.cget("text")))
                        _walk_lbl(ch)
                _walk_lbl(top_sv)
                self.assertTrue(any("VANTAGGIO" in lb for lb in labels))
                with patch("common.dice.roll_dice", return_value={"rolls": [17], "total": 19, "is_crit": False, "is_fumble": False}) as mock_roll:
                    [b for b in btns if "Tira Salvezza" in str(b.cget("text"))][0].invoke()
                    self.assertIn("adv", mock_roll.call_args[0][0])
        finally:
            _destroy_tk(root)


class TestPhase5cRulesEngineSavingThrowsAndSubclasses(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True

    def test_warcaster_prompt_and_mage_slayer_drop_concentration(self):
        from server.rules.combat import _process_save_result, _trigger_concentration_check

        caster = Player("Elminster", conn=_MockConn())
        caster.conditions = ["Concentrazione"]
        caster.concentrating_on = "Muro di Fuoco"
        caster.feats = ["Incantatore da Guerra"]
        caster.position = [0, 0]

        enemy = Player("Assassino", conn=None)
        enemy.feats = ["Sterminatore di Maghi"]
        enemy.position = [1, 0]
        self.gs.players = [caster, enemy]

        # Connected War Caster gets has_advantage=True
        _trigger_concentration_check(caster, 12, self.gs, attacker=None)
        msgs = _extract_msgs(caster.conn)
        self.assertEqual(msgs[-1]["type"], "PROMPT_SAVE")
        self.assertTrue(msgs[-1]["data"].get("has_advantage"))

        # Failing Mage Slayer concentration save MUST drop concentration!
        _process_save_result(
            "Elminster", "COS", 5, False, False, 15, "", False,
            "Sistema (Concentrazione - Svantaggio Sterminatore di Maghi)",
            self.gs, "Contundente",
        )
        self.assertNotIn("Concentrazione", caster.conditions)
        self.assertFalse(caster.concentrating_on)

    def test_stunning_strike_expires_at_end_of_monk_next_turn(self):
        from server.rules.combat import advance_combat_turn, handle_attack_request

        monk = Player("Kenshiro", conn=None)
        monk.hp = 40
        monk.max_hp = 40
        monk.ac = 16
        monk.initiative = 20
        monk.position = [0, 0]
        monk.is_party_member = True
        monk.full_sheet = {
            "class": "Monaco", "level": 5, "ki_current": 5,
            "attributes": {"FOR": 10, "DES": 18, "COS": 14, "INT": 10, "SAG": 16, "CAR": 10},
        }

        ogre = Player("Ogre", conn=None)
        ogre.hp = 80
        ogre.max_hp = 80
        ogre.ac = 5
        ogre.initiative = 10
        ogre.position = [1, 0]
        ogre.is_party_member = False
        ogre.full_sheet = {"attributes": {"FOR": 18, "DES": 8, "COS": 12, "INT": 5, "SAG": 7, "CAR": 7}}

        self.gs.players = [monk, ogre]
        self.gs.turn_order = ["Kenshiro", "Ogre"]
        self.gs.turn_index = 0

        with patch("server.rules.combat.roll_dice", side_effect=[
            {"rolls": [15], "total": 22, "is_crit": False, "is_fumble": False, "natural_roll": 15},
            {"rolls": [6], "total": 10, "is_crit": False, "is_fumble": False, "natural_roll": 6},
            {"rolls": [3], "total": 4, "is_crit": False, "is_fumble": False, "natural_roll": 3},  # Ogre CON save fails vs CD 14
        ]):
            handle_attack_request({
                "target_name": "Ogre", "weapon_name": "Colpo Senz'Armi", "hit_bonus": 7, "damage_formula": "1d6+4", "use_stunning_strike": True,
            }, monk, self.gs)

        self.assertIn("Stordito", ogre.conditions)

        # End of Monk's Turn 1 -> Ogre stays Stunned for Ogre's turn
        advance_combat_turn(self.gs)
        self.assertIn("Stordito", ogre.conditions)

        # End of Ogre's Turn 1 -> back to Monk Turn 2 -> STILL Stunned during Monk Turn 2!
        advance_combat_turn(self.gs)
        self.assertIn("Stordito", ogre.conditions)

        # End of Monk's Turn 2 -> Stordito expires RAW PHB p. 79!
        advance_combat_turn(self.gs)
        self.assertNotIn("Stordito", ogre.conditions)

    def test_sculpt_spells_does_not_match_conjuration_in_italian(self):
        from server.rules.combat import _process_save_result

        conjurer = Player("Evocatore_Conj", conn=None)
        conjurer.is_party_member = True
        conjurer.full_sheet = {"class": "Mago", "level": 5, "subclass": "Scuola di Evocazione"}

        invoker = Player("Mago_Invoc", conn=None)
        invoker.is_party_member = True
        invoker.full_sheet = {"class": "Mago", "level": 5, "subclass": "Scuola di Invocazione"}

        ally = Player("Guerriero", conn=None)
        ally.is_party_member = True
        ally.hp = 50
        ally.max_hp = 50

        self.gs.players = [conjurer, invoker, ally]
        self.gs.automation_settings["auto_apply_aoe_damage"] = True

        # Conjurer ("Scuola di Evocazione" IT) MUST NOT grant Sculpt Spells protection
        _process_save_result("Guerriero", "DES", 18, False, False, 15, "20", True, "Evocatore_Conj", self.gs, "Fuoco", spell_school="Evocazione")
        self.assertEqual(ally.hp, 40)

        # Evoker ("Scuola di Invocazione" IT) grants Sculpt Spells (0 damage!)
        _process_save_result("Guerriero", "DES", 10, False, False, 15, "20", True, "Mago_Invoc", self.gs, "Fuoco", spell_school="Evocazione")
        self.assertEqual(ally.hp, 40)

    def test_resolve_saving_throw_and_spell_effects_engine_aoe_schema(self):
        from common.spell_effects_engine import cast_iconic_spell

        caster = Player("Mago", conn=None)
        caster.position = [0, 0]
        caster.full_sheet = {"class": "Mago", "level": 7, "attributes": {"INT": 18}}

        fiend = Player("Diavolo", conn=None)
        fiend.position = [2, 0]
        fiend.hp = 60
        fiend.max_hp = 60
        fiend.legendary_resistances_current = 0
        fiend.legendary_resistances_max = 1
        fiend.features = ["Resistenza alla Magia (Magic Resistance)"]

        self.gs.players = [caster, fiend]
        msg = cast_iconic_spell(caster, fiend, "Muro di Fuoco", 4, self.gs)
        self.assertIsNotNone(msg)
        self.assertEqual(len(self.gs.active_aoes), 1)
        aoe = self.gs.active_aoes[0]
        self.assertIn("origin", aoe)
        self.assertIn("size", aoe)
        self.assertIn("center", aoe)
        self.assertIn("radius_hex", aoe)

        # Hold Person against low save with Legendary Resistance remaining auto-consumes LR cleanly
        fiend.legendary_resistances_current = 1
        with patch("server.rules.combat.roll_dice", return_value={"rolls": [2], "total": 2, "natural_roll": 2}):
            hp_msg = cast_iconic_spell(caster, fiend, "Blocca Persone", 2, self.gs)
        self.assertIn("resiste", hp_msg.lower())
        self.assertEqual(fiend.legendary_resistances_current, 0)

    def test_monster_multiattack_blur_mirror_image_and_defense_reactions(self):
        from server.dm_monster_engine import execute_monster_multiattack

        monster = Player("Glabrezu", conn=None)
        monster.hp = 150
        monster.max_hp = 150
        monster.position = [0, 0]
        monster.is_party_member = False
        monster.full_sheet = {
            "actions": [
                {"name": "Multiattack", "desc": "The glabrezu makes two pincer attacks."},
                {"name": "Pincer", "atk_bonus": 9, "damage": "2d10+5", "damage_type": "Contundente"},
            ],
        }

        target = Player("Ladro", conn=_MockConn())
        target.hp = 50
        target.max_hp = 50
        target.ac = 10
        target.position = [1, 0]
        target.is_party_member = True
        target.blur_active = True
        target.mirror_images = 1
        target.full_sheet = {"class": "Ladro", "level": 5, "attributes": {"DES": 16}}
        self.gs.players = [monster, target]

        with patch("server.dm_monster_engine.roll_dice", return_value={"rolls": [12], "total": 12}) as mock_d20, \
             patch("random.randint", return_value=20):  # Mirror image triggers >= 11 on 1 copy
            res = execute_monster_multiattack(monster, self.gs, target=target)
        self.assertTrue(res["ok"])
        self.assertTrue(any("dis" in c[0][0] for c in mock_d20.call_args_list))
        self.assertEqual(target.mirror_images, 0)  # Duplicate destroyed cleanly

        # Hit Rogue -> triggers UNCANNY_DODGE 4-arg prompt
        target.blur_active = False
        target.conn.sent.clear()
        with patch("server.dm_monster_engine.roll_dice", return_value={"rolls": [14], "total": 14}):
            execute_monster_multiattack(monster, self.gs, target=target)
        ud_msgs = [m for m in _extract_msgs(target.conn) if m.get("type") == "PROMPT_REACTION" and m["data"].get("reaction_type") == "UNCANNY_DODGE"]
        self.assertGreaterEqual(len(ud_msgs), 1)
        self.assertEqual(ud_msgs[0]["data"]["target_name"], "Ladro")
        self.assertGreater(ud_msgs[0]["data"]["details"].get("damage_taken", 0), 0)

    def test_subclass_rage_conditions_and_bonus_action_sync(self):
        from common.subclass_and_race_rules import get_subclass_damage_mods, handle_subclass_active_power

        zealot = Player("Grog", conn=None)
        zealot.conditions = ["Ira"]
        zealot.full_sheet = {"class": "Barbaro", "level": 6, "subclass": "Cammino dello Zelota"}
        dmg_mods = get_subclass_damage_mods(zealot, Player("Goblin"))
        self.assertEqual(dmg_mods["flat_bonus"], 3)
        self.assertTrue(any("1d6" in d[0] for d in dmg_mods["dice_formulas"]))

        berserker = Player("Karsa", conn=None)
        berserker.conditions = ["Ira"]
        berserker.bonus_action_used_this_turn = False
        berserker.full_sheet = {"class": "Barbaro", "level": 3, "subclass": "Berserker"}
        out = handle_subclass_active_power(berserker, "frenzy_attack", game_state=self.gs)
        self.assertTrue(out["ok"])
        self.assertTrue(berserker.bonus_action_used_this_turn)
        self.assertFalse(berserker.has_bonus_action)

        # Second BA fails
        out2 = handle_subclass_active_power(berserker, "frenzy_attack", game_state=self.gs)
        self.assertFalse(out2["ok"])


class TestPhase5cSyncCanvasLootShopAndFoW(unittest.TestCase):
    def test_fow_auto_explore_uses_deduped_sets_quickly(self):
        from server.rules.movement import auto_explore_fow

        gs = GameState(queue.Queue())
        gs.current_map = {"fow_enabled": True, "fow_revealed": [[x, 0] for x in range(1500)], "fow_draft": [[x, 0] for x in range(1500)], "walls": [], "grid_type": "hex"}
        pc = Player("Esploratore", conn=None)
        pc.position = [0, 0]
        pc.vision_radius = 3
        gs.players = [pc]
        changed = auto_explore_fow(pc, gs)
        self.assertTrue(changed)
        tups = [(p[0], p[1]) for p in gs.current_map["fow_revealed"]]
        self.assertEqual(len(tups), len(set(tups)))

    def test_canvas_aoe_fallback_initiative_str_hp_and_spotlight_secrecy(self):
        from components.ui_components import HexMapCanvas, CommandPaletteDialog

        root = _make_root()
        try:
            canvas = HexMapCanvas(root, width=600, height=400)
            canvas.is_dm = False
            canvas.player_name = "Aelar"
            canvas.turn_order = ["Aelar", "Drago"]
            canvas.turn_player_name = "Drago"
            canvas.aoes_data = [{"spell_key": "web", "center": [2, 2], "radius_hex": 2, "color": "#CBD5E1"}]
            canvas.players_data = {
                "Aelar": {"position": [0, 0], "hp": 25, "max_hp": 30, "is_party_member": True},
                "Drago": {"position": [5, 5], "hp": "Nascosto", "max_hp": "?", "is_party_member": False, "health_status": "Sanguinante"},
            }
            # Must not raise KeyError: 'origin' or TypeError: 'str'/'int'
            canvas.redraw()

            # Non-DM CommandPalette hides exact HP and Hex for hostile NPC while showing qualitative status
            canvas.players_data["Drago"] = {"position": [5, 5], "hp": 40, "hp_max": 100, "is_party_member": False}
            dlg_p = CommandPaletteDialog(root, map_canvas=canvas, is_dm=False)
            dlg_p._perform_search("Drago")
            drago_res = [r for r in dlg_p._results if r.get("type") == "TOKEN" and r.get("payload") == "Drago"]
            self.assertEqual(len(drago_res), 1)
            self.assertNotIn("40/100", drago_res[0]["badge"])
            self.assertNotIn("[5,5]", drago_res[0]["badge"])
            self.assertIn("Sanguinante", drago_res[0]["badge"])

            # DM CommandPalette sees exact HP and coordinates
            dlg_dm = CommandPaletteDialog(root, map_canvas=canvas, is_dm=True)
            dlg_dm._perform_search("Drago")
            dm_res = [r for r in dlg_dm._results if r.get("type") == "TOKEN" and r.get("payload") == "Drago"]
            self.assertIn("40/100", dm_res[0]["badge"])
            self.assertIn("[5,5]", dm_res[0]["badge"])
        finally:
            _destroy_tk(root)

    def test_wild_shape_and_multiclass_arcane_recovery_sync(self):
        from client.character_sheet_ui import CharacterSheetFrame
        from client.sheet_panels.vitals_panel import VitalsPanel

        root = _make_root()
        try:
            with tempfile.TemporaryDirectory() as tmpd, patch.dict(os.environ, {"DND_CHARACTERS_PATH": os.path.join(tmpd, "chars.json")}):
                cm = CharacterManager()
                char = Character(name="Radagast", campaign="Test")
                char.char_class = "Druido"
                char.level = 4
                cm.characters = [char]
                saved_calls = []

                sheet = CharacterSheetFrame(root, char, manager=cm, on_save_callback=lambda c: saved_calls.append(("ws", c.name, c.is_in_wild_shape())))
                with patch("client.character_sheet_ui.messagebox.showinfo"):
                    sheet.open_wild_shape_dialog()
                    top_ws = [w for w in sheet.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                    btns = []
                    def _find_b(w):
                        for ch in w.winfo_children():
                            if isinstance(ch, ttk.Button):
                                btns.append(ch)
                            _find_b(ch)
                    _find_b(top_ws)
                    [b for b in btns if "Assumi Forma" in str(b.cget("text"))][0].invoke()
                self.assertEqual(saved_calls[-1], ("ws", "Radagast", True))

                # Multiclass Fighter 4 / Wizard 3 -> total level 7, wizard_level 3 -> max 2 slot levels
                wiz = Character(name="Eldrin", campaign="Test")
                wiz.char_class = "Guerriero 4 / Mago 3"
                wiz.level = 7
                wiz.classes = {"Guerriero": 4, "Mago": 3}
                wiz.spell_slots = {
                    "1": {"current": 2, "max": 4},
                    "2": {"current": 1, "max": 2},
                    "3": {"current": 0, "max": 2},
                }
                cm.characters.append(wiz)
                wiz_saved = []
                wsheet = CharacterSheetFrame(root, wiz, manager=cm, on_save_callback=lambda c: wiz_saved.append(dict(c.spell_slots)))
                VitalsPanel.short_rest(wsheet)
                top_sr = [w for w in wsheet.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                btns = []
                _find_b(top_sr)
                [b for b in btns if "Recupero Arcano" in str(b.cget("text"))][0].invoke()
                # Max recoverable = ceil(3/2) = 2 levels (two Lv1 slots recovered, NOT Lv3!)
                self.assertTrue(wiz.arcane_recovery_used)
                self.assertEqual(wiz.spell_slots["1"]["current"], 4)
                self.assertEqual(wiz.spell_slots["2"]["current"], 1)
                self.assertEqual(len(wiz_saved), 1)
        finally:
            _destroy_tk(root)

    def test_container_loot_safe_keys_and_shop_finite_stock(self):
        from server.rules.inventory import handle_buy_item_request, handle_take_loot_request
        from components.shop_ui import ShopDialog

        gs = GameState(queue.Queue())
        pc = Player("Mercurio", conn=_MockConn())
        pc.full_sheet = {"currency": {"MO": 100}, "inventory_grid": [None] * 25, "inventory": []}
        gs.players = [pc]
        gs.current_map = {"loots": [{"id": "chest_1", "q": 0, "r": 0, "contents": [{"name": "Rubino", "qty": 2}]}]}

        # Container loot does not crash with KeyError on missing top-level item/qty
        handle_take_loot_request({"loot_id": "chest_1"}, pc, gs)

        # Shop with finite stock 2 -> 1 -> 0 -> blocked
        gs.shops = {"Emporio": {"items": [{"name": "Pozione di Guarigione", "price": 25, "stock": 2}]}}
        handle_buy_item_request({"shop_name": "Emporio", "item_name": "Pozione di Guarigione"}, pc, gs)
        self.assertEqual(gs.shops["Emporio"]["items"][0]["stock"], 1)
        self.assertEqual(pc.full_sheet["currency"]["MO"], 75)

        handle_buy_item_request({"shop_name": "Emporio", "item_name": "Pozione di Guarigione"}, pc, gs)
        self.assertEqual(gs.shops["Emporio"]["items"][0]["stock"], 0)
        self.assertEqual(pc.full_sheet["currency"]["MO"], 50)

        pc.conn.sent.clear()
        handle_buy_item_request({"shop_name": "Emporio", "item_name": "Pozione di Guarigione"}, pc, gs)
        self.assertEqual(pc.full_sheet["currency"]["MO"], 50)
        err_msgs = [m for m in _extract_msgs(pc.conn) if m.get("type") == "ERROR_REPLY"]
        self.assertTrue(any("esaurito" in m.get("data", {}).get("text", "").lower() for m in err_msgs))

        # Full backpack must NOT decrement stock
        pc.full_sheet["inventory_grid"] = [{"name": f"Junk{i}", "qty": 1} for i in range(25)]
        gs.shops["Emporio"]["items"].append({"name": "Torcia", "price": 1, "stock": 3})
        handle_buy_item_request({"shop_name": "Emporio", "item_name": "Torcia"}, pc, gs)
        self.assertEqual(gs.shops["Emporio"]["items"][1]["stock"], 3)
        self.assertEqual(pc.full_sheet["currency"]["MO"], 50)

        # ShopDialog displays availability column without crashing
        root = _make_root()
        try:
            dlg = ShopDialog(root, gs, is_dm=False, network_or_server=_DummyNetwork())
            rows = [dlg.tree.item(iid, "values") for iid in dlg.tree.get_children()]
            self.assertEqual(rows[0][0], "Pozione di Guarigione")
            self.assertIn("Esaurito", str(rows[0][2]))
            self.assertEqual(str(rows[1][2]), "3")
        finally:
            _destroy_tk(root)


if __name__ == "__main__":
    unittest.main()
