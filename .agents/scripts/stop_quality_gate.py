"""
.agents/scripts/stop_quality_gate.py

Antigravity `Stop` lifecycle hook for D&D OmniCompanion.
Intercepts turn termination (`terminationReason == "NO_TOOL_CALL"`) and verifies:
1. Protected data directories (`client_data/`, `campaigns/`, `manuals/`) are clean.
2. Modified or untracked `.py` files compile cleanly (`py_compile`).
3. Modified or untracked `.py` files have zero critical `pyflakes` errors
   (`undefined name`, `unable to detect undefined names`, `invalid syntax`).
4. Any modified or untracked `tests/test_*.py` modules pass in an isolated temp environment.

If any check fails (and `continuationActive` is False), outputs:
  {"decision": "continue", "reason": "<diagnostic report>"}
forcing the agent to fix the issue before stopping.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

CRITICAL_PYFLAKES_RE = re.compile(
    r"(undefined name|unable to detect undefined names|invalid syntax)",
    re.IGNORECASE,
)


def _run_git(repo_root: Path, args: List[str]) -> Tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _changed_files(repo_root: Path) -> List[str]:
    code, out = _run_git(repo_root, ["status", "--porcelain"])
    if code != 0:
        return []
    files: List[str] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        if "D" in status:
            continue
        raw_path = line[3:].strip()
        if " -> " in raw_path:
            raw_path = raw_path.split(" -> ", 1)[1].strip()
        raw_path = raw_path.strip('"')
        if raw_path:
            files.append(raw_path.replace("\\", "/"))
    return files


def main() -> int:
    try:
        raw_stdin = sys.stdin.read().strip()
        payload = json.loads(raw_stdin) if raw_stdin else {}
    except Exception:
        payload = {}

    term_reason = str(payload.get("terminationReason", "NO_TOOL_CALL") or "NO_TOOL_CALL")
    fully_idle = bool(payload.get("fullyIdle", True))
    continuation_active = bool(payload.get("continuationActive", False))

    # Do not block if background tasks are still running, if termination was not normal,
    # or if we already forced a continuation in this turn (prevents infinite loops).
    if term_reason != "NO_TOOL_CALL" or not fully_idle or continuation_active:
        print(json.dumps({}))
        return 0

    script_dir = Path(__file__).resolve().parent
    repo_root = Path(payload.get("cwd") or script_dir.parent.parent).resolve()
    if not (repo_root / ".git").exists():
        repo_root = script_dir.parent.parent

    # 1. Check protected data directories
    _, dirty_data = _run_git(repo_root, ["status", "--porcelain", "client_data", "campaigns", "manuals"])
    if dirty_data.strip():
        reason = (
            "[STOP QUALITY GATE FAILED] Protected data directories were modified:\n"
            f"{dirty_data.strip()}\n"
            "Restore them (`git checkout -- client_data campaigns manuals`) before finishing."
        )
        print(json.dumps({"decision": "continue", "reason": reason}))
        return 0

    changed = _changed_files(repo_root)
    py_changed = [f for f in changed if f.endswith(".py") and (repo_root / f).is_file()]
    if not py_changed:
        print(json.dumps({}))
        return 0

    # 2. Bytecode compile check on touched Python files
    proc_comp = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "py_compile", *py_changed],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc_comp.returncode != 0:
        err_txt = ((proc_comp.stdout or "") + (proc_comp.stderr or "")).strip()
        reason = (
            "[STOP QUALITY GATE FAILED] `py_compile` failed on modified Python files:\n"
            f"{err_txt[:1500]}\n"
            "Fix the syntax/compilation errors and verify before stopping."
        )
        print(json.dumps({"decision": "continue", "reason": reason}))
        return 0

    # 3. Critical pyflakes check on touched Python files
    proc_flakes = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pyflakes", *py_changed],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    flakes_out = ((proc_flakes.stdout or "") + (proc_flakes.stderr or "")).splitlines()
    crit_lines = [ln for ln in flakes_out if CRITICAL_PYFLAKES_RE.search(ln)]
    if crit_lines:
        reason = (
            "[STOP QUALITY GATE FAILED] Critical `pyflakes` issues detected:\n"
            + "\n".join(crit_lines[:25])
            + "\nFix all undefined names / syntax errors before stopping."
        )
        print(json.dumps({"decision": "continue", "reason": reason}))
        return 0

    # 4. Run any modified unittest modules in an isolated temp directory
    test_mods = [
        "tests." + Path(f).stem
        for f in py_changed
        if f.startswith("tests/test_") and Path(f).name not in ("test_ui_smoke.py", "test_e2e_gui.py")
    ]
    if test_mods:
        with tempfile.TemporaryDirectory(prefix="dnd_hook_gate_") as tmpd:
            env = dict(os.environ)
            env["DND_MOCK_AUDIO"] = "1"
            env["DND_SETTINGS_PATH"] = os.path.join(tmpd, "settings.json")
            env["DND_CHARACTERS_PATH"] = os.path.join(tmpd, "characters.json")
            for mod in test_mods[:6]:
                proc_t = subprocess.run(
                    [sys.executable, "-u", "-X", "utf8", "-m", "unittest", mod],
                    cwd=str(repo_root),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=25,
                )
                if proc_t.returncode != 0:
                    out_t = ((proc_t.stdout or "") + (proc_t.stderr or "")).strip()
                    reason = (
                        f"[STOP QUALITY GATE FAILED] Unit test module `{mod}` failed:\n"
                        f"{out_t[-1500:]}\n"
                        "Fix the failing test(s) and re-verify before stopping."
                    )
                    print(json.dumps({"decision": "continue", "reason": reason}))
                    return 0

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
