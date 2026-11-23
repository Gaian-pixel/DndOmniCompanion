import json
import os
import queue
import socket
import tempfile
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import MagicMock, patch

from common.campaign import Campaign
from common.campaign_journal import CampaignJournal, JournalEvent, JournalSession
from common.file_utils import atomic_save_json
from common.game_state import GameState, Player
from common.network_utils import (
    _recv_exact,
    broadcast,
    prepare_per_player_state_payload,
    receive_message,
    send_message,
)
from common.protocol import make_game_state, make_join
from common.theme import apply_modern_window_style


def _make_root():
    root = tk.Tk()
    root.withdraw()
    return root


class TestTask030NetworkingAndReconnect(unittest.TestCase):
    def test_make_join_known_asset_hashes_capped_and_clean(self):
        hashes = [f"h{i}" for i in range(80)] + [None, "", 123]
        pkt = make_join("Aelar", known_asset_hashes=hashes)
        self.assertEqual(pkt["type"], "JOIN")
        sent_hashes = pkt["data"]["known_asset_hashes"]
        self.assertLessEqual(len(sent_hashes), 64)
        self.assertTrue(all(isinstance(h, str) and h for h in sent_hashes))

    def test_recv_exact_and_receive_message_timeout_distinction(self):
        class _IdleTimeoutSock:
            def recv(self, _n):
                raise socket.timeout("idle")

        with self.assertRaises(socket.timeout):
            _recv_exact(_IdleTimeoutSock(), 4)

        self.assertIsNone(receive_message(_IdleTimeoutSock(), raise_on_timeout=False))
        with self.assertRaises(socket.timeout):
            receive_message(_IdleTimeoutSock(), raise_on_timeout=True)

        class _MidFrameTimeoutSock:
            def __init__(self):
                self.calls = 0

            def recv(self, _n):
                self.calls += 1
                if self.calls == 1:
                    return b"ab"
                raise socket.timeout("stalled mid-frame")

        with self.assertRaises(ConnectionError):
            _recv_exact(_MidFrameTimeoutSock(), 4)

    def test_ping_pong_and_send_message_return_bool_and_broadcast_isolation(self):
        from server.commands import command_handlers

        class _MockConn:
            def __init__(self, fail=False):
                self.fail = fail
                self.sent = bytearray()

            def settimeout(self, _t):
                pass

            def sendall(self, data):
                if self.fail:
                    raise BrokenPipeError("broken")
                self.sent.extend(data)

        ok_conn = _MockConn(fail=False)
        bad_conn = _MockConn(fail=True)
        self.assertTrue(send_message(ok_conn, {"type": "PING", "data": {}}))
        self.assertFalse(send_message(bad_conn, {"type": "PING", "data": {}}))

        gs = GameState(queue.Queue())
        p_ok = Player("Aelar")
        p_ok.conn = ok_conn
        p_bad = Player("Boric")
        p_bad.conn = bad_conn
        gs.players = [p_ok, p_bad]

        ok_conn.sent.clear()
        broadcast(gs, {"type": "PING", "data": {}})
        self.assertGreater(len(ok_conn.sent), 4)

        p_ok.conn = _MockConn(fail=False)
        with patch("common.network_utils.send_message") as mock_send:
            command_handlers["PING"]({}, p_ok, gs)
            mock_send.assert_called_once_with(p_ok.conn, {"type": "PONG", "data": {}})

    def test_cross_ip_reconnect_with_pin_and_dead_socket_and_asset_dedup(self):
        from server.network import Server

        class _FakeConn:
            def __init__(self, alive=True):
                self.alive = alive
                self.closed = False
                self.timeout = None

            def settimeout(self, t):
                self.timeout = t

            def setsockopt(self, *_a):
                pass

            def fileno(self):
                return 10 if (self.alive and not self.closed) else -1

            def getpeername(self):
                if not self.alive or self.closed:
                    raise OSError("not connected")
                return ("10.0.0.1", 50000)

            def shutdown(self, _how):
                pass

            def close(self):
                self.closed = True

            def sendall(self, _b):
                pass

        # 1. Cross-IP takeover consentito quando session_password PIN valida la sessione
        srv = Server("127.0.0.1", 0, queue.Queue())
        srv.set_session_password("9999")

        old_conn = _FakeConn(alive=True)
        existing = Player("Kaelen")
        existing.conn = old_conn
        existing.addr = ("10.0.0.1", 50000)
        existing.is_party_member = True
        existing.hp = 12
        existing.max_hp = 30
        existing._last_seen_ts = time.monotonic()
        srv.game_state.players.append(existing)

        new_conn = _FakeConn(alive=True)
        live_snapshots = []

        def _capture_send(_c, m):
            live_snapshots.append((existing.addr, existing.conn is new_conn, m.get("type") if isinstance(m, dict) else None))
            return True

        seq = iter([
            make_join("Kaelen", password="9999", known_asset_hashes=["abc123"]),
            None,
        ])
        with patch("server.network.receive_message", side_effect=lambda _c: next(seq)), \
             patch("server.network.send_message", side_effect=_capture_send), \
             patch("server.network.broadcast"):
            srv.handle_client(new_conn, ("10.0.0.99", 51111))

        self.assertTrue(old_conn.closed)
        self.assertTrue(any(addr == ("10.0.0.99", 51111) and is_new for addr, is_new, _ in live_snapshots))
        self.assertEqual(existing.hp, 12)
        self.assertIn("abc123", getattr(existing, "_sent_asset_hashes", set()))

        # 2. Cross-IP takeover consentito senza PIN quando il socket precedente e' morto
        srv2 = Server("127.0.0.1", 0, queue.Queue())
        dead_conn = _FakeConn(alive=False)
        existing2 = Player("Lyra")
        existing2.conn = dead_conn
        existing2.addr = ("10.0.0.5", 41000)
        existing2.is_party_member = True
        existing2.hp = 9
        existing2.max_hp = 20
        existing2._last_seen_ts = time.monotonic()
        srv2.game_state.players.append(existing2)

        fresh_conn = _FakeConn(alive=True)
        live_snapshots2 = []

        def _capture_send2(_c, m):
            live_snapshots2.append((existing2.addr, existing2.conn is fresh_conn, m.get("type") if isinstance(m, dict) else None))
            return True

        seq2 = iter([make_join("Lyra"), None])
        with patch("server.network.receive_message", side_effect=lambda _c: next(seq2)), \
             patch("server.network.send_message", side_effect=_capture_send2), \
             patch("server.network.broadcast"):
            srv2.handle_client(fresh_conn, ("10.0.0.88", 52222))

        self.assertTrue(any(addr == ("10.0.0.88", 52222) and is_new for addr, is_new, _ in live_snapshots2))
        self.assertEqual(existing2.hp, 9)

    def test_client_network_connect_async_and_pong_reply(self):
        from client.network import ClientNetwork

        net = ClientNetwork(queue.Queue(), lambda: None)
        with self.assertRaises((OSError, TimeoutError)):
            net.connect("127.0.0.1", 59999, timeout=0.05)
        self.assertFalse(net.is_connected)

        results = []
        done = threading.Event()

        attempt_id = net.connect_async(
            "127.0.0.1",
            59999,
            on_success=lambda: (results.append(("ok", None)), done.set()),
            on_error=lambda err: (results.append(("err", err)), done.set()),
            timeout=0.05,
        )
        self.assertGreater(attempt_id, 0)
        self.assertTrue(done.wait(timeout=3.0))
        self.assertEqual(results[0][0], "err")

        net2 = ClientNetwork(queue.Queue(), lambda: None)
        stale_gen = net2._connect_generation
        net2.cancel_pending_connect()
        self.assertGreater(net2._connect_generation, stale_gen)

        net2.is_connected = True
        net2.client_socket = MagicMock()
        msgs = iter([{"type": "PING", "data": {}}, None])
        with patch("client.network.receive_message", side_effect=lambda _s, **_kw: next(msgs)), \
             patch.object(net2, "send", return_value=True) as mock_send:
            net2.listen_to_server()
            mock_send.assert_any_call({"type": "PONG", "data": {}})

    def test_asset_hash_dedup_and_client_avatar_cache_restore(self):
        from client.network_handlers import ClientNetworkHandlersMixin

        p = Player("Lyra")
        p.avatar_b64 = "ZmFrZV9wbmdfYnl0ZXM="
        p.full_sheet = {"name": "Lyra", "avatar_b64": "ZmFrZV9wbmdfYnl0ZXM="}

        p._sent_asset_hashes = set()
        pkt1 = prepare_per_player_state_payload(make_game_state({"players": [p.to_dict()]}), p)
        first_avatar = pkt1["data"]["players"][0].get("avatar_b64", "")
        self.assertTrue(first_avatar)

        pkt2 = prepare_per_player_state_payload(make_game_state({"players": [p.to_dict()]}), p)
        p2_dict = pkt2["data"]["players"][0]
        self.assertFalse(p2_dict.get("avatar_b64"))
        self.assertTrue(p2_dict.get("avatar_hash"))

        class _DummyClient(ClientNetworkHandlersMixin):
            pass

        cli = _DummyClient()
        cache = ClientNetworkHandlersMixin._get_asset_cache(cli)
        cli._resolve_cached_avatar_assets(pkt1["data"]["players"])
        self.assertEqual(cache[p2_dict["avatar_hash"]], "ZmFrZV9wbmdfYnl0ZXM=")
        cli._resolve_cached_avatar_assets(pkt2["data"]["players"])
        self.assertEqual(pkt2["data"]["players"][0]["avatar_b64"], "ZmFrZV9wbmdfYnl0ZXM=")
        self.assertEqual(pkt2["data"]["players"][0]["full_sheet"]["avatar_b64"], "ZmFrZV9wbmdfYnl0ZXM=")

    def test_server_clamps_reconnecting_client_resources_against_server_state(self):
        from server.rules.character import handle_update_full_sheet_request

        gs = GameState(queue.Queue())
        p = Player("Elara")
        p.full_sheet = {
            "level": 3,
            "hp_current": 7,
            "hp_max": 24,
            "temp_hp": 0,
            "spell_slots": {"1": {"max": 4, "current": 1}},
            "pact_slots": {"max": 2, "current": 0, "level": 2},
            "custom_resources": [{"name": "Ki", "current": 1, "max": 3}],
            "hit_dice_current": 1,
            "hit_dice_total": 3,
        }
        p.hp = 7
        p.max_hp = 24
        gs.players = [p]

        handle_update_full_sheet_request(
            {
                "full_sheet": {
                    "level": 3,
                    "hp_current": 24,
                    "hp_max": 24,
                    "spell_slots": {"1": {"max": 4, "current": 4}},
                    "pact_slots": {"max": 2, "current": 2, "level": 2},
                    "custom_resources": [{"name": "Ki", "current": 3, "max": 3}],
                    "hit_dice_current": 3,
                    "hit_dice_total": 3,
                }
            },
            p,
            gs,
        )
        self.assertEqual(p.hp, 7)
        self.assertEqual(p.full_sheet["spell_slots"]["1"]["current"], 1)
        self.assertEqual(p.full_sheet["pact_slots"]["current"], 0)
        self.assertEqual(p.full_sheet["custom_resources"][0]["current"], 1)
        self.assertEqual(p.full_sheet["hit_dice_current"], 1)


class TestTask030HUDThemeAndSecrecy(unittest.TestCase):
    def test_theme_escape_exits_fullscreen_first_and_centers_in_vroot(self):
        root = _make_root()
        try:
            win = tk.Toplevel(root)
            called = []
            win._on_escape_close = lambda: called.append("closed")
            win.geometry("400x300+0+0")
            with patch.object(win, "winfo_vrootx", return_value=1920), \
                 patch.object(win, "winfo_vrooty", return_value=0), \
                 patch.object(win, "winfo_vrootwidth", return_value=1920), \
                 patch.object(win, "winfo_vrootheight", return_value=1080), \
                 patch.object(win, "winfo_width", return_value=500), \
                 patch.object(win, "winfo_height", return_value=400), \
                 patch.object(win, "geometry") as mock_geom:
                apply_modern_window_style(win)
                t0 = time.monotonic()
                while not mock_geom.called and (time.monotonic() - t0) < 0.4:
                    root.update()
                self.assertTrue(mock_geom.called)
                geo_arg = mock_geom.call_args[0][0]
                x_part = int(geo_arg.split("+")[1])
                self.assertGreaterEqual(x_part, 1920)

            self.assertTrue(bool(win.bind("<Escape>")))
            win.deiconify()
            win.update()
            win.focus_force()
            win.update()
            with patch.object(win, "attributes", side_effect=[True, None]) as mock_attr:
                win.event_generate("<Escape>")
                win.update()
                mock_attr.assert_any_call("-fullscreen", False)
            self.assertEqual(called, [])

            with patch.object(win, "attributes", return_value=False):
                win.event_generate("<Escape>")
                win.update()
            self.assertEqual(called, ["closed"])
        finally:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass

    def test_journal_secrecy_quest_sync_and_atomic_backup(self):
        sess = JournalSession(session_number=1, title="Session 1", dm_notes="Segreto DM totale")
        sess.events.append(JournalEvent(category="combat", title="Scontro coi Goblin", description="Scontro coi Goblin", timestamp="19:00"))
        sess.events.append(JournalEvent(category="dm_note", title="Doppleganger", description="Il locandiere è un doppleganger", data={"dm_only": True}, timestamp="19:05"))
        sess.events.append(JournalEvent(category="exploration", title="Passaggio", description="Scoperto passaggio segreto", timestamp="19:10"))
        sess.events.append(JournalEvent(category="social", title="Patto", description="Patto col borgomastro", timestamp="19:15"))

        pub = sess.to_dict(include_dm_notes=False)
        self.assertEqual(pub["dm_notes"], "")
        self.assertEqual(len(pub["events"]), 3)
        self.assertFalse(any(e["category"] == "dm_note" for e in pub["events"]))

        journal = CampaignJournal(campaign_name="Test")
        journal.sessions = [sess]
        prose = journal.synthesize_prose(0, "it")
        self.assertNotIn("doppleganger", prose)
        self.assertIn("Goblin", prose)
        self.assertIn("passaggio", prose)
        self.assertIn("borgomastro", prose)

        gs = GameState(queue.Queue())
        p = Player("Tharion")
        p.full_sheet = {
            "name": "Tharion",
            "notes": "Appunti pubblici.\n\nSEGRETO DM: Maledetto dal lich.",
            "description": "Alto elfo\nDM SECRET: Spia reale",
        }
        gs.players = [p]
        gs.quests = [
            {"title": "Trova la reliquia", "status": "In Corso", "completed": False, "dm_notes": "È falsa"},
            {"title": "Tradimento Segreto", "secret": True, "status": "In Corso"},
        ]
        gs.handouts = [
            {"title": "Mappa Antica", "content": "Rovine a nord", "is_revealed": True},
            {"title": "Lettera del Culto", "content": "Top secret", "is_revealed": False},
        ]

        player_state = gs.get_state_dict(is_dm=False)
        self.assertEqual(len(player_state["quests"]), 1)
        self.assertNotIn("dm_notes", player_state["quests"][0])
        self.assertEqual(len(player_state["handouts"]), 1)
        self.assertNotIn("Maledetto", player_state["players"][0]["full_sheet"]["notes"])
        self.assertNotIn("Spia reale", player_state["players"][0]["full_sheet"]["description"])

        dm_state = gs.get_state_dict(is_dm=True)
        self.assertEqual(len(dm_state["quests"]), 2)
        self.assertEqual(len(dm_state["handouts"]), 2)

        from server.rules.map_interaction import handle_quest_action_request
        p.conn = MagicMock()
        p.role = "Player"
        dm_actor = Player("DM")
        dm_actor.role = "DM"
        dm_actor.conn = MagicMock()
        with patch("server.rules.map_interaction.broadcast"):
            handle_quest_action_request({"action": "complete", "quest": {"title": "Trova la reliquia"}}, p, gs)
            self.assertFalse(gs.quests[0]["completed"])
            handle_quest_action_request({"action": "complete", "quest": {"title": "Trova la reliquia"}}, dm_actor, gs)
        self.assertTrue(gs.quests[0]["completed"])
        self.assertEqual(gs.quests[0]["status"], "Completata")

        with tempfile.TemporaryDirectory() as td:
            f_path = os.path.join(td, "save_test.json")
            atomic_save_json(f_path, {"v": 1}, create_backup=True)
            atomic_save_json(f_path, {"v": 2}, create_backup=True)
            self.assertTrue(os.path.exists(f_path + ".bak"))
            with open(f_path + ".bak", "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f)["v"], 1)

    def test_player_journal_markdown_filters_dm_note_and_manuals_debounce(self):
        from client.player_journal_dialog import PlayerJournalDialog
        from client.manuals_ui import ManualsDialog

        root = _make_root()
        try:
            sess = JournalSession(
                session_number=1,
                title="Cronaca",
                prose="### Capitolo 1\nIl gruppo **eroico** trova *indizi*.\n- Porta nord",
                dm_notes="NOTA SEGRETA SESSIONE",
            )
            sess.events = [
                JournalEvent(category="dm_note", title="Segreto", description="NOTA PRIVATA DM", data={"dm_only": True}, timestamp="10:00"),
                JournalEvent(category="combat", title="Vittoria sui Coboldi", description="Vittoria sui Coboldi", timestamp="10:05"),
            ]
            journal = CampaignJournal(campaign_name="TestCamp")
            journal.sessions = [sess]
            with tempfile.TemporaryDirectory() as td, \
                 patch("client.player_journal_dialog.get_writable_dir", return_value=td):
                dlg = PlayerJournalDialog(root, campaign_journal=journal, character_name="Aelar")
                events_txt = dlg.txt_events.get("1.0", tk.END)
                self.assertNotIn("NOTA PRIVATA DM", events_txt)
                self.assertIn("Coboldi", events_txt)
                prose_txt = dlg.txt_prose.get("1.0", tk.END)
                self.assertIn("Capitolo 1", prose_txt)
                self.assertNotIn("###", prose_txt)
                self.assertIn("md_h3", dlg.txt_prose.tag_names("1.0"))
                dlg.destroy()

            fake_mgr = MagicMock()
            fake_mgr.get_available_manuals.return_value = [("PHB", "Player's Handbook")]
            fake_mgr.get_manual_categories.return_value = ["Combattimento"]
            fake_mgr.search.return_value = []
            with patch("client.manuals_ui.ManualsManager", return_value=fake_mgr):
                m_dlg = ManualsDialog(root)
                calls_before = fake_mgr.search.call_count
                m_dlg.search_var.set("lotta")
                m_dlg._run_debounced_refresh()
                self.assertGreater(fake_mgr.search.call_count, calls_before)
                m_dlg.destroy()
        finally:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass

    def test_campaign_editor_dialog_modals_and_share_lore_handout(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        from server.dm_live_flow import DMLiveFlowDialog

        root = _make_root()
        try:
            camp = Campaign(name="Campagna Test")
            gs = GameState(queue.Queue())
            editor = CampaignEditorDialog(root, campaign=camp, game_state=gs)
            self.assertTrue(bool(editor.protocol("WM_DELETE_WINDOW")))
            self.assertEqual(editor._on_escape_close, editor._frame_internal.close_editor)

            with patch("server.campaign_editor_ui.broadcast") as mock_bcast, \
                 patch("server.campaign_editor_ui.messagebox.showinfo"):
                editor._frame_internal.apply_to_running_game()
                mock_bcast.assert_called()
            editor.destroy()

            node = MagicMock(
                title="Pergamena",
                data={"author": "Saggio", "language": "Comune", "read_aloud": "Antica profezia"},
            )
            flow_mock = MagicMock(spec=DMLiveFlowDialog)
            flow_mock._get_game_state.return_value = gs
            flow_mock.game_state = gs
            flow_mock.dm_gui = MagicMock()
            flow_mock.session_ledger = MagicMock()
            flow_mock.active_campaign = None
            flow_mock.show_status = MagicMock()
            with patch("common.network_utils.broadcast") as mock_bcast, \
                 patch("server.dm_live_flow.messagebox.showinfo"):
                DMLiveFlowDialog.share_lore(flow_mock, node)
                bcast_pkt = mock_bcast.call_args[0][1]
                self.assertEqual(bcast_pkt["type"], "HANDOUT_BROADCAST")
                self.assertIsNone(bcast_pkt["data"]["image_b64"])
                self.assertIn("Antica profezia", bcast_pkt["data"]["content"])
                self.assertTrue(any(h.get("is_revealed") for h in gs.handouts))
        finally:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass

    def test_client_hud_connection_indicator_and_scrollable_sidebar(self):
        from client.client import ClientGUI

        root = _make_root()
        try:
            with patch.object(ClientGUI, "process_queue", return_value=None):
                cli = ClientGUI(root)
            self.assertTrue(hasattr(cli, "hud_conn_btn"))
            self.assertTrue(hasattr(cli, "hdr_conn_badge"))
            self.assertTrue(hasattr(cli, "hdr_conn_btn"))
            self.assertTrue(hasattr(cli, "controls_canvas"))
            self.assertTrue(hasattr(cli, "controls_tab_outer"))
            self.assertGreaterEqual(len(cli.controls_canvas.find_all()), 1)

            cli.session_password = "7788"
            cli.network.connected = True
            cli.handle_disconnection(silent=True)
            self.assertEqual(cli.session_password, "7788")
            self.assertIn("🔴", cli.hud_conn_btn.cget("text"))
            self.assertTrue(bool(cli.hdr_conn_btn.cget("text")))
            with patch("client.client.messagebox.askokcancel", return_value=True):
                cli.on_closing()
        finally:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass


class TestTask030TabletopAndUXM08(unittest.TestCase):
    def test_tabletop_initiative_rests_death_saves_sheet_and_player_display(self):
        from client.character_manager import Character, CharacterManager
        from server.dm_campaign_session_mixin import import_party_character_to_game_state
        from server.dm_dialogs import DMPlayerSheetViewer
        from server.dm_gui import DM_GUI

        with tempfile.TemporaryDirectory() as td:
            char_file = os.path.join(td, "chars.json")
            with patch.dict(os.environ, {"DND_CHARACTERS_PATH": char_file}):
                c = Character(name="Garrick", char_class="Guerriero", level=3)
                c.hp_max = 30
                c.hp_current = 18
                c.ac = 17
                c.hit_dice_total = 3
                c.hit_dice_current = 1
                c.custom_resources = [{"name": "Azione Impetuosa", "current": 0, "max": 1, "reset_on": "short"}]
                mgr = CharacterManager()
                mgr.add_character(c)

                root = _make_root()
                try:
                    with patch("server.network.Server.start"), patch.object(DM_GUI, "process_queue", return_value=None):
                        dm = DM_GUI(root)

                    pc = import_party_character_to_game_state(dm.server.game_state, c.to_dict())
                    self.assertTrue(getattr(pc, "is_party_member", False))

                    goblin = Player("Goblin Boss")
                    goblin.hp = 21
                    goblin.max_hp = 21
                    goblin.is_npc = True
                    goblin.full_sheet = {"name": "Goblin Boss", "is_npc": True, "initiative": 2, "actions": [{"name": "Scimitar", "desc": "+4 to hit"}]}
                    goblin.layer = "gm"
                    hidden_scout = Player("Shadow Scout")
                    hidden_scout.hp = 10
                    hidden_scout.max_hp = 10
                    hidden_scout.is_npc = True
                    hidden_scout.is_hidden = True
                    dm.server.game_state.players.extend([goblin, hidden_scout])

                    with patch("random.randint", return_value=14), patch("server.dm_gui.broadcast"):
                        dm.roll_all_npcs_initiative()
                    self.assertEqual(pc.initiative, 0)
                    self.assertGreater(goblin.initiative, 0)

                    with patch("server.dm_gui.broadcast"):
                        dm.advance_time(1, is_rest=True)
                    self.assertEqual(pc.full_sheet["custom_resources"][0]["current"], 1)

                    pc.exhaustion_level = 1
                    pc.full_sheet["exhaustion_level"] = 1
                    with patch("server.dm_gui.broadcast"):
                        dm.advance_time(8, is_rest=True)
                    self.assertEqual(pc.hp, 30)
                    self.assertEqual(pc.exhaustion_level, 0)
                    self.assertEqual(pc.full_sheet["hit_dice_current"], 2)

                    cb_logs = []
                    viewer = DMPlayerSheetViewer(
                        root,
                        "Garrick",
                        pc.full_sheet,
                        game_state=dm.server.game_state,
                        on_change_callback=lambda msg=None: (cb_logs.append(msg), dm._on_dm_sheet_changed("Garrick", msg)),
                    )
                    viewer._apply_hp_delta(-20)
                    self.assertEqual(pc.hp, 10)
                    viewer._apply_hp_delta(-10)
                    self.assertEqual(pc.hp, 0)
                    self.assertIn("Incosciente", pc.conditions)

                    with patch("server.dm_dialogs.random.randint", return_value=20):
                        viewer.roll_death_save()
                    self.assertEqual(pc.hp, 1)
                    self.assertNotIn("Incosciente", pc.conditions)

                    viewer._apply_hp_delta(-1)
                    with patch("server.dm_dialogs.random.randint", side_effect=[1, 5]):
                        viewer.roll_death_save()
                        viewer.roll_death_save()
                    self.assertIn("Morto", pc.conditions)
                    viewer.destroy()

                    mgr2 = CharacterManager()
                    reloaded = mgr2.get_character_by_name("Garrick")
                    self.assertIsNotNone(reloaded)
                    self.assertEqual(reloaded.hp_current, 0)
                    self.assertIn("Morto", reloaded.conditions)

                    self.assertTrue(hasattr(dm, "npc_actions_canvas"))
                    self.assertTrue(hasattr(dm, "npc_actions_inner"))
                    dm.player_listbox.delete(0, tk.END)
                    dm.player_listbox.insert(0, "Goblin Boss (HP: 21/21)")
                    dm.player_listbox.selection_set(0)
                    dm.on_player_selected(None)
                    self.assertGreater(len(dm.npc_actions_inner.winfo_children()), 0)

                    win = dm.open_player_display_window()
                    self.assertFalse(dm.player_display_canvas.is_dm)
                    self.assertFalse(dm.player_display_canvas.can_move_token_callback("Garrick", (0, 0), (1, 1)))
                    self.assertNotIn("Goblin Boss", dm.player_display_canvas.players_data)
                    self.assertNotIn("Shadow Scout", dm.player_display_canvas.players_data)
                    self.assertIn("Garrick", dm.player_display_canvas.players_data)
                    self.assertTrue(win.winfo_exists())

                    with patch("server.dm_gui.messagebox.askokcancel", return_value=True):
                        dm.on_closing()
                finally:
                    try:
                        if root.winfo_exists():
                            root.destroy()
                    except tk.TclError:
                        pass


class TestTask035PerformanceAndNonBlockingNet(unittest.TestCase):
    def test_116k_hexes_hash_dedup_rehydration_and_cache_invalidation(self):
        import json
        import queue
        from common.network_utils import broadcast, compute_hexes_hash
        from common.protocol import make_game_state
        from server.network import GameState, Player
        from client.client import ClientGUI

        big_hexes = [{"q": i % 340, "r": i // 340, "t": "stone"} for i in range(116280)]
        expected_hash = compute_hexes_hash(big_hexes)
        self.assertTrue(expected_hash.startswith("hx_"))

        gs = GameState(queue.Queue())
        p1 = Player("P1", conn=object())
        gs.players = [p1]
        gs.current_map = {"name": "Megadungeon", "hexes": big_hexes, "fow_revealed": []}

        delivered = []
        with patch("common.network_utils.send_message", side_effect=lambda c, m: delivered.append(m)):
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            pkt1 = delivered[-1]
            self.assertEqual(pkt1["data"]["map"]["hexes_hash"], expected_hash)
            self.assertEqual(len(pkt1["data"]["map"]["hexes"]), 116280)
            full_wire_bytes = len(json.dumps(pkt1).encode("utf-8"))

            c_stub = MagicMock()
            c_stub._asset_cache = {}
            c_stub._MAX_ASSET_CACHE_ENTRIES = 32
            c_stub.local_map_data = None
            ClientGUI._resolve_cached_map_assets(c_stub, pkt1["data"]["map"])
            self.assertIn(expected_hash, c_stub._asset_cache)

            # Second broadcast after non-grid state change: hexes omitted on wire & restored from client cache
            gs.current_map["fow_revealed"] = [[0, 0]]
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            pkt2 = delivered[-1]
            self.assertIsNone(pkt2["data"]["map"]["hexes"])
            self.assertTrue(pkt2["data"]["map"].get("hexes_cached"))
            dedup_wire_bytes = len(json.dumps(pkt2).encode("utf-8"))
            self.assertLess(dedup_wire_bytes, full_wire_bytes * 0.05)

            ClientGUI._resolve_cached_map_assets(c_stub, pkt2["data"]["map"])
            self.assertEqual(len(pkt2["data"]["map"]["hexes"]), 116280)
            c_stub.local_map_data = pkt2["data"]["map"]

            # In-place mutation of hexes invalidates hash and sends full mutated grid
            gs.current_map["hexes"] = [{"q": 0, "r": 0, "t": "lava"}]
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            pkt3 = delivered[-1]
            self.assertNotEqual(pkt3["data"]["map"]["hexes_hash"], expected_hash)
            self.assertEqual(pkt3["data"]["map"]["hexes"], [{"q": 0, "r": 0, "t": "lava"}])

            # Clearing hexes to empty list must NOT resurrect old cached grid
            gs.current_map["hexes"] = []
            broadcast(gs, make_game_state(gs.get_state_dict(is_dm=False)))
            pkt4 = delivered[-1]
            ClientGUI._resolve_cached_map_assets(c_stub, pkt4["data"]["map"])
            self.assertEqual(pkt4["data"]["map"]["hexes"], [])

    def test_fow_visibility_memoization_skips_recompute_until_vision_inputs_change(self):
        from components.ui_components import HexMapCanvas, Hex

        root = _make_root()
        try:
            canvas = HexMapCanvas(root)
            canvas.player_name = "Hero"
            canvas.players_data = {
                "Hero": {"name": "Hero", "position": [0, 0], "vision_radius": 6, "light_radius": 0, "conditions": []}
            }
            canvas.map_data = {"lights": [{"q": 10, "r": 10, "radius": 4}]}
            fow_rev = {(0, 0), (1, 0)}
            walls = {Hex(2, 0)}

            with patch("components.ui_components.get_visible_hexes", side_effect=lambda h, r, w, grid_type="hex": [h, Hex(h.q + 1, h.r)]) as mock_vis:
                res1 = canvas._compute_player_visible_hexes(False, fow_rev, walls, "hex")
                self.assertEqual(mock_vis.call_count, 1)
                # Repeating computation (pan/zoom/redraw) or revealing empty floor away from lights -> cache hit!
                res2 = canvas._compute_player_visible_hexes(False, fow_rev | {(5, 5)}, walls, "hex")
                self.assertEqual(res1, res2)
                self.assertEqual(mock_vis.call_count, 1)

                # Moving token invalidates cache
                canvas.players_data["Hero"]["position"] = [1, 0]
                res3 = canvas._compute_player_visible_hexes(False, fow_rev | {(5, 5)}, walls, "hex")
                self.assertEqual(mock_vis.call_count, 2)
                self.assertNotEqual(res3, res1)

                # Distant stale static light in fow_revealed does not trigger remote light spying
                canvas._compute_player_visible_hexes(False, fow_rev | {(10, 10)}, walls, "hex")
                self.assertEqual(mock_vis.call_count, 2)
                # Placing/revealing static light inside active visible_now invalidates cache and computes light FoV
                canvas.map_data["lights"] = [{"q": 2, "r": 0, "radius": 4}]
                canvas._compute_player_visible_hexes(False, fow_rev, walls, "hex")
                self.assertEqual(mock_vis.call_count, 4)
        finally:
            try:
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass

    def test_broadcast_non_blocking_isolates_stalled_socket_from_healthy_client(self):
        import queue
        import socket
        from common.network_utils import broadcast, receive_message, _send_message_impl
        from common.protocol import make_chat_broadcast
        from server.network import GameState, Player

        slow_srv, slow_cli = socket.socketpair()
        ok_srv, ok_cli = socket.socketpair()
        try:
            slow_srv.settimeout(30.0)
            ok_srv.settimeout(5.0)
            ok_cli.settimeout(2.0)
            try:
                slow_srv.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                slow_cli.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
            except OSError:
                pass

            # Saturate slow_srv send buffer so its TCP peer cannot drain
            slow_srv.setblocking(False)
            try:
                while True:
                    slow_srv.send(b"X" * 4096)
            except OSError:
                pass
            slow_srv.setblocking(True)
            slow_srv.settimeout(30.0)

            gs = GameState(queue.Queue())
            gs.players = [Player("AAA_Slow", conn=slow_srv), Player("ZZZ_Healthy", conn=ok_srv)]

            t0 = time.monotonic()
            broadcast(gs, make_chat_broadcast("DM", "NonBlockingCheck"))
            elapsed = time.monotonic() - t0
            self.assertLess(elapsed, 1.5)

            pkt = receive_message(ok_cli)
            self.assertIsNotNone(pkt)
            self.assertEqual(pkt["type"], "CHAT_BROADCAST")
            self.assertEqual(pkt["data"]["text"], "NonBlockingCheck")

            # Verify chunked partial .send() handling
            class _PartialChunkSock:
                def __init__(self):
                    self.sent = bytearray()
                def fileno(self):
                    return 999
                def send(self, data):
                    step = min(len(data), 10000)
                    self.sent.extend(data[:step])
                    return step

            p_sock = _PartialChunkSock()
            with patch("common.network_utils.select.select", return_value=([], [p_sock], [])):
                ok = _send_message_impl(p_sock, {"type": "BIG", "data": "A" * 150000}, write_timeout=1.0)
            self.assertTrue(ok)
            self.assertGreater(len(p_sock.sent), 150000)
        finally:
            for s in (slow_srv, slow_cli, ok_srv, ok_cli):
                try:
                    s.close()
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
