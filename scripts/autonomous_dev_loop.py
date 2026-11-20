"""
scripts/autonomous_dev_loop.py - Autonomous Development & Quality Gate Runner for D&D OmniCompanion.

Capabilities:
1. `--status`: Parses `docs/DEVELOPMENT_ROADMAP.md` and prints summary counts of
   `COMPLETED`, `IN_PROGRESS`, and `TODO` tasks.
2. `--next-task`: Outputs the next `IN_PROGRESS` or `TODO` task from
   `docs/DEVELOPMENT_ROADMAP.md` and generates a self-contained agent prompt.
3. `--verify [--fast]`: Runs the repository quality gate in an isolated environment:
   - Protected data directories clean check (`client_data/`, `campaigns/`, `manuals/`)
   - `py_compile` across all repository `.py` files
   - Critical `pyflakes` check (`undefined name`, star-import, syntax error)
   - Isolated `unittest` execution (`--fast` runs core E2E & latest regression suites;
     full mode runs all 71+ `unittest` modules sequentially)
4. `--run-sdk [--max-tasks N]`: Autonomous multi-agent loop powered by the
   Antigravity Python SDK (`google.antigravity`) that iterates through open
   roadmap tasks, runs an Implementer Agent, validates via `--verify`, runs a
   clean-context Adversarial Reviewer Agent on `git diff`, and commits locally.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
ROADMAP_PATH = REPO_ROOT / "docs" / "DEVELOPMENT_ROADMAP.md"
STANDALONE_GUI_SCRIPTS = {"test_e2e_gui.py", "test_ui_smoke.py"}
FAST_TEST_MODULES = [
    "tests.test_phase5c_vtt_e2e",
    "tests.test_task041_resilience_sheets_rest",
    "tests.test_task040_state_sync_and_authority",
    "tests.test_phase5b_scenarios_e2e",
    "tests.test_gameplay_integration_e2e",
]
CRITICAL_PYFLAKES_RE = re.compile(
    r"(undefined name|unable to detect undefined names|invalid syntax)",
    re.IGNORECASE,
)
TASK_ROW_RE = re.compile(
    r"^\|\s*\*\*(TASK-\d+)\*\*\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*`(COMPLETED|IN_PROGRESS|TODO|OPEN|PENDING)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$"
)


def parse_roadmap_tasks(roadmap_file: Path = ROADMAP_PATH) -> List[Dict[str, str]]:
    if not roadmap_file.is_file():
        return []
    tasks: List[Dict[str, str]] = []
    for line in roadmap_file.read_text(encoding="utf-8").splitlines():
        m = TASK_ROW_RE.match(line.strip())
        if m:
            raw_status = m.group(4).upper()
            norm_status = "TODO" if raw_status in ("TODO", "OPEN", "PENDING") else raw_status
            tasks.append({
                "id": m.group(1),
                "title": m.group(2),
                "priority": m.group(3),
                "status": norm_status,
                "modules": m.group(5),
                "criteria": m.group(6),
            })
    return tasks


def get_next_open_task(tasks: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    for t in tasks:
        if t["status"] == "IN_PROGRESS":
            return t
    for t in tasks:
        if t["status"] == "TODO":
            return t
    return None


def build_autonomous_task_prompt(task: Optional[Dict[str, str]]) -> str:
    if task:
        return (
            f"Execute `{task['id']}` autonomously on branch `dev/v0.6.0-autonomous`:\n"
            f"- Title & Goal: {task['title']}\n"
            f"- Affected Modules: {task['modules']}\n"
            f"- Acceptance Criteria: {task['criteria']}\n\n"
            "Follow `AGENTS.md` and the `autonomous-loop` skill: implement cleanly, add/update "
            "regression tests in `tests/`, run `python -X utf8 scripts/autonomous_dev_loop.py --verify --fast`, "
            "update `docs/DEVELOPMENT_ROADMAP.md` and `docs/SESSION_HANDOFF.md`, and commit locally."
        )
    return (
        "All listed tasks in `docs/DEVELOPMENT_ROADMAP.md` are currently `COMPLETED`.\n"
        "Perform a targeted code audit of D&D OmniCompanion (5e 2014 Rules Engine, Battlemap/FoW, "
        "Multiplayer State Sync, and DM/Player UX; Zero AI), add the next highest-value task "
        "to `docs/DEVELOPMENT_ROADMAP.md`, implement it with regression tests, run "
        "`python -X utf8 scripts/autonomous_dev_loop.py --verify --fast`, update docs, and commit locally."
    )


def run_quality_gate(fast: bool = False) -> Tuple[bool, str]:
    logs: List[str] = []
    t0 = time.monotonic()

    # 1. Protected directories check
    proc_git = subprocess.run(
        ["git", "status", "--porcelain", "client_data", "campaigns", "manuals"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if (proc_git.stdout or "").strip():
        msg = f"FAIL: Protected directories dirty:\n{proc_git.stdout.strip()}"
        return False, msg
    logs.append("1. Protected directories (`client_data/`, `campaigns/`, `manuals/`): CLEAN")

    # 2. Bytecode compilation across all tracked + untracked .py files
    proc_ls = subprocess.run(
        ["git", "ls-files", "*.py", "--cached", "--others", "--exclude-standard"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    py_files = [
        ln.strip()
        for ln in (proc_ls.stdout or "").splitlines()
        if ln.strip().endswith(".py") and (REPO_ROOT / ln.strip()).is_file()
    ]
    proc_comp = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "py_compile", *py_files],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc_comp.returncode != 0:
        return False, f"FAIL: py_compile error:\n{(proc_comp.stdout or '') + (proc_comp.stderr or '')}"
    logs.append(f"2. Static bytecode compile (`py_compile`): OK ({len(py_files)} files)")

    # 3. Critical pyflakes check
    proc_flk = subprocess.run(
        [sys.executable, "-X", "utf8", "-m", "pyflakes", "common", "server", "client", "components", "main.py"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    flk_lines = ((proc_flk.stdout or "") + (proc_flk.stderr or "")).splitlines()
    crit = [ln for ln in flk_lines if CRITICAL_PYFLAKES_RE.search(ln)]
    if crit:
        return False, "FAIL: Critical pyflakes issues:\n" + "\n".join(crit)
    logs.append(f"3. Static analysis (`pyflakes`): CRIT=0 (lines={len(flk_lines)})")

    # 4. Isolated unittest execution
    if fast:
        modules = list(FAST_TEST_MODULES)
    else:
        test_files = sorted((REPO_ROOT / "tests").glob("test_*.py"))
        modules = [
            f"tests.{f.stem}"
            for f in test_files
            if f.name not in STANDALONE_GUI_SCRIPTS
        ]

    total_tests = 0
    with tempfile.TemporaryDirectory(prefix="dnd_verify_") as tmpd:
        env = dict(os.environ)
        env["DND_MOCK_AUDIO"] = "1"
        env["DND_SETTINGS_PATH"] = os.path.join(tmpd, "settings.json")
        env["DND_CHARACTERS_PATH"] = os.path.join(tmpd, "characters.json")
        for mod in modules:
            proc_u = subprocess.run(
                [sys.executable, "-u", "-X", "utf8", "-m", "unittest", mod],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            out_u = (proc_u.stdout or "") + (proc_u.stderr or "")
            m_ran = re.search(r"Ran (\d+) test", out_u)
            if m_ran:
                total_tests += int(m_ran.group(1))
            if proc_u.returncode != 0:
                return False, f"FAIL: Unittest module `{mod}` failed:\n{out_u}"

    elapsed = time.monotonic() - t0
    mode_lbl = "FAST" if fast else "FULL"
    logs.append(f"4. Isolated Unittest Gate ({mode_lbl}): {total_tests} tests across {len(modules)} modules OK in {elapsed:.2f}s")
    logs.append("VERIFY_STATUS=PASS")
    return True, "\n".join(logs)


async def _run_sdk_loop(max_tasks: int = 1) -> int:
    try:
        from google.antigravity import Agent, CapabilitiesConfig, LocalAgentConfig  # type: ignore
    except ImportError:
        print(
            "Antigravity Python SDK (`google-antigravity`) is not installed in this Python environment.\n"
            "Install it with: pip install google-antigravity\n"
            "Or use `/goal` and `/automation` directly inside Antigravity IDE / Antigravity 2.0."
        )
        return 1

    completed = 0
    while completed < max_tasks:
        tasks = parse_roadmap_tasks()
        next_task = get_next_open_task(tasks)
        prompt = build_autonomous_task_prompt(next_task)
        task_label = next_task["id"] if next_task else "AUTO-AUDIT"
        print(f"\n=== [AUTONOMOUS ORCHESTRATOR] Starting {task_label} ({completed + 1}/{max_tasks}) ===")

        impl_cfg = LocalAgentConfig(
            system_instructions="You are the autonomous lead developer of D&D OmniCompanion. Follow AGENTS.md strictly.",
            capabilities=CapabilitiesConfig(),
        )
        async with Agent(impl_cfg) as implementer:
            resp = await implementer.chat(prompt)
            async for token in resp:
                sys.stdout.write(token)
                sys.stdout.flush()
            print()

            ok, report = run_quality_gate(fast=True)
            if not ok:
                print(f"\n[QUALITY GATE FAILED — Requesting repair from Implementer]\n{report}")
                fix_resp = await implementer.chat(
                    f"The automated quality gate failed with:\n```\n{report}\n```\nFix all issues and re-verify."
                )
                async for token in fix_resp:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                print()
                ok, report = run_quality_gate(fast=True)
                if not ok:
                    print(f"[ORCHESTRATOR ABORT] Quality gate still failing:\n{report}")
                    return 1

        # Clean-context Adversarial Review
        rev_cfg = LocalAgentConfig(
            system_instructions=(
                "You are an adversarial code reviewer for D&D OmniCompanion. "
                "Inspect `git log -n 1 -p` and `git status`, verify 5e 2014 RAW correctness, "
                "thread safety, and non-DM secrecy. Reply with APPROVED if clean."
            ),
            capabilities=CapabilitiesConfig(),
        )
        async with Agent(rev_cfg) as reviewer:
            rev_resp = await reviewer.chat("Review the latest changes and run any spot checks needed.")
            async for token in rev_resp:
                sys.stdout.write(token)
                sys.stdout.flush()
            print()

        completed += 1
        if next_task is None:
            break

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="D&D OmniCompanion Autonomous Dev Loop & Quality Gate")
    parser.add_argument("--status", action="store_true", help="Show roadmap task status summary")
    parser.add_argument("--next-task", action="store_true", help="Print next open task and self-contained prompt")
    parser.add_argument("--verify", action="store_true", help="Run automated quality gate")
    parser.add_argument("--fast", action="store_true", help="Use fast core E2E subset for --verify")
    parser.add_argument("--run-sdk", action="store_true", help="Run external multi-agent loop via google-antigravity SDK")
    parser.add_argument("--max-tasks", type=int, default=1, help="Max tasks to execute in --run-sdk mode")
    args = parser.parse_args()

    if args.status:
        tasks = parse_roadmap_tasks()
        by_status: Dict[str, List[str]] = {"COMPLETED": [], "IN_PROGRESS": [], "TODO": []}
        for t in tasks:
            by_status.setdefault(t["status"], []).append(t["id"])
        print(
            f"ROADMAP_STATUS TOTAL={len(tasks)} "
            f"COMPLETED={len(by_status.get('COMPLETED', []))} "
            f"IN_PROGRESS={len(by_status.get('IN_PROGRESS', []))} "
            f"TODO={len(by_status.get('TODO', []))}"
        )
        nxt = get_next_open_task(tasks)
        if nxt:
            print(f"NEXT_OPEN_TASK={nxt['id']} ({nxt['status']}): {nxt['title']}")
        else:
            print("NEXT_OPEN_TASK=NONE (All 42 roadmapped tasks are COMPLETED)")
        return 0

    if args.next_task:
        tasks = parse_roadmap_tasks()
        nxt = get_next_open_task(tasks)
        print(build_autonomous_task_prompt(nxt))
        return 0

    if args.verify:
        ok, report = run_quality_gate(fast=args.fast)
        print(report)
        return 0 if ok else 1

    if args.run_sdk:
        return asyncio.run(_run_sdk_loop(max_tasks=max(1, args.max_tasks)))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
