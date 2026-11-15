import json
import os
import queue
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import tkinter as tk

from client.character_manager import Character, CharacterManager
from client.character_sheet_ui import CharacterSheetFrame
from client.network_handlers import ClientNetworkHandlersMixin
from client.sheet_panels.spells_panel import SpellsPanel
from common.campaign import Campaign
from common.character_schema import sync_hit_dice_pools
from common.file_utils import atomic_save_json, load_json
from common.game_state import GameState, Player
from common.network_utils import prepare_per_player_state_payload
from common.protocol import make_game_state, make_give_item_request
from server.commands import command_handlers
from server.dm_gui import DM_GUI
from server.rules.combat import handle_short_rest_request
from server.rules.inventory import handle_give_item_request


class _MockConn:
    def __init__(self):
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)


def _decode_frames(chunks):
    out = []
    for raw in chunks:
        text = raw.decode("utf-8", errors="ignore") if isinstance(raw, (bytes, bytearray)) else str(raw)
        idx = 0
        while idx < len(text):
            start = text.find("{", idx)
            if start < 0:
                break
            try:
                obj, end = json.JSONDecoder().raw_decode(text, start)
                out.append(obj)
                idx = end
            except Exception:
                break
    return out


class TestTask041ResilienceSheetsRest(unittest.TestCase):
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

    def test_toggle_features_view_mode_no_grid_pack_crash(self):
        with tempfile.TemporaryDirectory() as tmpd:
            chars_path = os.path.join(tmpd, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": chars_path}):
                mgr = CharacterManager()
                ch = Character(name="Lyra", char_class="Bardo", level=3)
                ch.features_list = [{"name": "Ispirazione Bardica", "category": "Privilegio di Classe", "desc": "d6"}]
                mgr.characters = [ch]
                frame = CharacterSheetFrame(self.root, ch, mgr)
                try:
                    self.root.update_idletasks()
                    self.assertEqual(frame._features_view_mode, "structured")
                    frame.toggle_features_view_mode()
                    self.assertEqual(frame._features_view_mode, "text")
                    frame.toggle_features_view_mode()
                    self.assertEqual(frame._features_view_mode, "structured")
                    self.root.update_idletasks()
                finally:
                    frame.destroy()

    def test_spells_panel_arcano_prep_cap_and_metamagic_rollback(self):
        self.assertEqual(SpellsPanel.get_spellcasting_ability("Ladro", "Mistificatore Arcano"), "INT")
        rogue = Character(name="Vex", char_class="Guerriero 3 / Ladro 4", subclass="Mistificatore Arcano", level=7)
        rogue.classes = {"Guerriero": 3, "Ladro": 4}
        rogue.attributes = {"FOR": 14, "DES": 18, "COS": 14, "INT": 16, "SAG": 10, "CAR": 8}
        stats = SpellsPanel.calculate_spell_stats(rogue)
        self.assertEqual(stats["ability"], "INT")

        # Toggle prepared spell respects daily cap (Wizard Lv 1 INT +2 => max 3)
        wiz = Character(name="Alaric", char_class="Mago", level=1)
        wiz.attributes = {"FOR": 8, "DES": 14, "COS": 12, "INT": 14, "SAG": 10, "CAR": 10}
        wiz.spellbook = [
            {"name": "Dardo Incantato", "level": 1, "prepared": True},
            {"name": "Scudo", "level": 1, "prepared": True},
            {"name": "Armatura Magica", "level": 1, "prepared": True},
            {"name": "Sonno", "level": 1, "prepared": False},
        ]
        tree = MagicMock()
        tree.selection.return_value = ["3"]  # Sonno (currently False)
        fake_sheet = SimpleNamespace(character=wiz, spell_tree=tree, manager=None)
        with patch("common.messagebox.messagebox.showwarning"):
            SpellsPanel.toggle_spell_prepared(fake_sheet)
        self.assertFalse(wiz.spellbook[3]["prepared"])

        # Failed Metamagic cleanly rolls back standard slot, pact slot, AND spell points
        sorc = Character(name="Kaelen", char_class="Stregone", level=5)
        sorc.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
        sorc.spell_slots["3"] = {"max": 2, "current": 2}
        sorc.sorcery_points_current = 1
        sorc.sorcery_points_max = 5
        sorc.custom_resources = [{"name": "Punti Stregoneria", "current": 1, "max": 5, "reset_on": "long"}]
        ok, _tags, err = SpellsPanel.execute_spell_resource_cost(
            sorc,
            {"name": "Palla di Fuoco", "level": 3},
            3,
            metamagic_key="twinned",  # Needs 3 sorcery points, has only 1!
        )
        self.assertFalse(ok)
        self.assertTrue(bool(err))
        self.assertEqual(sorc.spell_slots["3"]["current"], 2)

        # Pact slot rollback
        lock = Character(name="Mordred", char_class="Stregone 2 / Warlock 3", level=5)
        lock.classes = {"Stregone": 2, "Warlock": 3}
        lock.spell_slots = {str(i): {"max": 0, "current": 0} for i in range(1, 10)}
        lock.pact_slots = {"max": 2, "current": 2, "level": 2}
        lock.sorcery_points_current = 1
        lock.sorcery_points_max = 2
        lock.custom_resources = [{"name": "Punti Stregoneria", "current": 1, "max": 2, "reset_on": "long"}]
        ok_p, _, _ = SpellsPanel.execute_spell_resource_cost(
            lock,
            {"name": "Raggio Rovente", "level": 2},
            2,
            use_pact=True,
            metamagic_key="twinned",  # Needs 2 points, has 1
        )
        self.assertFalse(ok_p)
        self.assertEqual(lock.pact_slots["current"], 2)

        # Spell points + high-level usage rollback
        sorc.spell_points_max = 27
        sorc.spell_points_current = 27
        ok_s, _, _ = SpellsPanel.execute_spell_resource_cost(
            sorc,
            {"name": "Disintegrazione", "level": 6},
            6,
            use_spell_points=True,
            metamagic_key="twinned",  # Needs 6 sorcery points, has only 1
        )
        self.assertFalse(ok_s)
        self.assertEqual(sorc.spell_points_current, 27)
        self.assertNotIn(6, getattr(sorc, "_spell_points_high_used", set()))

    def test_asset_cache_miss_recovery_and_sheet_ui_refresh_and_item_bounce(self):
        # 1. Asset miss triggers REQUEST_ASSET_RESYNC and server resends full unstripped asset
        gs = GameState(queue.Queue())
        gs.current_map = {
            "name": "Dungeon",
            "width": 5,
            "height": 5,
            "bg_image_data": "QUJDREVGRw==",
            "hexes": {"0,0": {"terrain": "Pietra"}},
        }
        p = Player("Aria", None, _MockConn())
        gs.players = [p]

        pkt1 = prepare_per_player_state_payload(make_game_state(gs.get_state_dict(is_dm=False)), p)
        bg_h = pkt1["data"]["map"]["bg_image_hash"]
        hx_h = pkt1["data"]["map"]["hexes_hash"]
        # Second broadcast strips cached assets
        pkt2 = prepare_per_player_state_payload(make_game_state(gs.get_state_dict(is_dm=False)), p)
        self.assertIsNone(pkt2["data"]["map"]["bg_image_data"])
        self.assertTrue(pkt2["data"]["map"]["hexes_cached"])

        # Client lost its cache -> resolves pkt2 -> records missing hashes -> requests resync
        sent = []
        cli = SimpleNamespace(
            is_connected=True,
            _asset_cache={},
            local_map_data=None,
            network=SimpleNamespace(send=lambda m: sent.append(m)),
        )
        ClientNetworkHandlersMixin._resolve_cached_map_assets(cli, pkt2["data"]["map"])
        ClientNetworkHandlersMixin._maybe_request_asset_resync(cli)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["type"], "REQUEST_ASSET_RESYNC")
        self.assertIn(bg_h, sent[0]["data"]["hashes"])
        self.assertIn(hx_h, sent[0]["data"]["hashes"])

        # Server processes REQUEST_ASSET_RESYNC and resends full asset payload
        command_handlers["REQUEST_ASSET_RESYNC"](sent[0]["data"], p, gs)
        frames = _decode_frames(p.conn.sent)
        self.assertTrue(frames)
        last_gs = frames[-1]["data"]
        self.assertEqual(last_gs["map"]["bg_image_data"], "QUJDREVGRw==")
        self.assertEqual(last_gs["map"]["hexes"], {"0,0": {"terrain": "Pietra"}})

        # 2. handle_receive_currency & handle_receive_item refresh docked & detached sheets cleanly
        with tempfile.TemporaryDirectory() as tmpd:
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": os.path.join(tmpd, "chars.json")}):
                mgr = CharacterManager()
                hero = Character(name="Aria", char_class="Ladro", level=2)
                mgr.characters = [hero]
                docked_sheet = MagicMock()
                docked_sheet.winfo_exists.return_value = True
                detached_inner = MagicMock()
                detached_inner.winfo_exists.return_value = True
                top_win_without_load = SimpleNamespace(
                    winfo_exists=lambda: True,
                    _sheet_frame_internal=detached_inner,
                )
                recv_sent = []
                cli_ui = SimpleNamespace(
                    name="Aria",
                    active_character=hero,
                    character_manager=mgr,
                    network=SimpleNamespace(send=lambda m: recv_sent.append(m)),
                    stats_sheet_frame=docked_sheet,
                    stats_detached_window=top_win_without_load,
                    stats_window=top_win_without_load,
                    show_toast=MagicMock(),
                    log_to_chat=MagicMock(),
                )
                ClientNetworkHandlersMixin.handle_receive_gold(cli_ui, {"amount": 25, "sender": "DM"})
                self.assertEqual(hero.currency["MO"], 25)
                docked_sheet.load_data.assert_called()
                detached_inner.load_data.assert_called()

                # Fill all 25 slots with unique items + Potion in slot 0 -> receive Potion stacks instead of bouncing; full unstackable from DM never bounces
                hero.inventory_grid = [{"name": f"Reliquia {i}", "qty": 1} for i in range(25)]
                hero.inventory_grid[0] = {"name": "Pozione", "qty": 1}
                ClientNetworkHandlersMixin.handle_receive_item(cli_ui, {"item": {"name": "Pozione", "qty": 2, "_sender": "Il DM"}})
                self.assertEqual(hero.inventory_grid[0]["qty"], 3)

                recv_sent.clear()
                ClientNetworkHandlersMixin.handle_receive_item(cli_ui, {"item": {"name": "Spada Unica", "qty": 1, "_sender": "Il DM"}})
                self.assertFalse(any(m.get("type") == "GIVE_ITEM_REQUEST" for m in recv_sent))

    def test_give_item_split_stack_uses_explicit_slot_index(self):
        gs = GameState(queue.Queue())
        alice = Player("Alice", None, _MockConn())
        bob = Player("Bob", None, _MockConn())
        alice.full_sheet = {
            "inventory_grid": [
                {"name": "Pozione di Guarigione", "qty": 2},
                None,
                {"name": "Torcia", "qty": 1},
                {"name": "Pozione di Guarigione", "qty": 5},
            ] + [None] * 21,
            "attributes": {"DES": 12},
        }
        bob.full_sheet = {"inventory_grid": [None] * 25, "attributes": {"DES": 10}}
        gs.players = [alice, bob]

        pkt = make_give_item_request("Bob", {"name": "Pozione di Guarigione", "qty": 3, "_from_slot": 3}, slot_idx=3)
        with patch("server.rules.inventory.broadcast"), patch("server.rules.inventory.send_message"):
            handle_give_item_request(pkt["data"], alice, gs)

        self.assertEqual(alice.full_sheet["inventory_grid"][0]["qty"], 2)  # Slot 0 untouched!
        self.assertEqual(alice.full_sheet["inventory_grid"][3]["qty"], 2)  # Slot 3 decremented 5 -> 2!
        self.assertEqual(bob.full_sheet["inventory_grid"][0]["name"], "Pozione di Guarigione")
        self.assertEqual(bob.full_sheet["inventory_grid"][0]["qty"], 3)
        self.assertNotIn("_from_slot", bob.full_sheet["inventory_grid"][0])

    def test_short_rest_validation_bounds_and_zero_hp_recovery(self):
        gs = GameState(queue.Queue())
        hero = Player("Bram", None, _MockConn())
        hero.is_party_member = True
        hero.hp = 0
        hero.max_hp = 30
        hero.conditions = ["Incosciente", "Stabilizzato"]
        hero.death_save_successes = 2
        hero.death_save_failures = 1
        hero.death_saves = {"successes": 2, "failures": 1}
        hero.full_sheet = {
            "char_class": "Guerriero",
            "level": 3,
            "hp_current": 0,
            "hp_max": 30,
            "attributes": {"COS": 14},  # +2 mod
            "hit_dice_pools": {"d10": {"total": 3, "current": 3}},
            "hit_dice_total": 3,
            "hit_dice_current": 3,
            "conditions": ["Incosciente", "Stabilizzato"],
            "death_saves": {"successes": 2, "failures": 1},
        }
        gs.players = [hero]

        # 1. Invalid negative die_counts rejected without touching HP or dice
        with patch("server.rules.combat.broadcast"):
            handle_short_rest_request({"hd_spent": 1, "hp_recovered": 5, "die_counts": {"d10": -2}}, hero, gs)
        self.assertEqual(hero.hp, 0)
        self.assertEqual(hero.full_sheet["hit_dice_current"], 3)
        self.assertTrue(any(f.get("type") == "ERROR_REPLY" for f in _decode_frames(hero.conn.sent)))

        # 2. Invalid die key rejected
        hero.conn.sent.clear()
        with patch("server.rules.combat.broadcast"):
            handle_short_rest_request({"hd_spent": 1, "hp_recovered": 5, "die_counts": {"d20": 1}}, hero, gs)
        self.assertEqual(hero.hp, 0)
        self.assertTrue(any(f.get("type") == "ERROR_REPLY" for f in _decode_frames(hero.conn.sent)))

        # 3. Spoofed hp_recovered=999 on 1d10 (+2 COS => max 12) is capped AND heals from 0 HP clearing death saves & unconscious
        with patch("server.rules.combat.broadcast"):
            handle_short_rest_request({"hd_spent": 1, "hp_recovered": 999, "die_counts": {"d10": 1}}, hero, gs)
        self.assertEqual(hero.hp, 12)
        self.assertEqual(hero.full_sheet["hit_dice_current"], 2)
        self.assertNotIn("Incosciente", hero.conditions)
        self.assertNotIn("Stabilizzato", hero.conditions)
        self.assertEqual(hero.death_save_successes, 0)
        self.assertEqual(hero.death_save_failures, 0)
        self.assertEqual(hero.death_saves, {"successes": 0, "failures": 0})
        self.assertEqual(hero.full_sheet["death_saves"], {"successes": 0, "failures": 0})

    def test_bak_recovery_campaign_isolation_autosave_and_pdf_multiclass(self):
        with tempfile.TemporaryDirectory() as tmpd:
            # 1. .bak crash recovery for generic JSON, CharacterManager, Session & Campaign
            target_json = os.path.join(tmpd, "chars.json")
            atomic_save_json(target_json, [{"name": "Primo"}], create_backup=True)
            atomic_save_json(target_json, [{"name": "Secondo"}], create_backup=True)
            with open(target_json, "w", encoding="utf-8") as f:
                f.write("{CORRUPTED JSON!!!")
            recovered = load_json(target_json, default=[])
            self.assertEqual(recovered[0]["name"], "Primo")

            camp_dir = os.path.join(tmpd, "camp_a")
            camp_a = Campaign(name="Campagna A", folder_path=camp_dir)
            camp_a.quests = [{"title": "Old Quest"}]
            camp_a.shops = {"Fabbro": {"items": [{"name": "Spada"}]}}
            camp_a.starter_kit = [{"name": "Razione"}]
            camp_a.save(camp_dir)
            camp_a.dm_notes = "Updated"
            camp_a.save(camp_dir)
            with open(os.path.join(camp_dir, "campaign.json"), "w", encoding="utf-8") as f:
                f.write("{BAD!")
            reloaded_camp = Campaign.load(camp_dir)
            self.assertEqual(reloaded_camp.name, "Campagna A")

            # 2. Campaign.apply_to_game_state resets prior campaign state when switching to clean Campaign B
            gs = GameState(queue.Queue())
            camp_a.apply_to_game_state(gs)
            self.assertEqual(len(gs.quests), 1)
            self.assertIn("Fabbro", gs.shops)
            camp_b = Campaign(name="Campagna B")
            camp_b.apply_to_game_state(gs)
            self.assertEqual(gs.quests, [])
            self.assertEqual(gs.shops, {})
            self.assertEqual(gs.campaign_starter_kit, [])
            self.assertIsNone(gs.current_map)

            # 3. DM_GUI periodic autosave writes isolated recovery session
            auto_path = os.path.join(tmpd, "dm_session_autosave.json")
            with patch.dict(os.environ, {"DND_AUTOSAVE_PATH": auto_path}):
                fake_dm = SimpleNamespace(
                    _is_closing=False,
                    _autosave_job=None,
                    master=self.root,
                    server=SimpleNamespace(game_state=gs),
                    _resolve_autosave_path=lambda: DM_GUI._resolve_autosave_path(SimpleNamespace()),
                )
                fake_dm._run_periodic_autosave = lambda: DM_GUI._run_periodic_autosave(fake_dm)
                DM_GUI._run_periodic_autosave(fake_dm)
                if fake_dm._autosave_job:
                    self.root.after_cancel(fake_dm._autosave_job)
                self.assertTrue(os.path.isfile(auto_path))
                loaded_auto = load_json(auto_path, default={})
                self.assertIn("players", loaded_auto)

            # 4. sync_hit_dice_pools preserves newly gained level-up hit die despite stale scalar
            c_lvl = Character(name="Eldrin", char_class="Mago 3 / Guerriero 1", level=4)
            c_lvl.classes = {"Mago": 3, "Guerriero": 2}
            c_lvl.hit_dice_pools = {"d10": {"total": 1, "current": 1}, "d6": {"total": 3, "current": 1}}
            c_lvl.hit_dice_total = 4
            c_lvl.hit_dice_current = 2  # pre-level-up scalar!
            pools_after = sync_hit_dice_pools(c_lvl, allow_scalar_override=True)
            self.assertEqual(pools_after["d10"], {"total": 2, "current": 2})
            self.assertEqual(pools_after["d6"], {"total": 3, "current": 1})

            # 5. PDF generation with Artefice & empty hit_dice_type & multiclass pools
            from client.pdf_sheet_generator import generate_character_pdf
            from reportlab.pdfgen import canvas as rl_canvas
            tpl_path = os.path.join(tmpd, "tpl.pdf")
            c_tpl = rl_canvas.Canvas(tpl_path, pagesize=(594, 783))
            for _ in range(3):
                c_tpl.drawString(50, 700, "Page")
                c_tpl.showPage()
            c_tpl.save()
            art = Character(name="Tinker", char_class="Artefice", level=3)
            art.hit_dice_type = ""
            art.armor_proficiencies = ["Armature Leggere"]
            art.weapon_proficiencies = ["Armi Semplici"]
            out_pdf = os.path.join(tmpd, "tinker.pdf")
            generate_character_pdf(art, out_pdf, template_path=tpl_path)
            self.assertTrue(os.path.isfile(out_pdf))


if __name__ == "__main__":
    unittest.main()
