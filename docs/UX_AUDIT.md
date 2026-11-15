# UX Audit & Interface Maturity Report (Phase 4.5 & Phase 5)

**Branch:** `dev/v0.6.0-autonomous`  
**Audit Date:** 2026-11-15  
**Scope:** Full-application inventory, usability/accessibility/hierarchy/feedback/performance evaluation, live Tkinter geometry probing, and prioritized remediation roadmap (`TASK-021` through `TASK-031`).

---

## 1. Visual & Runtime Inspection Environment

Live Tkinter execution is available in this environment (virtual screen `1920 x 1080`), allowing full instantiation of windows, dialogs, themes, and computed layout geometry (`update()`, `winfo_width()`, `winfo_height()`, `winfo_reqwidth()`, `winfo_reqheight()`, `winfo_ismapped()`).

**Recorded Environment Limitation:**
- `PIL.ImageGrab.grab(bbox=(0, 0, 100, 100))` raises `OSError: screen grab failed` in `grabscreen_win32` because this Windows desktop station does not expose interactive GDI BitBlt screen capture.
- Consequently, this audit **does not claim pixel-level screenshot visual inspection**; verification combines **live Tkinter runtime widget/geometry probing** (exact measured values recorded below) and **complete source-code audit** across all GUI modules.

### Live Tkinter Baseline Measurements (Pre-Fix)

| Interface | Window / Mode | Measured Window / Container | Requested Content Size | Observed Layout Defect |
| :--- | :--- | :--- | :--- | :--- |
| `LoginDialog` (`client/login_ui.py`) | Locked Character (`lock_character=True`) | `520 x 370` | `490 x 391` | **21px vertical clipping** (`370 < 391`); bottom/button spacing compressed |
| `LoginDialog` (`client/login_ui.py`) | Unlocked Character List | `520 x 500` | `463 x 483` | Fits vertically (+17px headroom) |
| `DM_GUI` (`server/dm_gui.py`) | `1280 x 800`, Tab 1 (`tab_combat`) | `1280 x 800`, `right_notebook: 587 x 741` | `player_listbox req_h: 180`, actual `h: 422` (initial empty) | Initial empty state fits; unbounded `npc_actions_frame` buttons crush `player_listbox` for bosses/casters |
| `ClientGUI` (`client/client.py`) | `1280 x 800` OOC / `1366 x 768` Combat | `right_panel: 370 x 792`, `controls_tab: 681px` (`1366x768`) | `controls_tab req_h: 694` | **13px vertical overflow** on `1366x768` even before class features pack; `end_turn_btn` unmapped until turn update |
| `CharacterSheetUI` (`client/character_sheet_ui.py`) | Auto-sized Full vs. `1024 x 720` | Full: `1896 x 923` (`notebook: 985px`); Resized `1024x720` (`notebook: 113px`) | `notebook req_w: 985` | **Critical horizontal crush** (`113px` actual vs `985px` requested) due to 4 fixed-width left columns (~795px) |

---

## 2. Complete Application Interface Inventory

All 25 significant interfaces verified in the actual repository:

| Category | Interface / Workflow | Primary Module(s) | Verification Status |
| :--- | :--- | :--- | :--- |
| **App & Connection** | Role Launcher & Pre-Session Switcher | `main.py` | Code-audited |
| **App & Connection** | Login Dialog, Server History & Session PIN | `client/login_ui.py`, `client/network.py`, `server/dm_campaign_session_mixin.py` | Live Tkinter geometry + Code-audited |
| **App & Connection** | Client Connection State & Reconnect Flow | `client/client.py`, `client/network_handlers.py` | Live Tkinter + Code-audited |
| **Dungeon Master** | Main DM Window & Initiative/Combat Sidebar | `server/dm_gui.py` | Live Tkinter geometry + Code-audited |
| **Dungeon Master** | Pending Automation Decisions & Turn Controls | `server/dm_gui.py`, `server/dm_automation_panel.py` | Code-audited |
| **Dungeon Master** | Combat Config, Modify HP & Conditions Dialogs | `server/dm_entity_dialogs.py` | Code-audited |
| **Dungeon Master** | Encounter Builder & Spawning Workflow | `server/encounter_builder_ui.py`, `server/dm_bestiary_panel.py`, `server/dm_live_flow.py` | Code-audited |
| **Dungeon Master** | Campaign Editor, Quests, Handouts & Scenes | `server/campaign_editor_ui.py`, `server/dm_dialogs.py` | Code-audited |
| **Dungeon Master** | Campaign Studio Graph & Inspector | `server/campaign_studio_ui.py` | Code-audited |
| **Dungeon Master** | Soundboard & Automation Settings | `server/dm_soundboard_panel.py`, `server/dm_automation_panel.py` | Code-audited |
| **Dungeon Master** | Session Save/Load & Campaign Mixin | `server/dm_campaign_session_mixin.py` | Code-audited |
| **Player Interface** | Main Player Window, HUD & Action Economy | `client/client.py`, `client/network_handlers.py` | Live Tkinter geometry + Code-audited |
| **Player Interface** | Hero Card, Conditions, Turn Banner & Rests | `client/client.py`, `client/sheet_panels/vitals_panel.py` | Live Tkinter + Code-audited |
| **Player Interface** | Special 5e Powers & Quick Dice Bar | `client/client.py` | Code-audited |
| **Player Interface** | Character Sheet Layout & Notebook Tabs | `client/character_sheet_ui.py` | Live Tkinter geometry + Code-audited |
| **Player Interface** | Weapons Tab & Off-Hand Economy | `client/character_sheet_ui.py`, `client/sheet_panels/combat_panel.py` | Code-audited |
| **Player Interface** | Spellbook, Casting & Inventory Subpanels | `client/character_sheet_ui.py`, `client/sheet_panels/spells_panel.py`, `client/sheet_panels/inventory_panel.py` | Code-audited |
| **Player Interface** | Character Manager & Offline Sheet Access | `client/character_manager_ui.py` | Code-audited |
| **Player Interface** | Character Creation Wizard & Level-Up Dialog | `client/character_creation_wizard.py`, `client/progression_ui.py` | Code-audited |
| **Player Interface** | Player Journal & Rules Manual Dialog | `client/player_journal_dialog.py`, `client/manuals_ui.py` | Code-audited |
| **Virtual Tabletop** | Hex/Square Battlemap Canvas (`HexMapCanvas`) | `components/ui_components.py`, `common/hex_utils.py` | Code-audited + Unit tests |
| **Virtual Tabletop** | Map Editor (`MapEditorWindow`) | `server/map_editor.py` | Code-audited |
| **Shared Components** | Dark Fantasy Theme Engine & Window Centering | `common/theme.py` | Code-audited |
| **Shared Components** | Messagebox Wrapper, Tooltips & Toasts | `common/messagebox.py`, `components/ui_components.py` | Code-audited |
| **Shared Components** | Command Palette (`Ctrl+K`) & 3D Dice Overlay | `components/ui_components.py`, `components/dice_3d_canvas.py` | Code-audited |

---

## 3. Prioritized UX Audit Findings

### CRITICAL Issues (Prevents Important Workflows or Corrupts Rules State)

1. **[UX-C01] Battlemap Missing Drag Ownership Guard, Broken Companion Dragging & Silent Drop Failure (`components/ui_components.py`, `client/client.py`)**
   - `HexMapCanvas._on_canvas_click` starts `self.dragging_token_name = name` for **any** token (enemy monster, NPC, other PC) without consulting an ownership/permission callback, draws a green path preview, and then `ClientGUI.on_token_drop` silently ignores the drop (`if token_name == self.name:`) with zero user feedback.
   - Simultaneously, players **cannot** drag-and-drop their own summoned Familiars, Companions, or Mounts (`owner == self.name` or `master_name == self.name`), even though `server/rules/movement.py` permits owner-controlled companion movement.
   - **Target Task:** `TASK-021`.

2. **[UX-C02] DM Click/Drag on Any Map Token Accidentally Teleports Listbox-Selected Entity (`components/ui_components.py`, `server/dm_gui.py`)**
   - `HexMapCanvas._on_canvas_click` unconditionally fires `self.on_hex_click_callback(clicked_hex)` even when clicking on an existing token to select or drag it.
   - In `DM_GUI.on_hex_clicked`, this immediately calls `move_player(selected_name, [clicked_hex.q, clicked_hex.r])` on mouse-down—teleporting whichever combatant happened to be highlighted in `player_listbox` onto the clicked token's hex before the drag even begins!
   - **Target Task:** `TASK-021`.

3. **[UX-C03] DM Combat Sidebar Lacks Inline Selected-Combatant Quick Bar & Direct HP Edits Bypass Rules (`server/dm_gui.py`, `server/dm_entity_dialogs.py`)**
   - DMs must open a 21-item context menu and modal dialogs (`open_modify_hp_dialog`, `open_action_dialog`) for every manual HP/status adjustment; double-clicking a monster in `player_listbox` opens a broken Private Chat tab instead of inspecting its sheet / centering the map.
   - `open_modify_hp_dialog` mutates `player.hp` directly, ignoring `temp_hp` on damage, leaving `full_sheet["hp_current"]` out of sync, and skipping concentration DC prompts and `0 HP` unconsciousness handling.
   - **Target Task:** `TASK-022`.

4. **[UX-C04] Player Optimistic Action Economy Desyncs on `ERROR_REPLY` & Blocks UI (`client/client.py`)**
   - `perform_dash`, `perform_disengage`, `perform_dodge`, and `_mark_attack_action_economy` consume `action_spent` / `bonus_spent` / `reaction_spent` optimistically before server validation. If the server sends `ERROR_REPLY` (e.g., Incapacitated, not your turn), the economy stays spent until manual reset, while `ERROR_REPLY` freezes the loop with a modal `messagebox.showerror` and `SIMPLE_REPLY` is hidden inside inactive Tab 0 (`Chat`).
   - **Target Task:** `TASK-023`.

5. **[UX-C05] `CharacterSheetFrame` Horizontal Pack Crushes Notebook to `113px` at `1024x720` (`client/character_sheet_ui.py`)**
   - Five horizontally packed columns (`stats_frame`, `saves_frame`, `skills_frame` 280px canvas, `combat_frame`, `tabs_frame`) require `~795px` before the 6-tab `self.notebook` gets any width. Live geometry probing previously showed `notebook` collapsing to `113px` actual width (`985px` requested) at `1024x720`. **Addressed in `TASK-025`** via 4-tier responsive layout (`wide4 >=1280`, `wide3 1100..1279`, `medium 900..1099`, `compact <900`), reaching `nb_w=633` at `1024x720`.

---

### HIGH Issues (Significantly Reduces Usability)

- **[UX-H01] `LoginDialog` Clips Vertically (`370 < 391`) & "Cambia Eroe" Aborts Login (`client/login_ui.py`)**: Locked character mode sets `h = 370` vs `reqheight = 391`, and clicking `login_btn_change_char` runs `self.on_close` (`self.result = None`) instead of unlocking character selection. **Addressed in `TASK-021`.**
- **[UX-H02] Localized `"Sì"` Fails in `common/messagebox.py` (`askyesno`, `askokcancel`)**: `askyesno` only checks `result.lower() == "yes"`, returning `False` when `ttkbootstrap` returns localized `"Sì"`. **Addressed in `TASK-021`.**
- **[UX-H03] `open_combat_config` Two-Step Modal Cascade & Initiative Sort Order Bug (`server/dm_entity_dialogs.py`)**: `finalize_combat` calls `start_combat` *before* assigning newly rolled NPC initiatives `p.initiative = npc_initiatives.get(...)`, corrupting Round 1 turn order, and requires two sequential modals. **Addressed in `TASK-022`.**
- **[UX-H04] Encounter & Monster Spawners Stack All Tokens at `[0, 0]` (`server/dm_gui.py`, `server/dm_campaign_session_mixin.py`)**: `handle_encounter_start`, `on_monster_spawned`, and `handle_srd_import` leave spawned NPCs at default `[0, 0]` instead of finding non-overlapping free hexes. **Addressed in `TASK-022`.**
- **[UX-H05] `EncounterBuilderDialog` Ignores Local Party Members (`conn is None`) (`server/encounter_builder_ui.py`)**: Filters only `p.conn is not None`, ignoring imported local party characters (`is_party_member=True`) and falling back to fake Level 1 x 4 thresholds. **Addressed in `TASK-022`.**
- **[UX-H06] Tactical Combat Buttons (`btn_grapple`, `btn_shove`, `btn_ammo`) Lack State Sync & Dynamic Tooltips (`client/client.py`)**: Omitted from `_cfg_tactical_btn` in `update_action_economy_ui`, and tactical buttons lack dynamic disabled-reason tooltips. **Addressed in `TASK-023`.**
- **[UX-H07] Weapons Tab Missing Resize/Scroll & `🗡️ 2ª Mano` Spends Standard Action (`client/character_sheet_ui.py`, `client/sheet_panels/combat_panel.py`)**: Off-hand (`🗡️ 2ª Mano`) attack fails to pass `is_bonus_action=True` to `execute_targeted_attack`, spending Standard Action instead of Bonus Action; `create_weapons_tab` omits `<Configure>` width binding and `<MouseWheel>`. **Addressed in `TASK-023`.**
- **[UX-H08] `LevelUpDialog` Subclass Unlock & ASI Radio Desync (`client/progression_ui.py`)**: Allows picking a subclass before `unlock_lvl`, and selecting ASI dual/feat dropdowns fails to switch `asi_choice_var`; spell trees lack `<Double-1>` toggle. **Addressed in `TASK-023`.**
- **[UX-H09] Connection Banner Hidden in Tab 1 & Socket `connect()` Blocks Without Timeout (`client/client.py`, `client/network.py`)**: Wrong-PIN reconnect and transient disconnect map retention addressed in `TASK-023`; non-blocking `connect_async`, `PING`/`PONG` keepalive, cross-IP PIN reconnect, `hud_conn_btn`/`hdr_conn_badge` indicators, and transient password retention **addressed in `TASK-030`**.
- **[UX-H10] `controls_tab` Vertical Overflow (`694 > 681`) on `1366x768` & Split Chat/Controls Attention (`client/client.py`)**: Chat unread badge addressed in `TASK-023`; scrollable `controls_canvas` sidebar **addressed in `TASK-030`**.
- **[UX-H11] DM Map Tool Mutual Exclusion, Drag-Paint & Right-Click Drag Ruler (`server/dm_gui.py`, `components/ui_components.py`, `server/map_editor.py`)**: Right-click drag ruler, tool mutual exclusion, `<B1-Motion>` drag-paint, Map Editor Walls/Cover/Doors/Lights/Spawn layers, runtime Map Switcher, and `apply_modern_window_style` Escape-fullscreen-first guard **addressed in `TASK-028` and `TASK-030`**.
- **[UX-H12] Campaign Editor Modal Chains & Read-Only Handout Dialog (`server/campaign_editor_ui.py`, `client/character_creation_wizard.py`)**: Unified Quest status/Faction modals, editable handouts, `DMLiveFlowDialog.share_lore`, and Wizard/Progression improvements **addressed in `TASK-026` and `TASK-030`**.

---

### MEDIUM Issues (Causes Unnecessary Complexity / Visual Friction)

- **[UX-M01] `night_overlay` and `dice_3d` Drift During Canvas Pan (`components/ui_components.py`)**: `_pan_move` and `pan_by` omit `"night_overlay"` and `"dice_3d"` from HUD counter-move tags. **Addressed in `TASK-021`.**
- **[UX-M02] `HexMapCanvas._on_canvas_motion` Rebuilds `hud_coords` Every Pixel & Repeats Failed SRD Lookups (`components/ui_components.py`)**: Caching hovered hex and negative SRD lookups **addressed in `TASK-021`.**
- **[UX-M03] `ToastNotification` Fixed `330x68` Clips Multi-Line Text & Leaves Gaps (`components/ui_components.py`)**: Dynamic height sizing and stack reflow **addressed in `TASK-021`.**
- **[UX-M04] DM Turn Progression Lacks Keyboard Shortcuts (`server/dm_gui.py`)**: Missing `Alt+Right`/`Alt+Left` shortcuts and guarded focus check. **Addressed in `TASK-022`.**
- **[UX-M05] `DM_GUI.roll_all_npcs_initiative` Ignores `get_initiative_bonus()` & `ClientNetworkHandlersMixin.handle_request_initiative` Ignores `get_initiative_bonus()` (`server/dm_gui.py`, `client/network_handlers.py`)**: **Addressed in `TASK-022` and `TASK-023`.**
- **[UX-M06] `open_conditions_dialog` Omits Grappled / Paralyzed / Incapacitated (`server/dm_entity_dialogs.py`)**: **Addressed in `TASK-022`.**
- **[UX-M07] `Spell` Tree Lacks `<Double-1>` Quick Cast & `SpellsPanel` Cast Dialog Divergence (`client/character_sheet_ui.py`)**: `<Double-1>` binding **addressed in `TASK-023`**.
- **[UX-M08] Unbounded `npc_actions_frame` in `DM_GUI`, `HexMapCanvas` `O(N)` `gettags()` Redraw with 3D Dice, `HeroCard` Overflow & `ManualsDialog` Debounce**: Bounded scrollable `npc_actions_canvas` (`TASK-030`), `>4MP` image/tag redraw optimization (`TASK-028`), and debounced `ManualsDialog` search (`TASK-030`) **addressed**.

### LOW Issues (Cosmetic or Minor Consistency)

- **[UX-L01] `LoginDialog` PIN Field Lacks Show/Hide Toggle (`client/login_ui.py`)**: **Addressed in `TASK-021`.**
- **[UX-L02] `DM_GUI.toggle_party_status` Broken String-Split Parsing (`server/dm_gui.py`)**: **Addressed in `TASK-022`.**
- **[UX-L03] `PlayerJournalDialog` Unrendered Markdown in Prose Tab & Missing `Ctrl+S`**, multi-monitor virtual-desktop coordinate clamping in `common/theme.py`, and Markdown/`Ctrl+S` rendering in `PlayerJournalDialog`: **Addressed in `TASK-030`.**

---

## 4. Phase 4.5 Implementation Plan & Verified Delivery (`TASK-021` .. `TASK-024`)

| Task ID | Scope | Target Modules | Status |
| :--- | :--- | :--- | :--- |
| **TASK-021** | Battlemap Token Ownership/Companion Drag, DM Teleport Prevention, HUD Overlay Pan Sync, Canvas Motion Cache, Dynamic Toast Reflow, Localized `askyesno` (`Sì`), `LoginDialog` Clipping/Unlock/PIN Toggle | `components/ui_components.py`, `common/messagebox.py`, `client/login_ui.py`, `client/client.py`, `server/dm_gui.py` | `COMPLETED` |
| **TASK-022** | DM Selected-Combatant Quick Action Bar + `temp_hp`/`full_sheet` Sync, Double-Click Map/Sheet Sync, Left-Click Token Selection, Free Encounter Spawn Hexes, Single-Flow Combat Start Sort Order, Local Party Encounter Math, Turn Shortcuts & Conditions Completeness | `server/dm_gui.py`, `server/dm_entity_dialogs.py`, `server/dm_campaign_session_mixin.py`, `server/encounter_builder_ui.py` | `COMPLETED` |
| **TASK-023** | Player Action Economy Rollback + Non-Blocking Rejection Toasts + Unread Chat Badge, `btn_grapple`/`btn_shove`/`btn_ammo` State & Dynamic Tooltips, Initiative Bonus Fix, Transient Disconnect Map Retention, Weapons Tab Scroll/Off-Hand Bonus Action, `LevelUpDialog` ASI/Subclass/Double-Click UX & Server Companion Movement Routing | `client/client.py`, `client/network_handlers.py`, `client/character_sheet_ui.py`, `client/sheet_panels/combat_panel.py`, `client/progression_ui.py`, `server/rules/movement.py` | `COMPLETED` |
| **TASK-024** | Automated UX/Workflow Regression Tests (`TestPhase45UxAuditAndWorkflows`), Live Tkinter Post-Fix Verification, Bilingual Documentation & Roadmap Sync | `tests/test_gameplay_integration_e2e.py`, `docs/*`, `README*.md` | `COMPLETED` |
| **TASK-025 .. TASK-031** | Phase 5 Responsive Sheet (`[UX-C05]`), Progression/Wizard Authority, Battlemap LoS/FoW & Editor (`[UX-H11]`), 5e Engine Parity, Multiplayer Reconnect/HUD (`[UX-H09]`/`[UX-H10]`)/DM (`[UX-M08]`/`[UX-H12]`)/Secrecy/Tabletop (`[UX-L03]`) & E2E Workflows A–D | `client/`, `server/`, `common/`, `components/`, `tests/`, `docs/*` | `COMPLETED` |

---

## 5. Live Tkinter Post-Fix Verification & Automated Suite Results

Post-fix geometry probes on the `1920 x 1080` Win32 display (isolated temp environment, `DND_MOCK_AUDIO=1`) and full automated suite execution after all Phase 5 code edits (`2026-11-15`):

| Interface / Check | Pre-Fix Measurement | Post-Fix Measurement | Observed Result |
| :--- | :--- | :--- | :--- |
| `main.start_app()` (Launcher) | — | `780 x 550`, `children=1` | Launches cleanly with zero unhandled Tk errors |
| `LoginDialog` (Locked `lock_character=True`) | `520 x 370` (`REQ: 490 x 391`, `-21px`) | `520 x 435` (`REQ: 463 x 393`, `+42px`) | Zero vertical clipping |
| `LoginDialog` (Unlocked List) | `520 x 500` (`REQ: 463 x 483`) | `520 x 520` (`REQ: 463 x 485`, `+35px`) | Fits comfortably with PIN eye toggle & "Cambia Eroe" unlock |
| `DM_GUI` (`1280 x 800`, Combat Tab) | Unbounded `npc_actions_frame` | `right_notebook nb_w: 587`, `npc_actions_canvas=True` | Inline quick bar + bounded scrollable `npc_actions_canvas` (`TASK-030`) |
| `ClientGUI` (`1366 x 768`, Right Panel / Controls) | `CTAB_REQ_H: 694` vs `681` | `right_panel w: 370`, `hud_conn=True`, `controls_canvas items=1` | Persistent connection pill (`[UX-H09]`) & scrollable controls sidebar (`[UX-H10]`) |
| `CharacterSheetUI` (`1024 x 720` / `1366 x 768` / `1920 x 1080`) | `1024 x 720`: `NB_W: 113` (`REQ: 985`) | `1024x720`: `mode=medium`, `nb_w=633`; `1366x768`: `mode=wide4`, `nb_w=576`; `1920x1080`: `mode=wide4`, `nb_w=1090` | `[UX-C05]` resolved across all target desktop resolutions (`errors=0`) |
| **Full Headless Automated Suite** | `610` tests (`64` modules) | **`663` tests (`67` modules) in `62.953s`** | **PASSED (`0` failures, `0` errors, `0` skipped)** including `TestPhase5EndToEndWorkflows` (`4` E2E tests) and `tests/test_task030_*` (`13` tests) |
| **`py_compile` & CI `pyflakes` Check** | `348` non-critical lines | `py_compile`: `178` `.py` files PASS; `pyflakes`: `357` non-critical lines (`CRIT=0`) | **PASSED (`0` undefined names, `0` star imports)** |
