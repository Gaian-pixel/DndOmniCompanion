# D&D OmniCompanion — Architecture Audit & Development Roadmap

> **Branch:** `dev/v0.6.0-autonomous` (based on `v0.5.0-alpha` / `3b28c99`)  
> **Target System:** Dungeons & Dragons 5th Edition — 2014 Core Rules (PHB / DMG / MM / SRD 5.1) + XGtE (2017) / TCE (2020) options & 30 DM-configurable DMG/XGtE/TCE optional rules (`GameState.automation_settings`; no silent mixing of incompatible 2024 rules)  
> **Updated:** 2026-11-14

---

## 1. Architectural Overview

D&D OmniCompanion is a Python Desktop Virtual Tabletop (VTT) and Campaign Management application structured cleanly around a Client-Server model:

```text
main.py (Single-Window Unified Launcher: DM Host | Player Client)
├── common/         # Shared GameState, Player model, TCP framing, TypedDict protocol, 5e tables, hex/square geometry, i18n, theme
├── server/         # DM GUI, Campaign Studio, Live Flow, Bestiary, Audio Library, VoiceServer (UDP 53912), TCP Server (TCP 5000)
│   └── rules/      # Decoupled 5e server-authoritative rule handlers dispatched via server/commands.py
├── client/         # Player Client GUI, Character Manager/Wizard/Sheet, Progression, PDF Sheet Generator, ClientNetwork, VoiceClient
├── components/     # Reusable Tkinter/ttkbootstrap widgets (HexMapCanvas, 3D Dice Canvas, StatblockCardView, Shop, Quests, Calendar)
├── campaigns/      # Campaign JSON & flow-graph projects (e.g., la_cripta_dei_sussurri)
├── manuals/        # Custom markdown rules + cached PDF index (pdf_index_cache.json)
├── docs/           # Bilingual EN/IT User Guides, Operational Guides, Feature Maturity, Roadmap & Handoff
└── tests/          # 64 unittest modules (605 verified test cases) + 2 standalone GUI smoke/E2E scripts + 2 multiplayer simulations
```

### Communication & Persistence Model
* **TCP Control & State (`common/network_utils.py`, `common/protocol.py`, `server/network.py`, `client/network.py`)**: Length-prefixed UTF-8 JSON framing over persistent TCP sockets (`send_message` using `select.select` write-readiness + `receive_message`). `Server.handle_client` dispatches requests via `server/commands.py:command_handlers`, after stripping test/debug override keys via `sanitize_client_payload`.
* **UDP Voice (`server/voice_server.py`, `client/voice_client.py`)**: Low-latency raw PCM audio relay on UDP port `53912`, guarded on Windows with `SIO_UDP_CONNRESET` and exponential backoff in `_play_loop`.
* **State & Thread Safety (`common/game_state.py`)**: Server-authoritative `GameState` protected by `threading.RLock()` (`game_state.lock`) and bridged to Tkinter via `gui_queue` + `safe_after`.
* **Persistence (`common/file_utils.py`)**: `atomic_save_json` (temp file in target directory + `os.replace`) used across `client_data/characters.json`, `client_data/settings.json`, `campaigns/*/campaign.json`, and `audio_library/library.json`.

---

## 2. Current Functional Inventory

| Subsystem | Primary Modules | Status | Verification Notes |
|---|---|---|---|
| **Unified Single-Window Launcher & Join Flow** | `main.py`, `client/login_ui.py` | Fully Implemented and Tested | `test_join_game.py`, `test_mono_finestra.py`, `test_player_gui_flow.py` pass headlessly; persistent path isolation via `DND_SETTINGS_PATH` verified (`TASK-001`) |
| **Virtual Tabletop (Multi-Grid / Multi-Scale / LoS / FoW / Weather / 3D Dice)** | `components/ui_components.py`, `components/dice_3d_canvas.py`, `common/hex_utils.py`, `server/map_editor.py` | Fully Implemented and Tested | `test_3d_dice.py`, `test_map_editor.py`, `test_map_navigation.py`, `test_poi_rendering.py`, `test_render_perf.py`, `test_vtt_ui_overhaul.py` |
| **DM Suite, Campaign Studio & Flow-First Runner** | `server/dm_gui.py`, `server/campaign_editor_ui.py`, `server/campaign_studio_ui.py`, `server/flow_canvas.py`, `server/dm_live_flow.py` | Fully Implemented and Tested | `test_campaign_hierarchy.py`, `test_campaign_system.py`, `test_live_flow_and_chronicle.py`, `test_dm_gui_flow.py` |
| **Character Creation, Progression & Sheet** | `client/character_manager.py`, `client/character_creation_wizard.py`, `client/character_sheet_ui.py`, `client/sheet_panels/*.py`, `client/progression_ui.py`, `client/pdf_sheet_generator.py` | Fully Implemented and Tested | `test_character_schema.py`, `test_sheet_panels.py`, `test_levelup_progression.py`, `test_character_sheet_enhancements.py`; character storage isolated via `DND_CHARACTERS_PATH` (`TASK-001`) |
| **D&D 5e RAW Combat, Spells, Conditions, Reactions & Boss Engine** | `server/rules/combat.py`, `server/rules/class_abilities.py`, `server/rules/reaction_magic.py`, `server/dm_monster_engine.py`, `common/spell_effects_engine.py`, `common/feats_and_classes.py`, `common/subclass_and_race_rules.py` | Fully Implemented and Tested | Covered by `test_authentic_5e.py`, `test_tactical_combat.py`, `test_timed_effects_save_ends.py`, `test_block1`..`test_block6`, `test_full_5e_phb_dmg_mm.py`; `test_divine_smite_damage_and_crit` deterministic (`TASK-001`) |
| **Optional DMG/XGtE Rules & Calculators (30 toggles)** | `server/dm_optional_tools.py`, `server/dm_optional_tools_ui.py`, `server/dm_dmg_systems.py`, `server/dm_automation_panel.py`, `server/rules/downtime.py` | Fully Implemented and Tested | Covered by `test_block5_dmg_xgte_optional.py`, `test_phb_dmg_mm_complete.py`, `test_audit_fixes.py` |
| **Travel, Exploration, Camp, Quests & Shops** | `server/rules/character.py`, `server/dm_travel_dialog.py`, `common/travel_data.py`, `components/quest_ui.py`, `components/shop_ui.py`, `components/calendar_ui.py` | Fully Implemented and Tested | `is_dm_actor` + `game_state.lock` enforced across travel/camp/encounter & journal handlers (`TASK-002`); `test_audit_fixes.py`, `test_travel_manager_extended.py`, `test_campaign_journal.py` pass |
| **Audio Soundboard, Cache & UDP Voice Chat** | `server/audio_library.py`, `server/rules/audio.py`, `common/audio_player.py`, `server/voice_server.py`, `client/voice_client.py` | Implemented and Hardened (`TASK-005` Timeout Eviction Open) | `handle_audio_play` validates `http`/`https` + `netloc`; `handle_audio_track_chunk` validates chunk bounds/contiguity and writes atomically; `AudioLibrary` enforces safe IDs/containment (`TASK-002`) |
| **Bilingual i18n (`IT`/`EN`) & Imperial/Metric Units** | `common/i18n.py` | Fully Implemented and Tested | `STRINGS` IT/EN symmetry tested in `test_i18n_language_switch.py`; temp settings path isolated via `DND_SETTINGS_PATH` (`TASK-001`) |
| **SRD Compendium & Offline PDF Indexer** | `common/srd_offline.py`, `common/pdf_manuals_indexer.py`, `server/compendium_ui.py`, `client/manuals_ui.py` | Implemented (Partial Automated Coverage) | Offline search tested in `test_new_features.py` and `test_audit_fixes.py`; `manuals_ui.py` relies mainly on UI smoke checks |

---

## 3. Critical Bugs and Technical Risks

1. **Test Pollution of Real User Persistent Data (`client_data/settings.json` & `client_data/characters.json`) — PRIORITY 1**:
   * `tests/test_join_game.py` (`test_server_history_save_and_load`) and `tests/test_player_gui_flow.py` call `save_server_history` / `LoginDialog.connect()`, writing dummy IPs (`192.168.1.42`, `192.168.1.50:5555`, `10.1.2.3`) into the tracked `client_data/settings.json` file.
   * `tests/test_new_features.py` (`test_launcher_and_offline_character_manager`) and `tests/test_mono_finestra.py` instantiate `CharacterManager()` without overriding `CHARACTER_FILE`, mutating real user characters if present, and `set_language()` / `set_distance_unit()` overwrite `client_data/settings.json`.
2. **Stochastic Unit Test Flakiness (`tests/test_raw_5e_advanced_features.py`) — PRIORITY 1**:
   * `test_divine_smite_damage_and_crit` invokes `handle_attack_request` with `hit_bonus: 20` against AC 10 without mocking `random.randint`. Whenever `1d20` rolls `1` (5% Natural 1 auto-miss in 5e RAW), Divine Smite never fires and the test fails intermittently; additionally, the critical-hit doubling stated in the docstring was untested.
3. **Unauthenticated DM Privilege & Locking Gaps (`server/rules/character.py`, `server/rules/journal.py`) — PRIORITY 2**:
   * `handle_set_travel_params_request`, `handle_set_watch_shifts_request`, `handle_resolve_night_camp_request`, and `handle_generate_encounter_request` mutate `game_state` and advance campaign time/rests without checking `is_dm_actor(player)` or acquiring `game_state.lock`.
   * `server/rules/journal.py` uses `getattr(player, "conn", None) is None` instead of `is_dm_actor(player)`.
4. **Unsafe Client URL Opening & Non-Atomic Chunk Reassembly (`client/client.py`, `server/audio_library.py`) — PRIORITY 2**:
   * `ClientGUI.handle_audio_play` passes arbitrary `url` payloads straight to `webbrowser.open(url)`, which on Windows delegates to ShellExecute/`os.startfile` (risking `file://` or UNC paths).
   * `ClientGUI.handle_audio_track_chunk` does not validate integer bounds (`index`, `total`), decoded chunk size, or contiguous chunk coverage before writing directly to `target_path` without an atomic replace.
   * `AudioLibrary.get` and `_file_for` in `server/audio_library.py` do not enforce SHA1/alphanumeric `track_id` and `os.path.realpath` containment.

---

## 4. Architectural Weaknesses

* **Wildcard Imports (`from ... import *`)**: 15 wildcard import statements remain across `server/commands.py` (7), `server/network.py`, `server/dm_gui.py`, `client/client.py`, and `server/rules/{character,chat,combat,inventory,map_interaction}.py` (plus 2 in tests), blinding static analyzers (`pyflakes` reports `unable to detect undefined names`).
* **Missing Push/PR Continuous Integration**: Only `.github/workflows/release.yml` (triggered on `v*` tags) exists; there is no `.github/workflows/ci.yml` running `py_compile`, static checks, and `unittest discover tests` on commits and pull requests.
* **Monolithic GUI Files**: `client/client.py` (5,702 lines) and `server/dm_gui.py` (4,449 lines) still concentrate many panel builders and handlers; ongoing modularization should proceed incrementally without breaking public attributes used by tests.

---

## 5. Missing or Incomplete Features

* **CI Automated Verification Pipeline**: Missing `.github/workflows/ci.yml`.
* **Critical-Hit Divine Smite Regression Coverage**: Test docstring claimed crit verification without executing a Natural 20 crit case.
* **Headless E2E & Standalone Smoke Integration**: `tests/test_ui_smoke.py` and `tests/test_e2e_gui.py` sit in `tests/` as `test_*.py` standalone scripts rather than discoverable unit tests or separated manual scripts.
* **Map & Campaign Asset Synchronization Over Network**: Currently, audio tracks stream in chunks over TCP (`AUDIO_TRACK_CHUNK`), whereas large custom handout images or map backgrounds rely heavily on pre-loaded base64 strings inside `MAP_UPDATE` / `GAME_STATE` packets (future optimization candidate).

---

## 6. UX/UI Improvement Opportunities

* **In-Client Combat Roll / Action Error Toast**: Surface server validation rejections (`ERROR_REPLY`) consistently as non-intrusive toast banners when triggered from HUD quick buttons instead of interrupting modal popups where appropriate.
* **DM Pending Actions Dock Filtering**: Allow sorting/filtering pending item/currency/journal/reaction requests in `server/dm_automation_panel.py`.
* **Audio Soundboard Pre-Caching Progress Indicator**: Display download percentage in chat/status bar when receiving large `AUDIO_TRACK_CHUNK` streams.

---

## 7. Testing Gaps

* **Verified Status (`dev/v0.6.0-autonomous`)**: `64` `unittest` modules (`605` discovered test cases) pass headlessly in `unittest discover tests` (`47.578s`, `DND_MOCK_AUDIO=1`, `0` failures, `0` errors); distinct from in-memory `unittest` / `LoopbackSessionHarness` integration checks, `tests/test_gameplay_integration_e2e.py` also includes real loopback TCP E2E tests (`test_real_tcp_*`), alongside `2` standalone GUI smoke/E2E scripts (`tests/test_ui_smoke.py`, `tests/test_e2e_gui.py`) and `2` scripted multiplayer simulations (`tests/simulate_game_session.py`, `tests/simulate_4player_campaign.py`).
* **Documentation Drift**: Resolved and kept synchronized through `TASK-020` (`README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/FEATURE_MATURITY.md`, and `docs/SESSION_HANDOFF.md` all updated to `605` tests across `64` modules, explicit 5e 2014 ruleset policy, Phase 3.5 correctness hardening, Phase 4 UX polish, and `.github/workflows/ci.yml` documented).
* **Coverage Gaps**:
  * Missing negative security tests for travel/camp/encounter handlers (`server/rules/character.py`) and journal handlers (`server/rules/journal.py`).
  * Missing unit tests for `ClientGUI.handle_audio_play` URL scheme filtering and `handle_audio_track_chunk` chunk bounds/atomic caching.
  * Missing unit tests for `client/manuals_ui.py` PDF folder actions and search filtering.

---

## 8. Security Considerations

* **DM Privilege Verification**: All state-mutating DM actions (`is_dm_actor`) must reject non-DM connected sockets (`role != "DM"`), complementing `sanitize_client_payload` in `server/network.py`.
* **URL Scheme & Path Traversal Defense**: Network-received URLs passed to `webbrowser.open` must strictly whitelist `http`/`https` with a valid host (`netloc`), and all cached file writes (`audio_cache_dir`, `audio_library`) must validate safe identifiers plus `os.path.realpath` containment.
* **Socket Binding & Identity Spoofing**: `server/network.py` already blocks same-name hijacks from different remote hosts (`same_host` check). Optional room PIN / passphrase authentication remains a future enhancement (`TASK-006`).

---

## 9. Technical Debt

* Placeholder-free f-strings (`common/backgrounds_data.py`, `common/campaign_journal.py`, `common/session_chronicle.py`, `common/spell_effects_engine.py`).
* Unused imports (`common/game_state.py`, `common/protocol.py`, `common/starter_equipment.py`, `common/subclass_and_race_rules.py`, `common/theme.py`, `common/ui_lifecycle.py`, `server/audio_library.py`) and duplicate local imports (`DEFAULT_CAMPAIGNS_DIR` in `server/campaign_editor_ui.py`, `os` in `server/network.py`).
* Large procedural handlers in `server/rules/combat.py` that can gradually benefit from smaller helper extraction.

---

## 10. Prioritized Development Roadmap

| ID | Task | Priority | Status | Affected Modules | Acceptance Criteria |
|---|---|---|---|---|---|
| **TASK-001** | **Data Integrity, Persistent File Test Isolation & Deterministic Smite Test** | P1 (Critical) | `COMPLETED` | `client/login_ui.py`, `common/i18n.py`, `client/character_manager.py`, `client_data/settings.json`, `tests/test_join_game.py`, `tests/test_player_gui_flow.py`, `tests/test_new_features.py`, `tests/test_mono_finestra.py`, `tests/test_i18n_language_switch.py`, `tests/test_raw_5e_advanced_features.py` | 1. Clean `client_data/settings.json` has only default `127.0.0.1` server.<br>2. Tests support/patch temp paths and env overrides (`DND_SETTINGS_PATH`, `DND_CHARACTERS_PATH`) so running the full test suite leaves `client_data/settings.json` and `characters.json` untouched (`git diff` empty).<br>3. `test_divine_smite_damage_and_crit` deterministically tests both a hit and a Natural 20 crit with 0% flakiness. |
| **TASK-002** | **Server DM Privilege Enforcement & Client Audio URL/Chunk Hardening** | P2 (Security) | `COMPLETED` | `server/rules/character.py`, `server/rules/journal.py`, `server/audio_library.py`, `client/client.py`, `tests/test_audit_fixes.py` | 1. Non-DM clients cannot invoke travel params, watch shifts, night camp resolution, random encounter generation, or journal mutations.<br>2. State mutations inside those handlers acquire `game_state.lock`.<br>3. `handle_audio_play` only opens `http`/`https` URLs with valid `netloc`; `handle_audio_track_chunk` enforces bounds, chunk caps, contiguous completeness, and atomic write.<br>4. Regression tests in `tests/test_audit_fixes.py` pass. |
| **TASK-003** | **Eliminate All Star Imports, Clean `pyflakes` Warnings & Add GitHub CI** | P6 (Architecture & QA) | `COMPLETED` | `server/commands.py`, `server/network.py`, `server/dm_gui.py`, `client/client.py`, `server/rules/*.py`, `common/*.py`, `components/ui_components.py`, `server/audio_library.py`, `server/campaign_editor_ui.py`, `.github/workflows/ci.yml` | 1. Zero wildcard (`*`) imports remain in `common/`, `server/`, `client/`, `components/`.<br>2. Fixed 3 latent missing-import bugs uncovered by star-import removal (`is_incapacitated_entity` & `_get_entity_skill_bonus` in `combat.py`, `safe_after` in `ui_components.py`), plus placeholder-free f-strings and unused imports.<br>3. `.github/workflows/ci.yml` runs `py_compile`, `pyflakes` critical check, and `unittest discover tests` (`583 tests` passing, 0 failures). |
| **TASK-004** | **Documentation Reconciliation (EN/IT) & CI Runner Docs** | P3 (Docs & QA) | `COMPLETED` | `README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/SESSION_HANDOFF.md` | Reconciled bilingual test counts (`583` verified tests across `63` `unittest` modules), clarified standalone GUI smoke/E2E runners (`tests/test_ui_smoke.py`, `tests/test_e2e_gui.py`), documented `.github/workflows/ci.yml`, and added `docs/SESSION_HANDOFF.md`. |
| **TASK-005** | **Server/Client State Validation & Audio Transfer Timeout Eviction** | P3 (Reliability) | `COMPLETED` | `client/client.py`, `server/network.py`, `tests/test_audit_fixes.py` | 1. `_prune_stale_audio_downloads` evicts timed-out `_audio_downloads` (`60s` TTL) and enforces `_max_audio_downloads` cap; disconnect clears partial downloads.<br>2. `ClientGUI.handle_server_message` & `Server.handle_client` reject/ignore malformed packet types cleanly without dropping the client TCP loop.<br>3. Regression tests in `tests/test_audit_fixes.py` pass. |
| **TASK-006** | **Optional Session Passphrase / Room PIN Authentication** | P4 (Security) | `COMPLETED` | `server/network.py`, `client/login_ui.py`, `client/client.py`, `main.py`, `server/dm_gui.py`, `common/protocol.py`, `common/i18n.py`, `tests/test_audit_fixes.py` | 1. Optional DM session password verified with `hmac.compare_digest` on `JOIN` (`make_join(..., password=...)`) with per-IP sliding-window rate limiting & lockout.<br>2. `LoginDialog` PIN field preserves 2-tuple `.result` compatibility.<br>3. Regression tests & i18n parity tests pass. |
| **TASK-007** | **Chunked / Hash-Cached Map & Handout Image Transfer** | P5 (Performance) | `COMPLETED` | `common/network_utils.py`, `server/network.py`, `client/client.py`, `tests/test_audit_fixes.py` | 1. Per-player SHA-256 asset-hash tracking deduplicates repeated `bg_image_data` and handout `image_b64` blobs across `GAME_STATE`, `MAP_DATA_UPDATE`, and `HANDOUT_BROADCAST` without mutating payloads across clients.<br>2. Client `_asset_cache` transparently rehydrates cached assets before canvas/handout rendering.<br>3. Regression tests in `tests/test_audit_fixes.py` pass. |
| **TASK-008** | **Modular Extraction of `ClientGUI` Network Handlers & `DM_GUI` Toolbar** | P8 (Maintainability) | `COMPLETED` | `client/network_handlers.py`, `client/client.py`, `server/dm_campaign_session_mixin.py`, `server/dm_gui.py`, `tests/test_audit_fixes.py` | Extracted `ClientNetworkHandlersMixin` (861 lines: asset cache + 36 network/audio/chat/dialog handlers, honoring `client.client.time.monotonic` patches) and `DMCampaignSessionMixin` (706 lines: campaign/session/scene lifecycle + 4 player approval prompts); preserved public APIs, mock targets, and 100% passing suite (`test_client_and_dm_gui_mixin_extraction_preserves_public_api`). |
| **TASK-009** | **Post-Review Hardening: Log Redaction & LRU Asset Cache Sync** | P1 (Security & Reliability) | `COMPLETED` | `server/network.py`, `common/network_utils.py`, `client/network_handlers.py`, `docs/FEATURE_MATURITY.md`, `tests/test_audit_fixes.py` | 1. Redact session `password` (`'***'`) in server `JOIN` debug log.<br>2. Always recompute SHA-256 hashes from non-empty `bg_image_data` / `image_b64` so in-place image mutations never hit stale hashes.<br>3. Bound server `_sent_asset_hashes` (`<= 24`) under client LRU cache (`32`) + local map fallback, eliminating evicted-asset desync. |
| **TASK-010** | **Combat Action Economy, Extra Attack, Cunning Action & Class Feature Sync** | P2 (Gameplay) | `COMPLETED` | `server/rules/combat.py`, `server/rules/class_abilities.py`, `server/rules/movement.py`, `common/game_state.py`, `common/protocol.py`, `client/client.py`, `tests/test_audit_fixes.py` | 1. Fix server `has_acted_this_turn` lock after `max_attacks` (`Extra Attack`) and enforce `has_acted_this_turn` in `_validate_combat_tactical_action` under `strict_turn_lock`.<br>2. Add server-authoritative `action_surge`, `second_wind`, and `rage` handlers and wire client class buttons + `Cunning Action` (`Dash`/`Disengage`).<br>3. Serialize turn economy fields in `Player.to_dict`/`from_dict` and sync client `action_spent`/`bonus_spent`/`reaction_spent`/`movement_spent_ft`/`Extra Attack`. |
| **TASK-011** | **Character Sheet Spellcasting & Server 5e Spell Engine Integration** | P3 (Gameplay) | `COMPLETED` | `client/character_sheet_ui.py`, `client/client.py`, `common/protocol.py`, `server/rules/class_abilities.py`, `tests/test_audit_fixes.py` | 1. Deduct spell slots via `SpellsPanel.execute_spell_resource_cost` on leveled attack spells (`do_attack`) before rolling attack.<br>2. Wire `cast_spell` (`do_cast`) to `cast_spell_callback` -> `CAST_SPECIAL_SPELL_REQUEST` (`already_consumed_slot=True`) so Concentration, Ritual `+10m`, Counterspell, and iconic spells resolve authoritatively without double-spending slots. |
| **TASK-012** | **Lossless Session Persistence & In-Person Tabletop Party Hero Import** | P4 (UX & Persistence) | `COMPLETED` | `common/game_state.py`, `server/dm_campaign_session_mixin.py`, `server/dm_gui.py`, `common/i18n.py`, `tests/test_audit_fixes.py` | 1. Persist and restore `maps`, `active_map_id`, `pending_legendary_resistances`, `campaign_starter_kit`, and full `Player` 5e attributes on live re-loads.<br>2. Add `import_party_character_to_game_state` and DM UI dialog (`Import Local PC`) to spawn saved heroes from `CharacterManager` for in-person/hybrid sessions. |
| **TASK-013** | **Combat Action Economy, Class Abilities & Cross-Player Actor Authorization** | P0 (Gameplay Integrity) | `COMPLETED` | `common/game_state.py`, `server/rules/class_abilities.py`, `server/rules/combat.py`, `client/client.py`, `tests/test_gameplay_integration_e2e.py` | 1. Enforce actor ownership authorization (`_resolve_actor`) across all 14 actor-accepting class/spell handlers.<br>2. Track `action_surge_used_this_turn` (Lv 2+, 1/turn), Rage heavy armor block, concentration drop (`concentrating_on`/`concentrating_spell`), 0-HP Rage termination (`_end_rage_if_unconscious`), Second Wind HP clamp, and reaction rollback on failed readied/opportunity attacks. |
| **TASK-014** | **End-to-End Spellcasting Validation, Slot Refunds, Dedup & Sheet Sync** | P1 (Spellcasting & Sync) | `COMPLETED` | `server/rules/class_abilities.py`, `client/character_sheet_ui.py`, `client/client.py`, `tests/test_gameplay_integration_e2e.py` | 1. Fix cantrip `cast_level=0`/`base_level=0` parsing, Rage spellcasting block, `_consume_or_refund_server_spell_slot` server refund (`_reject_cast`), and `request_id` deduplication.<br>2. Add `_prevalidate_client_spell_cast` and `CharacterSheetFrame.sync_resources_from_character()` for live client/server resource convergence. |
| **TASK-015** | **Lossless Campaign/Session Persistence, Reconnect Protection & Hardened Local PC Import** | P2 (Persistence & Auth) | `COMPLETED` | `common/game_state.py`, `common/campaign.py`, `server/network.py`, `server/rules/character.py`, `server/dm_campaign_session_mixin.py`, `tests/test_gameplay_integration_e2e.py` | 1. Preserve unknown forward-compatible JSON keys via `_extra_fields`/`_extra_state_fields` in `Player`, `GameState`, and `Campaign`.<br>2. Protect server-authoritative HP, conditions, spell/pact slots, and resources across reconnect (`_preserve_server_state_on_join` / `_preserve_stats_on_join`).<br>3. Harden `import_party_character_to_game_state` with schema normalization, integer clamping, and bounds/wall-free spawn search. |
| **TASK-016** | **Real Loopback TCP Multiplayer & Gameplay Integration E2E Suite & Doc Sync** | P3 (Integration QA) | `COMPLETED` | `tests/test_gameplay_integration_e2e.py`, `README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/FEATURE_MATURITY.md`, `docs/SESSION_HANDOFF.md` | 1. Add `LoopbackSessionHarness` and 9 integration/real-TCP E2E tests (`602/602` passing across `64` modules).<br>2. Reconcile bilingual EN/IT documentation with Phase 3 hardening and verified QA status. |
| **TASK-017** | **5e 2014 Ruleset Determination, Action Surge Lv 17+ & Rest/Combat State Correctness** | P1 (Rules Correctness) | `COMPLETED` | `common/character_schema.py`, `common/game_state.py`, `server/rules/combat.py`, `server/rules/character.py`, `client/character_manager.py` | 1. Document and enforce D&D 5e (2014 Core + XGtE/TCE + 30 explicit DM-configurable `automation_settings`) without mixing incompatible 2024 rules.<br>2. Normalize Fighter Lv 17+ `action_surge_max=2` (and `add_class_level` `custom_resources` deltas) while keeping 1 use/turn; unify `restore_entity_rest_resources` & `_apply_player_long_rest` and allow `0`-HD Short Rests.<br>3. Clear `readied_action_data` / `"Azione Preparata"` at 0 HP or incapacitation and in `GameState.end_combat()`, and exclude `_extra_fields`/`_extra_state_fields` self-keys on load. |
| **TASK-018** | **Server Authority Concurrency, Atomic Resource Transactions & Reconnect Window Hardening** | P1 (Concurrency & Net) | `COMPLETED` | `common/protocol.py`, `server/rules/class_abilities.py`, `server/rules/character.py`, `server/network.py` | 1. Lock-synchronize bounded/TTL `_check_and_record_request_id(..., max_entries=32, ttl_sec=120.0)` and attach default 12-char hex `request_id` in cast/feature protocol helpers.<br>2. Execute spell slot/ward/turn-flag mutations and `action_surge`/`second_wind`/`rage` checks atomically under `game_state.lock`; scrub optimistic `"Concentrazione"` in `_reject_cast` when `actor.concentrating_on is None`.<br>3. Bound reconnect overwrite protection with monotonic `_preserve_join_until` TTL (`+5.0s` on TCP reconnect, `+1.0s` after campaign import). |
| **TASK-019** | **Player HUD & DM Party Tracker UX Polish** | P2 (UX & Clarity) | `COMPLETED` | `client/client.py`, `server/dm_gui.py` | 1. Show `🔮 [Conc: <Spell>]` badge in `hero_hp_lbl`, remaining `(cur/max)`/`(∞)` counters and dynamic `_get_feature_tooltip` tooltips on Second Wind/Action Surge/Rage buttons (preserved across `apply_translations`), and disable Action Surge mid-turn after use.<br>2. Support `0`-HD Short Rests in `open_short_rest_dialog` (`0..hd_cur` spinbox + dedicated `0`-HD button).<br>3. Extract `DM_GUI._format_dm_player_row` displaying `+temp_hp`, `🔮[Conc: ...]`, `⏳[Prep]`, and active-turn `[A:... B:... R:...]` badges. |
| **TASK-020** | **Deterministic E2E Hardening, Phase 3.5/4 Regression Tests & Bilingual Doc Sync** | P2 (QA & Docs) | `COMPLETED` | `tests/test_gameplay_integration_e2e.py`, `README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/FEATURE_MATURITY.md`, `docs/SESSION_HANDOFF.md` | 1. Stabilize Natural-1 attack roll flake in `test_real_tcp_pin_combat_action_surge_spellcast_and_reconnect` and add `TestPhase35AndPhase4HardeningAndUX` (`605/605` passing across `64` modules in `47.578s`).<br>2. Reconcile bilingual EN/IT docs and handoff metrics with verified Phase 3.5 & Phase 4 state. |
