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


if __name__ == "__main__":
    unittest.main()
