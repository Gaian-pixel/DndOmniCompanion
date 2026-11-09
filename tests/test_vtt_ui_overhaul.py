"""
test_vtt_ui_overhaul.py - Test unitari per le funzionalità del nuovo UI/UX VTT Overhaul
Verifica:
- Barra HUD fluttuante su HexMapCanvas
- Collasso ed espansione sidebar con toggle_sidebar e sincronizzazione pulsanti
- Hero Summary Card (HP bar, token interattivo, badge CA/Velocità/Iniziativa)
- Action Economy Tracker e Target HUD con evidenziazione dorata
- Hotbar buttons con stili Modern Dark Fantasy (Hotbar.TButton e HotbarAssigned.TButton)
"""

import unittest
import tkinter as tk
from unittest.mock import MagicMock
from client.client import ClientGUI
from client.character_manager import Character
from common.theme import (
    BG_COLOR, SURFACE_COLOR, SURFACE_COLOR_ALT, BORDER_COLOR, BORDER_GOLD,
    ACCENT_GOLD, ACCENT_GREEN, ACCENT_BLUE
)


class TestVttUiOverhaul(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
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
            self.skipTest("Tkinter non disponibile nell'ambiente corrente")
        self.char = Character(name="Valeros")
        self.char.char_class = "Guerriero"
        self.char.level = 3
        self.char.hp_max = 32
        self.char.hp_current = 28
        self.char.speed = 30
        self.app = ClientGUI(self.root, initial_character=self.char)
        self.root.update()

    def tearDown(self):
        if hasattr(self, 'app') and self.app:
            try:
                self.app.disconnect()
            except Exception:
                pass
        if self.root:
            for w in self.root.winfo_children():
                try:
                    w.destroy()
                except Exception:
                    pass

    def test_vtt_floating_hud_widgets(self):
        """Verifica la creazione e i comandi della barra HUD fluttuante VTT."""
        self.assertTrue(hasattr(self.app, "vtt_hud_bar"))
        hud = self.app.vtt_hud_bar
        self.assertIsNotNone(hud)
        self.assertEqual(hud.master, self.app.map_outer_frame)

        # Controllo pulsanti HUD
        self.assertTrue(hasattr(self.app, "btn_hud_zoom_in"))
        self.assertTrue(hasattr(self.app, "btn_hud_zoom_out"))
        self.assertTrue(hasattr(self.app, "btn_hud_center"))
        self.assertTrue(hasattr(self.app, "btn_hud_measure"))
        self.assertTrue(hasattr(self.app, "btn_hud_pan"))
        self.assertTrue(hasattr(self.app, "btn_hud_toggle_sidebar"))

        # Test zoom via HUD buttons
        initial_zoom = self.app.map_canvas.zoom_level
        self.app.btn_hud_zoom_in.invoke()
        self.assertGreater(self.app.map_canvas.zoom_level, initial_zoom)

        self.app.btn_hud_zoom_out.invoke()
        self.assertAlmostEqual(self.app.map_canvas.zoom_level, initial_zoom, delta=0.05)

    def test_sidebar_toggle_behavior(self):
        """Verifica che toggle_sidebar collassi e ripristini correttamente il right_panel."""
        # Stato iniziale: espanso
        self.assertFalse(self.app.sidebar_collapsed)
        self.assertIn("▶", self.app.btn_collapse_panel.cget("text"))

        # Primo toggle: collasso
        self.app.toggle_sidebar()
        self.assertTrue(self.app.sidebar_collapsed)
        self.assertIn("◀", self.app.btn_hud_toggle_sidebar.cget("text"))
        self.assertIn("◀", self.app.btn_collapse_panel.cget("text"))

        # Secondo toggle: espansione
        self.app.toggle_sidebar()
        self.assertFalse(self.app.sidebar_collapsed)
        self.assertIn("▶", self.app.btn_hud_toggle_sidebar.cget("text"))
        self.assertIn("▶", self.app.btn_collapse_panel.cget("text"))

    def test_hero_summary_card_rendering(self):
        """Verifica il corretto rendering dei dati eroe nell'Hero Summary Card."""
        self.app.active_character = self.char
        self.app.update_hero_summary_card()

        self.assertEqual(self.app.hero_name_lbl.cget("text"), "Valeros")
        self.assertIn("Livello 3", self.app.hero_class_lbl.cget("text"))
        self.assertIn("Guerriero", self.app.hero_class_lbl.cget("text"))
        self.assertIn("28 / 32", self.app.hero_hp_lbl.cget("text"))
        self.assertIn("🛡️", self.app.hero_ac_badge.cget("text"))
        self.assertIn("⚡", self.app.hero_init_badge.cget("text"))

    def test_target_hud_and_action_economy_styling(self):
        """Verifica il comportamento del Target HUD e dell'aggiornamento dell'economia turno."""
        # Nessun bersaglio
        self.app.on_target_changed(None)
        self.assertIn("Nessuno", self.app.lbl_target_hud.cget("text"))
        self.assertEqual(self.app.target_hud_frame.cget("highlightbackground"), BORDER_COLOR)

        # Bersaglio selezionato
        self.app.on_target_changed("Orco Guerriero")
        self.assertIn("Orco Guerriero", self.app.lbl_target_hud.cget("text"))
        self.assertEqual(self.app.target_hud_frame.cget("highlightbackground"), BORDER_GOLD)

        # Reset bersaglio
        self.app.on_target_changed(None)
        self.assertIn("Nessuno", self.app.lbl_target_hud.cget("text"))
        self.assertEqual(self.app.target_hud_frame.cget("highlightbackground"), BORDER_COLOR)

        # Economia turno in e fuori combattimento
        self.app.combat_active = False
        self.app.update_action_economy_ui()
        self.assertEqual(self.app.btn_act_tracker.cget("bg"), SURFACE_COLOR_ALT)

        self.app.combat_active = True
        self.app._is_my_turn = True
        self.app.is_connected = True
        self.app.action_spent = False
        self.app.update_action_economy_ui()
        self.assertEqual(self.app.btn_act_tracker.cget("bg"), ACCENT_GREEN)

    def test_hotbar_styling(self):
        """Verifica che i pulsanti Hotbar siano inizializzati e aggiornati con gli stili corretti."""
        self.assertEqual(len(self.app.hotbar_buttons), 10)
        self.assertEqual(str(self.app.hotbar_buttons[0].cget("style")), "Hotbar.TButton")

        # Assegna macro al primo slot
        self.char.hotbar = ["1d20+5", "", "", "", "", "", "", "", "", ""]
        self.app.active_character = self.char
        self.app.active_character_var.set("Valeros")
        self.app.on_active_character_changed()

        self.assertEqual(str(self.app.hotbar_buttons[0].cget("style")), "HotbarAssigned.TButton")
        self.assertEqual(self.app.hotbar_buttons[0].cget("text"), "1d20+5")
        self.assertEqual(str(self.app.hotbar_buttons[1].cget("style")), "Hotbar.TButton")


if __name__ == "__main__":
    unittest.main()
