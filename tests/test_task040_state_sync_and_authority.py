import copy
import os
import queue
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tkinter as tk
from tkinter import ttk

from client.character_manager import Character, CharacterManager
from client.client import ClientGUI
from client.character_sheet_ui import CharacterSheetFrame
from components.ui_components import HexMapCanvas
from common.game_state import GameState, Player
from common.protocol import (
    make_update_full_sheet_request,
    make_update_stats_request,
)
from server.rules.character import (
    handle_update_full_sheet_request,
    handle_update_stats_request,
)


class _MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


class TestTask040StateSyncAndAuthority(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tk.Tk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_target_sync_canvas_to_slash_ready_and_special_abilities(self):
        canvas = HexMapCanvas(self.root, width=300, height=200)
        try:
            canvas.players_data = {
                "Aria": {"position": [0, 0], "hp": 20, "max_hp": 20},
                "Goblin": {"position": [1, 0], "hp": 7, "max_hp": 7},
            }
            canvas.set_target("Goblin")
            self.assertEqual(canvas.current_target_name, "Goblin")
            self.assertEqual(canvas.selected_target_name, "Goblin")

            # Fake minimal ClientGUI namespace wired to real HexMapCanvas
            c = SimpleNamespace(
                master=self.root,
                name="Aria",
                is_connected=True,
                combat_active=True,
                map_canvas=canvas,
                players_data=canvas.players_data,
                network=SimpleNamespace(send=MagicMock()),
                active_character=Character(name="Aria", char_class="Guerriero", level=3),
                update_action_economy_ui=MagicMock(),
                log_to_chat=MagicMock(),
                show_toast=MagicMock(),
                perform_stand_up=MagicMock(),
                open_speed_factor_dialog=MagicMock(),
                open_jump_calculator_dialog=MagicMock(),
            )
            c.action_spent = False
            c.bonus_spent = False
            c.reaction_spent = False
            c._is_special_ability_ready = lambda *a, **kw: True
            c._has_class_feature = lambda *a, **kw: False

            handled = ClientGUI._try_dispatch_special_slash_command(c, "/maneuver trip")
            self.assertTrue(handled)
            self.assertTrue(c.network.send.called)
            pkt = c.network.send.call_args[0][0]
            self.assertEqual(pkt["data"]["target_name"], "Goblin")

            # Even if a caller/test only sets current_target_name directly (not selected_target_name):
            canvas.selected_target_name = None
            canvas.current_target_name = "Goblin"
            c.network.send.reset_mock()
            handled2 = ClientGUI._try_dispatch_special_slash_command(c, "/maneuver trip")
            self.assertTrue(handled2)
            pkt2 = c.network.send.call_args[0][0]
            self.assertEqual(pkt2["data"]["target_name"], "Goblin")

            # open_special_abilities_dialog target resolution (uses current_target_name fallback)
            ClientGUI.open_special_abilities_dialog(c)
            spec_dlg = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
            try:
                combos = [
                    child
                    for f in spec_dlg.winfo_children()
                    if isinstance(f, ttk.Frame)
                    for child in f.winfo_children()
                    if isinstance(child, ttk.Combobox)
                ]
                self.assertEqual(combos[0].get(), "Goblin")
            finally:
                if spec_dlg.winfo_exists():
                    spec_dlg.destroy()

            # perform_ready_action: ensure target resolved as Goblin when triggering a readied action
            c.network.send.reset_mock()
            c.players_data = {"Aria": {"conditions": ["Azione Preparata"]}}
            c.reaction_spent = False
            with patch("client.client.messagebox.askyesno", return_value=True):
                ClientGUI.perform_ready_action(c)
            self.assertTrue(c.network.send.called)
            pkt3 = c.network.send.call_args[0][0]
            self.assertEqual(pkt3["data"]["target_name"], "Goblin")
        finally:
            canvas.destroy()

    def test_handle_game_state_syncs_complete_character_fields_and_pools(self):
        hero = Character(name="Elara", char_class="Mago", level=5)
        hero.exp = 0
        hero.currency = {"MO": 10}
        hero.inventory_grid = [None] * 25
        hero.hit_dice_pools = {"d6": {"total": 5, "current": 5}}

        sent = []
        c = SimpleNamespace(
            name="Elara",
            is_connected=True,
            active_character=hero,
            players_data={},
            local_map_data=None,
            game_state=None,
            _asset_cache={},
            _is_my_turn=False,
            _action_surge_used_this_turn=False,
            combat_active=False,
            schedule_save_characters=MagicMock(),
            update_hero_summary_card=MagicMock(),
            update_action_economy_ui=MagicMock(),
            update_player_listbox=MagicMock(),
            redraw_map_and_players=MagicMock(),
            show_toast=MagicMock(),
            log_to_chat=MagicMock(),
            handle_dm_whisper_sync=None,
            network=SimpleNamespace(send=lambda m: sent.append(m)),
        )

        payload = {
            "combat_active": False,
            "players": [
                {
                    "name": "Elara",
                    "position": [2, 3],
                    "hp": 19,
                    "max_hp": 28,
                    "temp_hp": 5,
                    "conditions": ["Benedizione"],
                    "active_effects": [{"id": "bless", "name": "Benedizione", "duration": 10}],
                    "death_saves": {"successes": 2, "failures": 1},
                    "has_inspiration": True,
                    "full_sheet": {
                        "exp": 6500,
                        "hit_dice_current": 3,
                        "hit_dice_total": 5,
                        "hit_dice_pools": {"d6": {"total": 5, "current": 3}},
                        "currency": {"MO": 145, "MA": 30},
                        "inventory_grid": [{"name": "Bacchetta", "qty": 1}] + [None] * 24,
                        "portent_dice": [18, 4],
                        "sorcery_points_current": 2,
                        "sorcery_points_max": 5,
                        "superiority_dice_current": 1,
                        "superiority_dice_max": 4,
                        "lucky_points": 2,
                        "arcane_recovery_used": True,
                        "wild_shape_uses": 1,
                        "wild_shape_max": 2,
                        "spell_slots": {"1": {"max": 4, "current": 2}},
                        "has_inspiration": True,
                    },
                }
            ],
            "map": None,
        }

        ClientGUI.handle_game_state(c, payload)
        self.assertEqual(hero.hp_current, 19)
        self.assertEqual(hero.hp_max, 28)
        self.assertEqual(hero.exp, 6500)
        self.assertEqual(hero.death_saves, {"successes": 2, "failures": 1})
        self.assertTrue(hero.has_inspiration)
        self.assertEqual(hero.hit_dice_pools["d6"]["current"], 3)
        self.assertEqual(hero.currency["MO"], 145)
        self.assertEqual(hero.inventory_grid[0]["name"], "Bacchetta")
        self.assertEqual(hero.active_effects[0]["name"], "Benedizione")
        self.assertEqual(hero.portent_dice, [18, 4])
        self.assertEqual(hero.sorcery_points_current, 2)
        self.assertEqual(hero.superiority_dice_current, 1)
        self.assertEqual(hero.lucky_points, 2)
        self.assertTrue(hero.arcane_recovery_used)
        self.assertEqual(hero.wild_shape_uses, 1)
        c.update_action_economy_ui.assert_called()

    def test_sync_local_party_characters_to_manager_preserves_all_progression_and_pools(self):
        from server.dm_campaign_session_mixin import DMCampaignSessionMixin

        with tempfile.TemporaryDirectory() as tmpd:
            chars_path = os.path.join(tmpd, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": chars_path}):
                mgr = CharacterManager()
                pc = Character(name="Thorin", char_class="Paladino", level=3)
                pc.exp = 900
                mgr.characters = [pc]
                mgr.save_characters()

                gs = GameState(queue.Queue())
                srv_p = Player("Thorin", None, None)
                srv_p.is_party_member = True
                srv_p.hp = 24
                srv_p.max_hp = 30
                srv_p.ac = 18
                srv_p.full_sheet = {
                    "hp_current": 24,
                    "hp_max": 30,
                    "ac": 18,
                    "level": 4,
                    "exp": 2700,
                    "hit_dice_current": 2,
                    "hit_dice_total": 4,
                    "hit_dice_pools": {"d10": {"total": 4, "current": 2}},
                    "currency": {"MO": 250, "MA": 12},
                    "spellbook": [{"name": "Benedizione", "level": 1}],
                    "inventory_grid": [{"name": "Spada Lunga +1", "qty": 1}] + [None] * 24,
                    "weapons": [{"name": "Spada Lunga +1", "damage_dice": "1d8", "bonus": 1}],
                    "attributes": {"FOR": 18, "DES": 10, "COS": 14, "INT": 10, "SAG": 12, "CAR": 16},
                    "has_inspiration": True,
                    "lucky_points": 2,
                    "arcane_recovery_used": False,
                }
                gs.players = [srv_p]
                dummy_dm = SimpleNamespace(server=SimpleNamespace(game_state=gs))
                updated = DMCampaignSessionMixin.sync_local_party_characters_to_manager(dummy_dm)
                self.assertEqual(updated, 1)

                mgr2 = CharacterManager()
                mgr2.load_characters()
                reloaded = next(ch for ch in mgr2.characters if ch.name == "Thorin")
                self.assertEqual(reloaded.level, 4)
                self.assertEqual(reloaded.exp, 2700)
                self.assertEqual(reloaded.hit_dice_pools["d10"]["current"], 2)
                self.assertEqual(reloaded.currency["MO"], 250)
                self.assertEqual(reloaded.spellbook[0]["name"], "Benedizione")
                self.assertEqual(reloaded.weapons[0]["bonus"], 1)
                self.assertEqual(reloaded.attributes["FOR"], 18)
                self.assertTrue(reloaded.has_inspiration)
                self.assertEqual(reloaded.lucky_points, 2)

    def test_player_death_saves_and_is_npc_roundtrip_and_hero_point_sync(self):
        from server.dm_optional_tools import handle_spend_hero_point

        npc = Player("Bandito", None, None)
        npc.is_npc = True
        npc.death_saves = {"successes": 2, "failures": 1}
        d = npc.to_dict()
        self.assertTrue(d["is_npc"])
        self.assertEqual(d["death_saves"], {"successes": 2, "failures": 1})
        self.assertEqual(d["death_save_successes"], 2)
        self.assertEqual(d["death_save_failures"], 1)

        rehydrated = Player.from_dict(d)
        self.assertTrue(rehydrated.is_npc)
        self.assertEqual(rehydrated.death_saves, {"successes": 2, "failures": 1})
        self.assertEqual(rehydrated.death_save_successes, 2)
        self.assertEqual(rehydrated.death_save_failures, 1)

        gs = GameState(queue.Queue())
        gs.automation_settings["opt_hero_points"] = True
        hero = Player("Kael", None, _MockConn())
        hero.hp = 0
        hero.max_hp = 20
        hero.hero_points = 2
        hero.death_save_failures = 2
        hero.death_saves = {"successes": 1, "failures": 2}
        hero.full_sheet = {"hero_points": 2, "death_saves": {"successes": 1, "failures": 2}, "conditions": ["Incosciente"]}
        gs.players = [hero]

        with patch("server.dm_optional_tools.broadcast"):
            ok, _ = handle_spend_hero_point(hero, "death_save", gs)
        self.assertTrue(ok)
        self.assertEqual(hero.death_save_failures, 0)
        self.assertEqual(hero.death_saves["failures"], 0)
        self.assertEqual(hero.full_sheet["death_saves"]["failures"], 0)

    def test_monster_spawners_advance_time_isolation_and_action_dialog_rules(self):
        from server.dm_bestiary_panel import DMBestiaryPanel
        from server.dm_generators import RandomNPCDialog
        from server.dm_gui import DM_GUI

        gs = GameState(queue.Queue())
        pc = Player("Garrick", None, _MockConn())
        pc.is_party_member = True
        pc.hp = 10
        pc.max_hp = 40
        pc.full_sheet = {
            "hp_current": 10,
            "hp_max": 40,
            "hit_dice_total": 4,
            "hit_dice_current": 1,
            "hit_dice_pools": {"d10": {"total": 2, "current": 0}, "d8": {"total": 2, "current": 1}},
        }
        # Legacy monster without conn / is_party_member AND explicit is_npc monster
        legacy_orc = Player("Orco Ferito", None, None)
        legacy_orc.hp = 5
        legacy_orc.max_hp = 15
        gs.players = [pc, legacy_orc]

        # 1. Bestiary spawner sets ac and is_npc
        built = DMBestiaryPanel._build_npc_player(
            SimpleNamespace(), "Bugbear", {"size": "Medium"}, hp=27, ac=16, initiative=2, speed_val=30, speed_disp="30 ft", speed_unit="ft", attrs={"DES": 14}, pos=[1, 1]
        )
        self.assertTrue(built.is_npc)
        self.assertEqual(built.ac, 16)
        self.assertTrue(built.full_sheet["is_npc"])
        gs.add_player(built)
        built.hp = 9

        # 2. RandomNPCDialog.spawn_token reads sp_ac and sets is_npc
        with patch("server.dm_generators.broadcast"), patch("server.dm_generators.messagebox.showinfo"):
            dlg = RandomNPCDialog(self.root, gs)
            try:
                dlg.ent_name.delete(0, tk.END)
                dlg.ent_name.insert(0, "Guardia Scelta")
                dlg.sp_hp.delete(0, tk.END)
                dlg.sp_hp.insert(0, "24")
                dlg.sp_ac.delete(0, tk.END)
                dlg.sp_ac.insert(0, "18")
                dlg.spawn_token()
            finally:
                if dlg.winfo_exists():
                    dlg.destroy()
        guard = gs.find_player("Guardia Scelta")
        self.assertIsNotNone(guard)
        self.assertTrue(guard.is_npc)
        self.assertEqual(guard.ac, 18)
        self.assertTrue(guard.full_sheet["is_npc"])

        # 3. DM_GUI.advance_time heals party only & recovers hit_dice_pools without healing monsters
        fake_dm = SimpleNamespace(
            master=self.root,
            server=SimpleNamespace(game_state=gs),
            log_to_chat=MagicMock(),
            update_time_display=MagicMock(),
            sync_local_party_characters_to_manager=MagicMock(return_value=0),
        )
        with patch("server.network.broadcast"):
            DM_GUI.advance_time(fake_dm, 8, is_rest=True)
        self.assertEqual(pc.hp, 40)
        self.assertEqual(sum(v["current"] for v in pc.full_sheet["hit_dice_pools"].values()), 3)
        self.assertEqual(legacy_orc.hp, 5)
        self.assertEqual(built.hp, 9)

        # 4. DM_GUI.open_action_dialog routes through apply_damage / _apply_hp_change
        pc.temp_hp = 6
        fake_dm.get_player_name_from_listbox = lambda: "Garrick"
        DM_GUI.open_action_dialog(fake_dm)
        top_dlg = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        try:
            entries = [w for w in top_dlg.winfo_children() if isinstance(w, ttk.Entry)]
            submit_btn = [w for w in top_dlg.winfo_children() if isinstance(w, ttk.Button)][0]
            entries[0].insert(0, "10")  # Damage formula = 10 -> 6 absorbed by temp_hp, 4 to hp -> 36
            entries[1].insert(0, "Trappola")
            with patch("server.dm_gui.broadcast"), patch("server.rules.combat.broadcast"):
                submit_btn.invoke()
            self.assertEqual(pc.temp_hp, 0)
            self.assertEqual(pc.hp, 36)
        finally:
            if top_dlg.winfo_exists():
                top_dlg.destroy()

        # Heal from 0 HP clears Unconscious/Stabilized/death_saves
        pc.hp = 0
        pc.conditions = ["Incosciente", "Stabilizzato"]
        pc.death_saves = {"successes": 2, "failures": 1}
        pc.full_sheet["death_saves"] = {"successes": 2, "failures": 1}
        DM_GUI.open_action_dialog(fake_dm)
        top_dlg2 = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)][-1]
        try:
            radios = [c for w in top_dlg2.winfo_children() if isinstance(w, ttk.Frame) for c in w.winfo_children() if isinstance(c, ttk.Radiobutton)]
            radios[1].invoke()  # Select "heal"
            entries = [w for w in top_dlg2.winfo_children() if isinstance(w, ttk.Entry)]
            submit_btn = [w for w in top_dlg2.winfo_children() if isinstance(w, ttk.Button)][0]
            entries[0].insert(0, "8")
            with patch("server.dm_gui.broadcast"), patch("server.rules.combat.broadcast"):
                submit_btn.invoke()
            self.assertEqual(pc.hp, 8)
            self.assertNotIn("Incosciente", pc.conditions)
            self.assertNotIn("Stabilizzato", pc.conditions)
            self.assertEqual(pc.death_saves, {"successes": 0, "failures": 0})
            self.assertEqual(pc.full_sheet["death_saves"], {"successes": 0, "failures": 0})
        finally:
            if top_dlg2.winfo_exists():
                top_dlg2.destroy()

    def test_level_up_exact_hp_no_phantom_plus1_and_inspiration_clamping(self):
        # 1. Connected CharacterSheetFrame.on_level_up_applied sends UPDATE_FULL_SHEET (not pre-UPDATE_STATS)
        sent_packets = []
        char = Character(name="Ronan", char_class="Guerriero", level=2)
        char.hp_max = 20
        char.hp_current = 20
        char.initiative = 2
        char.has_inspiration = False
        char.inspiration = False
        char.attributes = {"FOR": 16, "DES": 14, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10}

        fake_frame = SimpleNamespace(
            character=char,
            is_connected=True,
            network=SimpleNamespace(send=lambda pkt: sent_packets.append(pkt)),
            _safe_update_character=MagicMock(),
            _safe_save_characters=MagicMock(),
            load_data=MagicMock(),
            on_save_callback=None,
        )
        CharacterSheetFrame.on_level_up_applied(fake_frame)
        self.assertEqual(sent_packets[0]["type"], "UPDATE_FULL_SHEET_REQUEST")

        # 2. Server rules authority: non-DM UPDATE_STATS cannot inflate max_hp; level-up gives exact client gain
        gs = GameState(queue.Queue())
        p = Player("Ronan", None, _MockConn())
        p.role = "player"
        p.hp = 12
        p.max_hp = 12
        p.has_inspiration = False
        p.full_sheet = {
            "name": "Ronan",
            "char_class": "Guerriero",
            "level": 1,
            "hp_current": 12,
            "hp_max": 12,
            "attributes": {"FOR": 16, "DES": 14, "COS": 14, "INT": 10, "SAG": 10, "CAR": 10},
            "has_inspiration": False,
            "inspiration": False,
        }
        gs.players = [p]

        with patch("server.rules.character.broadcast"):
            handle_update_stats_request(make_update_stats_request(12, 999, 2, [])["data"], p, gs)
        self.assertEqual(p.max_hp, 12)

        with patch("server.rules.character.broadcast"):
            for pkt in sent_packets:
                if pkt["type"] == "UPDATE_FULL_SHEET_REQUEST":
                    handle_update_full_sheet_request(pkt["data"], p, gs)
        # Level 1 -> Level 2 with req_hp_max=20 stays exact 20 (NOT 21!)
        self.assertEqual(p.max_hp, 20)
        self.assertEqual(p.full_sheet["hp_max"], 20)

        # Spoof has_inspiration=True when server has False is clamped back to False
        spoof_sheet = copy.deepcopy(p.full_sheet)
        spoof_sheet["has_inspiration"] = True
        with patch("server.rules.character.broadcast"):
            handle_update_full_sheet_request(make_update_full_sheet_request(spoof_sheet)["data"], p, gs)
        self.assertFalse(p.full_sheet["has_inspiration"])
        self.assertFalse(p.full_sheet["inspiration"])

        # Legitimate DM-granted inspiration can be consumed by player (True -> False)
        p.full_sheet["has_inspiration"] = True
        p.full_sheet["inspiration"] = True
        consume_sheet = copy.deepcopy(p.full_sheet)
        consume_sheet["has_inspiration"] = False
        consume_sheet["inspiration"] = False
        with patch("server.rules.character.broadcast"):
            handle_update_full_sheet_request(make_update_full_sheet_request(consume_sheet)["data"], p, gs)
        self.assertFalse(p.full_sheet["has_inspiration"])
        self.assertFalse(p.full_sheet["inspiration"])


if __name__ == "__main__":
    unittest.main()
