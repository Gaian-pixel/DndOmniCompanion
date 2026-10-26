# tests/test_3d_dice.py
"""
Test completi per il Motore 3D dei Dadi Poliedrici (components/dice_3d_canvas.py).
Verifica:
- Geometria e poliedri (d4, d6, d8, d10, d12, d20, d100)
- Matematica matriciale, quaternioni, Rodrigues alignment e slerp
- Sintesi audio WAV e riproduzione sicura
- Fisica, rimbalzi elastici e Z-sorting del Die3DInstance
- Overlay completo con lanci normali, vantaggio/svantaggio e critici
"""

import unittest
import math
import os
import wave
import tkinter as tk
from unittest.mock import patch
from components.dice_3d_canvas import (
    vec3_norm, vec3_dot, vec3_cross, vec3_add, vec3_sub, vec3_scale,
    quat_from_axis_angle, quat_multiply, quat_to_matrix, quat_slerp,
    matrix_to_quat, get_face_target_matrix, mat_vec_mul,
    get_polyhedron, ensure_dice_sound_file, play_dice_bounce_sound,
    Die3DInstance, Dice3DOverlay
)


class TestDice3DMathAndGeometry(unittest.TestCase):
    """Test unitari per la matematica 3D e la geometria dei poliedri."""

    def test_vector_operations(self):
        v1 = (1.0, 2.0, 3.0)
        v2 = (4.0, 5.0, 6.0)
        
        # Add & Sub
        self.assertEqual(vec3_add(v1, v2), (5.0, 7.0, 9.0))
        self.assertEqual(vec3_sub(v2, v1), (3.0, 3.0, 3.0))
        
        # Dot product
        self.assertEqual(vec3_dot(v1, v2), 4.0 + 10.0 + 18.0)
        
        # Cross product
        cross = vec3_cross((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        self.assertAlmostEqual(cross[0], 0.0)
        self.assertAlmostEqual(cross[1], 0.0)
        self.assertAlmostEqual(cross[2], 1.0)
        
        # Norm
        n = vec3_norm((0.0, 3.0, 4.0))
        self.assertAlmostEqual(n[0], 0.0)
        self.assertAlmostEqual(n[1], 0.6)
        self.assertAlmostEqual(n[2], 0.8)

    def test_quaternion_and_matrix_conversions(self):
        # Identity
        q_id = (1.0, 0.0, 0.0, 0.0)
        m_id = quat_to_matrix(q_id)
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(m_id[i][j], 1.0 if i == j else 0.0)
                
        # 90 deg rotation around Y
        q_y90 = quat_from_axis_angle((0.0, 1.0, 0.0), math.pi / 2.0)
        m_y90 = quat_to_matrix(q_y90)
        v = (1.0, 0.0, 0.0)
        rot_v = mat_vec_mul(m_y90, v)
        self.assertAlmostEqual(rot_v[0], 0.0, places=5)
        self.assertAlmostEqual(rot_v[1], 0.0, places=5)
        self.assertAlmostEqual(rot_v[2], -1.0, places=5)
        
        # Matrix to Quat round-trip
        q_rec = matrix_to_quat(m_y90)
        self.assertAlmostEqual(abs(q_y90[0] * q_rec[0] + q_y90[2] * q_rec[2]), 1.0, places=4)

    def test_face_target_alignment(self):
        """Verifica che get_face_target_matrix allinei il vettore normale della faccia a (0, 0, 1)."""
        test_normal = vec3_norm((0.577, 0.577, 0.577))
        test_up = vec3_norm((0.0, 1.0, 0.0))
        
        R = get_face_target_matrix(test_normal, test_up)
        aligned_normal = mat_vec_mul(R, test_normal)
        
        self.assertAlmostEqual(aligned_normal[0], 0.0, places=4)
        self.assertAlmostEqual(aligned_normal[1], 0.0, places=4)
        self.assertAlmostEqual(aligned_normal[2], 1.0, places=4)

    def test_polyhedron_models_completeness(self):
        """Verifica che tutti i dadi poliedrici 5e abbiano facce, vertici e numeri corretti."""
        dice_specs = [
            ("d4", 4, 4),
            ("d6", 8, 6),
            ("d8", 6, 8),
            ("d10", 12, 10),
            ("d12", 20, 12),
            ("d20", 12, 20),
            ("d100", 12, 10)
        ]
        
        for name, expected_verts, expected_faces in dice_specs:
            poly = get_polyhedron(name)
            self.assertEqual(len(poly.vertices), expected_verts, f"{name} vertices mismatch")
            self.assertEqual(len(poly.faces), expected_faces, f"{name} faces mismatch")
            self.assertEqual(len(poly.face_numbers), expected_faces, f"{name} numbers mismatch")
            self.assertEqual(len(poly.face_normals), expected_faces, f"{name} normals mismatch")
            self.assertEqual(len(poly.face_ups), expected_faces, f"{name} up directions mismatch")
            
            # Tutti i numeri/stringhe delle facce devono essere unici
            self.assertEqual(len(set(poly.face_numbers)), expected_faces, f"{name} duplicate numbers")


class TestDice3DSoundAndAudio(unittest.TestCase):
    """Test per la generazione del file audio di rimbalzo dei dadi."""

    def test_ensure_dice_sound_file(self):
        wav_path = ensure_dice_sound_file()
        self.assertTrue(os.path.exists(wav_path), "WAV sound file not created")
        self.assertGreater(os.path.getsize(wav_path), 500, "WAV sound file is too small")
        
        # Validazione header WAV
        with wave.open(wav_path, "rb") as wav:
            self.assertEqual(wav.getnchannels(), 1)
            self.assertEqual(wav.getsampwidth(), 2)
            self.assertEqual(wav.getframerate(), 44100)
            self.assertGreater(wav.getnframes(), 1000)

    def test_play_dice_sound_non_blocking(self):
        # Non deve lanciare eccezioni
        try:
            play_dice_bounce_sound()
        except Exception as e:
            self.fail(f"play_dice_bounce_sound ha sollevato un'eccezione: {e}")


class TestDice3DInstanceAndOverlay(unittest.TestCase):
    """Test per la simulazione fisica e il widget Canvas di overlay."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.frame = tk.Frame(self.root, width=600, height=400)
        self.frame.pack()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_die_instance_physics_and_render(self):
        canvas = tk.Canvas(self.frame, width=600, height=400)
        canvas.pack()
        
        die = Die3DInstance(
            die_type="d20",
            target_value=18,
            start_x=100.0,
            start_y=100.0,
            dest_x=300.0,
            dest_y=200.0,
            radius=52.0,
            is_crit=False,
            is_fumble=False,
            sound_enabled=False
        )
        
        bounds = (20.0, 20.0, 580.0, 380.0)
        # Step physics in rolling phase
        die.update(dt=0.02, progress=0.2, bounds=bounds)
        self.assertFalse(die.is_settled)
        
        # Render rolling state
        die.render(canvas)
        items = canvas.find_all()
        self.assertGreater(len(items), 0, "No canvas items rendered during roll")
        
        # Step physics into settle phase (progress > 0.65)
        for _ in range(30):
            die.update(dt=0.03, progress=0.99, bounds=bounds)
            
        self.assertTrue(die.is_settled)
        self.assertAlmostEqual(die.x, 300.0, delta=2.0)
        self.assertAlmostEqual(die.y, 200.0, delta=2.0)
        
        # Render settled state
        canvas.delete("all")
        die.render(canvas)
        items_settled = canvas.find_all()
        self.assertGreater(len(items_settled), 0, "No canvas items rendered when settled")

    def test_die_critical_and_fumble_modes(self):
        canvas = tk.Canvas(self.frame, width=600, height=400)
        canvas.pack()
        
        # Crit 20
        crit_die = Die3DInstance("d20", 20, 200, 200, 200, 200, is_crit=True, sound_enabled=False)
        crit_die.is_settled = True
        crit_die.render(canvas)
        glow_items = canvas.find_withtag("dice_glow")
        self.assertGreater(len(glow_items), 0, "Glow not rendered for critical hit")
        
        # Fumble 1
        canvas.delete("all")
        fumble_die = Die3DInstance("d20", 1, 200, 200, 200, 200, is_fumble=True, sound_enabled=False)
        fumble_die.is_settled = True
        fumble_die.render(canvas)
        fumble_glow = canvas.find_withtag("dice_glow")
        self.assertGreater(len(fumble_glow), 0, "Glow not rendered for fumble")

    def test_overlay_lifecycle_and_interaction(self):
        overlay = Dice3DOverlay(self.frame, sound_enabled=False, speed="fast")
        
        roll_res = {
            "rolls": [15],
            "other_rolls": [3],
            "modifier": 4,
            "total": 19,
            "is_crit": False,
            "is_fumble": False
        }
        
        overlay.roll("1d20+4 adv", roll_res, player_name="Gimli", reason="Attacco Ascia")
        self.assertTrue(overlay.is_running)
        self.assertEqual(len(overlay.dice), 2, "Advantage roll should generate 2 dice")
        self.assertFalse(overlay.dice[0].is_discarded)
        self.assertTrue(overlay.dice[1].is_discarded)
        
        # Advance animation step
        overlay._animate_step()
        
        # Click during roll skips immediately to result
        overlay._on_canvas_click(None)
        self.assertTrue(overlay.is_finished)
        
        # Subsequent click dismisses overlay
        overlay._on_canvas_click(None)
        self.assertFalse(overlay.is_running)


class TestDice3DAppIntegration(unittest.TestCase):
    """Test unitari per i metodi di integrazione in Client e DM_GUI."""

    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_client_3d_dice_methods(self):
        from client.client import ClientGUI
        with patch("client.client.ClientNetwork"), \
             patch("client.client.AudioManager"), \
             patch("client.client.VoiceClient"):
            app = ClientGUI(self.root)
            self.assertTrue(getattr(app, "enable_3d_dice", False))
            
            # Toggle 3D dice
            app.toggle_3d_dice()
            self.assertFalse(app.enable_3d_dice)
            app.toggle_3d_dice()
            self.assertTrue(app.enable_3d_dice)
            
            # Trigger roll
            res = {"rolls": [18], "modifier": 2, "total": 20, "is_crit": False, "is_fumble": False}
            app.trigger_3d_dice_roll("1d20+2", res, "Tester", "Prova Atletica")
            self.assertIsNotNone(app.dice_3d_overlay)
            self.assertTrue(app.dice_3d_overlay.is_running)
            
            # Dismiss
            app.dice_3d_overlay.dismiss()
            self.assertFalse(app.dice_3d_overlay.is_running)

    def test_dm_gui_3d_dice_methods(self):
        from server.dm_gui import DM_GUI
        with patch("server.dm_gui.Server"), \
             patch("server.dm_gui.AudioManager"), \
             patch("server.dm_gui.VoiceClient"):
            gui = DM_GUI(self.root)
            self.assertTrue(getattr(gui, "enable_3d_dice", False))
            
            # Toggle
            gui.toggle_3d_dice()
            self.assertFalse(gui.enable_3d_dice)
            gui.toggle_3d_dice()
            self.assertTrue(gui.enable_3d_dice)
            
            # Trigger
            res = {"rolls": [20], "modifier": 5, "total": 25, "is_crit": True, "is_fumble": False}
            gui.trigger_3d_dice_roll("1d20+5", res, "DM", "Tiro Incontro")
            self.assertIsNotNone(gui.dice_3d_overlay)
            self.assertTrue(gui.dice_3d_overlay.is_running)
            
            gui.dice_3d_overlay.dismiss()
            self.assertFalse(gui.dice_3d_overlay.is_running)


if __name__ == "__main__":
    unittest.main()
