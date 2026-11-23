"""tests/test_gameplay_integration_e2e.py - Phase 3 Gameplay Integrity, Integration & Real TCP E2E Suite."""

import copy
import json
import os
import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DND_MOCK_AUDIO"] = "1"

from client.character_manager import Character
from client.network import ClientNetwork
from common.campaign import Campaign
from common.game_state import GameState, Player
from common.protocol import (
    make_attack_request,
    make_cast_special_spell_request,
    make_class_feature_request,
    make_cunning_action_request,
    make_end_turn_request,
    make_game_state,
    make_join,
    make_ready_action_request,
    make_trigger_readied_action_request,
    make_update_full_sheet_request,
    make_update_stats_request,
)


class _MockConn:
    """In-memory connection mock capturing protocol frames sent via send_message."""

    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


def _decode_sent_frames(raw_chunks):
    """Decode newline/length-delimited protocol payloads captured on _MockConn."""
    import json

    decoded = []
    for chunk in raw_chunks:
        text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
        idx = 0
        while idx < len(text):
            start = text.find("{", idx)
            if start < 0:
                break
            try:
                obj, end = json.JSONDecoder().raw_decode(text, start)
                decoded.append(obj)
                idx = end
            except Exception:
                break
    return decoded


def _drain_queue(q: queue.Queue):
    items = []
    while True:
        try:
            items.append(q.get_nowait())
        except queue.Empty:
            break
    return items


def _wait_until(predicate, timeout=3.0, interval=0.02):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        res = predicate()
        if res:
            return res
        time.sleep(interval)
    return predicate()


# ==============================================================================
# REUSABLE PARTY CHARACTER FIXTURES
# ==============================================================================

def _build_pc(name: str, char_class: str, level: int, attrs: dict, hp: int, ac: int = 14) -> Character:
    ch = Character(name=name, race="Umano", char_class=char_class, level=level)
    ch.classes = {char_class: level}
    ch.attributes = dict(attrs)
    ch.hp_max = hp
    ch.hp_current = hp
    ch.ac = ac
    ch.conditions = []
    ch.spell_points_current = 0
    ch.spell_points_max = 0
    return ch


def make_fighter_pc(name: str = "Kaelen", level: int = 5) -> Character:
    ch = _build_pc(name, "Guerriero", level, {"FOR": 18, "DES": 14, "COS": 16, "INT": 10, "SAG": 12, "CAR": 10}, hp=44, ac=18)
    ch.armor_proficiencies = ["Tutte"]
    ch.weapon_proficiencies = ["Semplici", "Da Guerra"]
    ch.class_resources = {"second_wind": True, "action_surge": level >= 2, "rage_current": 0, "rage_max": 0}
    ch.weapons = [{"name": "Spada Lunga", "hit_bonus": "+7", "damage": "1d8+4", "damage_type": "Tagliente"}]
    return ch


def make_rogue_pc(name: str = "Vex", level: int = 5) -> Character:
    ch = _build_pc(name, "Ladro", level, {"FOR": 10, "DES": 18, "COS": 14, "INT": 12, "SAG": 14, "CAR": 14}, hp=33, ac=16)
    ch.armor_proficiencies = ["Leggere"]
    ch.weapons = [{"name": "Stocco", "hit_bonus": "+7", "damage": "1d8+4", "damage_type": "Perforante", "properties": "Accurata"}]
    return ch


def make_barbarian_pc(name: str = "Grog", level: int = 5) -> Character:
    ch = _build_pc(name, "Barbaro", level, {"FOR": 18, "DES": 14, "COS": 16, "INT": 8, "SAG": 12, "CAR": 10}, hp=55, ac=15)
    ch.armor_proficiencies = ["Leggere", "Medie", "Scudi"]
    ch.class_resources = {"second_wind": False, "action_surge": False, "rage_current": 3, "rage_max": 3}
    ch.weapons = [{"name": "Ascia Bipenne", "hit_bonus": "+7", "damage": "1d12+4", "damage_type": "Tagliente"}]
    return ch


def make_wizard_pc(name: str = "Elara", level: int = 5) -> Character:
    ch = _build_pc(name, "Mago", level, {"FOR": 8, "DES": 14, "COS": 14, "INT": 18, "SAG": 12, "CAR": 10}, hp=30, ac=12)
    ch.spell_slots["1"] = {"max": 4, "current": 4}
    ch.spell_slots["2"] = {"max": 3, "current": 3}
    ch.spell_slots["3"] = {"max": 2, "current": 2}
    ch.spellbook = [
        {"name": "Dardo Incantato", "level": 1, "time": "1 azione", "range": "120 ft", "school": "Invocazione", "duration": "Istantanea", "components": "V, S", "damage_formula": "1d4+1", "damage_type": "Forza", "prepared": True},
        {"name": "Palla di Fuoco", "level": 3, "time": "1 azione", "range": "150 ft", "school": "Invocazione", "duration": "Istantanea", "components": "V, S, M", "damage_formula": "8d6", "damage_type": "Fuoco", "prepared": True},
        {"name": "Scudo", "level": 1, "time": "1 reazione", "range": "Incantatore", "school": "Abiurazione", "duration": "1 round", "components": "V, S", "prepared": True},
        {"name": "Silenzio", "level": 2, "time": "1 azione", "range": "120 ft", "school": "Illusione", "duration": "Concentrazione, 10 minuti", "components": "V, S", "prepared": True},
    ]
    return ch


def make_cleric_pc(name: str = "Kyra", level: int = 5) -> Character:
    ch = _build_pc(name, "Chierico", level, {"FOR": 14, "DES": 10, "COS": 14, "INT": 10, "SAG": 18, "CAR": 12}, hp=38, ac=18)
    ch.armor_proficiencies = ["Leggere", "Medie", "Scudi"]
    ch.spell_slots["1"] = {"max": 4, "current": 4}
    ch.spell_slots["2"] = {"max": 3, "current": 3}
    ch.spell_slots["3"] = {"max": 2, "current": 2}
    ch.spellbook = [
        {"name": "Parola Guaritrice", "level": 1, "time": "1 azione bonus", "range": "60 ft", "school": "Invocazione", "duration": "Istantanea", "components": "V", "prepared": True},
        {"name": "Fiamma Sacra", "level": 0, "time": "1 azione", "range": "60 ft", "school": "Invocazione", "duration": "Istantanea", "components": "V, S", "prepared": True},
        {"name": "Benedizione", "level": 1, "time": "1 azione", "range": "30 ft", "school": "Ammaliamento", "duration": "Concentrazione, 1 minuto", "components": "V, S, M", "prepared": True},
    ]
    return ch


def make_warlock_pc(name: str = "Hex", level: int = 5) -> Character:
    ch = _build_pc(name, "Warlock", level, {"FOR": 8, "DES": 14, "COS": 14, "INT": 12, "SAG": 10, "CAR": 18}, hp=33, ac=13)
    ch.armor_proficiencies = ["Leggere"]
    ch.pact_slots = {"max": 2, "current": 2, "level": 3}
    ch.spellbook = [
        {"name": "Deflagrazione Occulta", "level": 0, "time": "1 azione", "range": "120 ft", "school": "Invocazione", "duration": "Istantanea", "components": "V, S", "damage_formula": "1d10", "damage_type": "Forza", "prepared": True},
    ]
    return ch


def _pc_to_player(pc: Character, pos=None, conn=None) -> Player:
    sheet = pc.to_dict()
    p = Player(pc.name, conn=conn)
    p.is_party_member = True
    p.is_npc = False
    p.role = "player"
    p.hp = pc.hp_current
    p.max_hp = pc.hp_max
    p.ac = pc.ac
    p.speed = pc.speed
    p.position = list(pos or [0, 0])
    p.full_sheet = sheet
    p.pact_slots_max = int(sheet.get("pact_slots", {}).get("max", 0) or 0)
    p.pact_slots_current = int(sheet.get("pact_slots", {}).get("current", 0) or 0)
    p.pact_slot_level = int(sheet.get("pact_slots", {}).get("level", 0) or 0)
    return p


class LoopbackSessionHarness:
    """Self-contained TCP loopback server + tracked ClientNetwork instances."""

    def __init__(self, session_password: str = "Pin5e"):
        from server.network import Server

        self._patcher = patch("server.network.VoiceServer", return_value=MagicMock())
        self._patcher.start()
        self.server_queue = queue.Queue()
        self.server = Server("127.0.0.1", 0, self.server_queue, session_password=session_password)
        self.clients = []
        self._thread = threading.Thread(target=self.server.start, daemon=True)
        self._thread.start()
        started = _wait_until(lambda: self.server.running and self.server.server_socket is not None, timeout=3.0)
        if not started:
            self.close()
            raise RuntimeError("Loopback Server failed to start")
        self.port = self.server.server_socket.getsockname()[1]

    def connect_client(self, join_name: str = None, password: str = None):
        q = queue.Queue()
        disconnected = threading.Event()
        cn = ClientNetwork(q, on_disconnect_callback=disconnected.set)
        cn.connect("127.0.0.1", self.port)
        self.clients.append(cn)
        if join_name is not None:
            cn.send(make_join(join_name, password=password))
        return cn, q, disconnected

    def close(self):
        for cn in list(self.clients):
            try:
                cn.disconnect()
            except Exception:
                pass
        self.clients.clear()
        try:
            self.server.stop()
        except Exception:
            pass
        try:
            self._thread.join(timeout=2.0)
        except Exception:
            pass
        try:
            self._patcher.stop()
        except Exception:
            pass


# ==============================================================================
# TEST SUITE 1: COMBAT ACTION ECONOMY, CLASS ABILITIES & CROSS-PLAYER AUTH
# ==============================================================================

class TestCombatActionEconomyAndAbilitiesIntegration(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.gs.combat_active = True
        self.gs.automation_settings["strict_turn_lock"] = True

    def test_fighter_extra_attack_action_surge_limit_and_second_wind_clamp(self):
        from server.rules.class_abilities import handle_class_feature_request
        from server.rules.combat import handle_attack_request

        fighter = _pc_to_player(make_fighter_pc("Kaelen", level=5), pos=[0, 0], conn=_MockConn())
        goblin = Player("Goblin", conn=None)
        goblin.hp = 120
        goblin.max_hp = 120
        goblin.ac = 5
        goblin.position = [1, 0]
        self.gs.players = [fighter, goblin]
        self.gs.turn_index = 0

        # 2 attacks consume Action (Extra Attack = 2)
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, self.gs)
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, self.gs)
        self.assertEqual(fighter.attacks_made_this_turn, 2)
        self.assertTrue(fighter.has_acted_this_turn)

        # 3rd attack without Action Surge blocked
        fighter.conn.sent.clear()
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, self.gs)
        self.assertTrue(fighter.conn.sent)

        # Action Surge restores Action for 2 more attacks; 2nd Action Surge on same turn blocked (1/turn)
        handle_class_feature_request({"feature": "action_surge"}, fighter, self.gs)
        self.assertFalse(fighter.has_acted_this_turn)
        self.assertTrue(fighter.action_surge_used_this_turn)
        self.assertFalse(fighter.full_sheet["class_resources"]["action_surge"])

        fighter.conn.sent.clear()
        fighter.full_sheet["class_resources"]["action_surge"] = True  # Even if restored manually on sheet
        handle_class_feature_request({"feature": "action_surge"}, fighter, self.gs)
        msgs = _decode_sent_frames(fighter.conn.sent)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in msgs))

        # Two more attacks succeed after single Action Surge
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, self.gs)
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d4"}, fighter, self.gs)
        self.assertTrue(fighter.has_acted_this_turn)

        # Lv 1 Fighter cannot use Action Surge
        novice = _pc_to_player(make_fighter_pc("Novizio", level=1), pos=[0, 1], conn=_MockConn())
        self.gs.players = [novice, goblin]
        self.gs.turn_index = 0
        novice.full_sheet["class_resources"]["action_surge"] = True
        handle_class_feature_request({"feature": "action_surge"}, novice, self.gs)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(novice.conn.sent)))

        # Second Wind clamps malicious client heal_amount and rejects already_consumed bypass when spent
        novice.hp = 1
        novice.max_hp = 50
        handle_class_feature_request({"feature": "second_wind", "already_consumed": True, "heal_amount": 9999}, novice, self.gs)
        self.assertEqual(novice.hp, 12)  # max 1 + (10 + level 1) = 12
        self.assertFalse(novice.full_sheet["class_resources"]["second_wind"])
        novice.bonus_action_used_this_turn = False
        novice.conn.sent.clear()
        handle_class_feature_request({"feature": "second_wind", "already_consumed": True, "heal_amount": 10}, novice, self.gs)
        self.assertEqual(novice.hp, 12)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(novice.conn.sent)))

    def test_rogue_cunning_action_hide_and_sneak_attack_once_per_turn(self):
        from server.rules.class_abilities import handle_cunning_action_request, handle_hide_request
        from server.rules.combat import handle_attack_request

        rogue = _pc_to_player(make_rogue_pc("Vex", level=5), pos=[0, 0], conn=_MockConn())
        ally = _pc_to_player(make_fighter_pc("Kaelen", level=5), pos=[1, 1], conn=None)
        goblin = Player("Goblin", conn=None)
        goblin.hp = 100
        goblin.max_hp = 100
        goblin.ac = 5
        goblin.position = [1, 0]
        self.gs.players = [rogue, ally, goblin]
        self.gs.turn_index = 0

        # Cunning Action consumes Bonus Action
        handle_cunning_action_request({"sub_action": "disengage"}, rogue, self.gs)
        self.assertTrue(rogue.bonus_action_used_this_turn)
        self.assertIn("Disimpegno", rogue.conditions)

        # Second Cunning Action on same turn rejected
        rogue.conn.sent.clear()
        handle_cunning_action_request({"sub_action": "dash"}, rogue, self.gs)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(rogue.conn.sent)))

        # Hide uses standard Action now that Bonus Action is spent
        handle_hide_request({}, rogue, self.gs)
        self.assertTrue(rogue.has_acted_this_turn)

        # Hide again fails once both Action and Bonus Action are spent
        rogue.conn.sent.clear()
        handle_hide_request({}, rogue, self.gs)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(rogue.conn.sent)))

        # Reset turn -> Sneak Attack triggers once cleanly with adjacent ally
        self.gs.next_turn()
        self.gs.next_turn()
        self.gs.next_turn()
        self.assertFalse(rogue.sneak_attack_used_this_turn)
        with patch("common.dice.random.randint", return_value=4):
            handle_attack_request({"target_name": "Goblin", "weapon_name": "Stocco", "hit_bonus": 15, "damage_formula": "1d8+4"}, rogue, self.gs)
        self.assertTrue(rogue.sneak_attack_used_this_turn)

    def test_barbarian_rage_heavy_armor_concentration_drop_and_zero_hp_termination(self):
        from server.rules.class_abilities import handle_cast_special_spell_request, handle_class_feature_request
        from server.rules.combat import apply_damage

        barb = _pc_to_player(make_barbarian_pc("Grog", level=5), pos=[0, 0], conn=_MockConn())
        wiz = _pc_to_player(make_wizard_pc("Elara", level=5), pos=[0, 1], conn=_MockConn())
        barb.conditions = ["Concentrazione"]
        barb.concentrating_on = "Benedizione"
        barb.concentrating_spell = "Benedizione"
        barb.full_sheet["inventory_grid"] = [
            {
                "name": "Armatura Completa (Plate)",
                "type": "Armatura",
                "armor_type": "Pesante",
                "category": "Pesante",
                "container": "equipped",
                "equipped": True,
            }
        ]
        self.gs.players = [barb, wiz]
        self.gs.turn_index = 0

        # Rage blocked in heavy armor
        handle_class_feature_request({"feature": "rage"}, barb, self.gs)
        self.assertNotIn("Ira", barb.conditions)
        self.assertEqual(barb.full_sheet["class_resources"]["rage_current"], 3)

        # Remove heavy armor -> Rage succeeds, drops concentration, blocks spells
        barb.full_sheet["inventory_grid"] = []
        handle_class_feature_request({"feature": "rage"}, barb, self.gs)
        self.assertIn("Ira", barb.conditions)
        self.assertNotIn("Concentrazione", barb.conditions)
        self.assertIsNone(barb.concentrating_on)
        self.assertIsNone(barb.concentrating_spell)
        self.assertEqual(barb.full_sheet["class_resources"]["rage_current"], 2)

        # Spellcasting while Raging blocked
        barb.has_acted_this_turn = False
        barb.conn.sent.clear()
        handle_cast_special_spell_request({"spell_name": "Dardo Incantato", "cast_level": 1}, barb, self.gs)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(barb.conn.sent)))

        # Knocking Barbarian to 0 HP automatically ends Rage
        apply_damage(barb, 999, "Forza", self.gs)
        self.assertEqual(barb.hp, 0)
        self.assertNotIn("Ira", barb.conditions)
        self.assertNotIn("Ira", barb.condition_durations)

    def test_readied_action_expiration_trigger_and_reaction_rollback(self):
        from server.rules.combat import (
            handle_attack_request,
            handle_ready_action_request,
            handle_trigger_readied_action_request,
        )

        wiz = _pc_to_player(make_wizard_pc("Elara", level=5), pos=[0, 0], conn=_MockConn())
        fighter = _pc_to_player(make_fighter_pc("Kaelen", level=5), pos=[0, 1], conn=_MockConn())
        goblin = Player("Goblin", conn=None)
        goblin.hp = 60
        goblin.max_hp = 60
        goblin.ac = 5
        goblin.position = [1, 0]
        self.gs.players = [wiz, fighter, goblin]
        self.gs.turn_index = 0

        # Ready spell consumes Lv 1 slot & sets Preparato concentration
        handle_ready_action_request(
            {
                "trigger_text": "Quando il Goblin entra a portata",
                "readied_action": "Dardo Incantato",
                "is_spell": True,
                "slot_level": 1,
                "action_payload": {"spell_name": "Dardo Incantato", "cast_level": 1, "target_name": "Goblin"},
            },
            wiz,
            self.gs,
        )
        self.assertEqual(wiz.full_sheet["spell_slots"]["1"]["current"], 3)
        self.assertEqual(wiz.concentrating_on, "Preparato: Dardo Incantato")
        self.assertIn("Azione Preparata", wiz.conditions)

        # Trigger on Goblin's turn: consumes Reaction and fires spell without double-reaction rejection
        self.gs.next_turn()  # Fighter
        self.gs.next_turn()  # Goblin
        handle_trigger_readied_action_request({"target_name": "Goblin"}, wiz, self.gs)
        self.assertTrue(wiz.has_reacted_this_turn)
        self.assertLess(goblin.hp, 60)
        self.assertNotIn("Azione Preparata", wiz.conditions)
        self.assertIsNone(wiz.concentrating_on)

        # Second trigger/reaction in same round rejected
        wiz.conn.sent.clear()
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Pugnale", "hit_bonus": 10, "damage_formula": "1d4", "is_reaction": True}, wiz, self.gs)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(wiz.conn.sent)))

        # Out-of-range melee reaction rolls back has_reacted_this_turn
        goblin.position = [10, 10]
        handle_attack_request({"target_name": "Goblin", "weapon_name": "Spada Lunga", "hit_bonus": 15, "damage_formula": "1d8", "is_reaction": True}, fighter, self.gs)
        self.assertFalse(fighter.has_reacted_this_turn)

        # Ready spell left untriggered expires cleanly on start of Wizard's next turn
        self.gs.next_turn()  # Back to Wizard
        self.assertFalse(wiz.has_reacted_this_turn)
        handle_ready_action_request(
            {"trigger_text": "Se apre la porta", "readied_action": "Raggio di Gelo", "is_spell": True, "slot_level": 1},
            wiz,
            self.gs,
        )
        self.assertEqual(wiz.full_sheet["spell_slots"]["1"]["current"], 2)
        self.gs.next_turn()  # Fighter
        self.gs.next_turn()  # Goblin
        self.gs.next_turn()  # Back to Wizard -> expires!
        self.assertIsNone(wiz.readied_action_data)
        self.assertNotIn("Azione Preparata", wiz.conditions)
        self.assertNotIn("Concentrazione", wiz.conditions)

    def test_cross_player_actor_authorization_enforced(self):
        from server.rules.class_abilities import handle_cast_special_spell_request, handle_class_feature_request

        p1 = _pc_to_player(make_fighter_pc("Kaelen", level=5), pos=[0, 0], conn=_MockConn())
        p2 = _pc_to_player(make_barbarian_pc("Grog", level=5), pos=[0, 1], conn=_MockConn())
        fam = Player("GufoFamiglio", conn=None)
        fam.is_companion = True
        fam.owner = "Kaelen"
        fam.position = [1, 1]
        self.gs.players = [p1, p2, fam]
        self.gs.turn_index = 0

        # Kaelen tries to activate Grog's Rage -> blocked!
        handle_class_feature_request({"feature": "rage", "actor_name": "Grog"}, p1, self.gs)
        self.assertNotIn("Ira", p2.conditions)
        self.assertTrue(any(m.get("type") == "ERROR_REPLY" for m in _decode_sent_frames(p1.conn.sent)))

        # DM can command Grog cleanly
        handle_class_feature_request({"feature": "rage", "actor_name": "Grog"}, None, self.gs)
        self.assertIn("Ira", p2.conditions)

        # Companion owner can act as their companion
        p1.conn.sent.clear()
        handle_cast_special_spell_request({"spell_name": "Dardo Incantato", "cast_level": 1, "actor_name": "GufoFamiglio"}, p1, self.gs)
        msgs = _decode_sent_frames(p1.conn.sent)
        self.assertFalse(any("Autorizzazione" in str(m.get("data", {}).get("text", "")) for m in msgs))


# ==============================================================================
# TEST SUITE 2: SPELLCASTING, SLOT REFUND, REQUEST DEDUP & SHEET SYNC
# ==============================================================================

class TestSpellcastingAndSheetResourceSyncIntegration(unittest.TestCase):
    def test_bonus_action_spell_rule_refund_dedup_and_client_sync(self):
        from client.character_sheet_ui import CharacterSheetFrame, _prevalidate_client_spell_cast
        from client.client import ClientGUI
        from server.rules.class_abilities import handle_cast_special_spell_request

        cleric_pc = make_cleric_pc("Kyra", level=5)
        ok_pre, _ = _prevalidate_client_spell_cast(cleric_pc, cleric_pc.spellbook[0], is_subtle=False)
        self.assertTrue(ok_pre)

        # Rage blocks client cast before touching resources
        cleric_pc.conditions = ["Ira"]
        ok_rage, err_rage = _prevalidate_client_spell_cast(cleric_pc, cleric_pc.spellbook[0])
        self.assertFalse(ok_rage)
        self.assertIn("Ira", err_rage)

        # Silenzio blocks verbal unless Subtle (Celato)
        cleric_pc.conditions = ["Silenziato"]
        ok_sil, _ = _prevalidate_client_spell_cast(cleric_pc, cleric_pc.spellbook[0], is_subtle=False)
        ok_subtle, _ = _prevalidate_client_spell_cast(cleric_pc, cleric_pc.spellbook[0], is_subtle=True)
        self.assertFalse(ok_sil)
        self.assertTrue(ok_subtle)

        # Reset conditions for server cast + refund + sheet sync check
        cleric_pc.conditions = []
        gs = GameState(queue.Queue())
        gs.combat_active = True
        gs.automation_settings["strict_turn_lock"] = True
        wiz_pc = make_wizard_pc("Elara", level=5)
        wiz = _pc_to_player(wiz_pc, pos=[0, 0], conn=_MockConn())
        cleric = _pc_to_player(cleric_pc, pos=[1, 0], conn=_MockConn())
        goblin = Player("Goblin", conn=None)
        goblin.hp = 80
        goblin.max_hp = 80
        goblin.ac = 5
        goblin.position = [2, 0]
        gs.players = [cleric, wiz, goblin]
        gs.turn_index = 0

        # Cleric casts Bonus Action Parola Guaritrice (Lv 1), then tries leveled Action spell (Palla di Fuoco Lv 3) with already_consumed_slot=True -> rejected & slot 3 refunded!
        handle_cast_special_spell_request(
            {"spell_name": "Parola Guaritrice", "cast_level": 1, "base_level": 1, "casting_time": "bonus", "already_consumed_slot": False, "request_id": "ba-1"},
            cleric,
            gs,
        )
        self.assertEqual(cleric.full_sheet["spell_slots"]["1"]["current"], 3)
        self.assertTrue(cleric.spell_cast_bonus_action_this_turn)

        # Duplicate request_id ignored without spending another slot
        handle_cast_special_spell_request(
            {"spell_name": "Parola Guaritrice", "cast_level": 1, "base_level": 1, "casting_time": "bonus", "already_consumed_slot": False, "request_id": "ba-1"},
            cleric,
            gs,
        )
        self.assertEqual(cleric.full_sheet["spell_slots"]["1"]["current"], 3)

        # Action leveled spell with client pre-consumed Lv 3 slot (3 -> 2) is rejected by BA rule and REFUNDED (1 -> 2)
        cleric.full_sheet["spell_slots"]["3"]["current"] = 1
        handle_cast_special_spell_request(
            {"spell_name": "Palla di Fuoco", "cast_level": 3, "base_level": 3, "casting_time": "action", "already_consumed_slot": True, "request_id": "act-1"},
            cleric,
            gs,
        )
        self.assertEqual(cleric.full_sheet["spell_slots"]["3"]["current"], 2)

        # Cantrip Action after Bonus Action spell is allowed!
        cleric.conn.sent.clear()
        handle_cast_special_spell_request(
            {"spell_name": "Fiamma Sacra", "cast_level": 0, "base_level": 0, "casting_time": "action", "already_consumed_slot": False, "request_id": "cant-1"},
            cleric,
            gs,
        )
        self.assertTrue(cleric.has_acted_this_turn)

        # ClientGUI.handle_game_state pushes refunded server slots back onto active_character & CharacterSheetFrame widgets
        root = tk.Tk()
        root.withdraw()
        try:
            frame = CharacterSheetFrame(root, cleric_pc, manager=None, is_connected=True)
            cleric_pc.spell_slots["3"]["current"] = 1  # Stale client before GAME_STATE arrives
            frame.slot_vars["3"]["current"].set(1)
            c_mock = MagicMock()
            c_mock.name = "Kyra"
            c_mock.active_character = cleric_pc
            c_mock.stats_sheet_frame = frame
            c_mock.stats_detached_window = None
            c_mock._asset_cache = {}
            ClientGUI.handle_game_state(c_mock, gs.get_state_dict(is_dm=False))
            self.assertEqual(cleric_pc.spell_slots["3"]["current"], 2)
            self.assertEqual(cleric_pc.spell_slots["1"]["current"], 3)
            self.assertEqual(frame.slot_vars["3"]["current"].get(), 2)
            self.assertEqual(frame.slot_vars["1"]["current"].get(), 3)
        finally:
            root.destroy()


# ==============================================================================
# TEST SUITE 3: PERSISTENCE LOSSLESSNESS, RECONNECT & CHARACTER IMPORT
# ==============================================================================

class TestPersistenceReconnectionAndCharacterImportIntegration(unittest.TestCase):
    def test_player_gamestate_and_campaign_preserve_extra_fields(self):
        # Campaign extra fields round-trip
        c_raw = Campaign(name="La Cripta").to_dict()
        c_raw["custom_campaign_plugin"] = {"version": 2, "flags": ["hardcore"]}
        c_loaded = Campaign.from_dict(c_raw)
        c_out = c_loaded.to_dict()
        self.assertEqual(c_out["custom_campaign_plugin"], {"version": 2, "flags": ["hardcore"]})

        # Player & GameState extra fields round-trip
        gs = GameState(queue.Queue())
        p = _pc_to_player(make_fighter_pc("Kaelen", level=5), pos=[2, 3])
        p.action_surge_used_this_turn = True
        p.full_sheet["custom_hero_tag"] = "EroeDelNord"
        p_dict = p.to_dict()
        p_dict["future_player_flag"] = {"tier": 4}
        p_restored = Player.from_dict(p_dict)
        self.assertTrue(p_restored.action_surge_used_this_turn)
        self.assertEqual(p_restored.full_sheet["custom_hero_tag"], "EroeDelNord")
        self.assertEqual(p_restored.to_dict()["future_player_flag"], {"tier": 4})

        state_snap = gs.get_state_dict(is_dm=True)
        state_snap["players"] = [p_dict]
        state_snap["custom_session_metadata"] = {"seed": 9981}
        with tempfile.TemporaryDirectory() as tmpdir:
            snap_path = os.path.join(tmpdir, "session_snap.json")
            with open(snap_path, "w", encoding="utf-8") as fh:
                json.dump(state_snap, fh)
            gs.load_session(snap_path)
        reloaded = gs.get_state_dict(is_dm=True)
        self.assertEqual(reloaded["custom_session_metadata"], {"seed": 9981})
        self.assertEqual(reloaded["players"][0]["future_player_flag"], {"tier": 4})

    def test_import_party_character_bounds_and_reconnect_protects_server_state(self):
        from server.dm_campaign_session_mixin import import_party_character_to_game_state
        from server.rules.character import handle_update_full_sheet_request, handle_update_stats_request

        gs = GameState(queue.Queue())
        gs.current_map = {"width": 10, "height": 10, "spawn_point": [0, 0], "walls": [[0, 0]]}

        warlock = make_warlock_pc("Hex", level=5)
        warlock.pact_slots["current"] = 1  # Already spent 1 pact slot on server
        warlock.hp_current = 18  # Damaged on server (max 33)
        warlock_raw = warlock.to_dict()
        warlock_raw["hit_dice_current"] = 3
        warlock_raw["legacy_extra_field"] = "keep_me"

        imported = import_party_character_to_game_state(gs, warlock_raw, spawn_pos=[0, 0])  # [0,0] is a wall -> chooses free hex!
        self.assertNotEqual(tuple(imported.position), (0, 0))
        self.assertEqual(imported.role, "player")
        self.assertTrue(imported._preserve_server_state_on_join)
        self.assertTrue(imported._preserve_stats_on_join)
        self.assertEqual(imported.pact_slots_current, 1)
        self.assertEqual(imported.hit_dice_current, 3)

        # Simulate stale client reconnect packets trying to reset HP to 33 and pact slots to 2
        imported.conn = _MockConn()
        imported.conditions = ["Avvelenato"]
        handle_update_stats_request(make_update_stats_request(33, 33, 2, conditions=[])["data"], imported, gs)
        self.assertEqual(imported.hp, 18)
        self.assertEqual(imported.conditions, ["Avvelenato"])

        stale_sheet = copy.deepcopy(warlock.to_dict())
        stale_sheet["hp_current"] = 33
        stale_sheet["pact_slots"] = {"max": 2, "current": 2, "level": 3}
        stale_sheet["conditions"] = []
        handle_update_full_sheet_request(make_update_full_sheet_request(stale_sheet)["data"], imported, gs)
        self.assertEqual(imported.hp, 18)
        self.assertEqual(imported.full_sheet["pact_slots"]["current"], 1)
        self.assertEqual(imported.pact_slots_current, 1)
        self.assertEqual(imported.conditions, ["Avvelenato"])


# ==============================================================================
# TEST SUITE 4: REAL TCP LOOPBACK MULTIPLAYER E2E
# ==============================================================================

class TestLoopbackMultiplayerGameplayE2E(unittest.TestCase):
    def test_real_tcp_pin_combat_action_surge_spellcast_and_reconnect(self):
        from server.dm_campaign_session_mixin import import_party_character_to_game_state

        harness = LoopbackSessionHarness(session_password="Pin5e")
        try:
            gs = harness.server.game_state
            gs.automation_settings["strict_turn_lock"] = True

            # 1. Wrong PIN is rejected cleanly over real TCP
            bad_cli, bad_q, _ = harness.connect_client("Intruder", password="wrong")
            err_pkt = _wait_until(
                lambda: next((m for m in _drain_queue(bad_q) if m.get("type") == "ERROR_REPLY"), None),
                timeout=3.0,
            )
            self.assertIsNotNone(err_pkt)
            self.assertIsNone(gs.find_player("Intruder"))
            bad_cli.disconnect()

            # 2. Pre-import party onto DM Server with pre-existing state, then join over real TCP
            kaelen_pc = make_fighter_pc("Kaelen", level=5)
            elara_pc = make_wizard_pc("Elara", level=5)
            srv_kaelen = import_party_character_to_game_state(gs, kaelen_pc, spawn_pos=[0, 0])
            srv_elara = import_party_character_to_game_state(gs, elara_pc, spawn_pos=[0, 1])

            goblin = Player("Goblin", conn=None)
            goblin.hp = 100
            goblin.max_hp = 100
            goblin.ac = 5
            goblin.position = [1, 0]
            gs.add_player(goblin)

            c_k, q_k, _ = harness.connect_client("Kaelen", password="Pin5e")
            c_e, q_e, _ = harness.connect_client("Elara", password="Pin5e")
            self.assertTrue(_wait_until(lambda: srv_kaelen.conn is not None and srv_elara.conn is not None, timeout=3.0))

            # Start combat cleanly: Kaelen -> Elara -> Goblin
            with gs.lock:
                gs.players = [srv_kaelen, srv_elara, goblin]
            gs.start_combat(["Kaelen", "Elara", "Goblin"])
            from common.network_utils import broadcast
            broadcast(gs, make_game_state(gs.get_state_dict()))
            _drain_queue(q_k)
            _drain_queue(q_e)

            # 3. Turn-lock check: Elara tries to cast out-of-turn with pre-consumed slot -> rejected + slot refunded!
            elara_stale_slot_cast = make_cast_special_spell_request(
                "Dardo Incantato",
                cast_level=1,
                target_name="Goblin",
                casting_time="action",
                base_level=1,
                already_consumed_slot=False,
                request_id="tcp-oob-1",
            )
            c_e.send(elara_stale_slot_cast)
            e_msgs = []
            got_oob_err = _wait_until(
                lambda: (e_msgs.extend(_drain_queue(q_e)), any(m.get("type") == "ERROR_REPLY" for m in e_msgs))[-1],
                timeout=3.0,
            )
            self.assertTrue(got_oob_err)
            self.assertEqual(srv_elara.full_sheet["spell_slots"]["1"]["current"], 4)

            # 4. Kaelen performs 2 Extra Attacks + Action Surge + 3rd attack over TCP
            with patch("random.randint", side_effect=lambda a, b: max(a, (a + b) // 2)):
                for _ in range(2):
                    c_k.send(make_attack_request("Goblin", "Spada Lunga", 20, "1d8+4"))
                self.assertTrue(_wait_until(lambda: srv_kaelen.has_acted_this_turn, timeout=3.0))
                hp_after_two = goblin.hp
                self.assertLess(hp_after_two, 100)

                c_k.send(make_class_feature_request("action_surge", already_consumed=False))
                self.assertTrue(_wait_until(lambda: srv_kaelen.action_surge_used_this_turn and not srv_kaelen.has_acted_this_turn, timeout=3.0))
                c_k.send(make_attack_request("Goblin", "Spada Lunga", 20, "1d8+4"))
                self.assertTrue(_wait_until(lambda: goblin.hp < hp_after_two, timeout=3.0))

            # 5. Kaelen ends turn -> Elara casts Dardo Incantato on her turn -> Lv 1 slot drops 4 -> 3
            c_k.send(make_end_turn_request())
            self.assertTrue(_wait_until(lambda: (gs.get_current_turn_player() or SimpleNamespace(name="")).name == "Elara", timeout=3.0))
            _drain_queue(q_e)

            c_e.send(
                make_cast_special_spell_request(
                    "Dardo Incantato",
                    cast_level=1,
                    target_name="Goblin",
                    casting_time="action",
                    base_level=1,
                    already_consumed_slot=False,
                    request_id="tcp-mm-1",
                )
            )
            self.assertTrue(_wait_until(lambda: srv_elara.full_sheet["spell_slots"]["1"]["current"] == 3, timeout=3.0))

            # Damage Elara on server, then disconnect & reconnect with stale local sheet -> server state preserved!
            srv_elara.hp = 12
            srv_elara.full_sheet["hp_current"] = 12
            old_conn = srv_elara.conn
            c_e.disconnect()
            self.assertTrue(_wait_until(lambda: srv_elara.conn is not old_conn, timeout=3.0))

            c_e2, q_e2, _ = harness.connect_client("Elara", password="Pin5e")
            self.assertTrue(_wait_until(lambda: srv_elara.conn is not None, timeout=3.0))
            c_e2.send(make_update_stats_request(30, 30, 2, conditions=[]))
            stale_elara_sheet = make_wizard_pc("Elara", level=5).to_dict()
            c_e2.send(make_update_full_sheet_request(stale_elara_sheet))

            reconn_states = []
            got_state = _wait_until(
                lambda: (
                    reconn_states.extend(m for m in _drain_queue(q_e2) if m.get("type") == "GAME_STATE"),
                    len(reconn_states) >= 2,
                )[-1],
                timeout=3.0,
            )
            self.assertTrue(got_state)
            self.assertEqual(srv_elara.hp, 12)
            self.assertEqual(srv_elara.full_sheet["spell_slots"]["1"]["current"], 3)
            last_p_map = {p["name"]: p for p in reconn_states[-1]["data"].get("players", [])}
            self.assertEqual(last_p_map["Elara"]["hp"], 12)
            self.assertEqual(last_p_map["Elara"]["full_sheet"]["spell_slots"]["1"]["current"], 3)
        finally:
            harness.close()


class TestPhase35AndPhase4HardeningAndUX(unittest.TestCase):
    """
    Phase 3.5 & Phase 4 regression suite covering:
    - TASK-017: Fighter Lv 17+ Action Surge (2/rest, max 1/turn), unified rest resource restoration, 0-HD short rest
    - TASK-018: Lock-protected bounded TTL request_id dedup, rejected cast optimistic concentration cleanup,
                reconnect _preserve_join_until expiry, end_combat / 0-HP readied cleanup, _extra_fields guard
    - TASK-019 / TASK-020: UI class feature counters & tooltips, hero Conc badge, 0-HD rest UI, DM listbox badges

    Note: Tests in this class exercise in-memory server handlers and headless Tk widgets; real TCP socket E2E
    coverage lives in TestLoopbackMultiplayerGameplayE2E above.
    """

    def test_task017_fighter_lv17_action_surge_upgrade_and_rest_restoration(self):
        from server.rules.class_abilities import handle_class_feature_request
        from server.rules.combat import handle_short_rest_request
        from server.rules.character import trigger_group_long_rest

        # Client level-up 16 -> 17 upgrades Action Surge max 1 -> 2 and bumps current by delta
        f_pc = make_fighter_pc("Titus", level=16)
        f_pc.class_resources = {"second_wind": True, "action_surge": False, "action_surge_max": 1, "action_surge_current": 0}
        f_pc.custom_resources = [{"name": "Azione Furente", "current": 0, "max": 1, "reset_on": "short"}]
        ok_lvl, _ = f_pc.add_class_level("Guerriero")
        self.assertTrue(ok_lvl)
        self.assertEqual(f_pc.level, 17)
        self.assertEqual(f_pc.class_resources["action_surge_max"], 2)
        self.assertEqual(f_pc.class_resources["action_surge_current"], 1)
        self.assertTrue(f_pc.class_resources["action_surge"])
        self.assertEqual(f_pc.custom_resources[0]["max"], 2)
        self.assertEqual(f_pc.custom_resources[0]["current"], 1)

        # Fresh Lv 17 Fighter with legacy custom_resources max=1 upgrades automatically on server Action Surge
        gs = GameState(queue.Queue())
        gs.combat_active = True
        f17 = make_fighter_pc("Valkor", level=17)
        f17.superiority_dice_max = 4
        f17.superiority_dice_current = 1
        f17_p = _pc_to_player(f17, pos=[0, 0], conn=_MockConn())
        f17_p.full_sheet["custom_resources"] = [{"name": "Azione Furente", "current": 1, "max": 1, "reset_on": "short"}]
        warlock_p = _pc_to_player(make_warlock_pc("Malakor", level=5), pos=[1, 0], conn=_MockConn())
        warlock_p.full_sheet["pact_slots"]["current"] = 0
        barb_p = _pc_to_player(make_barbarian_pc("Krag", level=5), pos=[2, 0], conn=_MockConn())
        barb_p.full_sheet["class_resources"]["rage_current"] = 0
        barb_p.full_sheet["class_resources"]["rage_max"] = 3
        wiz_p = _pc_to_player(make_wizard_pc("Lyra", level=5), pos=[3, 0], conn=_MockConn())
        wiz_p.full_sheet["spell_slots"]["1"]["current"] = 1
        wiz_p.full_sheet["sorcery_points_max"] = 5
        wiz_p.full_sheet["sorcery_points_current"] = 1

        gs.players = [f17_p, warlock_p, barb_p, wiz_p]
        gs.turn_index = 0

        # Use #1 on Turn 1 -> consumes 1/2 (1 remaining)
        handle_class_feature_request({"feature": "action_surge", "request_id": "as-1"}, f17_p, gs)
        self.assertTrue(f17_p.action_surge_used_this_turn)
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_max"], 2)
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_current"], 1)
        self.assertTrue(f17_p.full_sheet["class_resources"]["action_surge"])

        # Same turn #2 -> rejected (PHB p. 72 max 1/turn) without burning 2nd charge
        f17_p.conn.sent.clear()
        handle_class_feature_request({"feature": "action_surge", "request_id": "as-2-same-turn"}, f17_p, gs)
        errs = [f for f in _decode_sent_frames(f17_p.conn.sent) if f.get("type") == "ERROR_REPLY"]
        self.assertTrue(errs)
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_current"], 1)

        # Next turn -> 2nd Action Surge succeeds and leaves 0/2
        f17_p.action_surge_used_this_turn = False
        handle_class_feature_request({"feature": "action_surge", "request_id": "as-3-next-turn"}, f17_p, gs)
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_current"], 0)
        self.assertFalse(f17_p.full_sheet["class_resources"]["action_surge"])

        # Spend Second Wind before resting
        handle_class_feature_request({"feature": "second_wind", "heal_amount": 18, "request_id": "sw-1"}, f17_p, gs)
        self.assertFalse(f17_p.full_sheet["class_resources"]["second_wind"])

        # Short Rest with 0 Hit Dice outside combat restores Fighter & Warlock short-rest resources
        gs.end_combat()
        handle_short_rest_request({"hd_spent": 0, "hp_recovered": 0}, f17_p, gs)
        handle_short_rest_request({"hd_spent": 0, "hp_recovered": 0}, warlock_p, gs)
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_current"], 2)
        self.assertTrue(f17_p.full_sheet["class_resources"]["action_surge"])
        self.assertTrue(f17_p.full_sheet["class_resources"]["second_wind"])
        self.assertEqual(f17_p.full_sheet["superiority_dice_current"], 4)
        self.assertFalse(f17_p.action_surge_used_this_turn)
        self.assertEqual(warlock_p.full_sheet["pact_slots"]["current"], 2)

        # Drain Fighter/Barb/Wizard then trigger Group Long Rest -> restores Rage, Spell Slots, Sorcery Points, Action Surge
        f17_p.full_sheet["class_resources"]["action_surge_current"] = 0
        f17_p.full_sheet["class_resources"]["action_surge"] = False
        trigger_group_long_rest(gs, reason="Riposo Test")
        self.assertEqual(f17_p.full_sheet["class_resources"]["action_surge_current"], 2)
        self.assertEqual(barb_p.full_sheet["class_resources"]["rage_current"], 3)
        self.assertEqual(wiz_p.full_sheet["spell_slots"]["1"]["current"], 4)
        self.assertEqual(wiz_p.full_sheet["sorcery_points_current"], 5)

        # Client 0-HD Short Rest preserves int return value and restores 2/2 Action Surge
        f_pc.class_resources["action_surge_current"] = 0
        f_pc.class_resources["action_surge"] = False
        f_pc.class_resources["second_wind"] = False
        rec = f_pc.short_rest(hd_to_spend=0)
        self.assertIsInstance(rec, int)
        self.assertEqual(rec, 0)
        self.assertEqual(f_pc.class_resources["action_surge_current"], 2)
        self.assertTrue(f_pc.class_resources["second_wind"])

    def test_task018_request_id_dedup_conc_cleanup_reconnect_expiry_and_end_combat(self):
        from server.rules.class_abilities import handle_cast_special_spell_request, handle_class_feature_request
        from server.rules.character import handle_update_stats_request
        from server.rules.combat import apply_damage

        # Protocol helpers attach distinct request_id by default, respect explicit overrides and None suppression
        m1 = make_class_feature_request("second_wind")
        m2 = make_class_feature_request("second_wind")
        self.assertTrue(m1["data"].get("request_id"))
        self.assertNotEqual(m1["data"]["request_id"], m2["data"]["request_id"])
        self.assertNotIn("request_id", make_class_feature_request("rage", request_id=None)["data"])
        s1 = make_cast_special_spell_request("Dardo Incantato")
        self.assertTrue(s1["data"].get("request_id"))

        gs = GameState(queue.Queue())
        gs.combat_active = True
        fighter = _pc_to_player(make_fighter_pc("Doran", level=5), pos=[0, 0], conn=_MockConn())
        fighter.hp = 20
        fighter.max_hp = 44
        wiz = _pc_to_player(make_wizard_pc("Nyx", level=5), pos=[1, 0], conn=_MockConn())
        wiz.readied_action_data = {"trigger": "Goblin moves", "action": "Dardo Incantato", "is_spell": True}
        wiz.conditions = ["Concentrazione", "Azione Preparata"]
        wiz.concentrating_on = None  # Simulates optimistic client Concentrazione before server commit
        wiz.full_sheet["conditions"] = list(wiz.conditions)

        rogue = _pc_to_player(make_rogue_pc("Shade", level=5), pos=[2, 0], conn=_MockConn())
        rogue.has_reacted_this_turn = True
        rogue.sneak_attack_used_this_turn = True
        rogue.readied_action_data = {"trigger": "Enemy attacks", "action": "Stocco", "is_spell": False}
        rogue.conditions = ["Azione Preparata"]

        gs.players = [fighter, wiz, rogue]
        gs.turn_index = 0

        # Class feature request_id deduplication (duplicate Second Wind ignored -> single heal only)
        handle_class_feature_request({"feature": "second_wind", "heal_amount": 8, "request_id": "dup-sw"}, fighter, gs)
        self.assertEqual(fighter.hp, 28)
        fighter.hp = 20
        fighter.full_sheet["class_resources"]["second_wind"] = True
        fighter.bonus_action_used_this_turn = False
        handle_class_feature_request({"feature": "second_wind", "heal_amount": 8, "request_id": "dup-sw"}, fighter, gs)
        self.assertEqual(fighter.hp, 20)

        # Bounded dedup cache (max 32 entries) evicts oldest once exceeded
        for idx in range(36):
            handle_cast_special_spell_request(
                {"spell_name": "Dardo Incantato", "cast_level": 1, "request_id": f"fill-{idx}"},
                fighter,  # Rejected for no slots/non-caster or processed into recent map -> wait test on wiz out of combat
                gs,
            )
        self.assertLessEqual(len(getattr(fighter, "_recent_spell_req_ids", {})), 32)

        # Rejected cast cleans optimistic "Concentrazione" when server concentrating_on is None, preserving if active
        gs.turn_index = 1
        wiz.conditions = ["Silenzio", "Concentrazione"]
        wiz.full_sheet["conditions"] = ["Silenzio", "Concentrazione"]
        wiz.concentrating_on = None
        handle_cast_special_spell_request(
            {"spell_name": "Dardo Incantato", "cast_level": 1, "base_level": 1, "concentration": True, "request_id": "rej-conc"},
            wiz,
            gs,
        )
        self.assertNotIn("Concentrazione", wiz.conditions)
        self.assertNotIn("Concentrazione", wiz.full_sheet["conditions"])

        wiz.concentrating_on = "Silenzio"
        wiz.conditions = ["Silenzio", "Concentrazione"]
        handle_cast_special_spell_request(
            {"spell_name": "Dardo Incantato", "cast_level": 1, "base_level": 1, "request_id": "rej-keep"},
            wiz,
            gs,
        )
        self.assertIn("Concentrazione", wiz.conditions)

        # Reconnect _preserve_join_until expiry allows post-handshake handle_update_stats_request
        fighter._preserve_stats_on_join = True
        fighter._preserve_server_state_on_join = True
        fighter._preserve_join_until = time.monotonic() - 1.0
        handle_update_stats_request({"hp": 31, "max_hp": 44, "initiative": 2, "conditions": []}, fighter, gs)
        self.assertEqual(fighter.hp, 31)
        self.assertFalse(fighter._preserve_stats_on_join)

        # Incapacitated via handle_update_stats_request clears readied action & Azione Preparata
        fighter.readied_action_data = {"trigger": "Any", "action": "Attack", "is_spell": False}
        fighter.conditions = ["Azione Preparata"]
        handle_update_stats_request({"hp": 31, "max_hp": 44, "initiative": 2, "conditions": ["Azione Preparata", "Incapacitato"]}, fighter, gs)
        self.assertIsNone(fighter.readied_action_data)
        self.assertNotIn("Azione Preparata", fighter.conditions)

        # apply_damage dropping target to 0 HP clears readied action & Azione Preparata
        wiz.hp = 5
        wiz.conditions = ["Azione Preparata", "Concentrazione"]
        wiz.readied_action_data = {"trigger": "Enemy casts", "action": "Fireball", "is_spell": True}
        wiz.concentrating_on = "Preparato: Fireball"
        apply_damage(wiz, 10, game_state=gs)
        self.assertEqual(wiz.hp, 0)
        self.assertIsNone(wiz.readied_action_data)
        self.assertNotIn("Azione Preparata", wiz.conditions)

        # end_combat resets readied actions, "Preparato:" concentration, reaction, and sneak attack
        wiz.concentrating_on = "Preparato: Palla di Fuoco"
        wiz.conditions = ["Azione Preparata", "Concentrazione"]
        wiz.readied_action_data = {"trigger": "Door opens", "action": "Cast", "is_spell": True}
        wiz.full_sheet["conditions"] = list(wiz.conditions)
        gs.end_combat()
        self.assertFalse(gs.combat_active)
        self.assertFalse(rogue.has_reacted_this_turn)
        self.assertFalse(rogue.sneak_attack_used_this_turn)
        self.assertIsNone(rogue.readied_action_data)
        self.assertNotIn("Azione Preparata", rogue.conditions)
        self.assertIsNone(wiz.concentrating_on)
        self.assertIsNone(wiz.readied_action_data)
        self.assertNotIn("Azione Preparata", wiz.conditions)
        self.assertNotIn("Concentrazione", wiz.conditions)
        self.assertNotIn("Concentrazione", wiz.full_sheet["conditions"])

        # _extra_fields / _extra_state_fields never nest self-keys across repeated from_dict / load_session
        p_rt = Player.from_dict({**fighter.to_dict(), "custom_flag": 42, "_extra_fields": {"stale": True}})
        self.assertNotIn("_extra_fields", p_rt._extra_fields)
        self.assertEqual(p_rt._extra_fields.get("custom_flag"), 42)
        c_rt = Campaign.from_dict({**Campaign(name="C1").to_dict(), "ext_k": "ok", "_extra_fields": {"stale": True}})
        self.assertNotIn("_extra_fields", c_rt._extra_fields)
        self.assertEqual(c_rt._extra_fields.get("ext_k"), "ok")

    def test_task019_and_task020_ui_counters_tooltips_conc_badge_zero_hd_rest_and_dm_badges(self):
        from client.client import ClientGUI
        from server.dm_gui import DM_GUI
        from common.i18n import _t

        root = tk.Tk()
        root.withdraw()
        try:
            pc17 = make_fighter_pc("Ares", level=17)
            pc17.class_resources = {
                "second_wind": True,
                "action_surge": True,
                "action_surge_max": 2,
                "action_surge_current": 2,
                "rage_current": 0,
                "rage_max": 0,
            }
            pc17.concentrating_on = "Scudo della Fede"
            pc17.temp_hp = 5
            pc17.hit_dice_current = 0

            # Build lightweight Tk host wired to real ClientGUI unbound methods
            host = SimpleNamespace()
            host.name = pc17.name
            host.active_character = pc17
            host.players_data = {pc17.name: {"hp": 44, "max_hp": 44, "temp_hp": 5, "concentrating_on": "Scudo della Fede", "conditions": []}}
            host.combat_active = True
            host.is_connected = True
            host._is_my_turn = True
            host.action_spent = False
            host.bonus_spent = False
            host.reaction_spent = False
            host.movement_spent_ft = 0
            host._attacks_made_this_turn = 0
            host._action_surge_used_this_turn = False
            host.character_manager = MagicMock()
            host.network = MagicMock()
            host.show_toast = MagicMock()

            host.hero_name_lbl = tk.Label(root)
            host.hero_class_lbl = tk.Label(root)
            host.hero_hp_lbl = tk.Label(root)
            host.hero_hp_bar_fill = tk.Frame(root)
            host.hero_ac_badge = tk.Label(root)
            host.hero_speed_badge = tk.Label(root)
            host.hero_init_badge = tk.Label(root)
            host.btn_act_tracker = tk.Button(root)
            host.btn_bonus_tracker = tk.Button(root)
            host.btn_react_tracker = tk.Button(root)
            host.class_features_frame = tk.LabelFrame(root)
            host.btn_second_wind = tk.Button(host.class_features_frame)
            host.btn_action_surge = tk.Button(host.class_features_frame)
            host.btn_rage = tk.Button(host.class_features_frame)
            host.combat_btn = tk.Button(root)
            host.combat_btn.pack()
            host.center_window = lambda *a, **kw: None

            # Bind methods needed for chained calls
            host._get_class_feature_counts = lambda: ClientGUI._get_class_feature_counts(host)
            host._get_feature_tooltip = lambda k: ClientGUI._get_feature_tooltip(host, k)
            host._update_contextual_class_features = lambda counts=None: ClientGUI._update_contextual_class_features(host, counts=counts)
            host.update_hero_summary_card = lambda: ClientGUI.update_hero_summary_card(host)
            host.update_action_economy_ui = lambda: ClientGUI.update_action_economy_ui(host)
            host._has_cunning_action = lambda: False

            # Hero card shows temp HP + Concentration spell badge
            host.update_hero_summary_card()
            hp_txt = host.hero_hp_lbl.cget("text")
            self.assertIn("+5 Temp", hp_txt)
            self.assertIn("🔮 [Conc: Scudo della Fede]", hp_txt)

            # Live counters show (2/2) for Lv 17 Action Surge & (1/1) for Second Wind
            host.update_action_economy_ui()
            self.assertIn("(2/2)", host.btn_action_surge.cget("text"))
            self.assertIn("(1/1)", host.btn_second_wind.cget("text"))
            self.assertEqual(str(host.btn_action_surge.cget("state")), "normal")

            # Use Action Surge once -> (1/2) left, button disabled for remainder of same turn with PHB p. 72 tooltip
            ClientGUI.use_action_surge(host)
            self.assertTrue(host._action_surge_used_this_turn)
            self.assertEqual(pc17.class_resources["action_surge_current"], 1)
            self.assertTrue(pc17.class_resources["action_surge"])
            self.assertIn("(1/2)", host.btn_action_surge.cget("text"))
            self.assertEqual(str(host.btn_action_surge.cget("state")), "disabled")
            tip_same_turn = host._get_feature_tooltip("action_surge")
            self.assertIn("1/2", tip_same_turn)
            self.assertIn("PHB p. 72", tip_same_turn)

            # Reset turn resources re-enables Action Surge with 1/2 still available
            ClientGUI.reset_turn_resources(host)
            self.assertFalse(host._action_surge_used_this_turn)
            self.assertEqual(str(host.btn_action_surge.cget("state")), "normal")

            # Language switch / apply_translations preserves live counters when active_character present
            host.btn_action_surge.config(text=_t("btn_action_surge"))
            host._update_contextual_class_features()
            self.assertIn("(1/2)", host.btn_action_surge.cget("text"))

            # DM player listbox row badges (+temp_hp, Conc, Prep, [A/B/R] on active turn)
            dm_mock = MagicMock()
            dm_mock.server = SimpleNamespace(game_state=SimpleNamespace(combat_active=True))
            dm_p = Player("Ares", conn=None)
            dm_p.hp = 38
            dm_p.max_hp = 44
            dm_p.temp_hp = 7
            dm_p.initiative = 18
            dm_p.concentrating_on = "Benedizione"
            dm_p.conditions = ["Benedetto", "Azione Preparata"]
            dm_p.has_acted_this_turn = True
            dm_p.bonus_action_used_this_turn = False
            dm_p.has_reacted_this_turn = True
            row = DM_GUI._format_dm_player_row(dm_mock, dm_p, prefix="➡️ ", is_turn=True, in_combat=True)
            self.assertIn("(HP: 38+7/44)", row)
            self.assertIn("[A:❌ B:✔ R:❌]", row)
            self.assertIn("🔮[Conc: Benedizione]", row)
            self.assertIn("⏳[Prep]", row)

            # Verify open_short_rest_dialog supports 0 HD rest button without returning empty warning-only close
            host.master = root
            host.combat_active = False
            pc17.class_resources["action_surge_current"] = 0
            pc17.class_resources["action_surge"] = False
            ClientGUI.open_short_rest_dialog(host)
            toplevels = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)]
            self.assertEqual(len(toplevels), 1)
            sr_win = toplevels[0]
            def _find_buttons(widget):
                from tkinter import ttk
                out = []
                for child in widget.winfo_children():
                    if isinstance(child, (ttk.Button, tk.Button)):
                        out.append(child)
                    out.extend(_find_buttons(child))
                return out
            sr_btns = _find_buttons(sr_win)
            zero_hd_btns = [b for b in sr_btns if "0 DV" in str(b.cget("text"))]
            self.assertTrue(zero_hd_btns, f"Expected 0-HD rest button, found {[b.cget('text') for b in sr_btns]}")
            zero_hd_btns[0].invoke()
            self.assertEqual(pc17.class_resources["action_surge_current"], 2)
            self.assertTrue(pc17.class_resources["action_surge"])
        finally:
            root.destroy()


class TestPhase45UxAuditAndWorkflows(unittest.TestCase):
    """Phase 4.5 UX audit, workflow polish, companion drag-drop & regression tests."""

    def test_localized_messagebox_yesno_and_okcancel(self):
        from common.messagebox import messagebox as app_mb

        for res, expected in [("Sì", True), ("si", True), ("Yes", True), ("OK", True), ("No", False), (None, False)]:
            with patch("common.messagebox.Messagebox.yesno", return_value=res):
                self.assertIs(app_mb.askyesno("Titolo", "Confermi?"), expected, f"yesno failed for {res!r}")
        for res, expected in [("OK", True), ("ok", True), ("Cancel", False), (None, False)]:
            with patch("common.messagebox.Messagebox.okcancel", return_value=res):
                self.assertIs(app_mb.askokcancel("Titolo", "Procedi?"), expected, f"okcancel failed for {res!r}")

    def test_login_dialog_unlocked_geometry_change_hero_and_pin_toggle(self):
        from client.login_ui import LoginDialog

        with tempfile.TemporaryDirectory() as tmpdir:
            settings_path = os.path.join(tmpdir, "settings.json")
            root = tk.Tk()
            root.withdraw()
            try:
                char = Character(name="Lyra")
                char.char_class = "Bardo"
                char.level = 4
                mock_cm = MagicMock()
                mock_cm.characters = [char]
                mock_cm.get_all_characters.return_value = [char]
                mock_cm.get_character.return_value = char
                root.geometry("1x1+-2000+-2000")
                root.deiconify()
                with patch.dict(os.environ, {"DND_SETTINGS_PATH": settings_path, "DND_MOCK_AUDIO": "1"}):
                    dlg = LoginDialog(root, mock_cm, initial_character=char, initial_ip="127.0.0.1", lock_character=True)
                    dlg.update()
                    geom_w, geom_h = [int(x) for x in dlg.geometry().split("+")[0].split("x")]
                    self.assertGreaterEqual(geom_h, dlg.winfo_reqheight(), "Login locked dialog clips vertically")
                    self.assertGreaterEqual(dlg.minsize()[1], dlg.winfo_reqheight())

                    # PIN eye toggle switches show="•" <-> ""
                    init_show = dlg.pin_entry.cget("show")
                    self.assertIn(init_show, ("•", "*"))
                    dlg._toggle_pin_visibility()
                    self.assertEqual(dlg.pin_entry.cget("show"), "")
                    dlg._toggle_pin_visibility()
                    self.assertEqual(dlg.pin_entry.cget("show"), init_show)

                    # "Cambia Eroe" unlocks character selector & expands height
                    dlg.unlock_character_selection()
                    dlg.update()
                    unlocked_h = int(dlg.geometry().split("+")[0].split("x")[1])
                    self.assertGreaterEqual(unlocked_h, 520)
                    self.assertFalse(dlg.lock_character)
                    self.assertIsNotNone(dlg.char_listbox)

                    # Invalid port validation prevents connect and history save
                    dlg.ip_var.set("127.0.0.1:99999")
                    with patch("client.login_ui.messagebox.showerror") as mock_err:
                        dlg.connect()
                        self.assertTrue(mock_err.called)
                    self.assertIsNone(dlg.result)
                    self.assertFalse(os.path.exists(settings_path))
                    dlg.destroy()
            finally:
                root.destroy()

    def test_hex_map_canvas_ownership_block_dm_token_click_and_companion_drag_drop(self):
        from components.ui_components import HexMapCanvas
        from common.hex_utils import Hex
        from client.client import ClientGUI
        from server.rules.movement import handle_move_request

        root = tk.Tk()
        root.withdraw()
        try:
            canvas = HexMapCanvas(root, width=500, height=400)
            canvas.pack()
            canvas.map_data = {"width": 10, "height": 10, "hex_size": 30, "grid_type": "hex"}
            canvas.players_data = {
                "Druido": {"name": "Druido", "position": [0, 0], "color": "#4CAF50", "hp": 28, "max_hp": 28},
                "Goblin": {"name": "Goblin", "position": [1, 0], "color": "#E53935", "hp": 7, "max_hp": 7},
                "LupoEvocato": {
                    "name": "LupoEvocato", "position": [0, 1], "color": "#60A5FA",
                    "hp": 11, "max_hp": 11, "owner": "Druido", "master_name": "Druido",
                },
            }
            canvas.redraw()
            canvas.update_idletasks()

            hex_clicks = []
            selected_tokens = []
            dropped_tokens = []
            canvas.on_hex_click_callback = lambda hx: hex_clicks.append((hx.q, hx.r))
            canvas.on_token_select_callback = lambda nm: selected_tokens.append(nm)
            canvas.on_token_drop_callback = lambda nm, q, r: dropped_tokens.append((nm, q, r))
            canvas.can_move_token_callback = lambda nm: (
                (True, "") if nm in ("Druido", "LupoEvocato") else (False, f"Token {nm} bloccato")
            )

            # DM / normal click on token selects it WITHOUT triggering hex click (fixes DM click-to-teleport)
            wx, wy = canvas.hex_layout.hex_to_pixel(Hex(1, 0))
            cx = int(round(wx * canvas.zoom_level + canvas.pan_offset_x))
            cy = int(round(wy * canvas.zoom_level + canvas.pan_offset_y))
            ev_click = SimpleNamespace(x=cx, y=cy, num=1, state=0)
            canvas._on_canvas_click(ev_click)
            self.assertEqual(selected_tokens, ["Goblin"])
            self.assertEqual(hex_clicks, [])

            # Dragging unowned token shows warning & blocks drop callback
            ev_drag = SimpleNamespace(x=cx + 30, y=cy + 10, state=0)
            with patch("components.ui_components.show_toast") as mock_toast:
                canvas._on_canvas_drag(ev_drag)
                self.assertTrue(mock_toast.called)
                self.assertTrue(canvas._drag_blocked_shown)
            canvas._on_canvas_release(SimpleNamespace(x=cx + 30, y=cy + 10))
            self.assertEqual(dropped_tokens, [])

            # When hex click priority (AoE/target mode) is active, clicking on a token triggers hex click!
            canvas.is_hex_click_priority_callback = lambda: True
            canvas._on_canvas_click(ev_click)
            self.assertEqual(len(hex_clicks), 1)
            self.assertEqual(hex_clicks[0], (1, 0))

            # Companion Drag-Drop end-to-end: ClientGUI.on_token_drop -> server handle_move_request
            gs = GameState(gui_queue=queue.Queue())
            gs.map_data = {"width": 10, "height": 10}
            druido = Player("Druido", conn=_MockConn())
            druido.position = [0, 0]
            druido.speed = 30
            lupo = Player("LupoEvocato", conn=None)
            lupo.position = [0, 1]
            lupo.speed = 40
            lupo.owner = "Druido"
            lupo.master_name = "Druido"
            lupo.is_npc = True
            gs.add_player(druido)
            gs.add_player(lupo)
            gs.combat_active = True
            gs.players.sort(key=lambda p: 10 if p.name == "Druido" else 5, reverse=True)
            gs.current_turn_index = 0

            client_host = SimpleNamespace(
                is_connected=True,
                name="Druido",
                active_character=Character("Druido"),
                players_data={
                    "Druido": {"name": "Druido", "position": [0, 0]},
                    "LupoEvocato": {"name": "LupoEvocato", "position": [0, 1], "owner": "Druido", "master_name": "Druido"},
                },
                network=MagicMock(),
                show_toast=MagicMock(),
                redraw_map_and_players=MagicMock(),
            )
            ClientGUI.on_token_drop(client_host, "LupoEvocato", 1, 1)
            self.assertTrue(client_host.network.send.called)
            sent_pkt = client_host.network.send.call_args[0][0]
            self.assertEqual(sent_pkt["data"]["entity_name"], "LupoEvocato")
            self.assertEqual(sent_pkt["data"]["to"], [1, 1])

            handle_move_request(sent_pkt["data"], druido, gs)
            self.assertEqual(lupo.position, [1, 1])
            self.assertEqual(druido.position, [0, 0])
        finally:
            root.destroy()

    def test_dm_workflows_hp_temp_absorption_spawn_party_level_and_dialogs(self):
        from server.dm_gui import DM_GUI
        from server.dm_campaign_session_mixin import find_free_spawn_hex
        from server.encounter_builder_ui import EncounterBuilderDialog
        from server.dm_entity_dialogs import open_combat_config, open_conditions_dialog

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(gui_queue=queue.Queue())
            gs.map_data = {"width": 10, "height": 10, "obstacles": []}
            hero = Player("Kaelen", conn=MagicMock())
            hero.hp = 20
            hero.max_hp = 30
            hero.temp_hp = 5
            hero.concentrating_on = "Benedizione"
            hero.full_sheet = {"hp_current": 20, "level": 5}
            gs.add_player(hero)

            dm_logs = []
            dm_mock = SimpleNamespace(
                master=root,
                server=SimpleNamespace(game_state=gs),
                log_to_chat=lambda msg: dm_logs.append(msg),
                map_canvas=MagicMock(),
                default_font=("Arial", 10),
            )

            # DM HP delta absorbs Temp HP, syncs full_sheet["hp_current"], warns Concentration DC 10
            with patch("server.dm_gui.broadcast"):
                DM_GUI.apply_dm_hp_delta(dm_mock, "Kaelen", -8)
            self.assertEqual(hero.temp_hp, 0)
            self.assertEqual(hero.hp, 17)
            self.assertEqual(hero.full_sheet["hp_current"], 17)
            self.assertTrue(any("CD 10" in l for l in dm_logs))

            # Non-overlapping spawn around (0, 0)
            hero.position = [0, 0]
            seen = set()
            for idx in range(4):
                hx = find_free_spawn_hex(gs, anchor_hex=[0, 0])
                self.assertNotIn(tuple(hx), seen)
                seen.add(tuple(hx))
                gob = Player(f"Goblin_{idx}", conn=None)
                gob.is_npc = True
                gob.position = hx
                gs.add_player(gob)

            # EncounterBuilder includes local is_party_member=True heroes in average level
            ally = Player("CompagnoLocale", conn=None)
            ally.is_npc = True
            ally.is_party_member = True
            ally.full_sheet = {"level": 5}
            gs.add_player(ally)
            eb = EncounterBuilderDialog(root, gs)
            info_txt = eb.lbl_party_info.cget("text")
            self.assertIn("Giocatori: 2", info_txt)
            self.assertIn("5.0", info_txt)
            eb.destroy()

            # open_conditions_dialog includes new 5e conditions while keeping Applica first
            dm_mock.get_player_name_from_listbox = lambda: "Kaelen"
            dm_mock.get_selected_player = lambda: (hero, "Kaelen")
            dm_mock._apply_status_update_to_player = MagicMock()
            open_conditions_dialog(dm_mock)
            cond_win = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            def _collect_widgets(w, cls_type):
                out = []
                for ch in w.winfo_children():
                    if isinstance(ch, cls_type):
                        out.append(ch)
                    out.extend(_collect_widgets(ch, cls_type))
                return out
            from tkinter import ttk
            cond_btns = _collect_widgets(cond_win, (ttk.Button, tk.Button))
            self.assertEqual(cond_btns[0].cget("text"), "Applica Condizioni")
            cond_listboxes = _collect_widgets(cond_win, tk.Listbox)
            cond_items = list(cond_listboxes[0].get(0, tk.END))
            for expected_cond in ("Afferrato", "Paralizzato", "Incapacitato"):
                self.assertIn(expected_cond, cond_items)
            cond_win.destroy()

            # open_combat_config applies inline NPC initiative entry & starts combat sorted
            captured_start = {}
            def _fake_start_combat(participant_names=None):
                captured_start["names"] = participant_names
                gs.combat_active = True
                gs.players.sort(key=lambda p: (p.name in (participant_names or []), p.initiative), reverse=True)
            gs.start_combat = _fake_start_combat
            dm_mock._announce_turn = MagicMock()
            hero.initiative = 12
            open_combat_config(dm_mock)
            cfg_win = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            # Find Goblin_0 row frame and set its inline initiative entry to 25 (highest)
            gob0_chk = next(
                c for c in _collect_widgets(cfg_win, (ttk.Checkbutton, tk.Checkbutton))
                if str(c.cget("text")).startswith("Goblin_0")
            )
            gob0_entry = next(c for c in _collect_widgets(gob0_chk.master, (ttk.Entry, tk.Entry)))
            gob0_entry.delete(0, tk.END)
            gob0_entry.insert(0, "25")
            from common.i18n import _t
            expected_start_lbl = _t("btn_start_combat")
            start_btn = next(
                b for b in _collect_widgets(cfg_win, (ttk.Button, tk.Button))
                if expected_start_lbl in str(b.cget("text")) or "Avvia" in str(b.cget("text")) or "Start" in str(b.cget("text"))
            )
            start_btn.invoke()
            self.assertTrue(gs.combat_active)
            self.assertEqual(gs.players[0].name, "Goblin_0")
            self.assertEqual(gs.players[0].initiative, 25)
            self.assertTrue(dm_mock._announce_turn.called)
        finally:
            root.destroy()

    def test_player_client_rollback_unread_chat_offhand_init_and_levelup(self):
        from tkinter import ttk
        from client.client import ClientGUI
        from client.network_handlers import ClientNetworkHandlersMixin
        from client.sheet_panels.combat_panel import CombatPanel
        from client.progression_ui import LevelUpDialog

        root = tk.Tk()
        root.withdraw()
        try:
            # 1. ClientGUI optimistic economy rollback + unread chat counter
            host = SimpleNamespace(
                is_connected=True,
                combat_active=True,
                _is_my_turn=True,
                name="Aria",
                session_password="secret",
                action_spent=False,
                bonus_spent=False,
                reaction_spent=False,
                _attacks_made_this_turn=0,
                _pending_economy_snapshot=None,
                sidebar_collapsed=False,
                _unread_chat_count=0,
                network=MagicMock(),
                show_toast=MagicMock(),
                update_action_economy_ui=lambda: None,
                _has_cunning_action=lambda: False,
            )
            ClientGUI.perform_dash(host)
            self.assertTrue(host.action_spent)
            self.assertIsInstance(host._pending_economy_snapshot, dict)
            ClientGUI._on_server_error_reply(host, {"text": "Azione negata dal server"})
            self.assertFalse(host.action_spent)
            self.assertIsNone(host._pending_economy_snapshot)

            with patch("client.client.messagebox.showerror"):
                ClientGUI._on_server_error_reply(host, {"text": "PIN di sessione errato"})
            self.assertEqual(host.session_password, "")

            # Unread chat counter when viewing another tab
            nb = ttk.Notebook(root)
            tab0 = ttk.Frame(nb)
            tab1 = ttk.Frame(nb)
            nb.add(tab0, text="Chat")
            nb.add(tab1, text="Scheda")
            nb.select(tab1)
            txt = tk.Text(tab0)
            host.right_notebook = nb
            host.chat_tabs = {"Globale": txt}
            ClientGUI.log_to_chat(host, "Nuovo messaggio DM", tab_name="Globale", sender="DM", color="gold")
            self.assertEqual(host._unread_chat_count, 1)
            self.assertEqual(nb.tab(0, "text"), "Chat (1)")
            nb.select(tab0)
            ClientGUI._on_right_notebook_tab_changed(host)
            self.assertEqual(host._unread_chat_count, 0)
            self.assertEqual(nb.tab(0, "text"), "Chat")

            # 2. CombatPanel Off-Hand attack forwards is_bonus_action=True
            recorded = []
            sheet_mock = SimpleNamespace(
                character=SimpleNamespace(
                    name="Aria", attributes={"FOR": 10, "DES": 16}, level=3, char_class="Ladro",
                    weapons=[{"name": "Pugnale", "ability": "DES", "damage_dice": "1d4", "damage_type": "Perforante", "properties": "Leggera"}],
                    find_ammunition=lambda _n: (None, None),
                ),
                weapons_cards_frame=ttk.Frame(root),
                attack_callback=lambda *a, **kw: None,
                execute_targeted_attack=lambda w, txc, dmg, **kw: recorded.append((w["name"], kw)),
                open_weapon_dialog=lambda *a, **kw: None,
                delete_weapon=lambda *a, **kw: None,
            )
            CombatPanel.refresh_weapons_list(sheet_mock)
            parent_w = sheet_mock.weapons_cards_frame
            def _find_buttons(w):
                out = []
                for ch in w.winfo_children():
                    if isinstance(ch, (ttk.Button, tk.Button)):
                        out.append(ch)
                    out.extend(_find_buttons(ch))
                return out
            offhand_btn = next(b for b in _find_buttons(parent_w) if "2ª Mano" in str(b.cget("text")))
            offhand_btn.invoke()
            self.assertEqual(recorded[0][1].get("is_bonus_action"), True)

            # 3. Initiative uses get_initiative_bonus() (e.g. Alert feat +5)
            init_char = Character("Sentinella")
            init_char.attributes["DES"] = 14  # +2
            init_char.feats = ["Allerta"]     # +5 => +7 total
            init_host = SimpleNamespace(
                master=root,
                active_character=init_char,
                name="Sentinella",
                network=MagicMock(),
                show_toast=MagicMock(),
                log_to_chat=MagicMock(),
            )
            with patch("tkinter.Toplevel.grab_set"), patch("random.randint", return_value=10):
                ClientNetworkHandlersMixin.handle_request_initiative(init_host, {})
                init_win = [w for w in root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
                init_btns = _find_buttons(init_win)
                roll_btn = next(b for b in init_btns if "Tira" in str(b.cget("text")) or "Roll" in str(b.cget("text")) or "🎲" in str(b.cget("text")))
                roll_btn.invoke()
            sent_init = init_host.network.send.call_args[0][0]["data"]["initiative"]
            self.assertEqual(sent_init, 10 + init_char.get_initiative_bonus())

            # 4. LevelUpDialog locks subclass combo before unlock_lvl & auto-switches ASI radio
            lu_char = Character("Beren")
            lu_char.char_class = "Guerriero"
            lu_char.level = 1  # Leveling to 2 (unlock_lvl=3) -> subclass disabled
            lu_dlg = LevelUpDialog(root, lu_char, lambda *a: None)
            self.assertEqual(str(lu_dlg.subclass_combo.cget("state")), "disabled")
            lu_dlg.destroy()

            asi_char = Character("Beren4")
            asi_char.char_class = "Guerriero"
            asi_char.level = 3  # Leveling to 4 -> ASI tab enabled
            asi_dlg = LevelUpDialog(root, asi_char, lambda *a: None)
            def _find_combos(w):
                out = []
                for ch in w.winfo_children():
                    if isinstance(ch, ttk.Combobox):
                        out.append(ch)
                    out.extend(_find_combos(ch))
                return out
            asi_combos = _find_combos(asi_dlg.tab_asi)
            # Combos in tab_asi: [single_stat, dual_stat_1, dual_stat_2, feat_combo]
            self.assertGreaterEqual(len(asi_combos), 4)
            asi_combos[2].set("COS")
            asi_combos[2].event_generate("<<ComboboxSelected>>")
            asi_dlg.update_idletasks()
            self.assertEqual(asi_dlg.asi_choice_var.get(), "dual")
            feat_vals = list(asi_combos[3].cget("values") or [])
            if feat_vals:
                asi_combos[3].set(feat_vals[0])
                asi_combos[3].event_generate("<<ComboboxSelected>>")
                asi_dlg.update_idletasks()
                self.assertEqual(asi_dlg.asi_choice_var.get(), "feat")
            asi_dlg.destroy()
        finally:
            root.destroy()


# ==============================================================================
# TEST SUITE 7: PHASE 5 END-TO-END WORKFLOWS A-D
# ==============================================================================

class TestPhase5EndToEndWorkflows(unittest.TestCase):
    """Deterministic Phase 5 end-to-end integration tests across Workflows A-D."""

    def test_workflow_a_campaign_scene_walls_fow_journal_backup_and_share_lore(self):
        from client.player_journal_dialog import PlayerJournalDialog
        from common.campaign_journal import CampaignJournal, JournalEvent, JournalSession
        from common.hex_utils import Hex, has_line_of_sight
        from common.network_utils import resolve_map_image_data
        from server.dm_live_flow import DMLiveFlowDialog

        with tempfile.TemporaryDirectory() as td:
            camp_dir = os.path.join(td, "cripta_e2e")
            maps_dir = os.path.join(camp_dir, "maps")
            os.makedirs(maps_dir, exist_ok=True)
            map_file = os.path.join(maps_dir, "cripta.json")
            with open(map_file, "w", encoding="utf-8") as mf:
                json.dump(
                    {
                        "name": "Cripta Antica",
                        "grid_type": "hex",
                        "hexes": [[q, r] for q in range(6) for r in range(6)],
                        "walls": [[1, 0]],
                        "doors": [
                            {"q": 2, "r": 0, "state": "secret", "is_secret": True, "discovered": False},
                            {"q": 0, "r": 1, "state": "closed", "is_secret": False},
                        ],
                        "lights": [{"q": 0, "r": 0, "radius": 3, "color": "#ffbb44"}],
                        "fow_enabled": True,
                        "fow_revealed": [[0, 0]],
                        "fow_draft": [[4, 4]],
                        "bg_image_data": "ZmFrZQ==",
                    },
                    mf,
                )

            camp = Campaign(name="Cripta E2E", folder_path=camp_dir)
            camp.starting_map_file = "maps/cripta.json"
            camp.description = "Versione 1"
            camp.add_scene("Atrio", "maps/cripta.json", "Ingresso della cripta")
            camp.quests = [
                {"title": "Trova l'altare", "status": "In Corso", "completed": False, "dm_notes": "Trappola a DC 16"},
                {"title": "Patto Segreto", "status": "In Corso", "secret": True},
            ]
            camp.handouts = [
                {"title": "Iscrizione Pubblica", "content": "Prega prima di entrare", "is_revealed": True},
                {"title": "Lettera del Negromante", "content": "Solo DM", "is_revealed": False},
            ]
            journal = CampaignJournal(campaign_name="Cripta E2E")
            sess = JournalSession(
                session_number=1,
                title="Discesa",
                prose="### Capitolo 1\nIl gruppo **entra** nell'atrio.\n- Torce accese",
                dm_notes="NOTA SEGRETA DM",
            )
            sess.events = [
                JournalEvent(category="dm_note", title="Segreto", description="TRAP_DM_ONLY", data={"dm_only": True}, timestamp="09:00"),
                JournalEvent(category="discovery", title="Soglia", description="Porta runica individuata", timestamp="09:10"),
            ]
            journal.sessions = [sess]
            camp.journal = journal

            camp.save(camp_dir)
            camp.description = "Versione 2"
            camp.save(camp_dir)

            manifest_path = os.path.join(camp_dir, "campaign.json")
            bak_path = manifest_path + ".bak"
            self.assertTrue(os.path.exists(bak_path))
            with open(bak_path, "r", encoding="utf-8") as bf:
                self.assertEqual(json.load(bf)["description"], "Versione 1")

            reloaded = Campaign.load(camp_dir)
            self.assertEqual(reloaded.description, "Versione 2")
            self.assertEqual(len(reloaded.scenes), 1)

            gs = GameState(queue.Queue())
            reloaded.apply_to_game_state(gs)
            self.assertEqual(gs.current_map.get("name"), "Cripta Antica")
            self.assertEqual(resolve_map_image_data(gs.current_map), "ZmFrZQ==")
            self.assertEqual(len(gs.current_map.get("lights", [])), 1)

            hero = Player("Lyra", conn=object())
            hero.position = [0, 0]
            hero.is_party_member = True
            hero.light_radius = 20
            hero.full_sheet = {"name": "Lyra", "notes": "Note pubbliche.\n\nDM SECRET: Chiave d'osso"}
            hidden_fow_orc = Player("OrcoNascosto")
            hidden_fow_orc.position = [4, 4]
            hidden_fow_orc.is_party_member = False
            gs.players = [hero, hidden_fow_orc]

            player_state = gs.get_state_dict(is_dm=False)
            dm_state = gs.get_state_dict(is_dm=True)
            self.assertEqual(len(dm_state["quests"]), 2)
            self.assertEqual([q["title"] for q in player_state["quests"]], ["Trova l'altare"])
            self.assertNotIn("dm_notes", player_state["quests"][0])
            self.assertEqual([h["title"] for h in player_state["handouts"]], ["Iscrizione Pubblica"])
            self.assertNotIn("Chiave d'osso", player_state["players"][0]["full_sheet"]["notes"])
            self.assertEqual([p["name"] for p in player_state["players"]], ["Lyra"])

            p_map = player_state["map"]
            self.assertEqual(p_map.get("fow_draft", []), [])
            self.assertIn([2, 0], p_map["walls"])
            self.assertFalse(has_line_of_sight(Hex(0, 0), Hex(3, 0), p_map["walls"]))

            root = tk.Tk()
            root.withdraw()
            try:
                with patch("client.player_journal_dialog.get_writable_dir", return_value=td):
                    jdlg = PlayerJournalDialog(root, campaign_journal=reloaded.journal, character_name="Lyra")
                    ev_txt = jdlg.txt_events.get("1.0", tk.END)
                    self.assertNotIn("TRAP_DM_ONLY", ev_txt)
                    self.assertIn("Porta runica individuata", ev_txt)
                    prose_txt = jdlg.txt_prose.get("1.0", tk.END)
                    self.assertIn("Capitolo 1", prose_txt)
                    self.assertNotIn("###", prose_txt)
                    jdlg.destroy()

                lore_node = MagicMock(
                    title="Stele dell'Alba",
                    data={"author": "Saggio", "language": "Comune", "read_aloud": "Sigillo spezzato"},
                )
                flow_mock = MagicMock(spec=DMLiveFlowDialog)
                flow_mock._get_game_state.return_value = gs
                flow_mock.game_state = gs
                flow_mock.dm_gui = MagicMock()
                flow_mock.session_ledger = MagicMock()
                flow_mock.active_campaign = reloaded
                with patch("common.network_utils.broadcast") as mock_bcast, \
                     patch("server.dm_live_flow.messagebox.showinfo"):
                    DMLiveFlowDialog.share_lore(flow_mock, lore_node)
                    bcast_pkt = mock_bcast.call_args[0][1]
                    self.assertEqual(bcast_pkt["type"], "HANDOUT_BROADCAST")
                    self.assertIsNone(bcast_pkt["data"]["image_b64"])
                    self.assertIn("Sigillo spezzato", bcast_pkt["data"]["content"])
                revealed_state = gs.get_state_dict(is_dm=False)
                self.assertTrue(any(h.get("title") == "Stele dell'Alba" and h.get("is_revealed") for h in revealed_state["handouts"]))
            finally:
                try:
                    if root.winfo_exists():
                        root.destroy()
                except tk.TclError:
                    pass

    def test_workflow_b_real_tcp_pin_reconnect_keepalive_asset_dedup_clamp_and_password_retain(self):
        from client.client import ClientGUI
        from client.network_handlers import ClientNetworkHandlersMixin
        from common.network_utils import prepare_per_player_state_payload
        from server.dm_campaign_session_mixin import import_party_character_to_game_state

        harness = LoopbackSessionHarness(session_password="Pin5e")
        try:
            gs = harness.server.game_state
            kaelen_pc = make_fighter_pc("Kaelen", level=5)
            kaelen_pc.hp_current = 22
            kaelen_pc.hp_max = 44
            kaelen_pc.avatar_b64 = "ZmFrZV9wbmdfYnl0ZXNfZWJfaWNvbg=="
            srv_k = import_party_character_to_game_state(gs, kaelen_pc, spawn_pos=[0, 0])
            srv_k.avatar_b64 = kaelen_pc.avatar_b64
            srv_k.full_sheet["avatar_b64"] = kaelen_pc.avatar_b64

            # 1. Wrong PIN refused over TCP
            bad_cli, bad_q, _ = harness.connect_client("Intruder", password="wrong")
            err_pkt = _wait_until(
                lambda: next((m for m in _drain_queue(bad_q) if m.get("type") == "ERROR_REPLY"), None),
                timeout=3.0,
            )
            self.assertIsNotNone(err_pkt)
            bad_cli.disconnect()

            # 2. First join receives full avatar asset + avatar_hash; second payload deduplicates it
            c1, q1, d1 = harness.connect_client("Kaelen", password="Pin5e")
            state_pkt1 = _wait_until(
                lambda: next((m for m in _drain_queue(q1) if m.get("type") == "GAME_STATE"), None),
                timeout=3.0,
            )
            self.assertIsNotNone(state_pkt1)
            k1 = next(p for p in state_pkt1["data"]["players"] if p["name"] == "Kaelen")
            self.assertEqual(k1.get("avatar_b64"), "ZmFrZV9wbmdfYnl0ZXNfZWJfaWNvbg==")
            av_hash = k1.get("avatar_hash")
            self.assertTrue(bool(av_hash))

            class _DummyClient(ClientNetworkHandlersMixin):
                pass

            dummy = _DummyClient()
            cache = ClientNetworkHandlersMixin._get_asset_cache(dummy)
            dummy._resolve_cached_avatar_assets(state_pkt1["data"]["players"])
            self.assertEqual(cache.get(av_hash), "ZmFrZV9wbmdfYnl0ZXNfZWJfaWNvbg==")

            dedup_pkt = prepare_per_player_state_payload(make_game_state(gs.get_state_dict(is_dm=True)), srv_k)
            k_dedup = next(p for p in dedup_pkt["data"]["players"] if p["name"] == "Kaelen")
            self.assertFalse(k_dedup.get("avatar_b64"))
            self.assertEqual(k_dedup.get("avatar_hash"), av_hash)
            dummy._resolve_cached_avatar_assets(dedup_pkt["data"]["players"])
            self.assertEqual(k_dedup.get("avatar_b64"), "ZmFrZV9wbmdfYnl0ZXNfZWJfaWNvbg==")

            # 3. Cross-IP / fresh socket reconnect with known_asset_hashes & stale client resource clamp
            old_sock = srv_k.conn
            c2, q2, _ = harness.connect_client(None)
            c2.send(make_join("Kaelen", password="Pin5e", known_asset_hashes=[av_hash]))
            self.assertTrue(_wait_until(lambda: srv_k.conn is not None and srv_k.conn is not old_sock and d1.is_set(), timeout=3.0))

            # Client attempting to push inflated HP after trusted window is clamped to server authority
            c2.send(
                make_update_full_sheet_request(
                    {"name": "Kaelen", "hp_current": 999, "hp_max": 44, "ac": 18}
                )
            )
            time.sleep(0.15)
            self.assertEqual(srv_k.hp, 22)

            # 4. PING -> PONG keepalive in ClientNetwork
            net2 = ClientNetwork(queue.Queue(), lambda: None)
            net2.is_connected = True
            net2.client_socket = MagicMock()
            msgs = iter([{"type": "PING", "data": {}}, None])
            with patch("client.network.receive_message", side_effect=lambda _s, **_kw: next(msgs)), \
                 patch.object(net2, "send", return_value=True) as mock_send:
                net2.listen_to_server()
                mock_send.assert_any_call({"type": "PONG", "data": {}})

            # 5. ClientGUI preserves session_password across transient drop
            root = tk.Tk()
            root.withdraw()
            try:
                with patch.object(ClientGUI, "process_queue", return_value=None):
                    cli = ClientGUI(root, session_password="Pin5e")
                cli.network.is_connected = True
                cli.handle_disconnection(silent=True)
                self.assertEqual(cli.session_password, "Pin5e")
                with patch("client.client.messagebox.askokcancel", return_value=True):
                    cli.on_closing()
            finally:
                try:
                    if root.winfo_exists():
                        root.destroy()
                except tk.TclError:
                    pass
        finally:
            harness.close()

    def test_workflow_c_tabletop_and_full_combat_initiative_death_saves_rests_display_writeback(self):
        from client.character_manager import CharacterManager
        from server.dm_campaign_session_mixin import import_party_character_to_game_state
        from server.dm_dialogs import DMPlayerSheetViewer
        from server.dm_gui import DM_GUI
        from server.rules.combat import handle_death_save_request

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "characters.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                pc_char = make_fighter_pc("Garrick", level=5)
                pc_char.temp_hp = 8
                pc_char.hit_dice_total = 5
                pc_char.hit_dice_current = 2
                pc_char.spell_slots["1"] = {"max": 2, "current": 2}
                pc_char.custom_resources = [{"name": "Azione Impetuosa", "current": 0, "max": 1, "reset_on": "short"}]
                mgr = CharacterManager()
                mgr.add_character(pc_char)

                root = tk.Tk()
                root.withdraw()
                try:
                    with patch("server.network.Server.start"), patch.object(DM_GUI, "process_queue", return_value=None):
                        dm = DM_GUI(root)
                    gs = dm.server.game_state

                    srv_pc = import_party_character_to_game_state(gs, pc_char.to_dict(), spawn_pos=[0, 0])
                    self.assertTrue(srv_pc.is_party_member)

                    goblin = Player("Goblin")
                    goblin.hp = 20
                    goblin.max_hp = 20
                    goblin.is_npc = True
                    goblin.position = [1, 0]
                    ogre_gm = Player("Ogre Occulto")
                    ogre_gm.hp = 59
                    ogre_gm.max_hp = 59
                    ogre_gm.is_npc = True
                    ogre_gm.is_hidden = True
                    ogre_gm.layer = "gm"
                    ogre_gm.position = [2, 0]
                    gs.players.extend([goblin, ogre_gm])

                    # Roll initiative for NPCs only — local PC skipped
                    with patch("random.randint", return_value=12), patch("server.dm_gui.broadcast"):
                        dm.roll_all_npcs_initiative()
                    self.assertEqual(srv_pc.initiative, 0)
                    self.assertGreater(goblin.initiative, 0)
                    self.assertGreater(ogre_gm.initiative, 0)

                    # Start combat + TempHP absorption + drop to 0 HP
                    gs.start_combat(["Garrick", "Goblin"])
                    with patch("server.dm_gui.broadcast"):
                        dm.apply_dm_hp_delta("Garrick", -14, trigger_gui=False, log_change=False)
                    self.assertEqual(srv_pc.temp_hp, 0)
                    self.assertEqual(srv_pc.hp, 38)
                    with patch("server.dm_gui.broadcast"):
                        dm.apply_dm_hp_delta("Garrick", -40, trigger_gui=False, log_change=False)
                    self.assertEqual(srv_pc.hp, 0)
                    self.assertIn("Incosciente", srv_pc.conditions)

                    # Server-authoritative Death Save nat-1 adds 2 failures; direct _apply_hp_change honors same_hit_secondary
                    from server.rules.combat import _apply_hp_change
                    with patch("server.rules.combat.broadcast"):
                        _apply_hp_change(srv_pc, -5, gs, same_hit_secondary=True)
                        self.assertEqual((getattr(srv_pc, "death_saves", None) or {}).get("failures", 0), 0)
                        handle_death_save_request({"manual_roll": 1, "actor_name": "Garrick"}, None, gs)
                        self.assertEqual(srv_pc.death_saves["failures"], 2)
                        _apply_hp_change(srv_pc, -5, gs)
                    self.assertEqual(srv_pc.death_saves["failures"], 3)
                    self.assertIn("Morto", srv_pc.conditions)
                    srv_pc.conditions = [c for c in srv_pc.conditions if c != "Morto"]
                    srv_pc.death_saves["failures"] = 2

                    # Interactive DMPlayerSheetViewer tabletop controls (nat 20 rescue, slot spend, ability roll)
                    viewer = DMPlayerSheetViewer(
                        root,
                        "Garrick",
                        srv_pc.full_sheet,
                        game_state=gs,
                        on_change_callback=lambda msg=None: dm._on_dm_sheet_changed("Garrick", msg),
                    )
                    with patch("server.dm_dialogs.random.randint", return_value=20):
                        viewer.roll_death_save()
                    self.assertEqual(srv_pc.hp, 1)
                    self.assertNotIn("Incosciente", srv_pc.conditions)

                    viewer._adjust_spell_slot("1", -1)
                    self.assertEqual(srv_pc.full_sheet["spell_slots"]["1"]["current"], 1)
                    with patch("server.dm_dialogs.random.randint", return_value=15):
                        total = viewer.roll_ability_check("FOR", proficient=True)
                    self.assertGreaterEqual(total, 15)
                    viewer.destroy()

                    # Short Rest restores custom short-rest resource; Long Rest restores HP, slots & half HD
                    with patch("server.dm_gui.broadcast"):
                        dm.advance_time(1, is_rest=True)
                    self.assertEqual(srv_pc.full_sheet["custom_resources"][0]["current"], 1)

                    with patch("server.dm_gui.broadcast"):
                        dm.advance_time(8, is_rest=True)
                    self.assertEqual(srv_pc.hp, 44)
                    self.assertEqual(srv_pc.full_sheet["spell_slots"]["1"]["current"], 2)
                    self.assertEqual(srv_pc.full_sheet["hit_dice_current"], 4)

                    # Detached read-only Player Display hides GM-layer & hidden NPCs
                    disp_win = dm.open_player_display_window()
                    self.assertFalse(dm.player_display_canvas.is_dm)
                    self.assertFalse(dm.player_display_canvas.can_move_token_callback("Garrick", (0, 0), (1, 1)))
                    self.assertIn("Garrick", dm.player_display_canvas.players_data)
                    self.assertIn("Goblin", dm.player_display_canvas.players_data)
                    self.assertNotIn("Ogre Occulto", dm.player_display_canvas.players_data)
                    self.assertTrue(disp_win.winfo_exists())

                    with patch("server.dm_gui.messagebox.askokcancel", return_value=True):
                        dm.on_closing()

                    # Verify writeback persisted to CharacterManager
                    reloaded = CharacterManager().get_character_by_name("Garrick")
                    self.assertIsNotNone(reloaded)
                    self.assertEqual(reloaded.hp_current, 44)
                    self.assertEqual(reloaded.spell_slots["1"]["current"], 2)
                finally:
                    try:
                        if root.winfo_exists():
                            root.destroy()
                    except tk.TclError:
                        pass

    def test_workflow_d_wizard_inventory_levelup_multires_sheet_and_client_hud(self):
        from client.character_creation_wizard import CharacterCreationWizardFrame
        from client.character_manager import CharacterManager
        from client.character_sheet_ui import CharacterSheetUI
        from client.client import ClientGUI
        from client.progression_ui import LevelUpDialog
        from common.item_modifiers import compute_effective_ac
        from common.theme import apply_modern_window_style

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                mgr = CharacterManager()
                root = tk.Tk()
                root.withdraw()
                try:
                    # 1. CharacterCreationWizardFrame -> created Lv1 Character + _extra_fields round-trip
                    created_chars = []
                    wiz = CharacterCreationWizardFrame(
                        root,
                        mgr,
                        on_complete_callback=lambda c: created_chars.append(c),
                        is_embedded=True,
                    )
                    wiz.char_data["name"] = "Aerin"
                    wiz.char_data["race"] = "Elfo"
                    wiz.char_data["char_class"] = "Mago"
                    wiz.char_data["attributes"] = {"FOR": 8, "DES": 16, "COS": 14, "INT": 16, "SAG": 12, "CAR": 10}
                    with patch("urllib.request.urlopen", side_effect=OSError("offline")), \
                         patch("client.character_creation_wizard.messagebox.showinfo"):
                        wiz.finish_creation()
                        _wait_until(
                            lambda: (root.update(), bool(created_chars))[-1],
                            timeout=3.0,
                        )
                    self.assertEqual(len(created_chars), 1)
                    char = created_chars[0]
                    char._extra_fields["e2e_marker"] = "phase5"
                    char.inventory_grid = [
                        {
                            "name": "Armatura di Cuoio Borchiato",
                            "type": "Armatura",
                            "container": "equipped",
                            "qty": 1,
                        }
                    ] + [None] * 19
                    char.ac = compute_effective_ac(char)
                    self.assertEqual(char.ac, 16)
                    mgr.save_characters()

                    reloaded = CharacterManager().get_character_by_name("Aerin")
                    self.assertIsNotNone(reloaded)
                    self.assertEqual(reloaded._extra_fields.get("e2e_marker"), "phase5")

                    # 2. Multi-resolution CharacterSheetUI geometry probe (1920x1080, 1366x768, 860x700)
                    ui = CharacterSheetUI(root, reloaded, mgr, is_connected=False)
                    sheet = ui.sheet_frame
                    for geom, expected_mode in (
                        ("1920x1080", "wide4"),
                        ("1366x768", "wide4"),
                        ("860x700", "compact"),
                    ):
                        ui.geometry(geom)
                        ui.update_idletasks()
                        ui.update()
                        sheet._apply_responsive_layout(force=True)
                        ui.update()
                        self.assertEqual(sheet._layout_mode, expected_mode)
                        self.assertGreater(sheet.winfo_width(), 200)
                        self.assertGreater(sheet.winfo_height(), 200)
                        self.assertGreater(sheet.notebook.winfo_width(), 200)
                        self.assertGreater(sheet.lbl_sheet_banner.winfo_width(), 100)
                    ui.destroy()

                    # 3. LevelUpDialog Lv1 -> Lv2 unlocks Wizard Arcane Tradition & updates slots cleanly
                    up_calls = []
                    lu = LevelUpDialog(root, reloaded, lambda *a: up_calls.append(a))
                    self.assertEqual(str(lu.subclass_combo.cget("state")), "readonly")
                    with patch("client.progression_ui.messagebox.showinfo"), \
                         patch("client.progression_ui.messagebox.showwarning"):
                        lu.apply()
                    self.assertEqual(reloaded.level, 2)
                    self.assertEqual(reloaded.spell_slots["1"]["max"], 3)
                    self.assertTrue(len(up_calls) >= 1)

                    # 4. Theme Escape exits fullscreen first & Player HUD sidebar/indicator active
                    win = tk.Toplevel(root)
                    win.title("E2E Probe")
                    win.geometry("640x480")
                    apply_modern_window_style(win)
                    win.deiconify()
                    win.update()
                    win.focus_force()
                    win.update()
                    with patch.object(win, "attributes", side_effect=[True, None]) as mock_attr:
                        win.event_generate("<Escape>")
                        win.update()
                        mock_attr.assert_any_call("-fullscreen", False)
                    self.assertTrue(win.winfo_exists())
                    with patch.object(win, "attributes", return_value=False):
                        win.event_generate("<Escape>")
                        win.update()
                    self.assertFalse(win.winfo_exists())

                    with patch.object(ClientGUI, "process_queue", return_value=None):
                        cli = ClientGUI(root, initial_character=reloaded)
                    self.assertTrue(hasattr(cli, "hud_conn_btn"))
                    self.assertTrue(hasattr(cli, "hdr_conn_badge"))
                    self.assertTrue(hasattr(cli, "controls_canvas"))
                    with patch("client.client.messagebox.askokcancel", return_value=True):
                        cli.on_closing()
                finally:
                    try:
                        if root.winfo_exists():
                            root.destroy()
                    except tk.TclError:
                        pass


if __name__ == "__main__":
    unittest.main()
