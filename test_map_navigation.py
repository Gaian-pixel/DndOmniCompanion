import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from components.ui_components import HexMapCanvas, CommandPaletteDialog
from common.hex_utils import Hex, HexLayout


class TestMapNavigation(unittest.TestCase):
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

    def setUp(self):
        self.frame = tk.Frame(self.root)
        self.frame.pack()
        self.canvas = HexMapCanvas(self.frame, width=800, height=600)
        self.canvas.pack()
        self.canvas.hex_layout = HexLayout(size=30, origin=(400, 300))
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.canvas.destroy()
            self.frame.destroy()
        except Exception:
            pass

    def test_initial_pan_state(self):
        self.assertFalse(getattr(self.canvas, "pan_mode", True))
        self.assertFalse(getattr(self.canvas, "_space_held", True))
        self.assertEqual(self.canvas.pan_offset_x, 0)
        self.assertEqual(self.canvas.pan_offset_y, 0)

    def test_toggle_pan_mode(self):
        # Toggle ON
        res = self.canvas.toggle_pan_mode()
        self.assertTrue(res)
        self.assertTrue(self.canvas.pan_mode)
        self.assertEqual(self.canvas.cget("cursor"), "fleur")

        # Toggle OFF
        res = self.canvas.toggle_pan_mode()
        self.assertFalse(res)
        self.assertFalse(self.canvas.pan_mode)
        self.assertEqual(self.canvas.cget("cursor"), "")

        # Explicit set
        self.canvas.toggle_pan_mode(True)
        self.assertTrue(self.canvas.pan_mode)
        self.canvas.toggle_pan_mode(False)
        self.assertFalse(self.canvas.pan_mode)

    def test_pan_mode_cancels_ruler_and_pen(self):
        self.canvas.ruler_mode = True
        self.canvas.pen_mode = True
        self.canvas.toggle_pan_mode(True)
        self.assertTrue(self.canvas.pan_mode)
        self.assertFalse(self.canvas.ruler_mode)
        self.assertFalse(self.canvas.pen_mode)

    def test_ruler_mode_cancels_pan(self):
        self.canvas.toggle_pan_mode(True)
        self.assertTrue(self.canvas.pan_mode)
        self.canvas.toggle_ruler_mode()
        self.assertTrue(self.canvas.ruler_mode)
        self.assertFalse(self.canvas.pan_mode)

    def test_pan_by(self):
        initial_x = self.canvas.pan_offset_x
        initial_y = self.canvas.pan_offset_y
        self.canvas.pan_by(50, -30)
        self.assertEqual(self.canvas.pan_offset_x, initial_x + 50)
        self.assertEqual(self.canvas.pan_offset_y, initial_y - 30)

        self.canvas.pan_by(-20, 40)
        self.assertEqual(self.canvas.pan_offset_x, initial_x + 30)
        self.assertEqual(self.canvas.pan_offset_y, initial_y + 10)

    def test_space_press_and_release(self):
        class DummyEvent:
            pass

        e = DummyEvent()
        self.canvas._on_space_press(e)
        self.assertTrue(self.canvas._space_held)
        self.assertEqual(self.canvas.cget("cursor"), "fleur")

        self.canvas._on_space_release(e)
        self.assertFalse(self.canvas._space_held)
        self.assertEqual(self.canvas.cget("cursor"), "")

    def test_can_handle_key_respects_entry_focus(self):
        entry = tk.Entry(self.frame)
        entry.pack()

        # When Entry is focused, keys should not be handled by map shortcuts
        with patch.object(self.canvas, "focus_get", return_value=entry):
            self.assertFalse(self.canvas._can_handle_key())

        # When canvas has focus, keys should be handled
        with patch.object(self.canvas, "focus_get", return_value=self.canvas):
            self.assertTrue(self.canvas._can_handle_key())

        # When no focus, keys should be handled
        with patch.object(self.canvas, "focus_get", return_value=None):
            self.assertTrue(self.canvas._can_handle_key())

        entry.destroy()

    def test_escape_cancels_pan_mode(self):
        self.canvas.toggle_pan_mode(True)
        self.assertTrue(self.canvas.pan_mode)
        self.canvas._on_escape_press()
        self.assertFalse(self.canvas.pan_mode)
        self.assertEqual(self.canvas.cget("cursor"), "")

    def test_canvas_click_and_drag_in_pan_mode(self):
        self.canvas.toggle_pan_mode(True)

        class DummyMouseEvent:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        # Click starts pan
        self.canvas._on_canvas_click(DummyMouseEvent(100, 100))
        self.assertEqual(self.canvas._pan_start_x, 100)
        self.assertEqual(self.canvas._pan_start_y, 100)

        # Drag moves pan
        self.canvas._on_canvas_drag(DummyMouseEvent(150, 120))
        self.assertEqual(self.canvas.pan_offset_x, 50)
        self.assertEqual(self.canvas.pan_offset_y, 20)
        self.assertTrue(self.canvas._is_panning)

        # Release ends pan
        self.canvas._on_canvas_release(DummyMouseEvent(150, 120))
        self.assertFalse(self.canvas._is_panning)

    def test_hud_contains_pan_button(self):
        self.canvas.map_data = {"grid": []}
        self.canvas.redraw()
        bboxes = getattr(self.canvas, "_hud_control_bboxes", [])
        action_keys = [b[4] for b in bboxes]
        self.assertIn("pan", action_keys)
        self.assertIn("center", action_keys)
        self.assertIn("zoom_in", action_keys)
        self.assertIn("zoom_out", action_keys)
        self.assertIn("ruler", action_keys)

        # Find pan bbox and simulate click
        for bx1, by1, bx2, by2, action in bboxes:
            if action == "pan":
                class DummyClick:
                    x = (bx1 + bx2) // 2
                    y = (by1 + by2) // 2
                self.canvas._on_canvas_click(DummyClick())
                self.assertTrue(self.canvas.pan_mode)
                self.canvas._on_canvas_click(DummyClick())
                self.assertFalse(self.canvas.pan_mode)
                break

    def test_command_palette_includes_toggle_pan(self):
        cp = CommandPaletteDialog(self.root, map_canvas=self.canvas)
        self.root.update_idletasks()
        cp._perform_search("pan")
        found = any(r.get("payload") == "toggle_pan" for r in cp._results)
        self.assertTrue(found, "Command palette must include toggle_pan action")
        cp.destroy()

    def test_dm_gui_pan_integration(self):
        # Test DM_GUI toggle_pan_mode and key handlers logic
        from server.dm_gui import DM_GUI
        dm = MagicMock()
        dm.master = self.root
        dm.map_canvas = self.canvas
        dm.show_toast = MagicMock()

        # Call bound toggle_pan_mode
        DM_GUI.toggle_pan_mode(dm)
        self.assertTrue(self.canvas.pan_mode)
        dm.show_toast.assert_called()

        DM_GUI.toggle_pan_mode(dm)
        self.assertFalse(self.canvas.pan_mode)

        # Test space key handlers
        DM_GUI._on_space_key_press(dm, None)
        self.assertTrue(self.canvas._space_held)
        DM_GUI._on_space_key_release(dm, None)
        self.assertFalse(self.canvas._space_held)

        # Test palette action
        dm.toggle_pan_mode = MagicMock()
        DM_GUI._handle_command_palette_action(dm, "action", "toggle_pan")
        dm.toggle_pan_mode.assert_called_once()

    def test_client_pan_integration(self):
        from client.client import ClientGUI
        client = MagicMock()
        client.master = self.root
        client.map_canvas = self.canvas
        client.show_toast = MagicMock()

        ClientGUI.toggle_pan_mode(client)
        self.assertTrue(self.canvas.pan_mode)

        ClientGUI.toggle_pan_mode(client)
        self.assertFalse(self.canvas.pan_mode)

        ClientGUI._on_space_key_press(client, None)
        self.assertTrue(self.canvas._space_held)
        ClientGUI._on_space_key_release(client, None)
        self.assertFalse(self.canvas._space_held)

        client.toggle_pan_mode = MagicMock()
        ClientGUI._handle_command_palette_action(client, "action", "toggle_pan")
        client.toggle_pan_mode.assert_called_once()

    def test_map_editor_pan_methods(self):
        from server.map_editor import MapEditorWindow
        editor = MagicMock()
        editor.canvas = self.canvas
        editor.pan_offset_x = 0
        editor.pan_offset_y = 0
        editor._pan_start_x = 0
        editor._pan_start_y = 0
        editor.focus_get = MagicMock(return_value=None)

        MapEditorWindow.pan_by(editor, 40, -30)
        self.assertEqual(editor.pan_offset_x, 40)
        self.assertEqual(editor.pan_offset_y, -30)

        MapEditorWindow._on_space_press(editor)
        self.assertTrue(editor._space_held)
        MapEditorWindow._on_space_release(editor)
        self.assertFalse(editor._space_held)


if __name__ == "__main__":
    unittest.main()
