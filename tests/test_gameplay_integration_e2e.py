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


if __name__ == "__main__":
    unittest.main()
