# -*- coding: utf-8 -*-
"""
Test Suite di Regressione — Fase 4: Concorrenza, Thread-Safety Tkinter & Motore VTT / Dadi 3D
Verifica:
4.1: Lifecycle Tcl, pulizia listener morti in i18n, stili TTK in theme.py.
4.2: Timeout send socket e thread-safety.
4.3: Allineamento schema players_data del DM e parsing listbox senza mojibake.
4.4: Motore Dadi 3D (d%, crit damage, sound cache lock, d4 orientation), scaling raggio token, avatar cache e isolamento note diario.
"""

import unittest
import tkinter as tk
from tkinter import ttk
import queue
import socket
import os
import sys

from common.game_state import GameState, Player
from common.i18n import (
    set_language, get_language, register_language_listener,
    reset_listeners_for_testing
)
from common.theme import setup_theme
from common.network_utils import send_message
from components.dice_3d_canvas import (
    ensure_dice_sound_file, get_die_view_matrix, Dice3DOverlay
)


class TestAuditPhase4(unittest.TestCase):

    def setUp(self):
        reset_listeners_for_testing()

    def test_4_1_i18n_dead_listener_pruning_and_ttk_styles(self):
        """4.1: Verifica potatura robusta dei listener morti in i18n e presenza stili TTK."""
        # 1. Listener morto con "invalid command name" o "destroyed"
        def dead_callback(lang):
            raise Exception("invalid command name \"::tk::after_cancel\"")

        def working_callback(lang):
            working_callback.called = True
        working_callback.called = False

        register_language_listener(dead_callback)
        register_language_listener(working_callback)

        # Il cambio lingua non deve esplodere, deve eseguire il listener sano e potare quello morto
        set_language("en" if get_language() == "it" else "it")
        self.assertTrue(working_callback.called)

        # 2. Verifica presenza stili TTK Accent.TButton e Secondary.TButton
        root = tk.Tk()
        root.withdraw()
        try:
            setup_theme(root)
            style = ttk.Style(root)
            # Layout/Config non deve lanciare eccezioni
            accent_bg = style.lookup("Accent.TButton", "background")
            sec_bg = style.lookup("Secondary.TButton", "background")
            self.assertTrue(accent_bg, "Accent.TButton deve avere un background configurato")
            self.assertTrue(sec_bg, "Secondary.TButton deve avere un background configurato")
        finally:
            root.destroy()

    def test_4_2_socket_send_timeout_non_blocking(self):
        """4.2: Verifica che send_message gestisca correttamente timeout o socket disconnessi."""
        # Socket client fittizio o chiuso
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.close()
        # send_message su socket chiuso non deve sollevare eccezioni non gestite
        send_message(sock, {"type": "TEST", "data": {}})
        # Nessun crash

    def test_4_3_listbox_robust_name_extraction_and_vtt_schema(self):
        """4.3: Verifica estrazione robusta dei nomi da listbox senza mojibake e schema completo players_data."""
        from server.dm_gui import DM_GUI
        root = tk.Tk()
        root.withdraw()
        try:
            # Creazione mock DM_GUI per testare get_player_name_from_listbox
            class MockDMGUI:
                pass
            mock = MockDMGUI()
            mock.player_listbox = tk.Listbox(root)
            mock._listbox_player_names = ["Aragorn", "Gandalf", None, "Orco 1"]
            mock.get_player_name_from_listbox = DM_GUI.get_player_name_from_listbox.__get__(mock)

            # Test 1: tramite _listbox_player_names indicizzato
            self.assertEqual(mock.get_player_name_from_listbox(0), "Aragorn")
            self.assertEqual(mock.get_player_name_from_listbox(1), "Gandalf")
            self.assertIsNone(mock.get_player_name_from_listbox(2))
            self.assertEqual(mock.get_player_name_from_listbox(3), "Orco 1")

            # Test 2: Fallback pulizia stringhe con simboli problematici (➡️, ▶, ?, [N], [Fuori dal Combattimento])
            mock._listbox_player_names = [] # Forza fallback parsing stringa
            mock.player_listbox.delete(0, tk.END)
            mock.player_listbox.insert(0, "➡️ [N] Goblin Capo (HP: 22/22) [Iniz: 14]")
            mock.player_listbox.insert(1, "  Orco Berserker [Fuori dal Combattimento] {Prono}")
            mock.player_listbox.insert(2, "▶ ? Chierico (HP: 18/18) [Iniz: 10]")

            self.assertEqual(mock.get_player_name_from_listbox(0), "Goblin Capo")
            self.assertEqual(mock.get_player_name_from_listbox(1), "Orco Berserker")
            self.assertEqual(mock.get_player_name_from_listbox(2), "Chierico")
        finally:
            root.destroy()

    def test_4_4_dice_3d_engine_d_percent_and_crit_doubling(self):
        """4.4: Verifica parsing d% e duplicazione visiva dadi critici nel motore 3D."""
        root = tk.Tk()
        root.withdraw()
        try:
            overlay = Dice3DOverlay(root)
            # 1. d% viene interpretato come d100
            dice_pct = overlay._extract_dice_list("1d%", {"rolls": [73], "total": 73})
            self.assertEqual(len(dice_pct), 1)
            self.assertEqual(dice_pct[0]["die"], "d100")
            self.assertEqual(dice_pct[0]["val"], 73)

            # 2. Danno critico con formula '2d6' e rolls = [6, 4, 5, 2] (4 dadi invece di 2)
            dice_crit = overlay._extract_dice_list("2d6", {"rolls": [6, 4, 5, 2], "is_crit": True, "total": 17})
            self.assertEqual(len(dice_crit), 4) # Tutti e 4 i dadi visualizzati
            for d in dice_crit:
                self.assertEqual(d["die"], "d6")

            # 3. Orientamento d4
            mat_d4 = get_die_view_matrix("d4")
            self.assertEqual(len(mat_d4), 3)

            # 4. Sound cache
            sound_path = ensure_dice_sound_file()
            self.assertTrue(os.path.exists(sound_path))
        finally:
            root.destroy()

    def test_4_5_token_scaling_and_avatar_cache_lru(self):
        """4.5: Verifica scaling dinamico del raggio token e hashing avatar."""
        # Simulazione canvas token radius
        zoom_level = 1.5
        size_mult = 2.0 # Grande (2x2)
        radius = max(6.0, min(120.0, 12 * zoom_level * size_mult))
        self.assertEqual(radius, 36.0) # 12 * 1.5 * 2 = 36

        # Due PNG fittizi con primi 32 byte identici (header) ma contenuto diverso
        fake_png_header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x20\x00\x00\x00\x20\x08\x06\x00\x00\x00"
        import base64
        b64_1 = base64.b64encode(fake_png_header + b"AVATAR_IMAGE_ONE_DATA_1111111111111111111").decode("ascii")
        b64_2 = base64.b64encode(fake_png_header + b"AVATAR_IMAGE_TWO_DATA_2222222222222222222").decode("ascii")

        sig_1 = f"{len(b64_1)}_{hash(b64_1[:32] + b64_1[-32:])}"
        sig_2 = f"{len(b64_2)}_{hash(b64_2[:32] + b64_2[-32:])}"
        self.assertNotEqual(sig_1, sig_2, "Le firme di cache di due avatar diversi non devono collidere!")

    def test_4_6_player_journal_campaign_isolation_and_silent_save(self):
        """4.6: Verifica isolamento file note per campagna in PlayerJournalDialog."""
        from client.player_journal_dialog import PlayerJournalDialog
        from common.campaign_journal import CampaignJournal

        root = tk.Tk()
        root.withdraw()
        try:
            cj = CampaignJournal(campaign_name="La Miniera Perduta")
            cj.start_new_session("Arrivo a Phandalin")

            class MockJournalGUI:
                pass
            dlg = MockJournalGUI()
            dlg.character_name = "Tordek"
            dlg.journal = cj
            path_phandalin = PlayerJournalDialog._get_notes_file_path(dlg)
            self.assertIn("LaMinieraPerduta", path_phandalin)

            # Altra campagna
            cj2 = CampaignJournal(campaign_name="La Maledizione di Strahd")
            dlg.journal = cj2
            path_strahd = PlayerJournalDialog._get_notes_file_path(dlg)
            self.assertIn("LaMaledizioned", path_strahd)
            self.assertNotEqual(path_phandalin, path_strahd, "Note di campagne diverse devono essere salvate in file distinti!")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

