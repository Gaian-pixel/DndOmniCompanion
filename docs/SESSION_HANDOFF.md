# D&D OmniCompanion — Autonomous Development Session Handoff

> **Branch:** `dev/v0.6.0-autonomous` (`main` untouched at `3b28c99`, no remote pushes or tags)  
> **Latest Phase:** Phase 5B Core VTT Completion, Advanced Gameplay & Product Validation (`TASK-032` through `TASK-037`)  
> **Status:** All roadmap items (`TASK-001` through `TASK-037`) are **COMPLETED**, verified, and committed locally on `dev/v0.6.0-autonomous`.

---

## 1. Completed Work & Commit Log (`dev/v0.6.0-autonomous`)

1. **`2d03396` — Initial Audit & Roadmap (`docs/DEVELOPMENT_ROADMAP.md`)**
   - Full repository audit establishing the baseline test suite, architecture map, security/reliability findings, and prioritized backlog (`TASK-001` through `TASK-008`).

2. **`8bbee8e` — `TASK-001`: Storage Isolation & Deterministic Smite Test**
   - Added `DND_SETTINGS_PATH` and `DND_CHARACTERS_PATH` environment overrides in `client/settings_manager.py` and `client/character_manager.py` so automated test runs never mutate tracked files in `client_data/`.
   - Stabilized `tests/test_raw_5e_advanced_features.py` (fixed Divine Smite test RNG flakiness).

3. **`0e76c0a` — `TASK-002`: Security, Concurrency & Audio Hardening**
   - Enforced `is_dm_actor(gs, player)` on privileged travel, camp, and journal handlers (`server/commands.py`).
   - Added re-entrant lock synchronization (`game_state.lock`) around `GameState` mutations in `server/network.py` and `server/dm_gui.py`.
   - Restricted audio playback URLs to safe HTTP/HTTPS schemes and hardened `AUDIO_TRACK_CHUNK` bounded assembly/atomic writes in `client/client.py` and `common/network_utils.py`.

4. **`1e4881f` — `TASK-003`: Star Import Removal, Bug Fixes & GitHub CI**
   - Eliminated wildcard (`*`) imports across `common/`, `server/`, `client/`, and `components/`, uncovering and fixing 3 latent missing-import bugs (`is_incapacitated_entity` and `_get_entity_skill_bonus` in `server/rules/combat.py`, `safe_after` in `components/ui_components.py`).
   - Added `.github/workflows/ci.yml` running `py_compile`, `pyflakes` critical checks, and isolated headless `unittest discover tests`.

5. **`75542e7` — `TASK-004`: Bilingual Documentation Reconciliation & Session Handoff**
   - Reconciled EN/IT documentation test counts, documented CI execution and standalone GUI smoke/E2E scripts (`tests/test_ui_smoke.py`, `tests/test_e2e_gui.py`), and introduced `docs/SESSION_HANDOFF.md`.
   - Verified async `task-43750` completion against `75542e7` (`Ran 583 tests in 51.183s — OK`).

6. **`4f17d2e` — `TASK-005`: Malformed Packet Resilience & Audio Download Eviction**
   - Added `JOIN` payload validation (`dict`/name/type/`position` checks) and malformed-packet loop guards in `server/network.py` so bad client payloads return `ERROR_REPLY` without tearing down the connection loop.
   - Added `_audio_download_ttl = 60.0` stale cleanup (`_prune_stale_audio_downloads`), `_max_audio_downloads = 8` oldest-entry eviction, and clean reset on disconnect in `client/client.py`.
   - Added `test_audio_downloads_ttl_eviction_and_max_concurrent_cap` and `test_server_malformed_packets_do_not_drop_connection` in `tests/test_audit_fixes.py`.

7. **`5b597bf` — `TASK-006`: Optional Session Passphrase/PIN Auth & Rate Limiting**
   - Added optional `password` field to `JoinData` / `make_join()` in `common/protocol.py`.
   - Added constant-time passphrase verification (`hmac.compare_digest`), per-IP sliding-window rate limiting (`AUTH_MAX_ATTEMPTS = 5`, `AUTH_WINDOW_SECONDS = 60.0`, `AUTH_LOCKOUT_SECONDS = 30.0`), and live passphrase management (`Server.set_session_password`) in `server/network.py`.
   - Added symmetric EN/IT translations (`login_session_pin`, `menu_session_password`) in `common/i18n.py`, optional masked PIN field in `client/login_ui.py` (keeping `.result == (ip, char)` 2-tuple compatibility), wiring in `main.py` / `client/client.py`, and `DM_GUI.open_session_password_dialog()` in `server/dm_gui.py`.
   - Added `test_server_join_session_password_and_rate_limiting` in `tests/test_audit_fixes.py`.

8. **`010aacb` — `TASK-007`: SHA-256 Hash-Cached Map & Handout Transfer Deduplication**
   - Added `compute_asset_hash(b64_data)` (`SHA-256[:16]`) and per-player `_sent_asset_hashes` deduplication (`prepare_per_player_state_payload`, `_deduplicate_map_payload`, `_deduplicate_handout_dict`) in `common/network_utils.py`, wired through `broadcast()` and `server/network.py` (join/reconnect hash reset) without cross-player payload mutation.
   - Added bounded 32-entry client asset cache (`_get_asset_cache`, `_store_asset_in_cache`, `_resolve_cached_map_assets`, `_resolve_cached_handout_assets`) in `client/client.py`.
   - Added `test_hash_cached_map_and_handout_transfer_deduplication` in `tests/test_audit_fixes.py`.

9. **`e1e0ec7` / `13d76b9` — `TASK-008`: Modular Mixin Extraction & Phase 1 Handoff (`ClientNetworkHandlersMixin` & `DMCampaignSessionMixin`)**
   - Extracted `ClientNetworkHandlersMixin` into `client/network_handlers.py` and `DMCampaignSessionMixin` into `server/dm_campaign_session_mixin.py`, preserving public APIs and mock targets, followed by `13d76b9` updating bilingual docs and handoff metrics (`Ran 588 tests in 61.292s — OK`, verified via `task-44031`).

10. **`TASK-009` (Phase 2) — Post-Implementation Review Hardening & Feature Maturity Matrix**
   - Authored `docs/FEATURE_MATURITY.md` assessing `TASK-005`–`TASK-008`, E2E user journeys (DM, Player, In-Person Tabletop), transport security boundary (plaintext TCP without TLS; PIN protects LAN/tabletop room access and brute-force guessing, not passive sniffing), and 14-subsystem maturity ratings.
   - Redacted plaintext `password` (`'***'`) from server `JOIN` debug logs (`server/network.py`).
   - Recomputed SHA-256 asset hashes unconditionally on non-empty payloads (`common/network_utils.py`) and synchronized server hash tracking (`MAX_TRACKED_SENT_ASSET_HASHES = 24`) under client LRU eviction (`_MAX_ASSET_CACHE_ENTRIES = 32` + `local_map_data` fallback in `client/network_handlers.py`).

11. **`TASK-010` (Phase 2) — Combat Action Economy, Extra Attack, Cunning Action & Class Feature Sync**
   - Fixed `server/rules/combat.py` so `has_acted_this_turn` properly blocks extra standard attacks after `max_attacks` is exhausted, and enforced `has_acted_this_turn` inside `_validate_combat_tactical_action` when `strict_turn_lock` is enabled.
   - Added server-authoritative `action_surge`, `second_wind`, and `rage` handlers in `server/rules/class_abilities.py`.
   - Serialized `attacks_made_this_turn`, `has_reacted_this_turn`, `sneak_attack_used_this_turn`, `readied_action_data`, and `helped_targets_this_turn` in `Player.to_dict()` / `from_dict()` (`common/game_state.py`), added `movement_spent_this_turn` to `make_player_move` / `handle_move_request`, and wired client `ClientGUI` class feature / `Cunning Action` requests + Extra Attack & turn-economy HUD sync (`client/client.py`).

12. **`TASK-011` (Phase 2) — Character Sheet Spellcasting & Server 5e Spell Engine Integration**
   - Extended `make_cast_special_spell_request(..., **extra)` (`common/protocol.py`) and updated `handle_cast_special_spell_request` (`server/rules/class_abilities.py`) to support `already_consumed_slot` (avoiding double slot deduction or duplicate Wild Magic Surge rolls) and `is_reaction_spell` (`has_reacted_this_turn = True`).
   - Updated `client/character_sheet_ui.py` (`do_attack`, `do_cast`, `cast_spell_callback`) and `client/client.py` (`on_sheet_cast_spell`) so leveled attack spells charge slots via `SpellsPanel.execute_spell_resource_cost` and sheet casts dispatch `CAST_SPECIAL_SPELL_REQUEST`.

13. **`58cac3b` / `6cae90d` — `TASK-012` (Phase 2): Lossless Session Persistence & In-Person Tabletop Party Hero Import**
   - Updated `GameState.get_state_dict(is_dm=True)` and `GameState.load_session()` (`common/game_state.py`) to preserve `maps`, `active_map_id`, `pending_legendary_resistances`, `campaign_starter_kit`, and full `Player.from_dict()` state on connected players while keeping live socket/hash tracking intact.
   - Added `_find_free_party_spawn_hex`, `import_party_character_to_game_state`, `DMCampaignSessionMixin.import_party_character_data` / `open_import_party_character_dialog`, DM toolbar button `btn_import_local_pc`, and symmetric EN/IT translations (`common/i18n.py`).
   - Added E2E and regression coverage (`TestPhase2ProductMaturityAndE2E`) in `tests/test_audit_fixes.py`, plus `docs/FEATURE_MATURITY.md` (`58cac3b`).

14. **`TASK-013` (Phase 3) — Combat Action Economy, Class Abilities & Cross-Player Actor Authorization**
   - Enforced actor ownership authorization (`_resolve_actor`) across all 14 actor-accepting class/spell handlers in `server/rules/class_abilities.py`, along with incapacitation, turn-lock, Fighter Lv 2+ `action_surge_used_this_turn` (1/turn limit), Second Wind HP clamping, and Barbarian Rage heavy armor check (`calculate_character_item_modifiers` + equipped `inventory_grid` fallback).
   - Unified `concentrating_on`/`concentrating_spell` cleanup across `drop_concentration` (`server/rules/combat.py`), Barbarian Rage activation (`server/rules/class_abilities.py`), added `_end_rage_if_unconscious` on 0 HP, expired readied action turn cleanup, reaction rollback on range/Sanctuary failure, and synced Fighter Lv 2+ / `already_consumed` handling in `client/client.py`.

15. **`TASK-014` (Phase 3) — End-to-End Spellcasting Validation, Slot Refunds, Dedup & Sheet Sync**
   - Fixed cantrip `cast_level=0`/`base_level=0` parsing (`raw_cast`/`raw_base` without `0 or 1` coercion), enforced Rage spellcasting block, implemented `_consume_or_refund_server_spell_slot` + `_reject_cast` slot refund on server validation rejection, and added `request_id` deduplication in `server/rules/class_abilities.py`.
   - Added `_prevalidate_client_spell_cast`, `request_id` generation, and `CharacterSheetFrame.sync_resources_from_character()` in `client/character_sheet_ui.py`, wired through `client/client.py` (`on_sheet_cast_spell` and `handle_game_state`).

16. **`TASK-015` (Phase 3) — Lossless Campaign/Session Persistence, Reconnect Protection & Hardened Local PC Import**
   - Preserved unknown forward-compatible JSON keys via `_extra_fields`/`_extra_state_fields` in `Player`, `GameState` (`common/game_state.py`), and `Campaign` (`common/campaign.py`).
   - Protected server-authoritative HP, conditions, spell/pact slots, class/custom resources, spell points, hit dice, exhaustion, and inspiration across socket reconnection via `_preserve_server_state_on_join` and `_preserve_stats_on_join` (`server/network.py`, `server/rules/character.py`).
   - Hardened `import_party_character_to_game_state` (`server/dm_campaign_session_mixin.py`) with `normalize_character_dict`, `_safe_import_int`, bounds/wall-free `_find_free_party_spawn_hex`, and reconnect preservation flags.

17. **`TASK-016` (Phase 3) — Real Loopback TCP Multiplayer & Gameplay Integration E2E Suite & Doc Sync**
   - Created `tests/test_gameplay_integration_e2e.py` (9 integration and real loopback TCP multiplayer E2E tests via `LoopbackSessionHarness` covering PIN auth, action economy, spell refunds/dedup, reconnect state protection, and lossless persistence).
   - Reconciled bilingual documentation (`README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/FEATURE_MATURITY.md`, `docs/SESSION_HANDOFF.md`) to `602` verified tests across `64` modules.
18. **`TASK-017` (Phase 3.5) — 5e 2014 Ruleset Determination, Action Surge Lv 17+ & Rest/Combat State Correctness**
   - Codified **D&D 5e (2014 Core Rules — PHB / DMG / MM / SRD 5.1)** + **XGtE (2017) / TCE (2020)** + **30 DM-configurable optional rules** (`GameState.automation_settings`) with zero silent mixing of incompatible 2024 rules.
   - Normalized Fighter Lv 17+ `action_surge_max=2` in `common/character_schema.py` and `add_class_level` `custom_resources` upgrades in `client/character_manager.py`, extracted `restore_entity_rest_resources(entity_or_sheet, rest_type)` and `_apply_player_long_rest(p, game_state)`, and added `0`-HD Short Rest support (`hd_spent=0`) in `server/rules/combat.py` and `client/client.py`.
   - Cleared `readied_action_data` / `"Azione Preparata"` on 0 HP or incapacitation (`apply_damage`, `handle_update_stats_request`, `handle_update_full_sheet_request`) and reset turn/reaction/readied-action/prepared-concentration state cleanly in `GameState.end_combat()`, while guarding `_extra_fields`/`_extra_state_fields` against self-key collisions across `Player`, `GameState`, and `Campaign`.
19. **`TASK-018` (Phase 3.5) — Server Authority Concurrency, Atomic Resource Transactions & Reconnect Window Hardening**
   - Added lock-synchronized bounded/TTL `_check_and_record_request_id(..., max_entries=32, ttl_sec=120.0)` deduplication in `server/rules/class_abilities.py` and default 12-char hex `request_id` attachment via `_attach_request_id` in `common/protocol.py` (`make_cast_special_spell_request`, `make_class_feature_request`, honoring explicit `request_id=None`).
   - Refactored `handle_cast_special_spell_request` and `handle_class_feature_request` (`action_surge`, `second_wind`, `rage`) to validate and commit resource/slot/ward/turn-flag changes atomically under `game_state.lock`, scrubbing optimistic `"Concentrazione"` in `_reject_cast` when `actor.concentrating_on is None`.
   - Replaced sticky reconnect preservation with monotonic TTL timestamps (`_preserve_join_until = time.monotonic() + 5.0` on TCP reconnect in `server/network.py`, `+ 1.0` after campaign import in `server/rules/character.py`).
20. **`TASK-019` (Phase 4) — Player HUD & DM Party Tracker UX Polish**
   - Added live `🔮 [Conc: <Spell>]` badge in `update_hero_summary_card` (`hero_hp_lbl`), remaining `(cur/max)` / `(∞)` counters and dynamic `_get_feature_tooltip` ToolTips on Second Wind, Action Surge, and Rage buttons (preserved across `apply_translations`), mid-turn Action Surge lock via `_action_surge_used_this_turn`, and `0`-HD Short Rest controls in `open_short_rest_dialog`.
   - Extracted `DM_GUI._format_dm_player_row` in `server/dm_gui.py` to display `+temp_hp`, `🔮[Conc: ...]`, `⏳[Prep]`, and active-turn `[A:... B:... R:...]` badges in the DM party tracker.
21. **`TASK-020` (Phase 3.5 & 4) — Deterministic E2E Hardening, Regression Coverage & Bilingual Doc Sync**
   - Fixed the 5% Natural-1 attack roll flake in `test_real_tcp_pin_combat_action_surge_spellcast_and_reconnect` and added `TestPhase35AndPhase4HardeningAndUX` (3 new integration & headless Tk UX test methods in `tests/test_gameplay_integration_e2e.py`), reaching `605/605` passing tests across `64` modules.
   - Synchronized all 7 bilingual docs (`README.md`, `README_IT.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/GUIDA_OPERATIVA.md`, `docs/DEVELOPMENT_ROADMAP.md`, `docs/FEATURE_MATURITY.md`, `docs/SESSION_HANDOFF.md`).

22. **`TASK-021` (Phase 4.5) — Shared / Login / Battlemap UX & Interaction Hardening**
   - Updated `common/messagebox.py` (`askyesno`, `askokcancel`) to recognize localized `"Sì"`/`"si"`/`"OK"` responses alongside `"Yes"`.
   - Fixed `LoginDialog` vertical clipping in locked mode (`520x435` vs `reqheight 393`), wired `btn_change_char` to `unlock_character_selection()`, added password eye toggle (`_toggle_pin_visibility`), and validated `host:port` before persisting server history (`client/login_ui.py`).
   - Hardened `HexMapCanvas` (`components/ui_components.py`) with `can_move_token_callback`, `on_token_select_callback`, `is_hex_click_priority_callback`, non-drifting `night_overlay`/`dice_3d` pan tags, hover/SRD caches, and dynamic-height reflowing `ToastNotification` stacks; fixed DM click-token accidental hex teleport.

23. **`TASK-022` (Phase 4.5) — Dungeon Master Combat Sidebar, Spawner & Dialog Workflows**
   - Added inline `selected_entity_quick_bar` (`±HP`, target, sheet, conditions) on `DM_GUI` Tab 1 (`server/dm_gui.py`) without altering `npc_actions_frame`, bound `<Double-Button-1>` on `player_listbox` (`Alt+Double-1` for private chat), and added `Alt+Left`/`Alt+Right` turn shortcuts.
   - Routed DM HP changes through `apply_dm_hp_delta` (`temp_hp` absorption, `full_sheet["hp_current"]` sync, Concentration DC warnings, `0 HP` unconsciousness), generalized `find_free_spawn_hex` across spawners (`server/dm_campaign_session_mixin.py`), unified `open_combat_config` sort order & added 5e conditions in `server/dm_entity_dialogs.py`, and included local `is_party_member=True` heroes in `EncounterBuilderDialog` (`server/encounter_builder_ui.py`).

24. **`TASK-023` (Phase 4.5) — Player Economy Rollback, Companion Drag-Drop, Tooltips & Sheet/Level-Up UX**
   - Enabled player drag-and-drop movement of owned companions/familiars end-to-end across `ClientGUI.on_token_drop` (`client/client.py`) and `server/rules/movement.py` (`entity_name` routing).
   - Added optimistic turn-economy snapshots & automatic rollback on `ERROR_REPLY`, non-blocking rejection toasts, rejected-PIN clearing, transient disconnect map preservation, unread Chat tab badge (`Tab 0`), `btn_grapple`/`btn_shove`/`btn_ammo` sync + dynamic disabled-reason tooltips (`my_turn`-gated).
   - Fixed initiative bonus calculation (`client/network_handlers.py` using `get_initiative_bonus()`), off-hand `🗡️ 2ª Mano` (`is_bonus_action=True`) & weapons-tab resize/scroll + spell `<Double-1>` (`client/sheet_panels/combat_panel.py`, `client/character_sheet_ui.py`), and `LevelUpDialog` subclass unlock enforcement + ASI auto-radio switching (`client/progression_ui.py`).

25. **`496e2ea` — `TASK-024` (Phase 4.5): Complete UX Audit Report, Automated Workflow Tests & Bilingual Doc Sync**
   - Authored `docs/UX_AUDIT.md` with complete 25-interface inventory, explicit documentation of the `PIL.ImageGrab` environment limitation (`OSError: screen grab failed`), and pre/post live Tkinter widget geometry verification.
   - Appended `TestPhase45UxAuditAndWorkflows` (5 new UX/workflow/integration tests) in `tests/test_gameplay_integration_e2e.py`, reaching `610/610` passing tests across `64` modules (`65.163s`), and synchronized all bilingual docs and roadmap artifacts.

26. **`775dbc0` — `TASK-025` (Phase 5): Responsive Character Sheet (`[UX-C05]`), Vitals Display & Inventory/Combat Sync**
   - Implemented 4-tier responsive `CharacterSheetFrame` layout (`wide4 >=1280`, `wide3 1100..1279`, `medium 900..1099`, `compact <900` with sticky `vital_strip` toggle), live Sheet Vitals (`TempHP`, `HD`, `Exhaustion`, `Conditions`), `get_initiative_bonus()` Alert/feat display, `sync_resources_from_character()` + `update_dynamic_stats()`, and Artificer/Dual Wielder/Archery/combat-gate fixes (`tests/test_character_sheet_enhancements.py`).

27. **`1fec676` — `TASK-026` (Phase 5): Character Progression, Wizard, Unknown-Field JSON Preservation & Server Sheet Authority**
   - Preserved `_extra_fields` round-trip in `Character` / schema, fixed multiclass slot overwrites, Warlock `pact_slots` duplication, Health Hit Die tab refresh, Sorcerer-gated Draconic HP, Feats list sync, Wizard EN 4d6 / TCE swap / EN background rolls, null-manager sheet saves, and server `handle_update_full_sheet_request` authority (`623/623` passing).

28. **`ef985e7` — `TASK-027` (Phase 5): Battlemap, FoW/LoS Secrecy, Square/Gridless Math Parity & AoE Crash Fix**
   - Fixed `has_line_of_sight` 3-vs-4 arg AoE crash, unified closed/secret door LoS blocking, removed secret leaks (`teleports`/`spawn_point`/`fow_draft`/untriggered secret traps/empty-FoW loots/pocket-dimension tokens), passed `grid_type` consistently, synced `light_radius` & remote Darkvision, and added `tests/test_battlemap_fow_los.py` (`629/629` passing).

29. **`c715473` — `TASK-028` (Phase 5): Battlemap Interactions, Map Editor Layers, Tool Exclusion, Runtime Map Switcher & 4MP Perf**
   - Unblocked right-click drag ruler (`[UX-H11]`), enforced tool mutual exclusion, `<B1-Motion>` drag-paint, elevated/multi-hex token hit-testing, DM click selection without accidental hex teleport, Map Editor Walls/Cover/Doors/Lights/Spawn layers, runtime Map Switch/Create/Resize/Delete, Live Flow NPC deduplication, and `>4MP` redraw optimization (`637/637` passing).

30. **`634a0cd` — `TASK-029` (Phase 5): D&D 5e (2014) Rules Engine Completeness & Combat-Magic-Monster Integration**
   - Unified Radiant damage & Smite secondary `apply_damage(same_hit_secondary=True)`, elemental adept helpers, Wild Shape revert order, server-authoritative `DEATH_SAVE_REQUEST` (`compute_death_save_flat_bonus`, Halfling Lucky, Paladin Aura, `vitals_panel` sync), hardened lethal reaction rescues/`Absorb Elements`/`Counterspell`, `Font of Magic` Lv3+/BA, downward AC recalc, and MM Multiattack/Beholder/Lair/CR XP parity (`tests/test_rules_task029_completeness.py`, `646/646` passing).

31. **`5688125` — `TASK-030` (Phase 5): Multiplayer Reliability, HUD/DM UX (`[UX-H09]`/`[UX-H10]`/`[UX-M08]`/`[UX-H12]`/`[UX-L03]`), Secrecy & Tabletop Mode**
   - Implemented `ClientNetwork.connect_async` & `PING`/`PONG` keepalive, cross-IP PIN reconnect with `known_asset_hashes` deduplication & avatar cache restore, reconnect-window resource clamping, `[UX-H09]` HUD connection pill & `[UX-H10]` scrollable `controls_canvas`, `[UX-M08]` bounded `npc_actions_canvas`, `[UX-H12]` Quest/Faction editor fixes, `DMLiveFlowDialog.share_lore` handout broadcast, `.bak` atomic campaign backups, `DM SECRET:`/`dm_note` secrecy, `[UX-L03]` Markdown/`Ctrl+S` Player Journal, debounced `ManualsDialog`, and Tabletop mode (`roll_all_npcs_initiative` skipping PCs, real time rests, interactive `DMPlayerSheetViewer`, read-only `open_player_display_window`, `sync_local_party_characters_to_manager` writeback) (`tests/test_task030_multiplayer_ux_secrecy_tabletop.py`, `659/659` passing).

32. **`3952f8e` — `TASK-031` (Phase 5): Phase 5 E2E Workflows A–D, CI Bug Fix & Bilingual Documentation Sync**
   - Fixed latent `NameError` in `server/rules/combat.py` (`_apply_hp_change(..., same_hit_secondary=False)`) surfaced by `pyflakes`.
   - Added `TestPhase5EndToEndWorkflows` (`4` E2E tests covering Workflows A–D in `tests/test_gameplay_integration_e2e.py`, module total `21/21 OK` in `7.407s`), verified full isolated suite (`663/663 OK` across `67` modules in `62.953s`), `py_compile` (`178` files), `pyflakes` (`CRIT=0`), and live Tkinter probe (`errors=0`), and synchronized all bilingual docs.

33. **`80d88cd` — `TASK-032` (Phase 5B): Battlemap Player Display FoW, Marquee Group Move & Map Editor Undo/Layers**
   - Implemented second-screen Player Display (`is_dm=False`, `player_name=""`) party/companion union FoW/LoS + revealed lights (`_compute_player_visible_hexes`, `_compute_token_vision_hexes`).
   - Added `HexMapCanvas` content-signature `_map_hexes_set` invalidation (`_map_hexes_sig`), `Shift+Drag` marquee selection & `on_tokens_group_drop_callback` wired in DM & Client, 50-step Map Editor Undo/Redo (`Ctrl+Z`/`Ctrl+Y`), Trap/Loot/Teleport/Room-Pin layer tools/badges, `resize_grid`, and gridless auto-grid generation (`tests.test_map_editor` + `tests.test_battlemap_fow_los`: `31/31 OK`).

34. **`73ce9b7` — `TASK-033` (Phase 5B): D&D 5e 2014 Engine Polish**
   - Enforced single-concentration cleanup, `concentration_caster`, and non-permanent `+2 AC` cleanup in `Shield of Faith` (`get_spell_ac_bonus` across combat/multi-ray/multiattack); passed `grid_type` consistently to combat LoS/cover (`hex_linedraw`, `get_cover_between`) and allowed Barbarian Lv 20 Primal Champion up to `24` FOR/COS on server validation.
   - Added 3D AoE vertical extent checks (`_is_target_within_aoe_elevation`), `detected=False` cleanup on `reset_trap_at`, explicit `requires_attunement` compendium flag, and client-server ranged ammo sync (`41/41 OK` across targeted suites).

35. **`f8e9421` — `TASK-034` (Phase 5B): Feat Prerequisites, Half-Feat Automation & Multiclass Mixed Hit Dice Pools**
   - Added `check_feat_prerequisites` validation + UI badge blocking illegal feat picks in `LevelUpDialog`, `apply_half_feat_bonus` + Half-Feat selector (`+1` ability, retroactive CON HP, *Resiliente* save proficiency), and per-die `hit_dice_pools` (`d12`/`d10`/`d8`/`d6`) synced across `VitalsPanel`, `ClientGUI`, `make_short_rest_request(die_counts=...)`, and Long Rest `half total` (min `1`) recovery (`118/118 OK` across targeted suites).

36. **`89e225e` — `TASK-035` (Phase 5B): Static Grid (`hexes_hash`) Cache, LoS Memoization & Non-Blocking Broadcast**
   - Added `compute_hexes_hash` (`hx_<sha256[:16]>`) + shared `_deduplicate_map_payload` and client `_resolve_cached_map_assets` rehydration, chunked `select`-guarded `_send_message_impl` + parallel `_dispatch_native_broadcast()`, `HexMapCanvas._compute_player_visible_hexes` memoization, single-die scalar `hit_dice_current` regression fix (`common/character_schema.py`), and deterministic RNG mock in `test_gameplay_integration_e2e.py` (`92/92 OK` targeted run).

37. **`9f6eeb1` — `TASK-036` (Phase 5B): Disabled Contrast, 3D Dice Banner i18n & Security/Manuals Test Coverage**
   - Added accessible disabled button colors (`#1A1D24`/`#9CA3AF`, etc.) via `_map_btn` in `common/theme.py` and symmetric IT/EN `_t(...)` keys (`dice_banner_*`) for all 6 3D dice banner strings in `components/dice_3d_canvas.py`.
   - Added `TestTask036UxSecurityAndManualsTests` in `tests/test_audit_fixes.py` covering `journal.py`/`character.py` DM privilege rejection, `audio_library.py`/URL/chunk security bounds, and `ManualsDialog` PDF/manuals folder actions (`46/46 OK` targeted run).

38. **Current Commit (`TASK-037` — Phase 5B): Realistic Gameplay Acceptance Scenarios A–E, Legacy Teleport Compatibility, Live Multi-Res UI Audit & Final Sync**
   - Added `tests/test_phase5b_scenarios_e2e.py` (`TestPhase5BRealisticScenariosE2E`, `5/5 OK` in `2.683s`) proving end-to-end Scenarios A–E across tactical combat/3D AoE/ammo/boss LR, dungeon exploration/MapEditor/FoW/Player Display, multiclass Lv 1–5 progression/prereqs/Half-Feats/mixed rests, hybrid tabletop mode/writeback, and real loopback TCP auth/cache/stalled-socket isolation/reconnect clamping.
   - Fixed legacy list-format `teleports` migration in `MapEditorWindow.load_map_file()` (`server/map_editor.py`) caught by full-suite validation (`tests/test_audit_v17_phase1.py`), verified all post-edit checks (`682/682 OK` across `68` modules in `77.296s`, `179` compiled files, `pyflakes CRIT=0`, live multi-res Tk probe `errors=0`), and synchronized all EN/IT documentation.

---

## 2. Verified Final Baseline Metrics

| Check | Command / Scope | Observed Result |
|---|---|---|
| **Full Headless Unit Test Suite** | `$env:DND_MOCK_AUDIO="1";` with isolated temp `TEMP`/`TMP`/`APPDATA`/`LOCALAPPDATA` & `DND_SETTINGS_PATH`/`DND_CHARACTERS_PATH`, `python -m unittest discover -s tests -q` | **PASSED**: `Ran 682 tests in 77.296s — OK` (`0` failures, `0` errors, `0` skipped across `68` `unittest` modules, including `TestPhase5BRealisticScenariosE2E` Scenarios A–E, `TestPhase5EndToEndWorkflows`, `TestTask036UxSecurityAndManualsTests`, and real loopback TCP E2E tests) |
| **Static Bytecode Compile** | `py_compile.compile(...)` across `common`, `server`, `client`, `components`, `tests`, `main.py`, `build_release.py` | **PASSED**: `PY_COMPILE_OK count=179` |
| **Static Analysis (`pyflakes` Critical Check)** | CI check (`undefined name` / star-import / syntax error across `common`, `server`, `client`, `components`, `main.py`) | **PASSED**: `PYFLAKES_LINES=357 PYFLAKES_CRIT=0` (`0` undefined names, `0` star imports) |
| **Live Isolated Tkinter Probe** | `main.start_app()`, `LoginDialog` (`lock=True`/`False`), `DM_GUI` (`1024x720`, `1280x800`, `1366x768`), `ClientGUI` (`1024x720`, `1366x768`, `1920x1080`), `CharacterSheetFrame` (`1024x720`, `1366x768`, `1920x1080`), `MapEditorWindow` (`1280x800`) | **PASSED**: `LIVE_TK_PROBE_PASS=True errors=0` (`CharacterSheetFrame`: `1024x720` `nb_w=633` `medium`, `1366x768` `nb_w=576` `wide4`, `1920x1080` `nb_w=1090` `wide4`; `DM_GUI` `nb_w=587`; `ClientGUI` `right_panel_w=370`) |
| **Tracked Data Isolation** | `git status --short client_data campaigns manuals` after test runs | **CLEAN**: empty diff (no mutation of tracked files in `client_data/`, `campaigns/`, or `manuals/`) |
| **Roadmapped Tasks** | `docs/DEVELOPMENT_ROADMAP.md` (`TASK-001`..`TASK-037`) | **37 / 37 `COMPLETED`** |

---

## 3. Repository Conventions & Maintainer Notes

- **Isolated Test Runs**: Always set `$env:DND_MOCK_AUDIO="1"` and temporary `DND_SETTINGS_PATH` / `DND_CHARACTERS_PATH` paths when running `unittest discover tests` (or verify `git diff --stat client_data/` afterwards).
- **Standalone Runners (Not in `unittest discover`)**: `tests/test_ui_smoke.py` and `tests/test_e2e_gui.py` are standalone Tkinter smoke/E2E scripts requiring a GUI display and explicit script invocation.
- **Test Mock Compatibility**: Existing tests patch attributes directly on `client.client` (`ClientNetwork`, `AudioManager`, `VoiceClient`, `LoginDialog`, `time.monotonic`) and `server.dm_gui` (`Server`, `AudioManager`, `VoiceClient`), and use `MagicMock(spec=ClientGUI)` / `MagicMock(spec=DM_GUI)`. Keep these module attributes and mixin inheritance intact in future refactors.
- **Documentation & Localization Parity**: Maintain symmetry between Italian (`common/i18n.py` `"it"`, `README_IT.md`, `docs/GUIDA_OPERATIVA.md`, `docs/GUIDA_ALL_UTILIZZO.md`) and English (`common/i18n.py` `"en"`, `README.md`, `docs/OPERATIONAL_GUIDE.md`, `docs/USER_GUIDE.md`).

---

## 4. Next Steps (For Future Sessions)

All roadmap items through Phase 5B (`TASK-001`–`TASK-037`) are complete on `dev/v0.6.0-autonomous`:
1. Review diffs across `main..dev/v0.6.0-autonomous` and run interactive standalone GUI checks (`tests/test_ui_smoke.py`, `tests/test_e2e_gui.py`) if desired in a desktop session.
2. Merge `dev/v0.6.0-autonomous` into `main` and publish any release/tag **only** upon explicit human authorization.
3. Optional next architecture wave: incrementally modularize `ClientGUI.setup_gui` (`client/client.py`) and `DM_GUI` initialization/context menus (`server/dm_gui.py`) into focused mixin/builder modules without altering public mock targets.
