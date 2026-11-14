# D&D OmniCompanion — Feature Maturity & User Journey Assessment

> **Branch:** `dev/v0.6.0-autonomous`  
> **Assessment Scope:** Phase 3.5 Adversarial Gameplay Review & Phase 4 UX Polish (`TASK-017`–`TASK-020`) Building on Phase 2 (`TASK-009`–`TASK-012`) & Phase 3 (`TASK-013`–`TASK-016`)  
> **Date:** 2026-11-14

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

| Subsystem | Primary Modules | Current Rating (Phase 4 Status) | Notes & Evidence |
|---|---|---|---|
| **Unified Launcher & Join Auth** | `main.py`, `client/login_ui.py`, `server/network.py` | **`PRODUCTION_READY`** | Constant-time PIN verification, rate limiting, and plaintext password log redaction verified (`TASK-009`); verified over real loopback TCP sockets (`TASK-016`). TCP transport remains unencrypted (documented LAN/VPN boundary). |
| **Network Protocol & Asset Sync** | `common/network_utils.py`, `common/protocol.py`, `client/network_handlers.py` | **`PRODUCTION_READY`** | Bounds checks, malformed-packet safety, audio chunk atomic cache/TTL eviction, unconditional SHA-256 hashing & bounded LRU asset cache (`24` vs `32`) + local map fallback (`TASK-009`), and server state protection across reconnect (`TASK-015`). |
| **Virtual Tabletop Canvas & Maps** | `components/ui_components.py`, `components/dice_3d_canvas.py`, `server/map_editor.py`, `common/hex_utils.py` | **`PRODUCTION_READY`** | Multi-scale hex/square grids, LoS/FoW, elevations, weather particles, PoIs, 3D dice; covered by render/map/LoS tests. |
| **DM Suite & Campaign Studio** | `server/dm_gui.py`, `server/dm_campaign_session_mixin.py`, `server/campaign_studio_ui.py`, `server/dm_live_flow.py`, `common/campaign.py` | **`PRODUCTION_READY`** | Full campaign authoring, lossless `Player`/`GameState`/`Campaign` `_extra_fields` persistence (`TASK-012`, `TASK-015`), and hardened local PC tabletop import (`TASK-012`, `TASK-015`). |
| **Combat & Action Economy Engine** | `server/rules/combat.py`, `server/rules/class_abilities.py`, `server/rules/movement.py`, `client/client.py` | **`PRODUCTION_READY`** | Enforces actor ownership (`_resolve_actor`), Fighter Lv 17+ `Action Surge` (`action_surge_max=2`, 1 use/turn), atomic `game_state.lock` class-feature consumption, Rage heavy armor block / concentration drop / 0-HP termination, readied-action cleanup on 0 HP / incapacitation / `end_combat()`, Second Wind clamping, `0`-HD Short Rests (`hd_spent=0`), and reaction rollback on failed readied/opportunity attacks (`TASK-010`, `TASK-013`, `TASK-017`–`TASK-019`). |
| **Character Builder, Sheet & Level-Up** | `client/character_manager.py`, `client/character_creation_wizard.py`, `client/character_sheet_ui.py`, `client/progression_ui.py` | **`INTEGRATED`** | Complete 5e races/classes/subclasses/feats/ASI/PDF export; unified `restore_entity_rest_resources`, Fighter Lv 2+/17+ `custom_resources` Action Surge upgrades in `add_class_level`, sheet spellcasting wired end-to-end with `_prevalidate_client_spell_cast`, `request_id`, and `sync_resources_from_character()` convergence (`TASK-011`, `TASK-014`, `TASK-017`). |
| **Spellcasting & Concentration Engine** | `server/rules/class_abilities.py`, `common/spell_effects_engine.py`, `common/protocol.py`, `client/sheet_panels/spells_panel.py` | **`PRODUCTION_READY`** | Enforces Bonus Action spell rule (cantrips `cast_level=0`/`base_level=0`), Rage spell block, atomic `game_state.lock` slot/ward/turn-flag commits, `_consume_or_refund_server_spell_slot` rejection refunds & optimistic `"Concentrazione"` cleanup (`_reject_cast`), bounded/TTL `request_id` deduplication (`make_cast_special_spell_request`), live HUD `🔮 [Conc: <Spell>]` badge, and `concentrating_on`/`concentrating_spell` parity (`TASK-011`, `TASK-014`, `TASK-018`, `TASK-019`). |
| **Monster / Boss & Trap Engine** | `server/dm_monster_engine.py`, `server/rules/reaction_magic.py`, `server/bestiary_ui.py` | **`PRODUCTION_READY`** | Multiattack, Legendary/Lair actions, Legendary Resistance, Recharge abilities, Mythic traits, traps. |
| **Travel, Exploration, Camp, Shops & Quests** | `server/rules/character.py`, `server/dm_travel_dialog.py`, `components/shop_ui.py`, `components/quest_ui.py` | **`PRODUCTION_READY`** | DM-gated handlers, `game_state.lock` synchronization, hex travel weather/exhaustion, camp watch & encounters. |
| **DMG / XGtE Optional Systems (30 toggles)** | `server/dm_optional_tools.py`, `server/dm_dmg_systems.py`, `server/rules/downtime.py` | **`FUNCTIONAL`** | Flanking, Cleave, Lingering Injuries, Massive Damage, Madness, Honor/Sanity, Downtime; tested across dedicated 5e suites. |
| **In-Person Tabletop Support** | `server/dm_campaign_session_mixin.py`, `server/dm_gui.py`, `common/game_state.py` | **`PRODUCTION_READY`** | Multi-map management, hardened DM tabletop local PC import with `normalize_character_dict` & bounds/wall-free spawn search, lossless session reload, monotonic `_preserve_join_until` reconnect protection, and enriched DM party tracker badges via `_format_dm_player_row` (`+temp_hp`, `🔮[Conc: ...]`, `⏳[Prep]`, `[A:... B:... R:...]`) (`TASK-012`, `TASK-015`, `TASK-018`, `TASK-019`). |
| **Audio Soundboard & UDP Voice Chat** | `server/audio_library.py`, `server/rules/audio.py`, `server/voice_server.py`, `client/voice_client.py` | **`INTEGRATED`** | Validated URL/chunk streaming, path-containment hardening, UDP relay with mock-audio test mode (`DND_MOCK_AUDIO=1`). |
| **Bilingual i18n & Compendium / Manuals** | `common/i18n.py`, `common/srd_offline.py`, `common/pdf_manuals_indexer.py`, `client/manuals_ui.py` | **`FUNCTIONAL`** | Symmetric IT/EN dictionary, Imperial/Metric conversion, offline SRD search, PDF manual indexing (UI-heavy PDF viewer tested lightly). |
| **CI & Automated Regression Suite** | `.github/workflows/ci.yml`, `tests/test_*.py` | **`INTEGRATED`** | `64` `unittest` modules (`605` verified passing tests in `47.578s`), isolated via `DND_SETTINGS_PATH` / `DND_CHARACTERS_PATH`, including deterministic Phase 3.5/4 hardening tests (`TestPhase35AndPhase4HardeningAndUX`) alongside in-memory & real loopback TCP E2E suites (`tests/test_gameplay_integration_e2e.py`). |
