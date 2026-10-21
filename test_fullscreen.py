# test_fullscreen.py
import unittest
import tkinter as tk
from common.i18n import _t, set_language

class TestFullscreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except tk.TclError:
            cls.root = None

    @classmethod
    def tearDownClass(cls):
        if cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        if not self.root:
            self.skipTest("Tkinter GUI not available in headless environment")

    def test_i18n_strings(self):
        set_language("it")
        self.assertEqual(_t("menu_view"), "Visualizza")
        self.assertIn("F11", _t("menu_fullscreen"))
        self.assertIn("Esc", _t("toast_fullscreen_on"))

        set_language("en")
        self.assertEqual(_t("menu_view"), "View")
        self.assertIn("F11", _t("menu_fullscreen"))

    def test_window_fullscreen_toggle(self):
        win = tk.Toplevel(self.root)
        try:
            is_fs = bool(win.attributes("-fullscreen"))
            self.assertFalse(is_fs)

            # Toggle fullscreen on
            win.attributes("-fullscreen", True)
            self.assertTrue(bool(win.attributes("-fullscreen")))

            # Toggle fullscreen off
            win.attributes("-fullscreen", False)
            self.assertFalse(bool(win.attributes("-fullscreen")))
        finally:
            win.destroy()

    def test_dm_gui_fullscreen_methods(self):
        from server.dm_gui import DM_GUI
        # Verifica presenza dei metodi toggle_fullscreen e exit_fullscreen
        self.assertTrue(hasattr(DM_GUI, "toggle_fullscreen"))
        self.assertTrue(hasattr(DM_GUI, "exit_fullscreen"))

    def test_client_gui_fullscreen_methods(self):
        from client.client import ClientGUI
        self.assertTrue(hasattr(ClientGUI, "toggle_fullscreen"))
        self.assertTrue(hasattr(ClientGUI, "exit_fullscreen"))

    def test_live_flow_fullscreen_methods(self):
        from server.dm_live_flow import DMLiveFlowDialog
        self.assertTrue(hasattr(DMLiveFlowDialog, "toggle_fullscreen"))
        self.assertTrue(hasattr(DMLiveFlowDialog, "exit_fullscreen"))

    def test_campaign_studio_fullscreen_methods(self):
        from server.campaign_studio_ui import CampaignStudioFrame
        self.assertTrue(hasattr(CampaignStudioFrame, "toggle_fullscreen"))
        self.assertTrue(hasattr(CampaignStudioFrame, "exit_fullscreen"))

    def test_campaign_editor_fullscreen_methods(self):
        from server.campaign_editor_ui import CampaignEditorDialog
        self.assertTrue(hasattr(CampaignEditorDialog, "toggle_fullscreen"))
        self.assertTrue(hasattr(CampaignEditorDialog, "exit_fullscreen"))

if __name__ == '__main__':
    unittest.main()
