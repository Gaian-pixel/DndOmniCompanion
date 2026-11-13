"""
tests/test_audit_fixes.py - Test di regressione mirati per i fix dell'audit completo.
"""

import os
import sys
import queue
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["DND_MOCK_AUDIO"] = "1"

from common.game_state import GameState, Player
from common.network_utils import is_dm_actor
from common.srd_offline import normalize_npc_actions
from common.theme import setup_theme
from common.campaign import Campaign
from common.campaign_script import FlowNode


class _MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


class TestSecurityAndAuthorizationFixes(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())
        self.attacker = Player("Attaccante", conn=_MockConn())
        self.attacker.is_party_member = True
        self.target = Player("Goblin", conn=None)
        self.target.hp = 30
        self.target.max_hp = 30
        self.gs.players = [self.attacker, self.target]

    def test_is_dm_actor_does_not_treat_plain_offline_player_as_dm(self):
        plain_pc = Player("OfflineHero")
        dm_actor = SimpleNamespace(role="DM")
        self.assertFalse(is_dm_actor(plain_pc))
        self.assertFalse(is_dm_actor(self.attacker))
        self.assertTrue(is_dm_actor(None))
        self.assertTrue(is_dm_actor(dm_actor))

    def test_sanitize_client_payload_strips_forced_keys_for_non_dm(self):
        from server.network import sanitize_client_payload

        raw = {"forced_roll": 1, "forced_wild_d20": 1, "free_test": True, "dc": 15}
        sanitized_pc = sanitize_client_payload(raw, self.attacker)
        self.assertEqual(sanitized_pc, {"dc": 15})
        sanitized_dm = sanitize_client_payload(raw, None)
        self.assertEqual(sanitized_dm, raw)

    def test_non_dm_rejected_from_admin_map_combat_monster_and_optional_tools(self):
        from server.rules.map_interaction import (
            handle_clear_drawings_request,
            handle_quest_action_request,
            handle_handout_share_request,
            handle_toggle_wall_request,
            handle_toggle_cover_request,
        )
        from server.rules.combat import (
            handle_apply_pending_damage_request,
            handle_set_automation_mode_request,
        )
        from server.dm_monster_engine import handle_resolve_legendary_resistance_request
        from server.dm_optional_tools import handle_optional_rule_action_request

        self.gs.drawn_lines = [{"points": [(0, 0), (1, 1)]}]
        handle_clear_drawings_request({}, self.attacker, self.gs)
        self.assertEqual(len(self.gs.drawn_lines), 1)

        self.gs.current_map = {"walls": [], "half_cover": [], "doors": [], "fow_revealed": [], "fow_draft": []}
        handle_toggle_wall_request({"q": 2, "r": 2}, self.attacker, self.gs)
        handle_toggle_cover_request({"q": 2, "r": 3, "cover_type": "half_cover"}, self.attacker, self.gs)
        self.assertEqual(self.gs.current_map["walls"], [])
        self.assertEqual(self.gs.current_map["half_cover"], [])

        before_quests = list(self.gs.quests)
        handle_quest_action_request({"action": "add", "title": "Hack"}, self.attacker, self.gs)
        self.assertEqual(self.gs.quests, before_quests)

        before_mode = self.gs.automation_mode
        handle_set_automation_mode_request({"mode": "manual"}, self.attacker, self.gs)
        self.assertEqual(self.gs.automation_mode, before_mode)

        self.gs.pending_damages["d1"] = {"target": "Goblin", "damage": 10, "damage_type": "Fuoco", "source": "Attaccante"}
        handle_apply_pending_damage_request({"pending_id": "d1", "action": "apply"}, self.attacker, self.gs)
        self.assertIn("d1", self.gs.pending_damages)
        self.assertEqual(self.target.hp, 30)

        self.gs.pending_legendary_resistances["lr1"] = {"target": "Goblin", "stat": "DES", "dc": 15}
        handle_resolve_legendary_resistance_request({"pending_id": "lr1", "decision": "use"}, self.attacker, self.gs)
        self.assertIn("lr1", self.gs.pending_legendary_resistances)

        with patch("server.dm_optional_tools.broadcast") as mock_bc:
            handle_handout_share_request({"title": "Spam", "content": "x"}, self.attacker, self.gs)
            handle_optional_rule_action_request({"action": "morale_check"}, self.attacker, self.gs)
            mock_bc.assert_not_called()


class TestCombatAndRulesFixes(unittest.TestCase):
    def setUp(self):
        self.gs = GameState(queue.Queue())

    def test_deferred_legendary_resistance_avoids_double_damage_and_preserves_concentration(self):
        from server.rules.combat import _process_save_result
        from server.dm_monster_engine import handle_resolve_legendary_resistance_request

        self.gs.automation_settings["opt_legendary_res_prompt"] = True
        self.gs.automation_settings["auto_apply_aoe_damage"] = True
        dragon = Player("Drago")
        dragon.hp = 100
        dragon.max_hp = 100
        dragon.legendary_resistances_max = 3
        dragon.legendary_resistances_current = 3
        dragon.conditions = ["Concentrazione"]
        dragon.active_effects = [{"name": "Veleno", "save_ends": {"stat": "COS", "dc": 15}}]
        wizard = Player("Mago")
        self.gs.players = [dragon, wizard]

        # Failed save against 20 fire damage (half on success): must defer cleanly
        _process_save_result("Drago", "DES", 5, False, False, 18, "20", True, "Mago", self.gs, "Fuoco")
        self.assertEqual(dragon.hp, 100)
        self.assertIn("Concentrazione", dragon.conditions)
        self.assertEqual(len(self.gs.pending_legendary_resistances), 1)
        lr_id = next(iter(self.gs.pending_legendary_resistances))

        # DM decides to use Legendary Resistance -> save succeeds (takes half: 10), LR becomes 2
        with patch("threading.Timer") as mock_timer:
            handle_resolve_legendary_resistance_request({"pending_id": lr_id, "decision": "use"}, None, self.gs)
            self.assertEqual(dragon.legendary_resistances_current, 2)
            self.assertEqual(dragon.hp, 90)
            self.assertEqual(len(self.gs.pending_legendary_resistances), 0)
            self.assertTrue(mock_timer.called or "Concentrazione" in dragon.conditions)

        # Second failed save where DM chooses NOT to spend LR -> takes full 20
        _process_save_result("Drago", "DES", 5, False, False, 18, "20", True, "Mago", self.gs, "Fuoco")
        lr_id_2 = next(iter(self.gs.pending_legendary_resistances))
        handle_resolve_legendary_resistance_request({"pending_id": lr_id_2, "decision": "fail"}, None, self.gs)
        self.assertEqual(dragon.legendary_resistances_current, 2)
        self.assertEqual(dragon.hp, 70)

    def test_bonus_action_attack_rollback_on_validation_failure(self):
        from server.rules.combat import handle_attack_request

        hero = Player("Guerriero", conn=_MockConn())
        hero.position = [0, 0]
        orc = Player("Orco")
        orc.position = [10, 10]
        orc.hp = 30
        orc.max_hp = 30
        self.gs.players = [hero, orc]
        self.gs.combat_active = True
        self.gs.automation_settings["strict_turn_lock"] = True

        # Out-of-reach bonus attack must fail cleanly and NOT burn bonus_action_used_this_turn
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertFalse(hero.bonus_action_used_this_turn)
        self.assertTrue(len(hero.conn.sent) >= 1)

        # In-reach bonus attack must mark bonus_action_used_this_turn
        orc.position = [1, 0]
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertTrue(hero.bonus_action_used_this_turn)

        # Second bonus attack in the same turn must be rejected
        prev_msgs = len(hero.conn.sent)
        handle_attack_request(
            {"target_name": "Orco", "weapon_name": "Pugnale", "hit_bonus": 15, "damage_formula": "1d4", "is_bonus_action": True},
            hero,
            self.gs,
        )
        self.assertGreater(len(hero.conn.sent), prev_msgs)

    def test_give_item_rejects_excess_quantity_and_transfers_valid_quantity(self):
        from server.rules.inventory import handle_give_item_request

        sender = Player("Bardo", conn=_MockConn())
        receiver = Player("Chierico", conn=_MockConn())
        potion = {"name": "Pozione di Guarigione", "type": "Consumabile", "qty": 2, "weight": 0.5}
        sender.full_sheet = {"inventory_grid": [dict(potion)] + [None] * 24}
        receiver.full_sheet = {"inventory_grid": [None] * 25}
        self.gs.players = [sender, receiver]

        # Attempt to give 5 when owning 2 -> rejected
        handle_give_item_request({"target_name": "Chierico", "item": {"name": "Pozione di Guarigione", "qty": 5}}, sender, self.gs)
        self.assertEqual(sender.full_sheet["inventory_grid"][0]["qty"], 2)
        self.assertIsNone(receiver.full_sheet["inventory_grid"][0])

        # Valid give of 1
        handle_give_item_request({"target_name": "Chierico", "item": {"name": "Pozione di Guarigione", "qty": 1}}, sender, self.gs)
        self.assertEqual(sender.full_sheet["inventory_grid"][0]["qty"], 1)
        self.assertEqual(receiver.full_sheet["inventory_grid"][0]["qty"], 1)

    def test_knock_and_dispel_magic_enforce_spell_slots(self):
        from server.rules.map_interaction import handle_toggle_door_request
        from server.rules.reaction_magic import handle_dispel_magic_request

        caster = Player("Mago", conn=_MockConn())
        caster.position = [0, 0]
        caster.full_sheet = {
            "spell_slots": {"1": {"max": 2, "current": 2}, "2": {"max": 1, "current": 0}, "3": {"max": 1, "current": 0}}
        }
        victim = Player("Alleato")
        victim.active_effects = [{"name": "Blocca Persone", "target": "Alleato", "caster": "Cultista"}]
        self.gs.current_map = {"doors": [{"q": 1, "r": 0, "state": "locked", "name": "Porta"}], "walls": [], "fow_revealed": [], "fow_draft": []}
        self.gs.players = [caster, victim]

        # No 2nd-level slot -> knock fails
        handle_toggle_door_request({"q": 1, "r": 0, "method": "knock"}, caster, self.gs)
        self.assertEqual(self.gs.current_map["doors"][0]["state"], "locked")

        # No 3rd-level slot -> dispel fails
        handle_dispel_magic_request({"target_name": "Alleato", "slot_level": 3}, caster, self.gs)
        self.assertEqual(len(victim.active_effects), 1)

        # Grant slots -> both succeed and consume slots
        caster.full_sheet["spell_slots"]["2"]["current"] = 1
        caster.full_sheet["spell_slots"]["3"]["current"] = 1
        handle_toggle_door_request({"q": 1, "r": 0, "method": "knock"}, caster, self.gs)
        self.assertEqual(self.gs.current_map["doors"][0]["state"], "open")
        self.assertEqual(caster.full_sheet["spell_slots"]["2"]["current"], 0)

        handle_dispel_magic_request({"target_name": "Alleato", "slot_level": 3}, caster, self.gs)
        self.assertEqual(len(victim.active_effects), 0)
        self.assertEqual(caster.full_sheet["spell_slots"]["3"]["current"], 0)


class TestDataCampaignAndUIFixes(unittest.TestCase):
    def test_normalize_npc_actions(self):
        self.assertEqual(normalize_npc_actions(None), [])
        str_res = normalize_npc_actions("Morso. +4 a colpire, 1d6+2 perforanti.\nArtiglio. 1d4 taglienti.")
        self.assertEqual(len(str_res), 2)
        self.assertEqual(str_res[0]["name"], "Morso")
        self.assertEqual(normalize_npc_actions(["Schianto: 1d8"])[0]["name"], "Schianto")
        self.assertEqual(normalize_npc_actions([{"name": "Soffio", "desc": "Fuoco"}])[0]["name"], "Soffio")

    def test_activate_encounter_on_vtt_count_qty_ac_and_victory_reset(self):
        from server.dm_live_flow import DMLiveFlowDialog

        gs = GameState(queue.Queue())
        camp = Campaign(name="CampTest")

        dlg = DMLiveFlowDialog.__new__(DMLiveFlowDialog)
        dlg.master_gui = MagicMock()
        dlg._get_game_state = lambda: gs
        dlg.campaign = camp
        dlg.session_ledger = MagicMock()
        dlg._record_to_campaign_journal = MagicMock()
        dlg.winfo_exists = lambda: True

        node = FlowNode(
            id="n1",
            node_type="encounter",
            title="Agguato",
            data={"monsters": [{"name": "Goblin", "count": 3, "hp": 7, "ac": 15, "cr": "1/4"}]},
        )
        with patch("server.network.broadcast"), patch("server.dm_live_flow.messagebox.showinfo"):
            DMLiveFlowDialog.activate_encounter_on_vtt(dlg, node)

        spawned = [p for p in gs.players if p.name.startswith("Goblin")]
        self.assertEqual(len(spawned), 3)
        self.assertTrue(all(p.ac == 15 for p in spawned))
        dlg.session_ledger.record_combat.assert_called_once()
        self.assertFalse(dlg.session_ledger.record_combat.call_args.kwargs["victory"])

    def test_theme_defines_all_referenced_ttk_styles(self):
        root = tk.Tk()
        root.withdraw()
        try:
            setup_theme(root)
            style = ttk.Style(root)
            for s_name in ("Gold.TLabel", "Primary.TLabel", "Small.TButton", "Warning.TButton"):
                cfg = style.configure(s_name)
                self.assertTrue(cfg, f"Style {s_name} should be configured")
        finally:
            root.destroy()

    def test_dm_automation_panel_badge_includes_pending_legendary_resistances(self):
        from server.dm_automation_panel import update_pending_actions_ui

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(queue.Queue())
            gs.pending_legendary_resistances["lr1"] = {"target": "Drago", "stat": "DES", "dc": 15}
            dm_mock = MagicMock()
            dm_mock.server.game_state = gs
            dm_mock.pending_actions_container = tk.Frame(root)
            del dm_mock.dm_quick_dice_strip

            update_pending_actions_ui(dm_mock)
            texts = [
                w.cget("text")
                for parent in dm_mock.pending_actions_container.winfo_children()
                for w in [parent] + parent.winfo_children()
                if isinstance(w, tk.Label)
            ]
            self.assertIn("(1)", texts)
        finally:
            root.destroy()

    def test_open_conditions_dialog_preserves_custom_conditions(self):
        from server.dm_entity_dialogs import open_conditions_dialog

        root = tk.Tk()
        root.withdraw()
        try:
            gs = GameState(queue.Queue())
            hero = Player("Eroe")
            hero.conditions = ["Benedetto", "Prono", "Concentrazione"]
            gs.players = [hero]

            dm_mock = MagicMock()
            dm_mock.master = root
            dm_mock.server.game_state = gs
            dm_mock.get_player_name_from_listbox.return_value = "Eroe"

            open_conditions_dialog(dm_mock)
            top = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))

            def all_widgets(w):
                res = [w]
                for c in w.winfo_children():
                    res.extend(all_widgets(c))
                return res

            apply_btn = next(w for w in all_widgets(top) if isinstance(w, (ttk.Button, tk.Button)))
            with patch("server.dm_entity_dialogs.broadcast"):
                apply_btn.invoke()
            self.assertIn("Benedetto", hero.conditions)
            self.assertIn("Concentrazione", hero.conditions)
        finally:
            root.destroy()

    def test_client_companion_filtered_out_and_sheet_dirty_preserved(self):
        from client.client import ClientGUI
        from client.character_manager import Character
        from client.character_sheet_ui import CharacterSheetFrame

        root = tk.Tk()
        root.withdraw()
        try:
            # Verify companion filtering from owned_chars
            c_mock = MagicMock()
            c_mock.name = "Aragorn"
            c_mock.players_data = {}
            c_mock.active_character = None
            c_mock.character_manager = None
            c_mock.map_canvas = None
            c_mock.combat_active = False
            c_mock._is_my_turn = False
            c_mock.lbl_time = None
            c_mock.active_character_var = tk.StringVar(value="Aragorn")
            c_mock.active_character_combo = {"values": []}
            data = {
                "players": [
                    {"name": "Aragorn", "is_companion": False},
                    {"name": "Lupo Fedele", "owner": "Aragorn", "is_companion": True},
                ]
            }
            ClientGUI.handle_game_state(c_mock, data)
            self.assertEqual(c_mock.active_character_combo["values"], ["Aragorn"])

            # Verify recalculate_and_refresh_derived_stats keeps dirty state intact
            char = Character("Eroe", "Guerriero")
            sheet = CharacterSheetFrame(root, char, manager=None, is_connected=False)
            sheet._initial_state_snapshot = {"marker": "orig"}
            sheet.recalculate_and_refresh_derived_stats()
            self.assertEqual(sheet._initial_state_snapshot, {"marker": "orig"})
            sheet.destroy()
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
