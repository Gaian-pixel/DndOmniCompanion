"""Phase 6 release readiness, v0.5.0 migration, maturity & zero-AI verification suite."""

import ast
import gc
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("DND_MOCK_AUDIO", "1")

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestPhase6ReleaseReadiness(unittest.TestCase):
    """Verifiche finali v0.6.0: packaging dry-run, migrazione v0.5.0, maturita 14/14, docs bilingui e Zero AI."""

    def test_build_release_dry_run_and_validate_inputs(self):
        import build_release

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RELEASE_VERSION", None)
            self.assertEqual(build_release.VERSION, "v0.6.0-alpha")

        errors = build_release.validate_build_inputs()
        self.assertEqual(errors, [], f"build_release validation errors: {errors}")

        proc = subprocess.run(
            [sys.executable, "-X", "utf8", "build_release.py", "--dry-run"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, f"build_release --dry-run failed:\n{out}")
        self.assertIn("DRY_RUN_STATUS=OK", out)
        self.assertIn("v0.6.0-alpha", out)

    def test_v050_legacy_character_migration_to_v060(self):
        from client.character_manager import Character

        legacy_v05_char = {
            "name": "Aldric v05",
            "char_class": "Guerriero",
            "level": 5,
            "race": "Umano",
            "hp_max": 44,
            "hp_current": 31,
            "attributes": {"FOR": 16, "DES": 14, "COS": 14, "INT": 10, "SAG": 12, "CAR": 10},
            "spell_slots": {"1": [2, 3]},
            "spell_list": [{"name": "Dardo Incantato", "level": 1}],
            "legacy_v05_badge": "veteran",
        }
        char = Character.from_dict(legacy_v05_char)
        self.assertEqual(char.name, "Aldric v05")
        self.assertEqual(char.spell_slots["1"], {"max": 3, "current": 2})
        self.assertEqual(len(char.spellbook), 1)
        self.assertEqual(char.spellbook[0]["name"], "Dardo Incantato")
        self.assertIsInstance(char.hit_dice_pools, dict)
        self.assertIsInstance(char.death_saves, dict)
        self.assertIsInstance(char.saving_throw_proficiencies, list)

        reserialized = char.to_dict()
        self.assertEqual(reserialized.get("legacy_v05_badge"), "veteran")
        self.assertEqual(reserialized.get("hp_current"), 31)
        self.assertIn("hit_dice_pools", reserialized)
        self.assertIn("death_saves", reserialized)

    def test_v050_legacy_gamestate_campaign_and_map_teleports_migration(self):
        from common.campaign import Campaign
        from common.file_utils import atomic_save_json
        from common.game_state import GameState
        from common.hex_utils import Hex
        from server.map_editor import MapEditorWindow

        with tempfile.TemporaryDirectory(prefix="dnd_mig_v05_") as tmpd:
            # 1) Legacy GameState session JSON (senza maps, active_map_id, pending_legendary_resistances, death_saves, is_npc)
            session_path = os.path.join(tmpd, "legacy_session.json")
            legacy_session = {
                "combat_active": False,
                "round_number": 3,
                "map": {"grid_type": "hex", "hex_size": 35, "hexes": [[0, 0], [1, 0]], "walls": [], "doors": []},
                "players": [
                    {
                        "name": "Lyra",
                        "role": "player",
                        "hp": 22,
                        "max_hp": 28,
                        "position": [1, 0],
                        "conditions": [],
                    }
                ],
                "legacy_v05_meta": "session_archive_tag",
            }
            atomic_save_json(session_path, legacy_session)

            gs = GameState(queue.Queue())
            gs.load_session(session_path)
            self.assertEqual(gs.round_number, 3)
            self.assertEqual(len(gs.players), 1)
            self.assertEqual(gs.players[0].name, "Lyra")
            self.assertIsInstance(gs.players[0].death_saves, dict)
            state_out = gs.get_state_dict(is_dm=True)
            self.assertEqual(state_out.get("legacy_v05_meta"), "session_archive_tag")

            # 2) Legacy Campaign JSON (senza flow_graph/journal + flag legacy + .bak creazione al salvataggio)
            camp_dir = os.path.join(tmpd, "legacy_campaign")
            os.makedirs(camp_dir, exist_ok=True)
            manifest_path = os.path.join(camp_dir, "campaign.json")
            atomic_save_json(
                manifest_path,
                {
                    "name": "Rocca v05",
                    "description": "Campagna storica",
                    "level_range": "1-4",
                    "legacy_camp_flag": 42,
                },
            )
            camp = Campaign.load(camp_dir)
            self.assertEqual(camp.name, "Rocca v05")
            self.assertEqual(camp.to_dict().get("legacy_camp_flag"), 42)
            camp.save(camp_dir)
            self.assertTrue(os.path.isfile(manifest_path + ".bak"))
            reloaded_camp = Campaign.load(camp_dir)
            self.assertEqual(reloaded_camp.to_dict().get("legacy_camp_flag"), 42)

            # 3) Legacy list-format map teleports migration in MapEditorWindow
            map_path = os.path.join(tmpd, "legacy_map.json")
            atomic_save_json(
                map_path,
                {
                    "grid_type": "hex",
                    "hex_size": 35,
                    "hexes": [[0, 0], [2, 3]],
                    "teleports": [{"q": 2, "r": 3, "target_map": "tavern.json"}],
                },
            )
            root = tk.Tk()
            root.withdraw()
            editor = None
            try:
                editor = MapEditorWindow(root)
                editor.withdraw()
                with patch("server.map_editor.filedialog.askopenfilename", return_value=map_path), \
                     patch("common.messagebox.messagebox.showinfo"):
                    editor.load_map_file()
                self.assertEqual(editor.teleports, {Hex(2, 3): "tavern.json"})
            finally:
                if editor is not None:
                    try:
                        editor.grab_release()
                    except Exception:
                        pass
                    if editor.winfo_exists():
                        editor.destroy()
                editor = None
                gc.collect()
                if root.winfo_exists():
                    root.destroy()

    def test_feature_maturity_all_14_subsystems_production_ready(self):
        maturity_text = (REPO_ROOT / "docs" / "FEATURE_MATURITY.md").read_text(encoding="utf-8")
        sec_idx = maturity_text.index("## 4. Subsystem Maturity Matrix")
        matrix_block = maturity_text[sec_idx:]
        rows = [
            ln.strip()
            for ln in matrix_block.splitlines()
            if ln.strip().startswith("| **")
        ]
        self.assertEqual(len(rows), 14, f"Expected 14 subsystem rows in FEATURE_MATURITY.md, got {len(rows)}")
        for row in rows:
            self.assertIn("`PRODUCTION_READY`", row, f"Subsystem not PRODUCTION_READY: {row}")
            for non_ready in ("`FUNCTIONAL`", "`INTEGRATED`", "`PARTIALLY_IMPLEMENTED`", "`PROTOTYPE`", "`NOT_IMPLEMENTED`"):
                self.assertNotIn(non_ready, row)

    def test_bilingual_docs_parity_and_zero_ai_policy(self):
        doc_pairs = [
            ("README.md", "README_IT.md"),
            ("docs/OPERATIONAL_GUIDE.md", "docs/GUIDA_OPERATIVA.md"),
            ("docs/USER_GUIDE.md", "docs/GUIDA_ALL_UTILIZZO.md"),
        ]
        for en_rel, it_rel in doc_pairs:
            en_path = REPO_ROOT / en_rel
            it_path = REPO_ROOT / it_rel
            self.assertTrue(en_path.is_file(), f"Missing doc: {en_rel}")
            self.assertTrue(it_path.is_file(), f"Missing doc: {it_rel}")
            self.assertGreater(len(en_path.read_text(encoding="utf-8").strip()), 500)
            self.assertGreater(len(it_path.read_text(encoding="utf-8").strip()), 500)

        banned_pkgs = {
            "openai",
            "anthropic",
            "langchain",
            "chromadb",
            "faiss",
            "ollama",
            "google.generativeai",
            "google.genai",
            "transformers",
            "llama_index",
            "sentence_transformers",
        }
        req_text = (REPO_ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        for pkg in banned_pkgs:
            self.assertNotIn(pkg.split(".")[0], req_text)

        scan_files = []
        for root_dir in ("common", "server", "client", "components"):
            scan_files.extend((REPO_ROOT / root_dir).rglob("*.py"))
        scan_files.extend([REPO_ROOT / "main.py", REPO_ROOT / "build_release.py"])

        for py_path in scan_files:
            tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        self.assertNotIn(alias.name, banned_pkgs, f"Banned AI import {alias.name} in {py_path}")
                        self.assertNotIn(top, banned_pkgs, f"Banned AI import {top} in {py_path}")
                elif isinstance(node, ast.ImportFrom) and node.module:
                    top = node.module.split(".")[0]
                    if not re.match(r"^(common|server|client|components)\b", node.module):
                        self.assertNotIn(node.module, banned_pkgs, f"Banned AI import {node.module} in {py_path}")
                        self.assertNotIn(top, banned_pkgs, f"Banned AI import {top} in {py_path}")


if __name__ == "__main__":
    unittest.main()
