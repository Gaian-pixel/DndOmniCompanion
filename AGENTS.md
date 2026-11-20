# D&D OmniCompanion — Workspace Agent Rules & Autonomous Contract

These rules apply at all times when working in this repository.

## 1. Core Product & Ruleset Invariants

- **Target Ruleset**: **D&D 5th Edition (2014 Core Rules — PHB / DMG / MM / SRD 5.1)** plus **Xanathar's Guide to Everything (2017)**, **Tasha's Cauldron of Everything (2020)**, and the **30 DM-configurable optional/variant rules** in `GameState.automation_settings`. Never silently mix incompatible 2024 rule revisions into 2014 gameplay mechanics (keep existing PDF indexer titles and `resolve_bastion_turn` compatibility intact).
- **Zero AI Restriction**: Never introduce AI, LLMs, external AI APIs, RAG, or vector databases anywhere in the application, UI, or documentation.
- **Bilingual Symmetry (IT / EN)**: Keep Italian and English localization keys (`common/i18n.py`) and bilingual documentation (`README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/USER_GUIDE.md`, `docs/GUIDA_ALL_UTILIZZO.md`) synchronized.

## 2. Git, Branch & Data-Directory Safety

- **Active Development Branch**: Work and commit locally on `dev/v0.6.0-autonomous` (unless explicitly instructed otherwise).
- **No Remote / Destructive Git Actions**: Never push to remotes, never create or modify Git tags, and never checkout, merge into, or modify `main` unless explicitly authorized by the user.
- **Protected Data Directories**: Automated tests and probes must **never** dirty tracked files in `client_data/`, `campaigns/`, or `manuals/`. Always isolate test runs with environment overrides:
  - `DND_MOCK_AUDIO=1`
  - `DND_SETTINGS_PATH=<temp_dir>/settings.json`
  - `DND_CHARACTERS_PATH=<temp_dir>/characters.json`

## 3. Autonomous Execution & Quality Gate

When executing tasks from `docs/DEVELOPMENT_ROADMAP.md` (or multi-step user requests):

1. **Session Recovery**: Check `git status --short`, read `docs/SESSION_HANDOFF.md` and `docs/DEVELOPMENT_ROADMAP.md`, and pick the highest-priority `TODO` or `IN_PROGRESS` task without waiting for human micro-prompts.
2. **Surgical Implementation**: Prefer clean, DRY helper functions and existing architecture patterns (`ClientNetworkHandlersMixin`, `DMCampaignSessionMixin`, `CharacterSheetFrame` panels). Keep mock targets on `client.client` and `server.dm_gui` intact.
3. **Mandatory Verification Before Stopping or Committing**:
   - **Bytecode Compilation**: `python -X utf8 -m py_compile` across all repository `.py` files must succeed (`0` errors).
   - **Static Analysis (`pyflakes`)**: Zero critical issues (`undefined name`, `unable to detect undefined names`, `invalid syntax`) across `common`, `server`, `client`, `components`, `main.py`, and `tests`.
   - **Automated Tests**: Run affected and new `unittest` suites (and full isolated suite before milestone commits) using `C:\Users\gaian\AppData\Local\Python\pythoncore-3.14-64\python.exe -u -X utf8 -m unittest` with `DND_MOCK_AUDIO=1` and isolated `DND_SETTINGS_PATH` / `DND_CHARACTERS_PATH`.
   - **Protected Folders Check**: Verify `git status --short client_data campaigns manuals` is empty.
4. **Documentation & Local Commit**: Update `docs/DEVELOPMENT_ROADMAP.md` and `docs/SESSION_HANDOFF.md` with exact observed counts/results, commit locally on `dev/v0.6.0-autonomous`, and automatically proceed to the next open `TODO` task until all requested tasks are `COMPLETED`.
