# D&D OmniCompanion — Workspace Agent Rules & Autonomous Contract

These rules apply at all times when working in this repository.

## 1. Environment & Tooling Quick Reference (Windows / PowerShell)

- **Python Interpreter**: `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8`
- **Code Search**: `rg` (`ripgrep`) is **not** installed on this machine. Always use PowerShell `Select-String` (e.g., `Select-String -Path "server\**\*.py" -Pattern "..."`) or Python scripts instead of `rg`.
- **Autonomous Runner & Quality Gate (`scripts/autonomous_dev_loop.py`)**:
  - Check backlog status: `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 scripts/autonomous_dev_loop.py --status`
  - Print next open task prompt: `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 scripts/autonomous_dev_loop.py --next-task`
  - Fast verification gate (~25s): `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 scripts/autonomous_dev_loop.py --verify --fast`
  - Full 71-module verification gate: `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -X utf8 scripts/autonomous_dev_loop.py --verify`

## 2. Core Product, Ruleset & Bilingual Invariants

- **Target Ruleset**: **D&D 5th Edition (2014 Core Rules — PHB / DMG / MM / SRD 5.1)** plus **Xanathar's Guide to Everything (2017)**, **Tasha's Cauldron of Everything (2020)**, and the **30 DM-configurable optional/variant rules** in `GameState.automation_settings`. Never silently mix incompatible 2024 rule revisions into 2014 gameplay mechanics (keep existing PDF indexer titles `"PHB 2024"` / `"DMG 2024"` and `resolve_bastion_turn` compatibility intact for existing tests).
- **Zero AI Restriction**: Never introduce AI, LLMs, external AI APIs, RAG, or vector databases anywhere in the application, UI, or documentation.
- **Bilingual Symmetry & 5e IT/EN Domain Traps**:
  - Keep Italian and English localization keys (`common/i18n.py`) and bilingual documentation (`README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/USER_GUIDE.md`, `docs/GUIDA_ALL_UTILIZZO.md`) synchronized.
  - **False Friend Warning**: In Italian 5e, *"Scuola di Evocazione"* is **Conjuration**, whereas **Evocation** is *"Scuola di Invocazione"* (note that legacy spell dicts may still use `"school": "Evocazione"` for Evocation spells — distinguish wizard subclass checks from spell school checks).
  - Always use canonical bilingual helpers instead of raw string equality: `canonical_element_key` (`server/rules/reaction_magic.py`), `is_condition_active` (`common/i18n.py`), `entity_get_class_level`, `entity_get_total_level`, and `entity_has_keyword` (`common/dnd5e_tables.py`).

## 3. Git, Branch & Data-Directory Safety

- **Active Development Branch**: Work and commit locally on `dev/v0.6.0-autonomous` (unless explicitly instructed otherwise).
- **No Remote / Destructive Git Actions**: Never push to remotes, never create or modify Git tags, and never checkout, merge into, or modify `main` unless explicitly authorized by the user.
- **Protected Data Directories**: Automated tests and probes must **never** dirty tracked files in `client_data/`, `campaigns/`, or `manuals/`. Always isolate test runs with environment overrides:
  - `DND_MOCK_AUDIO=1`
  - `DND_SETTINGS_PATH=<temp_dir>/settings.json`
  - `DND_CHARACTERS_PATH=<temp_dir>/characters.json`

## 4. Architecture, Secrecy & Mock-Target Compatibility

- **Public Symbols & Mock Targets (Must Remain Importable)**:
  - `client.client`: `ClientGUI` (inherits `ClientNetworkHandlersMixin`), `ClientNetwork`, `AudioManager`, `VoiceClient`, `LoginDialog`, `time.monotonic`.
  - `server.dm_gui`: `DM_GUI` (inherits `DMCampaignSessionMixin`), `Server`, `AudioManager`, `VoiceClient`.
  - `components.ui_components`: `HexMapCanvas` (`canvas.redraw()`), `CommandPaletteDialog`, `ToastNotification`, `ToolTip`.
  - `client.character_sheet_ui`: `CharacterSheetFrame(master, character, manager, ...)` (alias `CharacterSheetUI`).
  - `client.character_manager`: `CharacterManager()` (uses `DND_CHARACTERS_PATH` env var, no `filepath` constructor arg).
  - `common.protocol`: `make_error_reply(text)` emits `{"type": "ERROR_REPLY", "data": {"text": text}}`; `make_prompt_reaction(reaction_type, source_name, target_name="", details=None)` uses 4 args (with 3-arg backward compatibility).
- **Server Authority, Thread-Safety & Non-DM Secrecy**:
  - Protect server state mutations with `with game_state.lock:` (`threading.RLock`), verify DM privileges via `is_dm_actor(player)` (`common/network_utils.py`), and enforce actor ownership via `_resolve_actor` (`server/rules/class_abilities.py`).
  - Never leak hostile NPC exact HP, AC, hit dice, `Hex [q,r]` coordinates, `dm_note`, or `DM SECRET:` / `SEGRETO DM:` text to non-DM players across `GAME_STATE`, `FOW_UPDATE_BROADCAST`, `HexMapCanvas._update_hover_tooltip`, `CommandPaletteDialog`, `PlayerJournalDialog`, or `QuestTrackerFrame`.

## 5. Tkinter Testing & Autonomous Quality Gate

- **Tkinter Headless Best Practices**:
  - Run the full suite per-module via `scripts/autonomous_dev_loop.py --verify` (avoids cross-module Tcl/Tk teardown hangs from monolithic `unittest discover` across 70+ modules). Note that `tests/test_ui_smoke.py` and `tests/test_e2e_gui.py` are standalone scripts.
  - In any test creating `tk.Tk()`, immediately call `root.withdraw()`, patch blocking `messagebox` / `simpledialog` calls, release grabs (`w.grab_release()`) on child `Toplevel` windows (note: `CharacterSheetFrame` dialogs parent `tk.Toplevel` to `sheet`, not `root`), and destroy widgets inside `try...finally`.
  - Do not use `PIL.ImageGrab.grab()` in headless tests (fails with `OSError` on non-interactive Windows sessions); verify layout via `update_idletasks()` and `winfo_width()` / `winfo_reqwidth()`.
- **Autonomous Execution Loop**:
  1. Check `git status --short` and run `scripts/autonomous_dev_loop.py --status` to pick the highest-priority `IN_PROGRESS` or `TODO` task from `docs/DEVELOPMENT_ROADMAP.md`.
  2. Implement the fix/feature surgically with deterministic regression tests in `tests/`.
  3. Run `scripts/autonomous_dev_loop.py --verify --fast` (and full `--verify` before milestone completion). The `.agents/hooks.json` `Stop` hook also enforces `py_compile`, `pyflakes`, clean data folders, and touched test execution automatically before turn termination.
  4. Update `docs/DEVELOPMENT_ROADMAP.md` and `docs/SESSION_HANDOFF.md` with exact observed counts, commit locally on `dev/v0.6.0-autonomous`, and proceed to the next open `TODO` task.
