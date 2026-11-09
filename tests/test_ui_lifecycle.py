"""
test_ui_lifecycle.py - Test unitari per ui_lifecycle (safe_after, cancel_all_after_timers, safe_destroy_window)
Verifica l'assenza di crash Tcl o bgerror su widget distrutti.
"""

import unittest
import tkinter as tk
import time
from common.ui_lifecycle import safe_after, cancel_safe_timer, cancel_all_after_timers, safe_destroy_window
from common.i18n import set_language, get_language, register_language_listener, unregister_language_listener


class TestUILifecycle(unittest.TestCase):
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

    def test_safe_after_normal_execution(self):
        """Verifica che safe_after esegua regolarmente la callback se il widget è vivo."""
        frame = tk.Frame(self.root)
        frame.pack()
        executed = []

        def callback():
            executed.append(True)

        tid = safe_after(frame, 10, callback)
        self.assertIsNotNone(tid)
        
        # Attendi esecuzione
        self.root.update()
        time.sleep(0.05)
        self.root.update()

        self.assertTrue(executed and executed[0])
        frame.destroy()

    def test_safe_after_cancellation(self):
        """Verifica che un timer possa essere cancellato tramite cancel_safe_timer."""
        frame = tk.Frame(self.root)
        frame.pack()
        executed = []

        tid = safe_after(frame, 100, lambda: executed.append(True))
        cancel_safe_timer(frame, tid)

        self.root.update()
        time.sleep(0.12)
        self.root.update()

        self.assertEqual(len(executed), 0)
        frame.destroy()

    def test_cancel_all_after_timers(self):
        """Verifica che cancel_all_after_timers ripulisca tutti i timer pendenti."""
        frame = tk.Frame(self.root)
        frame.pack()
        executed = []

        safe_after(frame, 100, lambda: executed.append(1))
        safe_after(frame, 100, lambda: executed.append(2))
        self.assertEqual(len(getattr(frame, "_safe_timers", set())), 2)

        cancel_all_after_timers(frame)
        self.assertEqual(len(getattr(frame, "_safe_timers", set())), 0)

        self.root.update()
        time.sleep(0.12)
        self.root.update()

        self.assertEqual(len(executed), 0)
        frame.destroy()

    def test_safe_after_widget_destroyed_before_timer_fires(self):
        """Verifica che se il widget viene distrutto prima dello scatto del timer, non si sollevino errori Tcl."""
        top = tk.Toplevel(self.root)
        executed = []

        safe_after(top, 30, lambda: executed.append(True))
        
        # Distruggi la finestra prima che il timer scatti
        safe_destroy_window(top)
        self.root.update()
        time.sleep(0.06)
        self.root.update()

        # Non deve essere eseguito e non deve sollevare TclError
        self.assertEqual(len(executed), 0)

    def test_safe_after_on_dead_widget_returns_none(self):
        """safe_after invocato su widget già distrutto o None ritorna None senza errori."""
        self.assertIsNone(safe_after(None, 10, lambda: None))

        top = tk.Toplevel(self.root)
        top.destroy()
        self.root.update()

        self.assertIsNone(safe_after(top, 10, lambda: None))


if __name__ == "__main__":
    unittest.main()

