---
name: autonomous-loop
description: End-to-end autonomous development workflow for D&D OmniCompanion. Activate when running unattended backlog execution (/goal, /automation, or multi-task roadmap progression) to pick tasks from docs/DEVELOPMENT_ROADMAP.md, implement, self-verify, review, update docs, and commit locally without human prompting.
---

# Autonomous Backlog Execution Skill (`DndOmniCompanion`)

Follow this closed-loop protocol whenever asked to advance the project autonomously or process tasks from `docs/DEVELOPMENT_ROADMAP.md`.

## Loop Protocol (Repeat Until No `TODO` / `IN_PROGRESS` Tasks Remain)

1. **Discover Next Task**:
   - Run `python -X utf8 scripts/autonomous_dev_loop.py --status` (or inspect `docs/DEVELOPMENT_ROADMAP.md`) to locate the first task with status `IN_PROGRESS` or `TODO`.
   - If all roadmap tasks are `COMPLETED` and the user asked for continuous improvement, perform a targeted subsystem audit (Rules Engine, Battlemap/FoW, Multiplayer/Sync, DM/Player UX), append the newly discovered prioritized tasks (`TASK-XXX`) as `TODO` in `docs/DEVELOPMENT_ROADMAP.md`, and immediately begin executing them.

2. **Implement Cleanly**:
   - Mark the chosen task `IN_PROGRESS` in `docs/DEVELOPMENT_ROADMAP.md`.
   - Read only the exact line ranges needed. Keep diffs DRY and modular.
   - Add or extend deterministic regression and E2E tests in `tests/` (wrapping any Tkinter roots with `withdraw()` and `try...finally` cleanup).

3. **Run the Automated Quality Gate**:
   - Execute:
     ```powershell
     C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 scripts/autonomous_dev_loop.py --verify --fast
     ```
     for per-task verification (or `--verify` without `--fast` for full 71+ module verification before milestone completion).
   - If any check fails (`py_compile`, `pyflakes`, `unittest`, or dirty `client_data/`), fix the root cause and re-run until `VERIFY_STATUS=PASS`.

4. **Adversarial Self-Review**:
   - Inspect `git diff` for edge cases: thread-safety (`game_state.lock`), DM vs non-DM secrecy (`sanitize_player_for_players`, `sanitize_map_for_players`), bilingual IT/EN strings, and Tkinter widget existence guards (`winfo_exists()`).

5. **Document & Commit Locally**:
   - Mark the task `COMPLETED` in `docs/DEVELOPMENT_ROADMAP.md` with exact observed test and compile counts.
   - Update `docs/SESSION_HANDOFF.md` (and `README.md` / `README_IT.md` if test counts changed).
   - Commit locally on `dev/v0.6.0-autonomous` and immediately continue to the next `TODO` task in the same turn.
