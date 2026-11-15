# D&D OmniCompanion — Feature Maturity & User Journey Assessment

> **Branch:** `dev/v0.6.0-autonomous`  
> **Assessment Scope:** Phase 5 & Phase 5B Core VTT Completion, Advanced Gameplay & Product Validation (`TASK-025`–`TASK-037`) Building on Phases 2–4.5 (`TASK-009`–`TASK-024`)  
> **Date:** 2026-11-15

---

## 1. Maturity Classification Scale

Every major subsystem is classified using the following evidence-based levels:

- **`NOT_IMPLEMENTED`**: Referenced in documentation or UI plans without backing code.
- **`PROTOTYPE`**: Partial scaffolding or local-only stub lacking validation or persistence.
- **`PARTIALLY_IMPLEMENTED`**: Core logic exists on one side (client or server) or works only in isolated paths, with incomplete E2E integration.
- **`FUNCTIONAL`**: Works reliably across its primary flows with unit test coverage, with minor UX or integration rough edges.
- **`INTEGRATED`**: Connected end-to-end across UI, networking, server rules engine, and persistence with regression tests.
- **`PRODUCTION_READY`**: Integrated, hardened against invalid input/concurrency races, covered by unit + E2E lifecycle tests, and free of known security or state-sync defects.

---

## 1b. Ruleset Determination & Consistency Policy

D&D OmniCompanion explicitly targets **D&D 5th Edition (2014 Core Rules — PHB / DMG / MM / SRD 5.1)** alongside **Xanathar's Guide to Everything (2017)** and **Tasha's Cauldron of Everything (2020)** character/spell options, plus **30 explicit DM-configurable optional/variant rules** exposed via `GameState.automation_settings`.

- Incompatible 2024 rules revisions (e.g., the 2024 Action Surge ban on the Magic action) are intentionally **not** mixed silently into 2014 rules behavior.
- In-memory integration harnesses (`LoopbackSessionHarness` in-process/state tests and scripted simulations) remain explicitly distinguished from real loopback TCP socket E2E workflows (`test_real_tcp_*` in `tests/test_gameplay_integration_e2e.py`).

## 2. Post-Implementation Technical Review (`TASK-005`–`TASK-008`)

Before advancing to new product features, `TASK-005` through `TASK-008` were reviewed directly against the source code:

1. **Session Passphrase / PIN Authentication (`TASK-006`, `server/network.py`, `client/login_ui.py`)**:
   - **Strengths**: `hmac.compare_digest` constant-time password verification, per-IP sliding-window lockout (`_auth_failures` under `_auth_lock`), runtime password changes via `Server.set_session_password`, same-host reconnection support, and 2-tuple compatibility in `LoginDialog.result`.
   - **Transport Confidentiality Boundary**: Custom TCP framing (`common/network_utils.py`) runs over **plaintext TCP** (no TLS/STARTTLS wrapper). Therefore, the session PIN/passphrase protects against unauthorized LAN/tabletop room joins and online brute-force guessing, **not** against passive network sniffing on untrusted networks (recommended over trusted LAN or VPN/tunnel for remote sessions).
   - **Defect Found (`TASK-009`)**: `Server.handle_client` (`server/network.py`) logs `RICEVUTO MESSAGGIO INIZIALE: join_msg` verbatim before verifying the password, printing plaintext session passwords to server stdout/logs. Fixed by redacting `password` before logging.
2. **Asset Caching & SHA-256 Deduplication (`TASK-007`, `common/network_utils.py`, `client/network_handlers.py`)**:
   - **Strengths**: Per-player `_sent_asset_hashes` avoids mutating shared payloads across clients and preserves GM layer/hidden-entity sanitization (`sanitize_map_for_players`).
   - **Defects Found (`TASK-009`)**:
     - `sanitize_map_for_players`, `_deduplicate_map_payload`, and `_deduplicate_handout_dict` short-circuited `map_dict.get("bg_image_hash") or compute_asset_hash(...)`. Mutating `bg_image_data` or `image_b64` in-place while an old hash key remained caused stale hashes to be treated as already sent.
     - Client `_asset_cache` evicts entries at `32` items while server `player._sent_asset_hashes` grew unboundedly as a `set`, meaning assets evicted by a long-lived client after >32 map/handout switches could later be stripped by the server (`bg_image_data = None`). Fixed by enforcing LRU eviction (`_MAX_ASSET_CACHE_ENTRIES = 32` client vs `MAX_TRACKED_SENT_ASSET_HASHES = 24` server) plus local fallback and unconditional payload hashing.
3. **GUI Modularization (`TASK-008`, `client/network_handlers.py`, `server/dm_campaign_session_mixin.py`)**:
   - **Assessment**: Clean mixin extraction without circular imports (`_monotonic_now` honors `unittest.mock.patch` on `client.client.time.monotonic`; public APIs and mock targets in `client.client` and `server.dm_gui` remain intact). No further file splitting is warranted without a concrete functional need.
4. **Network Reliability & Audio Transfer (`TASK-005`, `client/network_handlers.py`, `server/network.py`)**:
   - **Assessment**: Malformed packet types in `Server.handle_client` and `ClientGUI.handle_server_message` are rejected cleanly without dropping the socket loop; `_prune_stale_audio_downloads` enforces `60s` TTL and `_max_audio_downloads` cap, and disconnections purge incomplete transfers.

---

## 3. End-to-End User Journey Analysis

### Journey 1 — Dungeon Master Workflow
`Launch main.py -> Start DM Host -> Create/Load Campaign & Maps -> Optionally set Session PIN -> Spawn Party / Monsters / Objects -> Run Initiative & Combat -> Apply Conditions / Spells / Traps / Rests -> Save Session / Reload Session`
- **Gaps Identified**:
  - `GameState.get_state_dict(is_dm=True)` and `GameState.load_session()` omitted `maps`, `active_map_id`, `pending_legendary_resistances`, and `campaign_starter_kit`, and `load_session` did not refresh ~25 newer 5e `Player` attributes on already-connected sockets (`TASK-012`).
  - DM Combat validation in `server/rules/combat.py` had a logic bug (`has_acted_this_turn and attacks_made_this_turn == 0`) that allowed infinite standard Attack actions after finishing `Extra Attack`, and `_validate_combat_tactical_action` did not check `has_acted_this_turn` under `strict_turn_lock` (`TASK-010`).

### Journey 2 — Player Workflow
`Launch main.py -> Join Game (with optional PIN) -> Select/Create Character -> Move Token -> Cast Spells / Make Weapon Attacks / Use Extra Attack & Class Features (Action Surge, Second Wind, Cunning Action, Rage) -> Track Turn Economy & Resources -> Rest & Level Up`
- **Gaps Identified**:
  - `Player.to_dict()` / `from_dict()` omitted combat turn-economy counters (`movement_spent_this_turn`, `has_acted_this_turn`, `attacks_made_this_turn`, `has_reacted_this_turn`, `sneak_attack_used_this_turn`, `readied_action_data`, `helped_targets_this_turn`), and `ClientGUI` marked `action_spent = True` on the very first strike of `Extra Attack` or on bonus/reaction attacks (`TASK-010`).
  - Client `perform_dash` / `perform_disengage` did not send `make_cunning_action_request` when consuming a Rogue Bonus Action, and `use_action_surge` / `use_second_wind` / `use_rage` only updated local state instead of dispatching `make_class_feature_request` to the server (`TASK-010`).
  - Character sheet spellcasting (`client/character_sheet_ui.py`) did not charge spell slots when clicking **Attacca Bersaglio** on leveled attack spells (*Guiding Bolt*, *Chromatic Orb*, *Inflict Wounds*) and `do_cast` only printed to chat instead of invoking the server 5e spell engine (`make_cast_special_spell_request`) (`TASK-011`).

### Journey 3 — In-Person Tabletop Workflow
`Launch DM Host -> Load Saved Local Characters from client_data/characters.json directly as Table Tokens -> Run Shared Map/Monitor Combat -> Export/Save Session & Reseat Live LAN Players`
- **Gaps Identified**:
  - No direct DM workflow existed to import saved local characters (`CharacterManager` / `characters.json`) onto the DM battlemap with computed effective AC, initiative bonus, spell slots, weapons, and portraits (`TASK-012`).

---

## 4. Subsystem Maturity Matrix

| Subsystem | Primary Modules | Current Rating (Phase 5 Status) | Notes & Evidence |
|---|---|---|---|
| **Unified Launcher & Join Auth** | `main.py`, `client/login_ui.py`, `server/network.py` | **`PRODUCTION_READY`** | Constant-time PIN verification, rate limiting, plaintext password log redaction (`TASK-009`), real loopback TCP verification (`TASK-016`), and Phase 4.5 login UX hardening: expanded unclipped locked geometry (`520x435`), `"Cambia Eroe"` unlock flow, PIN visibility toggle, `host:port` validation, and rejected-PIN clearing (`TASK-021`, `TASK-023`). TCP transport remains unencrypted (documented LAN/VPN boundary). |
| **Network Protocol & Asset Sync** | `common/network_utils.py`, `common/protocol.py`, `client/network.py`, `client/network_handlers.py`, `server/network.py` | **`PRODUCTION_READY`** | Bounds checks, malformed-packet safety, audio chunk atomic cache/TTL eviction, unconditional SHA-256 hashing & bounded LRU asset cache (`24` vs `32`) + local map fallback (`TASK-009`), static grid `hexes_hash` deduplication (`TASK-035`), non-blocking parallel `_dispatch_native_broadcast()` isolating stalled sockets (`TASK-035`), server state protection across reconnect (`TASK-015`, clamped on `TASK-030`), non-blocking `connect_async`, `PING`/`PONG` idle keepalive, cross-IP PIN reconnect with `known_asset_hashes` & avatar cache restore (`TASK-030`), non-blocking `ERROR_REPLY` economy rollback & transient map preservation (`TASK-023`). |
| **Virtual Tabletop Canvas & Maps** | `components/ui_components.py`, `components/dice_3d_canvas.py`, `server/map_editor.py`, `common/hex_utils.py`, `server/rules/map_interaction.py` | **`PRODUCTION_READY`** | Multi-scale hex/square/gridless parity, `has_line_of_sight` + closed/secret door blocking, FoW/trap/loot/pocket-dimension secrecy (`TASK-027`, `reset_trap_at` `detected=False` `TASK-033`), Player Display union FoW/LoS, `Shift+Drag` marquee group movement (`on_tokens_group_drop_callback`), Map Editor 50-step Undo/Redo, Trap/Loot/Teleport/Room-Pin layers & gridless auto-grid (`TASK-032`, legacy teleport list migration `TASK-037`), FoW `visible_now` memoization (`TASK-035`), right-click drag ruler (`[UX-H11]`), tool mutual exclusion, `<B1-Motion>` drag-paint, runtime Map Switch/Create/Resize/Delete, `>4MP` redraw optimization (`TASK-028`), drag ownership guards, companion drag-drop, DM left-click select without teleport, dynamic reflowing toasts & localized confirms (`TASK-021`). |
| **DM Suite & Campaign Studio** | `server/dm_gui.py`, `server/dm_campaign_session_mixin.py`, `server/campaign_studio_ui.py`, `server/dm_live_flow.py`, `server/campaign_editor_ui.py`, `common/campaign.py`, `common/campaign_journal.py` | **`PRODUCTION_READY`** | Full campaign authoring with `.bak` atomic backups (`TASK-030`), lossless persistence (`TASK-012`, `TASK-015`, `TASK-026`), DM-gated & secret-isolated quests/handouts/journal (`TASK-030`, negative checks `TASK-036`), bounded scrollable `npc_actions_canvas` (`[UX-M08]`), unified Quest/Faction dialogs (`[UX-H12]`), inline combat quick bar, rule-accurate `apply_dm_hp_delta`, non-overlapping spawners, local-party encounter math, and `Alt+Left`/`Alt+Right` turn shortcuts (`TASK-022`). |
| **Combat & Action Economy Engine** | `server/rules/combat.py`, `server/rules/class_abilities.py`, `server/rules/reaction_magic.py`, `server/rules/movement.py`, `client/client.py` | **`PRODUCTION_READY`** | Enforces actor ownership (`_resolve_actor`), Fighter Lv 17+ `Action Surge`, Barbarian Primal Champion `24` cap & `Shield of Faith` concentration AC lifecycle (`TASK-033`), combat LoS `grid_type` parity & 3D AoE elevation extent (`TASK-033`), atomic class-feature consumption, companion drag-drop routing, unified Radiant/Smite/Elemental Adept & Death Save rules (`handle_death_save_request` + Pal/Monk/Halfling bonuses, `TASK-029`), hardened reaction rescues/`Absorb Elements`/`Counterspell`/`_apply_hp_change`, ranged ammo server sync (`TASK-033`), client rollback, `my_turn` controls + tooltips, off-hand `is_bonus_action=True`, and initiative sync (`TASK-010`–`TASK-033`). |
| **Character Builder, Sheet & Level-Up** | `client/character_manager.py`, `client/character_creation_wizard.py`, `client/character_sheet_ui.py`, `client/sheet_panels/`, `client/progression_ui.py` | **`PRODUCTION_READY`** | Complete 5e races/classes/subclasses/feats/ASI/PDF export; 4-tier responsive `CharacterSheetFrame` (`[UX-C05]`, verified at `1024x720` with `633px` notebook), live Sheet Vitals (`TempHP`, `HD`, `Exhaustion`, `Conditions`), `_extra_fields` round-trip, `check_feat_prerequisites`, `apply_half_feat_bonus` & Half-Feat automation, multiclass mixed `hit_dice_pools` & Short/Long Rest recovery (`TASK-034`, `TASK-035`), Wizard TCE/4d6 fixes, `SpellsPanel` & downward AC recalc, and `LevelUpDialog` subclass unlock + ASI auto-radio (`TASK-023`–`TASK-035`). |
| **Spellcasting & Concentration Engine** | `server/rules/class_abilities.py`, `common/spell_effects_engine.py`, `common/protocol.py`, `client/sheet_panels/spells_panel.py` | **`PRODUCTION_READY`** | Enforces Bonus Action spell rule (cantrips `cast_level=0`/`base_level=0`), Rage spell block, `shield_of_faith` single-concentration cleanup (`TASK-033`), atomic `game_state.lock` slot/ward/turn-flag commits, `_consume_or_refund_server_spell_slot` rejection refunds & optimistic `"Concentrazione"` cleanup (`_reject_cast`), bounded/TTL `request_id` deduplication (`make_cast_special_spell_request`), live HUD `🔮 [Conc: <Spell>]` badge, and `concentrating_on`/`concentrating_spell` parity (`TASK-011`, `TASK-014`, `TASK-018`, `TASK-019`, `TASK-033`). |
| **Monster / Boss & Trap Engine** | `server/dm_monster_engine.py`, `server/rules/reaction_magic.py`, `server/bestiary_ui.py` | **`PRODUCTION_READY`** | Multiattack, Legendary/Lair actions, Legendary Resistance, Recharge abilities, Mythic traits, traps. |
| **Travel, Exploration, Camp, Shops & Quests** | `server/rules/character.py`, `server/dm_travel_dialog.py`, `components/shop_ui.py`, `components/quest_ui.py` | **`PRODUCTION_READY`** | DM-gated handlers, `game_state.lock` synchronization, hex travel weather/exhaustion, camp watch & encounters. |
| **DMG / XGtE Optional Systems (30 toggles)** | `server/dm_optional_tools.py`, `server/dm_dmg_systems.py`, `server/rules/downtime.py` | **`FUNCTIONAL`** | Flanking, Cleave, Lingering Injuries, Massive Damage, Madness, Honor/Sanity, Downtime; tested across dedicated 5e suites. |
| **In-Person Tabletop Support** | `server/dm_campaign_session_mixin.py`, `server/dm_gui.py`, `server/dm_dialogs.py`, `common/game_state.py` | **`PRODUCTION_READY`** | Multi-map management, hardened DM tabletop local PC import, `roll_all_npcs_initiative` skipping local PCs, real Short/Long Rest time recovery, interactive `DMPlayerSheetViewer` tabletop tab (slots/HD/death-saves/rolls), read-only detached Player Display (`open_player_display_window`) with union FoW (`TASK-032`), and `sync_local_party_characters_to_manager` writeback (`TASK-012`, `TASK-030`, `TASK-037`). |
| **Audio Soundboard & UDP Voice Chat** | `server/audio_library.py`, `server/rules/audio.py`, `server/voice_server.py`, `client/voice_client.py` | **`INTEGRATED`** | Validated URL/chunk streaming, path-containment hardening (`TestTask036UxSecurityAndManualsTests`), UDP relay with mock-audio test mode (`DND_MOCK_AUDIO=1`). |
| **Bilingual i18n & Compendium / Manuals** | `common/i18n.py`, `common/srd_offline.py`, `common/pdf_manuals_indexer.py`, `common/theme.py`, `client/manuals_ui.py`, `client/player_journal_dialog.py` | **`PRODUCTION_READY`** | Symmetric IT/EN dictionary (incl. all 6 3D dice banner keys `TASK-036`), accessible disabled button contrast (`WCAG >= 4.5:1`), Imperial/Metric conversion, offline SRD search, PDF manual indexing, debounced `ManualsDialog` search with dynamic wraplength & PDF folder actions (`TASK-030`, `TASK-036`), and `[UX-L03]` Markdown/`Ctrl+S` Player Journal with `dm_note` isolation (`TASK-030`). |
| **CI & Automated Regression Suite** | `.github/workflows/ci.yml`, `tests/test_*.py`, `docs/UX_AUDIT.md` | **`PRODUCTION_READY`** | `68` `unittest` modules (`682` verified passing tests in `77.296s`), isolated via `DND_SETTINGS_PATH` / `DND_CHARACTERS_PATH`, including `TestPhase35AndPhase4HardeningAndUX`, `TestPhase45UxAuditAndWorkflows`, `TestPhase5EndToEndWorkflows` (Workflows A–D), `TestPhase5BRealisticScenariosE2E` (`tests/test_phase5b_scenarios_e2e.py`, Scenarios A–E), `TestTask036UxSecurityAndManualsTests`, `test_task030_*`, `py_compile` (`179` `.py` files), CI `pyflakes` (`357` non-critical lines, `CRIT=0`), live multi-res Tkinter runtime geometry probes (`docs/UX_AUDIT.md`, `errors=0`), and real loopback TCP E2E suites. |
